"""
Chatbot Engine for GRESTA (GREST Real-time Engagement Support & Technology Assistant)

This module handles the core chatbot logic:
- Query processing with RAG
- Integration with OpenAI for response generation
- Context management for multi-turn conversations
- Product pricing queries from PostgreSQL
"""

import os
import re
from typing import List, Optional, Tuple

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from knowledge_base import search_knowledge_base, get_knowledge_base_stats
from safety_guardrails import apply_safety_filters, get_system_prompt, filter_response_for_safety, inject_product_links, append_contextual_links
from database import (
    get_products_under_price,
    get_products_in_price_range,
    get_cheapest_product,
    get_all_products_formatted,
    search_products_for_chatbot,
    search_product_by_specs,
    get_product_variants,
    get_storage_options_for_model,
    get_product_specifications,
    compare_products,
    search_products_by_category,
    get_db_session,
    GRESTProduct
)

_openai_client = None

# Session-level product context tracking for multi-turn conversations
# Key: session_id, Value: dict with model, storage, condition, color, last_updated
_session_product_context = {}

def get_session_context(session_id: str) -> dict:
    """Get the product context for a session."""
    return _session_product_context.get(session_id, {})

def update_session_context(session_id: str, model: str = None, storage: str = None, 
                           condition: str = None, color: str = None):
    """Update the product context for a session. Only updates non-None values."""
    if session_id not in _session_product_context:
        _session_product_context[session_id] = {}
    
    ctx = _session_product_context[session_id]
    if model:
        ctx['model'] = model
    if storage:
        ctx['storage'] = storage
    if condition:
        ctx['condition'] = condition
    if color:
        ctx['color'] = color
    
    import time
    ctx['last_updated'] = time.time()

def detect_coreference(message: str) -> bool:
    """Detect if the message contains a co-reference to a previous product."""
    coreference_patterns = [
        r'\bsame\s*(product|model|phone|device|one)?\b',
        r'\bthat\s*(one|product|model|phone)?\b',
        r'\bthis\s*(one|product|model|phone)?\b',
        r'\bwoh\s*wala\b',  # Hinglish: "that one"
        r'\bwahi\b',  # Hinglish: "the same"
        r'\biske\b',  # Hinglish: "of this"
        r'\buska\b',  # Hinglish: "of that"
        r'\bprevious\b',
        r'\babove\b',
        r'\bmentioned\b',
        r'\bit\b(?!\s*is)',  # "it" but not "it is"
    ]
    message_lower = message.lower()
    for pattern in coreference_patterns:
        if re.search(pattern, message_lower):
            return True
    return False

def merge_with_session_context(session_id: str, parsed_model: str, parsed_storage: str, 
                                parsed_condition: str, parsed_color: str = None,
                                message: str = "") -> Tuple[str, str, str, str]:
    """
    Merge parsed query values with session context.
    If message contains co-reference and parsed values are missing, use session context.
    """
    ctx = get_session_context(session_id)
    has_coreference = detect_coreference(message)
    
    final_model = parsed_model
    final_storage = parsed_storage
    final_condition = parsed_condition
    final_color = parsed_color
    
    # If no model detected but has co-reference, use session context
    if not final_model and has_coreference and ctx.get('model'):
        final_model = ctx['model']
        print(f"[Session Context] Using model from context: {final_model}")
    
    # Update session context with new values
    if final_model or final_storage or final_condition or final_color:
        update_session_context(session_id, final_model, final_storage, final_condition, final_color)
    
    return (final_model, final_storage, final_condition, final_color)


def get_iphone_specs_from_db(model_name: str) -> dict:
    """Get specifications for a product from the database (canonical source)."""
    if not model_name:
        return {}
    
    try:
        with get_db_session() as session:
            if not session:
                return {}
            
            # Clean up model name for matching
            model_clean = model_name.replace("Apple ", "").strip()
            
            # Try exact match first (with Apple prefix)
            product = session.query(GRESTProduct).filter(
                GRESTProduct.name == f"Apple {model_clean}"
            ).first()
            
            # If not found, try without Apple prefix
            if not product:
                product = session.query(GRESTProduct).filter(
                    GRESTProduct.name == model_clean
                ).first()
            
            # Fallback to partial match with exact model boundaries
            if not product:
                # Use word boundary matching - avoid matching "iPhone 14" to "iPhone 14 Pro"
                product = session.query(GRESTProduct).filter(
                    GRESTProduct.name.ilike(f"%{model_clean}")
                ).first()
            
            if product and product.specifications:
                specs_data = product.specifications
                if isinstance(specs_data, str):
                    import json
                    specs_data = json.loads(specs_data)
                
                # Extract the 'specs' dict from the specifications JSON
                raw_specs = specs_data.get('specs', {})
                
                if raw_specs:
                    # Normalize keys for consistent display
                    normalized = {}
                    key_mapping = {
                        'display': 'display',
                        'processor': 'processor',
                        'rear camera': 'rear_camera',
                        'front camera': 'front_camera',
                        'water resistance': 'water_resistance',
                        'secure authentication': 'face_id',
                        'battery': 'battery',
                        'operating system': 'os',
                        'sim card': 'sim',
                        'bluetooth': 'bluetooth',
                        'connectors': 'connectors',
                        'storage': 'storage_options',
                        'size and weight': 'size_weight',
                        'network and connectivity': 'network',
                    }
                    for key, value in raw_specs.items():
                        norm_key = key.lower().strip()
                        mapped = key_mapping.get(norm_key, norm_key.replace(' ', '_'))
                        normalized[mapped] = value
                    
                    # Extract 5G info from network field
                    network_info = normalized.get('network', '')
                    if '5g' in network_info.lower():
                        normalized['5g'] = 'Yes'
                    elif network_info:
                        normalized['5g'] = 'No (4G LTE)'
                    
                    # Extract design info from size_weight or connectors if available
                    connectors = normalized.get('connectors', '')
                    if 'titanium' in str(connectors).lower() or 'titanium' in str(normalized.get('size_weight', '')).lower():
                        normalized['design'] = 'Titanium frame'
                    elif 'aluminum' in str(connectors).lower() or 'aluminium' in str(normalized.get('size_weight', '')).lower():
                        normalized['design'] = 'Aluminum frame'
                    else:
                        # Default based on model naming
                        if 'Pro' in model_clean:
                            normalized['design'] = 'Titanium frame' if '15' in model_clean or '16' in model_clean else 'Stainless steel frame'
                        else:
                            normalized['design'] = 'Aluminum frame'
                    
                    return normalized
            
            return {}
    except Exception as e:
        print(f"Error fetching specs from DB: {e}")
        return {}


def get_iphone_specs(model_name: str) -> dict:
    """Get specifications for an iPhone model - reads from database."""
    return get_iphone_specs_from_db(model_name)


def get_openai_client():
    """Lazy initialization of OpenAI client with validation."""
    global _openai_client
    
    if _openai_client is not None:
        return _openai_client
    
    api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    
    if not api_key or not base_url:
        return None
    
    try:
        from openai import OpenAI
        _openai_client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        return _openai_client
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        return None


def is_openai_available() -> bool:
    """Check if OpenAI is properly configured."""
    return get_openai_client() is not None


def is_rate_limit_error(exception: BaseException) -> bool:
    """Check if the exception is a rate limit or quota violation error."""
    error_msg = str(exception)
    return (
        "429" in error_msg
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower()
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, "status_code") and exception.status_code == 429)
    )


def detect_price_query(message: str) -> Tuple[bool, Optional[float], Optional[float], Optional[str]]:
    """
    Detect if the message is asking about pricing/products.
    Returns: (is_price_query, max_price, min_price, category)
    
    Handles queries like:
    - "iPhone under 25000"
    - "sabse sasta iPhone" (cheapest iPhone)
    - "phones between 10000 to 50000"
    - "suggest me an iPhone"
    - "kitne ka hai iPhone 12"
    """
    message_lower = message.lower()
    
    price_keywords = [
        'price', 'cost', 'kitne', 'kitna', 'rupee', 'rs', '₹', 'budget',
        'under', 'below', 'less than', 'within', 'affordable', 'cheap',
        'sasta', 'mehnga', 'expensive', 'range', 'between', 'suggest',
        'recommend', 'best', 'which', 'kaunsa', 'konsa', 'available'
    ]
    
    is_price_query = any(kw in message_lower for kw in price_keywords)
    
    if not is_price_query:
        product_query_patterns = [
            r'iphone\s*\d+',
            r'ipad',
            r'macbook',
            r'do you have',
            r'show me',
            r'list.*products'
        ]
        for pattern in product_query_patterns:
            if re.search(pattern, message_lower):
                is_price_query = True
                break
    
    max_price = None
    min_price = None
    
    price_patterns = [
        r'under\s*(?:rs\.?|₹)?\s*(\d[\d,]*)',
        r'below\s*(?:rs\.?|₹)?\s*(\d[\d,]*)',
        r'less than\s*(?:rs\.?|₹)?\s*(\d[\d,]*)',
        r'within\s*(?:rs\.?|₹)?\s*(\d[\d,]*)',
        r'(?:rs\.?|₹)\s*(\d[\d,]*)\s*(?:ke andar|tak|under)',
        r'(\d[\d,]*)\s*(?:ke andar|tak|rupee|rs)',
        r'budget\s*(?:of|is)?\s*(?:rs\.?|₹)?\s*(\d[\d,]*)',
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, message_lower)
        if match:
            price_str = match.group(1).replace(',', '')
            max_price = float(price_str)
            break
    
    range_patterns = [
        r'between\s*(?:rs\.?|₹)?\s*(\d[\d,]*)\s*(?:to|and|-)\s*(?:rs\.?|₹)?\s*(\d[\d,]*)',
        r'(\d[\d,]*)\s*(?:se|to)\s*(\d[\d,]*)',
    ]
    
    for pattern in range_patterns:
        match = re.search(pattern, message_lower)
        if match:
            min_price = float(match.group(1).replace(',', ''))
            max_price = float(match.group(2).replace(',', ''))
            break
    
    category = None
    if 'iphone' in message_lower:
        category = 'iPhone'
    elif 'ipad' in message_lower:
        category = 'iPad'
    elif 'macbook' in message_lower or 'mac book' in message_lower:
        category = 'MacBook'
    
    if 'sasta' in message_lower or 'cheapest' in message_lower or 'lowest' in message_lower:
        is_price_query = True
    
    return (is_price_query, max_price, min_price, category)


def detect_variant_query(message: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Detect if the message is asking about a specific product variant.
    Returns: (model_name, storage, condition)
    
    Handles queries like:
    - "iPhone 12 128GB price"
    - "iPhone 12 256GB Superb kya price hai"
    - "iPhone 13 Pro Max 512GB Good condition"
    - "iPad Pro 256GB price"
    - "iPhone 12 Pro Max 128GB"
    """
    message_lower = message.lower()
    
    model_pattern = r'(iphone|ipad|macbook)\s*(\d+)?\s*(pro\s*max|pro|mini|air|plus|ultra|se)?'
    model_match = re.search(model_pattern, message_lower)
    
    if not model_match:
        return (None, None, None)
    
    model_parts = []
    device = model_match.group(1).capitalize()
    if device == 'Iphone':
        device = 'iPhone'
    elif device == 'Ipad':
        device = 'iPad'
    elif device == 'Macbook':
        device = 'MacBook'
    model_parts.append(device)
    
    if model_match.group(2):
        model_parts.append(model_match.group(2))
    
    if model_match.group(3):
        variant_type = model_match.group(3).replace('  ', ' ').title()
        model_parts.append(variant_type)
    
    model_name = ' '.join(model_parts)
    
    storage_pattern = r'(\d+)\s*(gb|tb)'
    storage_matches = re.findall(storage_pattern, message_lower)
    storage = None
    if storage_matches:
        for num, unit in storage_matches:
            if num not in model_name:
                storage = f"{num} {unit.upper()}"
                break
    
    condition = None
    if 'superb' in message_lower:
        condition = 'Superb'
    elif 'good' in message_lower:
        condition = 'Good'
    elif 'fair' in message_lower:
        condition = 'Fair'
    
    return (model_name, storage, condition)


def parse_query_with_llm(message: str) -> dict:
    """
    Use LLM to parse natural language queries into structured product intent.
    
    This handles Hinglish, synonyms, and natural language that deterministic
    regex cannot handle:
    - "theek si condition" → Fair
    - "acchi wali" → Good
    - "ekdum mast" → Superb
    - "20000 ke budget mein" → budget_max: 20000
    - "30 se 40 hazar" → budget_min: 30000, budget_max: 40000
    - "neela wala" → color: Blue
    
    Returns:
        dict with keys: model, storage, condition, color, category, budget_min, budget_max, 
                       is_price_query, spec_only, comparison_models
    """
    client = get_openai_client()
    if client is None:
        return None
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a query parser for GREST, an Indian refurbished iPhone/MacBook store.

Extract structured intent from user queries. Output ONLY valid JSON, nothing else.

CONDITION MAPPINGS (Indian/Hinglish to English):
- Fair: theek, theek si, ok ok, chalega, basic, sasti, budget wali, kam price
- Good: acchi, accha, badhiya, decent, theek thaak, normal
- Superb: ekdum, mast, best, top, premium, zabardast, shandar, first class, A1

COLOR MAPPINGS (Indian/Hinglish to English):
- Blue: neela, neeli, blue
- Black: kaala, kaali, black, midnight
- White: safed, white, silver, starlight
- Red: laal, red, product red
- Green: hara, hari, green, alpine green
- Gold: sona, golden, gold
- Purple: jamuni, purple
- Pink: gulabi, pink, rose
- Yellow: peela, yellow
- Desert Titanium: desert, titanium brown
- Natural Titanium: natural, titanium grey
- White Titanium: white titanium

MODEL MAPPINGS:
- iPhone 11, 12, 13, 14, 15, 16 (with Pro, Pro Max, Plus, mini variants)
- MacBook Air, MacBook Pro
- iPad, iPad Pro, iPad Air, iPad mini

CATEGORY (when no specific model):
- iPhone, MacBook, iPad

STORAGE: 64GB, 128GB, 256GB, 512GB, 1TB

BUDGET PARSING:
- "20000 ke andar" → budget_max: 20000
- "30 se 40 hazar" → budget_min: 30000, budget_max: 40000
- "25k tak" → budget_max: 25000
- "lakh" = 100000, "hazar/k" = 1000

OUTPUT FORMAT (JSON only):
{
  "model": "iPhone 12" or null,
  "storage": "128 GB" or null,
  "condition": "Fair" or "Good" or "Superb" or null,
  "color": "Blue" or "Black" or null,
  "category": "iPhone" or "MacBook" or "iPad" or null,
  "budget_min": 30000 or null,
  "budget_max": 40000 or null,
  "is_price_query": true/false,
  "is_cheapest_query": true/false,
  "spec_only": true/false,
  "comparison_models": ["iPhone 15", "iPhone 16"] or null,
  "query_type": "specific_price" | "budget_search" | "cheapest" | "comparison" | "specs" | "general" | "other"
}

EXAMPLES:
Query: "iPhone 16 Pro Max 256GB Blue Superb price"
{"model": "iPhone 16 Pro Max", "storage": "256 GB", "condition": "Superb", "color": "Blue", "category": "iPhone", "budget_min": null, "budget_max": null, "is_price_query": true, "is_cheapest_query": false, "spec_only": false, "comparison_models": null, "query_type": "specific_price"}

Query: "Neela wala iPhone dikhao"
{"model": null, "storage": null, "condition": null, "color": "Blue", "category": "iPhone", "budget_min": null, "budget_max": null, "is_price_query": true, "is_cheapest_query": false, "spec_only": false, "comparison_models": null, "query_type": "budget_search"}

Query: "Cheapest 256GB iPhone"
{"model": null, "storage": "256 GB", "condition": null, "color": null, "category": "iPhone", "budget_min": null, "budget_max": null, "is_price_query": true, "is_cheapest_query": true, "spec_only": false, "comparison_models": null, "query_type": "cheapest"}

Query: "Show specs for iPhone 16 Pro Max"
{"model": "iPhone 16 Pro Max", "storage": null, "condition": null, "color": null, "category": "iPhone", "budget_min": null, "budget_max": null, "is_price_query": false, "is_cheapest_query": false, "spec_only": true, "comparison_models": null, "query_type": "specs"}

Query: "Compare iPhone 15 vs iPhone 16"
{"model": null, "storage": null, "condition": null, "color": null, "category": "iPhone", "budget_min": null, "budget_max": null, "is_price_query": true, "is_cheapest_query": false, "spec_only": false, "comparison_models": ["iPhone 15", "iPhone 16"], "query_type": "comparison"}

Query: "sabse sasta iPad"
{"model": null, "storage": null, "condition": null, "color": null, "category": "iPad", "budget_min": null, "budget_max": null, "is_price_query": true, "is_cheapest_query": true, "spec_only": false, "comparison_models": null, "query_type": "cheapest"}

Query: "MacBook under 80000"
{"model": null, "storage": null, "condition": null, "color": null, "category": "MacBook", "budget_min": null, "budget_max": 80000, "is_price_query": true, "is_cheapest_query": false, "spec_only": false, "comparison_models": null, "query_type": "budget_search"}

Query: "what warranty do you offer"
{"model": null, "storage": null, "condition": null, "color": null, "category": null, "budget_min": null, "budget_max": null, "is_price_query": false, "is_cheapest_query": false, "spec_only": false, "comparison_models": null, "query_type": "other"}"""
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            max_tokens=300,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        
        if result.startswith('```'):
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:]
        result = result.strip()
        
        import json
        parsed = json.loads(result)
        print(f"[Query Parser] '{message}' -> {parsed}")
        return parsed
        
    except Exception as e:
        print(f"[Query Parser] Error: {e}, falling back to regex")
        return None


def get_product_context_with_parsed_intent(message: str, parsed_intent: dict, session_id: str = None) -> str:
    """
    Get product context using LLM-parsed intent for accurate pricing.
    This is the hybrid approach: LLM understands, database provides prices.
    Supports session context for multi-turn conversations.
    """
    if not parsed_intent:
        return get_product_context_from_database(message, session_id)
    
    context_parts = []
    context_parts.append("\n\n=== PRODUCT DATABASE (AUTHORITATIVE PRICING SOURCE) ===")
    context_parts.append("NOTE: Use ONLY these prices. They are current and accurate.")
    context_parts.append("IMPORTANT: You MUST use the EXACT prices shown below. Do not estimate or round.\n")
    
    # Get parsed values
    parsed_model = parsed_intent.get('model')
    parsed_storage = parsed_intent.get('storage')
    parsed_condition = parsed_intent.get('condition')
    parsed_color = parsed_intent.get('color')
    
    # Merge with session context for multi-turn conversations
    if session_id:
        model, storage, condition, color = merge_with_session_context(
            session_id, parsed_model, parsed_storage, parsed_condition, parsed_color, message
        )
    else:
        model, storage, condition, color = parsed_model, parsed_storage, parsed_condition, parsed_color
    
    category = parsed_intent.get('category')
    budget_min = parsed_intent.get('budget_min')
    budget_max = parsed_intent.get('budget_max')
    is_cheapest = parsed_intent.get('is_cheapest_query', False)
    spec_only = parsed_intent.get('spec_only', False)
    comparison_models = parsed_intent.get('comparison_models')
    query_type = parsed_intent.get('query_type', 'other')
    
    if query_type == 'specs' and spec_only and model:
        specs = get_product_specifications(model)
        iphone_specs = get_iphone_specs(model)
        
        if specs or iphone_specs:
            context_parts.append(f"PRODUCT SPECIFICATIONS FOR {specs.get('name', model) if specs else model}:")
            if specs:
                context_parts.append(f"  Category: {specs.get('category', 'iPhone')}")
                if specs.get('price_range'):
                    context_parts.append(f"  Price Range: {specs['price_range']}")
                if specs.get('storage_options'):
                    context_parts.append(f"  Storage Options: {', '.join(specs['storage_options'])}")
                if specs.get('colors'):
                    context_parts.append(f"  Colors: {', '.join(specs['colors'])}")
                if specs.get('conditions'):
                    context_parts.append(f"  Conditions: {', '.join(specs['conditions'])}")
            
            # Always use hardcoded specs for iPhones (database specs are often empty)
            if iphone_specs:
                context_parts.append(f"\n  *** TECHNICAL SPECIFICATIONS (AUTHORITATIVE - USE THESE EXACTLY) ***")
                context_parts.append(f"  - **Display:** {iphone_specs.get('display', 'N/A')}")
                context_parts.append(f"  - **Processor:** {iphone_specs.get('processor', 'N/A')}")
                context_parts.append(f"  - **Rear Camera:** {iphone_specs.get('rear_camera', 'N/A')}")
                context_parts.append(f"  - **Front Camera:** {iphone_specs.get('front_camera', 'N/A')}")
                context_parts.append(f"  - **5G:** {iphone_specs.get('5g', 'N/A')}")
                context_parts.append(f"  - **Design:** {iphone_specs.get('design', 'N/A')}")
                context_parts.append(f"  - **Water Resistance:** {iphone_specs.get('water_resistance', 'N/A')}")
                context_parts.append(f"  *** COPY THESE SPECS EXACTLY - DO NOT MODIFY OR HALLUCINATE ***")
            elif specs.get('specifications'):
                context_parts.append(f"\n  Technical Specifications:")
                for key, value in specs['specifications'].items():
                    context_parts.append(f"    - {key}: {value}")
        else:
            context_parts.append(f"No specifications found for {model}")
        return "\n".join(context_parts)
    
    if query_type == 'comparison' and comparison_models and len(comparison_models) >= 2:
        comparison = compare_products(comparison_models[0], comparison_models[1])
        if comparison:
            context_parts.append(f"PRODUCT COMPARISON:")
            for i, key in enumerate(['model1', 'model2']):
                data = comparison.get(key)
                if data:
                    context_parts.append(f"\n  {comparison_models[i]}:")
                    context_parts.append(f"    Name: {data['name']}")
                    context_parts.append(f"    Price Range: Rs. {int(data['min_price']):,} - Rs. {int(data['max_price']):,}")
                    context_parts.append(f"    Storage: {', '.join(data['storage_options'])}")
                    context_parts.append(f"    Conditions: {', '.join(data['conditions'])}")
                    context_parts.append(f"    Colors: {', '.join(data['colors'][:5])}")
                    context_parts.append(f"    Variants: {data['variant_count']}")
                    context_parts.append(f"    URL: {data['product_url']}")
                else:
                    context_parts.append(f"\n  {comparison_models[i]}: Not available on GREST")
        return "\n".join(context_parts)
    
    if query_type == 'specific_price' and (model or category):
        product = search_product_by_specs(model, storage, condition, color, category)
        
        if product:
            condition_shown = product.get('condition') or 'Unknown'
            storage_shown = product.get('storage') or ''
            is_starting_price = not storage and not condition
            is_out_of_stock = product.get('out_of_stock', False)
            
            if is_out_of_stock:
                context_parts.append(f"PRODUCT FOUND (CURRENTLY OUT OF STOCK):")
                context_parts.append(f"  Model: {product['name']}")
                context_parts.append(f"  Storage: {storage_shown}")
                context_parts.append(f"  Condition: {condition_shown}")
                context_parts.append(f"  PRICE: Rs. {int(product['price']):,}")
                context_parts.append(f"  STATUS: OUT OF STOCK - Tell user to check grest.in for availability")
                context_parts.append(f"  URL: {product['product_url']}")
            elif is_starting_price:
                context_parts.append(f"STARTING PRICE (Lowest in-stock variant):")
                context_parts.append(f"  Model: {product['name']}")
                context_parts.append(f"  Storage: {storage_shown}")
                context_parts.append(f"  Condition: {condition_shown}")
                context_parts.append(f"  PRICE: Rs. {int(product['price']):,} (USE THIS EXACT PRICE)")
                context_parts.append(f"  URL: {product['product_url']}")
            else:
                context_parts.append(f"EXACT MATCH FOUND:")
                context_parts.append(f"  Model: {product['name']}")
                context_parts.append(f"  Storage: {storage_shown}")
                context_parts.append(f"  Condition: {condition_shown}")
                context_parts.append(f"  PRICE: Rs. {int(product['price']):,} (USE THIS EXACT PRICE)")
                context_parts.append(f"  URL: {product['product_url']}")
            if product.get('image_url'):
                context_parts.append(f"  IMAGE: {product['image_url']}")
            
            iphone_specs = get_iphone_specs(product['name'])
            if iphone_specs:
                context_parts.append(f"\n  *** SPECIFICATIONS (MANDATORY - INCLUDE IN RESPONSE) ***")
                context_parts.append(f"  - **Display:** {iphone_specs.get('display', 'N/A')}")
                context_parts.append(f"  - **Processor:** {iphone_specs.get('processor', 'N/A')}")
                context_parts.append(f"  - **Rear Camera:** {iphone_specs.get('rear_camera', 'N/A')}")
                context_parts.append(f"  - **Front Camera:** {iphone_specs.get('front_camera', 'N/A')}")
                context_parts.append(f"  - **5G:** {iphone_specs.get('5g', 'N/A')}")
                context_parts.append(f"  - **Design:** {iphone_specs.get('design', 'N/A')}")
                context_parts.append(f"  *** USE THESE EXACT SPECS IN YOUR RESPONSE ***")
            
            if storage and not condition:
                variants = get_product_variants(model, storage)
                if len(variants) > 1:
                    context_parts.append(f"\n  ALL CONDITIONS FOR {storage}:")
                    for v in variants:
                        context_parts.append(f"    - {v.get('condition', 'Unknown')}: Rs. {int(v['price']):,}")
            elif not storage:
                storage_options = get_storage_options_for_model(model)
                if storage_options:
                    context_parts.append(f"\n  STORAGE OPTIONS AVAILABLE:")
                    context_parts.append(f"    {', '.join(storage_options)}")
        else:
            context_parts.append(f"\n*** CRITICAL: PRODUCT NOT IN DATABASE ***")
            context_parts.append(f"Product: {model}")
            context_parts.append(f"Status: NOT AVAILABLE at GREST")
            context_parts.append(f"\n*** YOU MUST TELL THE USER: ***")
            context_parts.append(f"'Sorry, {model} is not currently available on GREST. Please check grest.in for the latest inventory.'")
            context_parts.append(f"DO NOT invent or guess any price or specifications.")
            context_parts.append(f"DO NOT use your training data for this product's price.")
            context_parts.append(f"*** END CRITICAL INSTRUCTION ***\n")
    
    elif query_type == 'cheapest' or is_cheapest:
        search_category = category if category else ('iPhone' if not model or 'iphone' in (model or '').lower() else None)
        
        if storage or color:
            product = search_product_by_specs(model, storage, condition, color, search_category)
            if product:
                context_parts.append(f"CHEAPEST MATCHING PRODUCT:")
                context_parts.append(f"  Model: {product['name']}")
                context_parts.append(f"  Storage: {product.get('storage', 'N/A')}")
                context_parts.append(f"  Color: {product.get('color', 'N/A')}")
                context_parts.append(f"  Condition: {product.get('condition', 'N/A')}")
                context_parts.append(f"  PRICE: Rs. {int(product['price']):,} (USE THIS EXACT PRICE)")
                context_parts.append(f"  URL: {product['product_url']}")
        else:
            cheapest = get_cheapest_product(search_category)
            if cheapest:
                category_label = search_category if search_category else 'Product'
                context_parts.append(f"CHEAPEST {category_label} AVAILABLE:")
                context_parts.append(f"  Model: {cheapest['name']}")
                context_parts.append(f"  Storage: {cheapest.get('storage', 'N/A')}")
                context_parts.append(f"  Condition: {cheapest.get('condition', 'N/A')}")
                context_parts.append(f"  PRICE: Rs. {int(cheapest['price']):,} (USE THIS EXACT PRICE)")
                context_parts.append(f"  URL: {cheapest['product_url']}")
    
    elif query_type == 'budget_search':
        if budget_min and budget_max:
            products = get_products_in_price_range(budget_min, budget_max, category)
        elif budget_max:
            products = get_products_under_price(budget_max, category)
        else:
            products = []
        
        if condition:
            condition_lower = condition.lower() if condition else ''
            products = [p for p in products if (p.get('condition') or '').lower() == condition_lower]
        
        if color:
            products = [p for p in products if color.lower() in (p.get('color', '') or '').lower()]
        
        if products:
            context_parts.append(f"PRODUCTS MATCHING YOUR CRITERIA:")
            if condition:
                context_parts.append(f"  Condition filter: {condition}")
            if budget_max:
                context_parts.append(f"  Budget: Up to Rs. {int(budget_max):,}")
            if budget_min:
                context_parts.append(f"  Minimum: Rs. {int(budget_min):,}")
            context_parts.append("")
            
            for p in products[:8]:
                variant_info = ""
                if p.get('storage') or p.get('condition'):
                    parts = []
                    if p.get('storage'):
                        parts.append(p['storage'])
                    if p.get('condition'):
                        parts.append(p['condition'])
                    variant_info = f" ({', '.join(parts)})"
                context_parts.append(f"  - {p['name']}{variant_info}: Rs. {int(p['price']):,}")
                context_parts.append(f"    URL: {p['product_url']}")
        else:
            context_parts.append(f"No products found matching criteria.")
            if condition:
                context_parts.append(f"  Condition: {condition}")
            if budget_max:
                context_parts.append(f"  Budget: Rs. {int(budget_max):,}")
            cheapest = get_cheapest_product(None)
            if cheapest:
                context_parts.append(f"\n  Cheapest available: {cheapest['name']} at Rs. {int(cheapest['price']):,}")
    
    elif query_type == 'general' and (model or condition or color):
        if model:
            product = search_product_by_specs(model, storage, condition, color)
            if product:
                context_parts.append(f"SPECIFIC PRODUCT MATCH (use these exact details):")
                context_parts.append(f"  Model: {product['name']}")
                context_parts.append(f"  Storage: {product.get('storage', 'N/A')}")
                context_parts.append(f"  Condition: {product.get('condition', 'N/A')}")
                if product.get('color'):
                    context_parts.append(f"  Color: {product.get('color')}")
                context_parts.append(f"  *** EXACT PRICE: Rs. {int(product['price']):,} ***")
                context_parts.append(f"  URL: {product['product_url']}")
                if product.get('image_url'):
                    context_parts.append(f"  IMAGE: {product['image_url']}")
                context_parts.append(f"\n  CRITICAL: Quote EXACTLY Rs. {int(product['price']):,} - do NOT use 'starting from' or other prices.")
                if color:
                    context_parts.append(f"  NOTE: User asked for {color} color specifically.")
                if condition:
                    context_parts.append(f"  NOTE: User asked for {condition} condition specifically.")
            else:
                context_parts.append(f"\n*** CRITICAL: PRODUCT NOT AVAILABLE ***")
                context_parts.append(f"Product: {model}")
                context_parts.append(f"Status: NOT IN STOCK or NOT AVAILABLE at GREST")
                context_parts.append(f"*** YOU MUST SAY: 'Sorry, {model} is not currently available. Check grest.in for latest inventory.' ***")
                context_parts.append(f"DO NOT guess price. DO NOT use training data.")
        elif condition:
            products = get_products_under_price(500000, None)
            condition_lower = condition.lower() if condition else ''
            products = [p for p in products if (p.get('condition') or '').lower() == condition_lower]
            if products:
                context_parts.append(f"PRODUCTS IN {condition.upper()} CONDITION:")
                for p in products[:5]:
                    context_parts.append(f"  - {p['name']} ({p.get('storage', 'N/A')}): Rs. {int(p['price']):,}")
                    context_parts.append(f"    URL: {p['product_url']}")
    
    elif model or storage or condition or color:
        # Fallback: if we have any product attributes (including from session context), look up the product
        product = search_product_by_specs(model, storage, condition, color)
        if product:
            context_parts.append(f"PRODUCT MATCH (from context):")
            context_parts.append(f"  Model: {product['name']}")
            context_parts.append(f"  Storage: {product.get('storage', 'N/A')}")
            context_parts.append(f"  Condition: {product.get('condition', 'N/A')}")
            if product.get('color'):
                context_parts.append(f"  Color: {product.get('color')}")
            context_parts.append(f"  *** PRICE: Rs. {int(product['price']):,} (USE THIS EXACT PRICE) ***")
            context_parts.append(f"  URL: {product['product_url']}")
            if product.get('image_url'):
                context_parts.append(f"  IMAGE: {product['image_url']}")
        else:
            # Fallback to database context
            return get_product_context_from_database(message, session_id)
    else:
        return get_product_context_from_database(message, session_id)
    
    context_parts.append("\n=== END PRODUCT DATABASE ===")
    context_parts.append("REMINDER: Use the EXACT prices above. Do not estimate or use old prices.\n")
    
    return "\n".join(context_parts)


def get_product_context_from_database(message: str, session_id: str = None) -> str:
    """
    Get product/pricing context from the database based on the user's query.
    Returns formatted string for LLM context injection.
    
    Now supports session context for multi-turn conversations.
    If message contains co-reference (e.g., "same product", "that one") and
    no model is detected, uses the model from session context.
    
    Priority order:
    1. Specific variant queries (iPhone 12 128GB Superb)
    2. Cheapest product queries (sabse sasta iPhone)
    3. Price range queries (iPhone under 25000)
    4. General product listing
    """
    parsed_model, parsed_storage, parsed_condition = detect_variant_query(message)
    is_price_query, max_price, min_price, category = detect_price_query(message)
    
    # Merge with session context for multi-turn conversations
    if session_id:
        model_name, storage, condition, _ = merge_with_session_context(
            session_id, parsed_model, parsed_storage, parsed_condition, None, message
        )
    else:
        model_name, storage, condition = parsed_model, parsed_storage, parsed_condition
    
    context_parts = []
    context_parts.append("\n\n=== PRODUCT DATABASE (AUTHORITATIVE PRICING SOURCE) ===")
    context_parts.append("NOTE: Use ONLY these prices. They are current and accurate.")
    context_parts.append("IMPORTANT: Show the LOWEST in-stock price. Clearly state storage & condition of the shown price.\n")
    
    if model_name:
        product = search_product_by_specs(model_name, storage, condition)
        
        if product:
            condition_shown = product.get('condition') or 'Unknown'
            storage_shown = product.get('storage') or ''
            
            is_starting_price = not storage and not condition
            
            if is_starting_price:
                context_parts.append(f"STARTING PRICE (Lowest in-stock variant):")
            else:
                context_parts.append(f"SPECIFIC PRODUCT MATCH:")
            context_parts.append(f"  Model: {product['name']}")
            context_parts.append(f"  Storage: {storage_shown}")
            context_parts.append(f"  Condition: {condition_shown}")
            if is_starting_price:
                context_parts.append(f"  Starting Price: Rs. {int(product['price']):,}")
            else:
                context_parts.append(f"  Price: Rs. {int(product['price']):,}")
            context_parts.append(f"  URL: {product['product_url']}")
            if product.get('image_url'):
                context_parts.append(f"  IMAGE: {product['image_url']}")
            
            specs = get_iphone_specs(product['name'])
            if specs:
                context_parts.append(f"\n  *** SPECIFICATIONS - YOU MUST INCLUDE THESE EXACT SPECS IN YOUR RESPONSE ***")
                context_parts.append(f"  - **Display:** {specs.get('display', 'N/A')}")
                context_parts.append(f"  - **Processor:** {specs.get('processor', 'N/A')}")
                context_parts.append(f"  - **Rear Camera:** {specs.get('rear_camera', 'N/A')}")
                context_parts.append(f"  - **Front Camera:** {specs.get('front_camera', 'N/A')}")
                context_parts.append(f"  - **5G:** {specs.get('5g', 'N/A')}")
                context_parts.append(f"  - **Design:** {specs.get('design', 'N/A')}")
                context_parts.append(f"  - **Water Resistance:** {specs.get('water_resistance', 'N/A')}")
                context_parts.append(f"  *** COPY THESE SPECS EXACTLY INTO YOUR RESPONSE USING BULLET POINTS ***")
            
            if storage:
                variants = get_product_variants(model_name, storage)
                if len(variants) > 1:
                    context_parts.append(f"\n  OTHER CONDITIONS AVAILABLE FOR {storage}:")
                    for v in variants:
                        if v.get('condition') != condition_shown:
                            context_parts.append(f"    - {v.get('condition', 'Unknown')}: Rs. {int(v['price']):,}")
            else:
                storage_options = get_storage_options_for_model(model_name)
                if storage_options:
                    context_parts.append(f"\n  STORAGE OPTIONS AVAILABLE:")
                    context_parts.append(f"    {', '.join(storage_options)}")
        else:
            context_parts.append(f"\n*** CRITICAL: PRODUCT NOT AVAILABLE ***")
            context_parts.append(f"Product: {model_name}")
            context_parts.append(f"Status: NOT IN STOCK or NOT AVAILABLE at GREST")
            context_parts.append(f"*** YOU MUST SAY: 'Sorry, {model_name} is not currently available. Check grest.in for latest inventory.' ***")
            context_parts.append(f"DO NOT guess price. DO NOT use training data.")
    
    elif 'sasta' in message.lower() or 'cheapest' in message.lower() or 'lowest' in message.lower():
        cheapest = get_cheapest_product(category)
        if cheapest:
            context_parts.append(f"CHEAPEST {'iPhone' if category == 'iPhone' else 'Product'}:")
            context_parts.append(f"  - {cheapest['name']}: Rs. {int(cheapest['price']):,}")
            context_parts.append(f"    URL: {cheapest['product_url']}")
            if cheapest.get('image_url'):
                context_parts.append(f"    IMAGE: {cheapest['image_url']}")
    
    elif min_price and max_price:
        products = get_products_in_price_range(min_price, max_price, category)
        if products:
            context_parts.append(f"Products between Rs. {int(min_price):,} - Rs. {int(max_price):,}:")
            for p in products[:5]:
                variant_info = ""
                if p.get('storage') or p.get('condition'):
                    parts = []
                    if p.get('storage'):
                        parts.append(p['storage'])
                    if p.get('condition'):
                        parts.append(p['condition'])
                    variant_info = f" ({', '.join(parts)})"
                context_parts.append(f"  - {p['name']}{variant_info}: Rs. {int(p['price']):,}")
                context_parts.append(f"    URL: {p['product_url']}")
        else:
            context_parts.append(f"No products found between Rs. {int(min_price):,} - Rs. {int(max_price):,}")
    
    elif max_price:
        products = get_products_under_price(max_price, category)
        if products:
            context_parts.append(f"Products under Rs. {int(max_price):,}:")
            for p in products[:5]:
                discount_text = f" (Save {p['discount_percent']}%)" if p.get('discount_percent') else ""
                variant_info = ""
                if p.get('storage') or p.get('condition'):
                    parts = []
                    if p.get('storage'):
                        parts.append(p['storage'])
                    if p.get('condition'):
                        parts.append(p['condition'])
                    variant_info = f" ({', '.join(parts)})"
                context_parts.append(f"  - {p['name']}{variant_info}: Rs. {int(p['price']):,}{discount_text}")
                context_parts.append(f"    URL: {p['product_url']}")
        else:
            cheapest = get_cheapest_product(category)
            if cheapest:
                context_parts.append(f"No products under Rs. {int(max_price):,}.")
                context_parts.append(f"Cheapest option: {cheapest['name']} at Rs. {int(cheapest['price']):,}")
    
    elif is_price_query:
        all_products = get_all_products_formatted()
        context_parts.append(all_products)
    else:
        return ""
    
    context_parts.append("\n=== END PRODUCT DATABASE ===\n")
    
    return "\n".join(context_parts)


def should_trigger_web_search(message: str) -> Tuple[bool, str, str]:
    """
    Determine if GRESTA should perform a web search.
    This is GRESTA's decision, not triggered by user request.
    
    Returns: (should_search, search_query, search_category)
    
    Categories that trigger web search:
    1. Trust/reviews: Trustpilot, Mouthshut, reviews, ratings
    2. Competitor comparison: Cashify, other refurb sellers, why GREST
    3. Product comparison with NON-GREST products: iPhone vs Realme, Samsung, OnePlus, etc.
    4. Specifications of non-Apple products
    """
    message_lower = message.lower()
    
    non_apple_brands = [
        'realme', 'samsung', 'oneplus', 'one plus', 'xiaomi', 'redmi', 'poco',
        'vivo', 'oppo', 'motorola', 'moto', 'nokia', 'google pixel', 'pixel',
        'nothing', 'iqoo', 'tecno', 'infinix', 'asus', 'rog', 'huawei', 'honor',
        'mi ', 'note ', 'galaxy', 'a52', 'a53', 'a54', 's21', 's22', 's23', 's24'
    ]
    
    has_non_apple = any(brand in message_lower for brand in non_apple_brands)
    
    if has_non_apple:
        if re.search(r'(vs|versus|compare|comparison|difference|better|or)\b', message_lower):
            return (True, f"{message} comparison specifications features India", "external_product_comparison")
        
        if re.search(r'(spec|specification|feature|camera|display|battery|price)', message_lower):
            return (True, f"{message} specifications features India 2024", "external_product_specs")
    
    trust_keywords = [
        'trust', 'trustpilot', 'mouthshut', 'review', 'rating', 'ratings',
        'reliable', 'genuine', 'fake', 'scam', 'fraud', 'legitimate',
        'bharosa', 'vishwas', 'reputation', 'feedback', 'experience',
        'safe to buy', 'is grest good', 'grest review'
    ]
    
    if any(kw in message_lower for kw in trust_keywords):
        return (True, "GREST grest.in reviews ratings customer feedback India 2024", "trust_verification")
    
    competitor_keywords = [
        'cashify', 'togofogo', 'yaantra', 'budli', 'quikr', 'olx',
        'other seller', 'competitor', 'vs other', 'dusra seller',
        'why grest', 'why should i buy from grest', 'better than',
        'kyon grest', 'grest kyun', 'grest se kyun', 'why not'
    ]
    
    if any(kw in message_lower for kw in competitor_keywords):
        competitor = "cashify" if "cashify" in message_lower else "refurbished phone sellers"
        return (True, f"GREST vs {competitor} comparison refurbished phones India reviews 2024", "competitor_comparison")
    
    if re.search(r'(iphone|ipad|macbook).*(vs|versus|compare|difference|better).*(iphone|ipad|macbook)', message_lower):
        return (True, f"{message} comparison specifications features", "apple_product_comparison")
    
    if re.search(r'difference between.*and|compare.*with|which is better', message_lower):
        return (True, f"{message} comparison specifications", "product_comparison")
    
    non_grest_specs = re.search(
        r'(specs?|specifications?|features?)\s*(of|for)?\s*(realme|samsung|oneplus|xiaomi|redmi|poco|vivo|oppo|motorola|nokia|pixel)',
        message_lower
    )
    if non_grest_specs:
        return (True, f"{message} specifications features India 2024", "external_product_specs")
    
    return (False, "", "")


def perform_web_search(query: str, category: str) -> str:
    """
    Perform a real web search using Serper.dev API.
    Returns formatted search results for LLM context.
    
    Use Cases:
    1. Product comparison with non-GREST products (iPhone vs Realme, Samsung, etc.)
    2. Specifications of products not in GREST database
    3. Competitor comparisons (GREST vs Cashify, Togofogo, etc.)
    4. External reviews and trust verification
    """
    try:
        import requests
        
        api_key = os.environ.get("SERPER_API_KEY")
        if not api_key:
            print("[Web Search] SERPER_API_KEY not configured")
            return ""
        
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "gl": "in",
            "hl": "en",
            "num": 5
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code != 200:
            print(f"[Web Search] Serper API returned status {response.status_code}: {response.text}")
            return ""
        
        data = response.json()
        results = []
        
        if data.get("answerBox"):
            box = data["answerBox"]
            if box.get("answer"):
                results.append(f"**Quick Answer**: {box['answer']}")
            elif box.get("snippet"):
                results.append(f"**Quick Answer**: {box['snippet']}")
        
        organic = data.get("organic", [])
        if organic:
            results.append("\n**Search Results**:")
            for i, item in enumerate(organic[:5], 1):
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                results.append(f"{i}. **{title}**")
                results.append(f"   {snippet}")
                if link:
                    results.append(f"   Source: {link}")
        
        if not results:
            print(f"[Web Search] No results from Serper for: {query}")
            return ""
        
        search_results = f"""
=== WEB SEARCH RESULTS (Live from Google) ===
Search Query: {query}
Category: {category}

{chr(10).join(results)}

Note: GRESTA searched this automatically to help answer your question. For GREST-specific policies, refer to our official information.
=== END WEB SEARCH RESULTS ===
"""
        print(f"[Web Search] Successfully retrieved {len(organic)} results for: {query}")
        return search_results
        
    except requests.exceptions.Timeout:
        print(f"[Web Search] Timeout for query: {query}")
        return ""
    except Exception as e:
        print(f"[Web Search] Error: {e}")
        return ""


def get_web_search_context(message: str) -> str:
    """
    Check if web search is needed and return search results context.
    This implements the guardrails - GRESTA decides when to search.
    
    GUARDRAILS:
    - Only search for: trust verification, competitor comparison, product specs
    - Never search for: medical, financial, legal, personal information
    - User cannot trigger search directly (only GRESTA decides)
    """
    should_search, search_query, category = should_trigger_web_search(message)
    
    if not should_search:
        return ""
    
    forbidden_topics = ['medical', 'doctor', 'medicine', 'legal', 'lawyer', 'financial', 'investment']
    if any(topic in message.lower() for topic in forbidden_topics):
        return ""
    
    print(f"[Web Search] Triggered for category: {category}, query: {search_query}")
    
    if category == "trust_verification":
        grest_info = """
=== GREST OFFICIAL INFORMATION (VERIFIED) ===
GREST (grest.in) is a legitimate refurbished electronics seller in India:
- Registered company: Radical Aftermarket Services Pvt. Ltd.
- CIN: U74999HR2018PTC076488
- GSTIN: 06AAJCR2110E1ZX
- Office: Gurugram, Haryana

Trust Signals:
- 50+ quality checks on every device
- 6-month warranty (extendable to 12 months for Rs. 1,499)
- 7-day return policy
- COD available across India

Review Links:
- Trustpilot: https://www.trustpilot.com/review/grest.in
- Mouthshut: https://www.mouthshut.com/product-reviews/Grest-in-reviews-926089093
=== END OFFICIAL INFO ===
"""
        live_search = perform_web_search(search_query, category)
        return grest_info + (live_search if live_search else "")
    
    elif category == "competitor_comparison":
        grest_advantages = """
=== GREST ADVANTAGES (OFFICIAL) ===
1. 50+ Quality Checks on every device
2. 6-month warranty (extendable to 12 months for Rs. 1,499)
3. 7-day hassle-free return policy
4. COD available across India
5. Free delivery
6. Premium replacement batteries
7. In-house expert technicians
8. Focus exclusively on Apple products (deep expertise)
=== END GREST ADVANTAGES ===
"""
        live_search = perform_web_search(search_query, category)
        return grest_advantages + (live_search if live_search else "")
    
    elif category in ["external_product_comparison", "external_product_specs", "apple_product_comparison", "product_comparison"]:
        live_search = perform_web_search(search_query, category)
        if live_search:
            return live_search
        return f"""
=== PRODUCT COMPARISON CONTEXT ===
For detailed Apple product comparisons, GRESTA can provide general specification differences.
For specific GREST pricing on available models, refer to the PRODUCT DATABASE section.

Note: Specifications are based on official Apple data. Availability and pricing at GREST may vary.
=== END COMPARISON ===
"""
    
    elif category == "product_specs":
        from database import get_product_with_specs
        product = get_product_with_specs(search_query)
        if product and product.get('specs'):
            specs = product['specs']
            context = f"""
=== PRODUCT SPECIFICATIONS FROM GREST DATABASE (AUTHORITATIVE) ===
Product: {product['name']}
Price: Rs. {int(product['price']):,} (MRP: Rs. {int(product['original_price']):,}) - Save {product.get('discount_percent', 0)}%
URL: {product.get('product_url', '')}
Warranty: {product.get('warranty_months', 6)} months

SPECIFICATIONS:
"""
            ignore_keys = ['Case', 'Charging', 'Screenprotector', 'Protection Variant', 'Meta Description']
            for key, value in specs.items():
                if key not in ignore_keys and value and not str(value).isdigit():
                    context += f"  - {key}: {value}\n"
            context += "\n=== END SPECIFICATIONS ===\n"
            return context
        
        live_search = perform_web_search(search_query, category)
        if live_search:
            return live_search
        return ""
    
    return ""


def get_source_authority_level(source: str) -> tuple:
    """
    Assign authority level to sources. Lower number = higher authority.
    Returns (authority_level, source_type_label).
    
    Authority Hierarchy:
    1. GREST official policy documents (warranty, refund, shipping policies)
    2. Official FAQ page
    3. Contact info and about pages
    4. Custom knowledge base documents (curated by admin)
    5. Product collection pages
    6. Individual product pages (least authoritative - may have simplified info)
    """
    source_lower = source.lower()
    
    # Level 1: Official policy documents (MOST AUTHORITATIVE)
    if any(x in source_lower for x in ['warranty_policy', 'grest_warranty', 'refund_policy', 'shipping_policy']):
        return (1, "OFFICIAL POLICY - HIGHEST AUTHORITY")
    if '/policies/' in source_lower or '/pages/warranty' in source_lower:
        return (1, "OFFICIAL POLICY - HIGHEST AUTHORITY")
    
    # Level 2: FAQ page (official answers)
    if '/pages/faq' in source_lower or 'faqs' in source_lower:
        return (2, "OFFICIAL FAQ")
    
    # Level 3: Contact and about pages
    if any(x in source_lower for x in ['contact', 'about', 'grest_contact']):
        return (3, "OFFICIAL INFO")
    
    # Level 4: Curated knowledge base docs
    if source_lower.endswith('.txt') and 'grest_' in source_lower:
        return (4, "CURATED DOCUMENT")
    
    # Level 5: Collection pages
    if '/collections/' in source_lower:
        return (5, "PRODUCT COLLECTION")
    
    # Level 6: Individual product pages (LEAST AUTHORITATIVE for policies)
    if '/products/' in source_lower:
        return (6, "PRODUCT PAGE - may contain simplified info")
    
    # Default: Unknown source
    return (7, "GENERAL INFO")


def format_context_from_docs(documents: List[dict]) -> str:
    """
    Format retrieved documents into context for the LLM.
    Aggregates chunks by source URL and sorts by authority level.
    Higher authority sources appear first with clear labels.
    """
    if not documents:
        return "No relevant information found in the knowledge base."
    
    # Aggregate chunks by source URL with authority info
    source_data = {}
    for doc in documents:
        source = doc.get("source", "Unknown source")
        content = doc.get("content", "")
        
        if source not in source_data:
            authority_level, authority_label = get_source_authority_level(source)
            source_data[source] = {
                'contents': [],
                'authority_level': authority_level,
                'authority_label': authority_label
            }
        source_data[source]['contents'].append(content)
    
    # Sort by authority level (lower = more authoritative)
    sorted_sources = sorted(source_data.items(), key=lambda x: x[1]['authority_level'])
    
    # Format with authority labels
    context_parts = []
    for i, (source, data) in enumerate(sorted_sources, 1):
        combined_content = "\n\n".join(data['contents'])
        authority_label = data['authority_label']
        context_parts.append(f"[Source {i} - {authority_label}: {source}]\n{combined_content}")
    
    return "\n\n---\n\n".join(context_parts)


def format_conversation_history(messages: List[dict]) -> List[dict]:
    """Format conversation history for the API call."""
    formatted = []
    for msg in messages[-6:]:
        if msg.get("role") in ["user", "assistant", "system"]:
            formatted.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    return formatted


def build_context_aware_query(user_message: str, conversation_history: List[dict] = None) -> str:
    """
    Build a search query that includes context from conversation history.
    This helps with follow-up questions like "tell me more about that program".
    
    Uses robust detection that handles:
    - Typos (e.g., "programm", "progam")
    - Various follow-up patterns
    - Short queries that reference previous context
    """
    if not conversation_history:
        return user_message
    
    product_names = [
        "iPhone 12", "iPhone 13", "iPhone 14", "iPhone 15",
        "iPhone 12 Pro", "iPhone 13 Pro", "iPhone 14 Pro", "iPhone 15 Pro",
        "iPhone 12 Pro Max", "iPhone 13 Pro Max", "iPhone 14 Pro Max", "iPhone 15 Pro Max",
        "MacBook Air", "MacBook Pro", "MacBook Air M1", "MacBook Air M2",
        "MacBook Pro M1", "MacBook Pro M2", "refurbished", "warranty"
    ]
    
    message_lower = user_message.lower()
    
    follow_up_indicators = [
        "this", "that", "it", "the product", "the phone", "the macbook",
        "more details", "more information", "tell me more",
        "details", "about it", "learn more", "know more",
        "give me", "share more", "explain", "what is it",
        "how does it", "how much", "price", "cost", "specs",
        "buy", "order", "purchase", "warranty", "delivery"
    ]
    
    product_typo_patterns = ["iphone", "macbook", "phone", "laptop", "product"]
    
    has_follow_up = any(phrase in message_lower for phrase in follow_up_indicators)
    has_product_reference = any(pattern in message_lower for pattern in product_typo_patterns)
    is_short_query = len(user_message.split()) <= 8
    
    should_add_context = has_follow_up or (has_product_reference and is_short_query)
    
    if not should_add_context:
        return user_message
    
    recent_products = []
    for msg in reversed(conversation_history[-6:]):
        content = msg.get("content", "")
        for product in product_names:
            if product.lower() in content.lower():
                if product not in recent_products:
                    recent_products.append(product)
    
    if recent_products:
        context_str = " ".join(recent_products[:3])
        return f"{user_message} {context_str}"
    
    return user_message


def fix_typos_with_llm(user_message: str) -> str:
    """
    Use GPT-3.5-turbo to fix typos in user message before processing.
    
    This is a fast, lightweight call that:
    - Corrects spelling mistakes
    - Preserves original intent and meaning
    - Does NOT change the language or add/remove content
    
    Returns the original message if LLM is unavailable or on error.
    """
    if len(user_message.strip()) < 3:
        return user_message
    
    client = get_openai_client()
    if client is None:
        return user_message
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a typo correction assistant. Your ONLY job is to fix spelling mistakes.

RULES:
1. Fix spelling errors and typos
2. DO NOT change the meaning or intent
3. DO NOT add or remove words
4. DO NOT change the language
5. DO NOT add punctuation unless fixing obvious errors
6. Return ONLY the corrected text, nothing else

Examples:
Input: "plese give me detials of this programm"
Output: "please give me details of this program"

Input: "waht is beynd the hustle"
Output: "what is beyond the hustle"

Input: "tell me abot balace mastery"
Output: "tell me about balance mastery"

Input: "hi how are you"
Output: "hi how are you" (no changes needed)"""
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            max_tokens=200,
            temperature=0
        )
        
        corrected = response.choices[0].message.content.strip()
        
        if corrected and len(corrected) < len(user_message) * 3:
            if corrected.lower() != user_message.lower():
                print(f"[Typo Fixer] '{user_message}' -> '{corrected}'")
            return corrected
        
        return user_message
        
    except Exception as e:
        print(f"[Typo Fixer] Error: {e}, using original message")
        return user_message


def generate_response(
    user_message: str,
    conversation_history: List[dict] = None,
    n_context_docs: int = 8,
    user_name: str = None,
    is_returning_user: bool = False,
    last_topic_summary: str = None,
    session_id: str = None
) -> dict:
    """
    Generate a response to the user's message using RAG.
    
    Args:
        user_message: The user's question
        conversation_history: Previous messages in the conversation
        n_context_docs: Number of context documents to retrieve
        user_name: User's first name for personalized greeting
        is_returning_user: Whether this is a returning user
        last_topic_summary: Summary of user's last conversation topic (for returning users)
    
    Returns:
        dict with 'response', 'sources', and 'safety_triggered' keys
    """
    client = get_openai_client()
    if client is None:
        return {
            "response": "I'm temporarily unavailable. Please try again later or contact us at https://grest.in/pages/contact-us for assistance.",
            "sources": [],
            "safety_triggered": False,
            "error": "openai_not_configured"
        }
    
    should_redirect, redirect_response = apply_safety_filters(user_message)
    
    if should_redirect:
        return {
            "response": redirect_response,
            "sources": [],
            "safety_triggered": True,
            "safety_category": "safety_redirect"
        }
    
    search_query = build_context_aware_query(user_message, conversation_history)
    relevant_docs = search_knowledge_base(search_query, n_results=n_context_docs)
    context = format_context_from_docs(relevant_docs)
    
    parsed_intent = parse_query_with_llm(user_message)
    
    should_use_hybrid = (
        parsed_intent and (
            parsed_intent.get('is_price_query') or
            parsed_intent.get('condition') or
            parsed_intent.get('budget_max') or
            parsed_intent.get('budget_min') or
            parsed_intent.get('is_cheapest_query') or
            parsed_intent.get('storage') or  # Use hybrid when storage is detected (LLM parsing)
            parsed_intent.get('model') or    # Use hybrid when model is detected
            parsed_intent.get('color')       # Use hybrid when color is detected
        )
    )
    
    if should_use_hybrid:
        product_context = get_product_context_with_parsed_intent(user_message, parsed_intent, session_id)
    else:
        product_context = get_product_context_from_database(user_message, session_id)
    
    web_search_context = get_web_search_context(user_message)
    
    system_prompt = get_system_prompt()
    
    personalization_context = ""
    if user_name:
        personalization_context = f"\nUSER CONTEXT:\nThe user's name is {user_name}. Address them by name naturally."
        if is_returning_user and last_topic_summary:
            personalization_context += f"""

**** CRITICAL RETURNING USER INSTRUCTION ****
This user has spoken with you before. You MUST greet them with specific details from their previous conversation.

PREVIOUS CONVERSATION SUMMARY:
{last_topic_summary}

YOUR GREETING MUST INCLUDE:
1. Their name ({user_name})
2. Acknowledge you remember them ("Great to see you back!" or similar)
3. SPECIFICALLY mention what they shared from the summary above
4. Ask if they want to continue where they left off

DO NOT give a generic greeting like "How can I help you today?" 
DO mention their specific issues and programs from the summary.
**** END CRITICAL INSTRUCTION ****
"""
        elif is_returning_user:
            personalization_context += f"""
This is a returning user but you have NO RECORD of their previous conversation topics.
Welcome them back warmly and ask how you can help today.
DO NOT mention any specific topics like "stress", "career", "relationships" or any programs as if you discussed them before.
ONLY say something like: "Great to see you back! How can I help you today?"
"""
    
    augmented_system_prompt = f"""{system_prompt}
{personalization_context}

KNOWLEDGE BASE CONTEXT:
The following information is from GREST's official website and documents. Multiple sources may contain relevant information about the same topic.

{context}
{product_context}
{web_search_context}

MULTI-SOURCE SYNTHESIS INSTRUCTIONS:
1. Sources are listed in ORDER OF AUTHORITY - "OFFICIAL POLICY" and "OFFICIAL FAQ" sources are MORE RELIABLE than "PRODUCT PAGE" sources
2. If sources have CONFLICTING information (e.g., different warranty durations), ALWAYS TRUST the higher authority source
   - Example: If warranty policy says "6 months" but product page says "12 months", USE "6 months" from the policy
3. Synthesize information from ALL sources, but when conflicts exist, the HIGHEST AUTHORITY source wins
4. For policies (warranty, refund, shipping), ONLY use information from "OFFICIAL POLICY" or "OFFICIAL FAQ" sources
5. Product pages may contain simplified or outdated information - defer to official policies
6. At the end, cite the primary authoritative source(s) that answered the question

CRITICAL PRICING AND SPECS INSTRUCTIONS:
- If "PRODUCT DATABASE" section is provided above, use ONLY those prices - they are current and accurate
- The Product Database prices override any pricing from other sources (website scrapes may be outdated)
- When recommending products by price, list the specific products from the database with their exact prices
- Always include the product URL so users can purchase directly
- MANDATORY: If SPECIFICATIONS are provided in the database context, you MUST include them in your response using bullet points
- Copy the exact specs (Display, Processor, Camera, 5G, Design) - DO NOT say "not specified"

IMPORTANT: Only use information from the context above. If the answer is not in the context, politely say you don't have that specific information and offer to help them contact us at https://grest.in/pages/contact-us"""

    messages = [{"role": "system", "content": augmented_system_prompt}]
    
    if conversation_history:
        formatted_history = format_conversation_history(conversation_history)
        messages.extend(formatted_history)
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_completion_tokens=1024
        )
        
        assistant_message = response.choices[0].message.content
        
        filtered_response, was_filtered = filter_response_for_safety(assistant_message)
        
        response_with_product_links = inject_product_links(filtered_response)
        
        final_response = append_contextual_links(user_message, response_with_product_links)
        
        sources = []
        for doc in relevant_docs:
            source = doc.get("source", "Unknown")
            if source not in sources:
                sources.append(source)
        
        return {
            "response": final_response,
            "sources": sources[:3],
            "safety_triggered": was_filtered,
            "safety_category": "output_filtered" if was_filtered else None
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error generating response: {error_msg}")
        
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            return {
                "response": "I'm experiencing high demand right now. Please try again in a moment.",
                "sources": [],
                "safety_triggered": False,
                "error": "rate_limit"
            }
        
        return {
            "response": "I apologize, but I'm having trouble processing your question right now. Please try again, or contact us at https://grest.in/pages/contact-us for assistance.",
            "sources": [],
            "safety_triggered": False,
            "error": str(e)
        }


def generate_response_stream(
    user_message: str,
    conversation_history: List[dict] = None,
    n_context_docs: int = 8,
    user_name: str = None,
    is_returning_user: bool = False,
    last_topic_summary: str = None,
    session_id: str = None
):
    """
    Generate a streaming response to the user's message using RAG.
    
    Yields chunks of text as they are generated by the LLM.
    Final yield is a special dict with metadata (sources, etc).
    """
    client = get_openai_client()
    if client is None:
        yield {"type": "error", "content": "I'm temporarily unavailable. Please try again later."}
        return
    
    should_redirect, redirect_response = apply_safety_filters(user_message)
    
    if should_redirect:
        yield {"type": "content", "content": redirect_response}
        yield {"type": "done", "sources": [], "safety_triggered": True}
        return
    
    search_query = build_context_aware_query(user_message, conversation_history)
    relevant_docs = search_knowledge_base(search_query, n_results=n_context_docs)
    context = format_context_from_docs(relevant_docs)
    
    parsed_intent = parse_query_with_llm(user_message)
    
    should_use_hybrid = (
        parsed_intent and (
            parsed_intent.get('is_price_query') or
            parsed_intent.get('condition') or
            parsed_intent.get('budget_max') or
            parsed_intent.get('budget_min') or
            parsed_intent.get('is_cheapest_query') or
            parsed_intent.get('storage') or  # Use hybrid when storage is detected (LLM parsing)
            parsed_intent.get('model') or    # Use hybrid when model is detected
            parsed_intent.get('color')       # Use hybrid when color is detected
        )
    )
    
    if should_use_hybrid:
        product_context = get_product_context_with_parsed_intent(user_message, parsed_intent, session_id)
    else:
        product_context = get_product_context_from_database(user_message, session_id)
    
    web_search_context = get_web_search_context(user_message)
    
    system_prompt = get_system_prompt()
    
    personalization_context = ""
    if user_name:
        personalization_context = f"\nUSER CONTEXT:\nThe user's name is {user_name}. Address them by name naturally."
        if is_returning_user and last_topic_summary:
            personalization_context += f"""

**** CRITICAL RETURNING USER INSTRUCTION ****
This user has spoken with you before. You MUST greet them with specific details from their previous conversation.

PREVIOUS CONVERSATION SUMMARY:
{last_topic_summary}

YOUR GREETING MUST INCLUDE:
1. Their name ({user_name})
2. Acknowledge you remember them ("Great to see you back!" or similar)
3. SPECIFICALLY mention what they shared from the summary above
4. Ask if they want to continue where they left off

DO NOT give a generic greeting like "How can I help you today?" 
DO mention their specific issues and programs from the summary.
**** END CRITICAL INSTRUCTION ****
"""
        elif is_returning_user:
            personalization_context += f"""
This is a returning user but you have NO RECORD of their previous conversation topics.
Welcome them back warmly and ask how you can help today.
DO NOT mention any specific topics like "stress", "career", "relationships" or any programs as if you discussed them before.
ONLY say something like: "Great to see you back! How can I help you today?"
"""
    
    augmented_system_prompt = f"""{system_prompt}
{personalization_context}

KNOWLEDGE BASE CONTEXT:
The following information is from GREST's official website and documents. Multiple sources may contain relevant information about the same topic.

{context}
{product_context}
{web_search_context}

MULTI-SOURCE SYNTHESIS INSTRUCTIONS:
1. Sources are listed in ORDER OF AUTHORITY - "OFFICIAL POLICY" and "OFFICIAL FAQ" sources are MORE RELIABLE than "PRODUCT PAGE" sources
2. If sources have CONFLICTING information (e.g., different warranty durations), ALWAYS TRUST the higher authority source
   - Example: If warranty policy says "6 months" but product page says "12 months", USE "6 months" from the policy
3. Synthesize information from ALL sources, but when conflicts exist, the HIGHEST AUTHORITY source wins
4. For policies (warranty, refund, shipping), ONLY use information from "OFFICIAL POLICY" or "OFFICIAL FAQ" sources
5. Product pages may contain simplified or outdated information - defer to official policies
6. At the end, cite the primary authoritative source(s) that answered the question

CRITICAL PRICING AND SPECS INSTRUCTIONS:
- If "PRODUCT DATABASE" section is provided above, use ONLY those prices - they are current and accurate
- The Product Database prices override any pricing from other sources (website scrapes may be outdated)
- When recommending products by price, list the specific products from the database with their exact prices
- Always include the product URL so users can purchase directly
- MANDATORY: If SPECIFICATIONS are provided in the database context, you MUST include them in your response using bullet points
- Copy the exact specs (Display, Processor, Camera, 5G, Design) - DO NOT say "not specified"

IMPORTANT: Only use information from the context above. If the answer is not in the context, politely say you don't have that specific information and offer to help them contact us at https://grest.in/pages/contact-us"""

    messages = [{"role": "system", "content": augmented_system_prompt}]
    
    if conversation_history:
        formatted_history = format_conversation_history(conversation_history)
        messages.extend(formatted_history)
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_completion_tokens=1024,
            stream=True
        )
        
        full_response = ""
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    full_response += content
                    yield {"type": "content", "content": content}
        
        filtered_response, was_filtered = filter_response_for_safety(full_response)
        response_with_links = inject_product_links(filtered_response)
        final_response = append_contextual_links(user_message, response_with_links)
        
        sources = []
        for doc in relevant_docs:
            source = doc.get("source", "Unknown")
            if source not in sources:
                sources.append(source)
        
        yield {
            "type": "done",
            "full_response": final_response,
            "sources": sources[:3],
            "safety_triggered": was_filtered
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error in streaming response: {error_msg}")
        
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            yield {"type": "error", "content": "I'm experiencing high demand right now. Please try again in a moment."}
        else:
            yield {"type": "error", "content": "I apologize, but I'm having trouble processing your question. Please try again."}


def get_greeting_message() -> str:
    """Return the initial greeting message for new conversations."""
    return """Namaste! I'm GRESTA — your friendly assistant for GREST, India's trusted destination for premium refurbished iPhones and MacBooks!

Main kaise help kar sakti hoon? I can assist you with:
- iPhone collection (12, 13, 14, 15 series)
- MacBook options (Air M1/M2, Pro)
- Warranty & quality details (12-month warranty, 50+ checks)
- Order tracking & delivery info
- EMI & payment options

Kya dekhna chahenge aaj?"""


def check_knowledge_base_status() -> dict:
    """Check if the knowledge base is ready."""
    stats = get_knowledge_base_stats()
    return {
        "ready": stats["total_chunks"] > 0,
        "chunks": stats["total_chunks"],
        "last_updated": stats.get("last_scrape")
    }


def generate_conversation_summary(conversation_history: List[dict]) -> dict:
    """
    Generate a structured summary of the conversation using LLM.
    Extracts emotional themes, recommended programs, and last topics.
    """
    client = get_openai_client()
    if not client or not conversation_history:
        return None
    
    history_text = ""
    for msg in conversation_history[-10:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_text += f"{role.upper()}: {content}\n\n"
    
    summary_prompt = """Analyze this conversation and extract key information in a structured format.

CONVERSATION:
{history}

Respond in this EXACT format (use "None" if not applicable):
INTERESTS: [List any products or features the user showed interest in, e.g., "iPhone 14 Pro", "MacBook Air M2", "warranty information"]
RECOMMENDED_PRODUCTS: [List any GREST products mentioned as recommendations, e.g., "iPhone 15", "MacBook Pro M2"]
LAST_TOPICS: [Summarize in 1-2 sentences what the conversation was about]
CONVERSATION_STATUS: [One of: "exploring products", "asked about warranty", "asked for pricing", "general inquiry", "ready to purchase"]

Be concise. Focus on the most important product interests and recommendations."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a conversation analyzer. Extract key themes from conversations accurately and concisely."},
                {"role": "user", "content": summary_prompt.format(history=history_text)}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        summary_text = response.choices[0].message.content.strip()
        
        result = {
            'emotional_themes': None,
            'recommended_programs': None,
            'last_topics': None,
            'conversation_status': None
        }
        
        for line in summary_text.split('\n'):
            line = line.strip()
            if line.startswith('EMOTIONAL_THEMES:'):
                value = line.replace('EMOTIONAL_THEMES:', '').strip()
                if value.lower() != 'none' and value != '[]':
                    result['emotional_themes'] = value
            elif line.startswith('RECOMMENDED_PROGRAMS:'):
                value = line.replace('RECOMMENDED_PROGRAMS:', '').strip()
                if value.lower() != 'none' and value != '[]':
                    result['recommended_programs'] = value
            elif line.startswith('LAST_TOPICS:'):
                value = line.replace('LAST_TOPICS:', '').strip()
                if value.lower() != 'none':
                    result['last_topics'] = value
            elif line.startswith('CONVERSATION_STATUS:'):
                value = line.replace('CONVERSATION_STATUS:', '').strip()
                if value.lower() != 'none':
                    result['conversation_status'] = value
        
        return result
        
    except Exception as e:
        print(f"Error generating conversation summary: {e}")
        return None
