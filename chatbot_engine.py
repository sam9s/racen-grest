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
    search_products_for_chatbot
)

_openai_client = None


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
        r'under\s*(?:rs\.?|₹)?\s*(\d{1,3}(?:,?\d{3})*)',
        r'below\s*(?:rs\.?|₹)?\s*(\d{1,3}(?:,?\d{3})*)',
        r'less than\s*(?:rs\.?|₹)?\s*(\d{1,3}(?:,?\d{3})*)',
        r'within\s*(?:rs\.?|₹)?\s*(\d{1,3}(?:,?\d{3})*)',
        r'(?:rs\.?|₹)\s*(\d{1,3}(?:,?\d{3})*)\s*(?:ke andar|tak|under)',
        r'(\d{1,3}(?:,?\d{3})*)\s*(?:ke andar|tak|rupee|rs)',
        r'budget\s*(?:of|is)?\s*(?:rs\.?|₹)?\s*(\d{1,3}(?:,?\d{3})*)',
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, message_lower)
        if match:
            price_str = match.group(1).replace(',', '')
            max_price = float(price_str)
            break
    
    range_patterns = [
        r'between\s*(?:rs\.?|₹)?\s*(\d{1,3}(?:,?\d{3})*)\s*(?:to|and|-)\s*(?:rs\.?|₹)?\s*(\d{1,3}(?:,?\d{3})*)',
        r'(\d{1,3}(?:,?\d{3})*)\s*(?:se|to)\s*(\d{1,3}(?:,?\d{3})*)',
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


def get_product_context_from_database(message: str) -> str:
    """
    Get product/pricing context from the database based on the user's query.
    Returns formatted string for LLM context injection.
    """
    is_price_query, max_price, min_price, category = detect_price_query(message)
    
    if not is_price_query:
        return ""
    
    context_parts = []
    context_parts.append("\n\n=== PRODUCT DATABASE (AUTHORITATIVE PRICING SOURCE) ===")
    context_parts.append("NOTE: Use ONLY these prices. They are current and accurate.\n")
    
    if 'sasta' in message.lower() or 'cheapest' in message.lower() or 'lowest' in message.lower():
        cheapest = get_cheapest_product(category)
        if cheapest:
            context_parts.append(f"CHEAPEST {'iPhone' if category == 'iPhone' else 'Product'}:")
            context_parts.append(f"  - {cheapest['name']}: Rs. {int(cheapest['price']):,}")
            context_parts.append(f"    URL: {cheapest['product_url']}")
    
    elif min_price and max_price:
        products = get_products_in_price_range(min_price, max_price, category)
        if products:
            context_parts.append(f"Products between Rs. {int(min_price):,} - Rs. {int(max_price):,}:")
            for p in products[:5]:
                context_parts.append(f"  - {p['name']}: Rs. {int(p['price']):,}")
                context_parts.append(f"    URL: {p['product_url']}")
        else:
            context_parts.append(f"No products found between Rs. {int(min_price):,} - Rs. {int(max_price):,}")
    
    elif max_price:
        products = get_products_under_price(max_price, category)
        if products:
            context_parts.append(f"Products under Rs. {int(max_price):,}:")
            for p in products[:5]:
                discount_text = f" (Save {p['discount_percent']}%)" if p.get('discount_percent') else ""
                context_parts.append(f"  - {p['name']}: Rs. {int(p['price']):,}{discount_text}")
                context_parts.append(f"    URL: {p['product_url']}")
        else:
            cheapest = get_cheapest_product(category)
            if cheapest:
                context_parts.append(f"No products under Rs. {int(max_price):,}.")
                context_parts.append(f"Cheapest option: {cheapest['name']} at Rs. {int(cheapest['price']):,}")
    
    else:
        all_products = get_all_products_formatted()
        context_parts.append(all_products)
    
    context_parts.append("\n=== END PRODUCT DATABASE ===\n")
    
    return "\n".join(context_parts)


def should_trigger_web_search(message: str) -> Tuple[bool, str, str]:
    """
    Determine if GRESTA should perform a web search.
    This is GRESTA's decision, not triggered by user request.
    
    Returns: (should_search, search_query, search_category)
    
    Categories that trigger web search:
    1. Trust/reviews: Trustpilot, Mouthshut, reviews, ratings
    2. Competitor comparison: Cashify, other refurb sellers
    3. Product comparison: iPhone X vs Y (external specs)
    4. General product info not in our database
    """
    message_lower = message.lower()
    
    trust_keywords = [
        'trust', 'trustpilot', 'mouthshut', 'review', 'rating', 'ratings',
        'reliable', 'genuine', 'fake', 'scam', 'fraud', 'legitimate',
        'bharosa', 'vishwas', 'reputation', 'feedback', 'experience'
    ]
    
    if any(kw in message_lower for kw in trust_keywords):
        return (True, "GREST grest.in reviews ratings Trustpilot Mouthshut customer feedback", "trust_verification")
    
    competitor_keywords = [
        'cashify', 'togofogo', 'yaantra', 'budli', 'quikr', 'olx',
        'other seller', 'competitor', 'compare with', 'vs other',
        'why grest', 'why should i buy from grest', 'better than'
    ]
    
    if any(kw in message_lower for kw in competitor_keywords):
        competitor = "cashify" if "cashify" in message_lower else "refurbished phone sellers India"
        return (True, f"GREST vs {competitor} comparison refurbished phones India reviews", "competitor_comparison")
    
    comparison_pattern = re.search(
        r'(iphone|ipad|macbook)\s*(\d+)\s*(pro|max|plus|mini)?\s*(vs|versus|or|compare|difference|better)\s*(iphone|ipad|macbook)?\s*(\d+)\s*(pro|max|plus|mini)?',
        message_lower
    )
    
    if comparison_pattern:
        return (True, f"Apple {comparison_pattern.group(0)} comparison specs features", "product_comparison")
    
    if re.search(r'difference between.*and|compare.*with|which is better', message_lower):
        return (True, f"Apple {message} comparison specs", "product_comparison")
    
    specs_pattern = re.search(
        r'(iphone|ipad|macbook)\s*(\d+)\s*(pro|max|plus|mini)?\s*(specs?|specifications?|features?|camera|display|screen|battery|processor|chip|storage)',
        message_lower
    )
    if specs_pattern:
        return (True, f"Apple {specs_pattern.group(0)} specifications features", "product_specs")
    
    if re.search(r'(tell me about|what are the|how good is)\s*(the\s+)?(camera|display|battery|performance)', message_lower):
        product_match = re.search(r'(iphone|ipad|macbook)\s*(\d+)\s*(pro|max|plus|mini)?', message_lower)
        if product_match:
            return (True, f"Apple {product_match.group(0)} specifications features", "product_specs")
    
    return (False, "", "")


def perform_web_search(query: str, category: str) -> str:
    """
    Perform a real web search using DuckDuckGo API and return formatted results.
    DuckDuckGo API is free and doesn't require an API key.
    """
    try:
        import requests
        
        ddg_url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        
        response = requests.get(ddg_url, params=params, timeout=10)
        
        if response.status_code not in [200, 202]:
            print(f"[Web Search] DuckDuckGo API returned status {response.status_code}")
            return ""
        
        data = response.json()
        
        results = []
        
        if data.get("Abstract"):
            results.append(f"**Summary**: {data['Abstract']}")
            if data.get("AbstractSource"):
                results.append(f"Source: {data['AbstractSource']}")
        
        if data.get("Answer"):
            results.append(f"**Direct Answer**: {data['Answer']}")
        
        related_topics = data.get("RelatedTopics", [])
        if related_topics:
            results.append("\n**Related Information**:")
            for i, topic in enumerate(related_topics[:5]):
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"- {topic['Text'][:200]}")
        
        if data.get("Infobox") and data["Infobox"].get("content"):
            results.append("\n**Quick Facts**:")
            for item in data["Infobox"]["content"][:5]:
                if item.get("label") and item.get("value"):
                    results.append(f"- {item['label']}: {item['value']}")
        
        if not results:
            print(f"[Web Search] No results from DuckDuckGo for: {query}")
            return ""
        
        search_results = f"""
=== WEB SEARCH RESULTS (Live Data) ===
Search Query: {query}
Category: {category}

{chr(10).join(results)}

Note: GRESTA performed this search automatically. Prioritize GREST's official policies for company-specific questions.
=== END WEB SEARCH RESULTS ===
"""
        print(f"[Web Search] Successfully retrieved results for: {query}")
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
        return """
=== GREST TRUST & REVIEWS (Verified Information) ===
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
- Positive reviews on Trustpilot and Mouthshut

For latest reviews, customers can check:
- Trustpilot: https://www.trustpilot.com/review/grest.in
- Mouthshut: https://www.mouthshut.com/product-reviews/Grest-in-reviews-926089093

=== END TRUST VERIFICATION ===
"""
    
    elif category == "competitor_comparison":
        return """
=== WHY CHOOSE GREST OVER COMPETITORS ===
GREST Advantages:
1. **50+ Quality Checks**: Every device undergoes rigorous testing
2. **Warranty**: 6-month warranty (extendable to 12 months for Rs. 1,499)
3. **7-Day Returns**: Hassle-free return policy
4. **COD Available**: Pay when you receive
5. **Free Delivery**: Across India
6. **Premium Batteries**: Quality replacement batteries
7. **In-House Refurbishment**: Own expert technicians

GREST focuses exclusively on Apple products (iPhone, iPad, MacBook), ensuring deep expertise and quality control.

Note: Compare warranties, return policies, and quality checks when choosing any refurbished seller.
=== END COMPARISON ===
"""
    
    elif category == "product_comparison":
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
    last_topic_summary: str = None
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
    
    product_context = get_product_context_from_database(user_message)
    
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

CRITICAL PRICING INSTRUCTIONS:
- If "PRODUCT DATABASE" section is provided above, use ONLY those prices - they are current and accurate
- The Product Database prices override any pricing from other sources (website scrapes may be outdated)
- When recommending products by price, list the specific products from the database with their exact prices
- Always include the product URL so users can purchase directly

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
    last_topic_summary: str = None
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
    
    product_context = get_product_context_from_database(user_message)
    
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

CRITICAL PRICING INSTRUCTIONS:
- If "PRODUCT DATABASE" section is provided above, use ONLY those prices - they are current and accurate
- The Product Database prices override any pricing from other sources (website scrapes may be outdated)
- When recommending products by price, list the specific products from the database with their exact prices
- Always include the product URL so users can purchase directly

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
