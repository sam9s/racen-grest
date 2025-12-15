"""
Chatbot Engine for GRESTA (GREST Real-time Engagement Support & Technology Assistant)

This module handles the core chatbot logic:
- Query processing with RAG
- Integration with OpenAI for response generation
- Context management for multi-turn conversations
- Product pricing queries from PostgreSQL
"""

import os
from typing import List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from knowledge_base import search_knowledge_base, get_knowledge_base_stats
from safety_guardrails import apply_safety_filters, get_system_prompt, filter_response_for_safety, inject_product_links, append_contextual_links

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

MULTI-SOURCE SYNTHESIS INSTRUCTIONS:
1. Sources are listed in ORDER OF AUTHORITY - "OFFICIAL POLICY" and "OFFICIAL FAQ" sources are MORE RELIABLE than "PRODUCT PAGE" sources
2. If sources have CONFLICTING information (e.g., different warranty durations), ALWAYS TRUST the higher authority source
   - Example: If warranty policy says "6 months" but product page says "12 months", USE "6 months" from the policy
3. Synthesize information from ALL sources, but when conflicts exist, the HIGHEST AUTHORITY source wins
4. For policies (warranty, refund, shipping), ONLY use information from "OFFICIAL POLICY" or "OFFICIAL FAQ" sources
5. Product pages may contain simplified or outdated information - defer to official policies
6. At the end, cite the primary authoritative source(s) that answered the question

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

MULTI-SOURCE SYNTHESIS INSTRUCTIONS:
1. Sources are listed in ORDER OF AUTHORITY - "OFFICIAL POLICY" and "OFFICIAL FAQ" sources are MORE RELIABLE than "PRODUCT PAGE" sources
2. If sources have CONFLICTING information (e.g., different warranty durations), ALWAYS TRUST the higher authority source
   - Example: If warranty policy says "6 months" but product page says "12 months", USE "6 months" from the policy
3. Synthesize information from ALL sources, but when conflicts exist, the HIGHEST AUTHORITY source wins
4. For policies (warranty, refund, shipping), ONLY use information from "OFFICIAL POLICY" or "OFFICIAL FAQ" sources
5. Product pages may contain simplified or outdated information - defer to official policies
6. At the end, cite the primary authoritative source(s) that answered the question

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
