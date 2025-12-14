"""
SOMERA Engine - Empathetic Coaching Assistant

SOMERA (Supportive, Open-Minded, Empathetic, Reflective Advisor) uses Shweta's
coaching content from video transcripts and session recordings to provide
empathetic, coaching-style support.

Unlike Jovee (informational), SOMERA focuses on emotional support and coaching guidance.
"""

import os
from typing import List, Generator

from knowledge_base import search_coaching_content
from safety_guardrails import (
    get_somera_system_prompt,
    apply_safety_filters,
    filter_response_for_safety
)

_openai_client = None


def get_openai_client():
    """Get OpenAI client singleton."""
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
        print(f"Error initializing OpenAI client for SOMERA: {e}")
        return None


def format_coaching_context(documents: List[dict]) -> str:
    """Format retrieved coaching documents into context for SOMERA."""
    if not documents:
        return "No specific coaching content found for this topic."
    
    context_parts = []
    for i, doc in enumerate(documents, 1):
        source = doc.get("video_title", doc.get("source", "Coaching Content"))
        topic = doc.get("topic", "general")
        content = doc.get("content", "")
        context_parts.append(f"[From: {source} | Topic: {topic}]\n{content}")
    
    return "\n\n---\n\n".join(context_parts)


def format_conversation_history(messages: List[dict]) -> List[dict]:
    """Format conversation history for the API call."""
    formatted = []
    for msg in messages[-8:]:
        if msg.get("role") in ["user", "assistant", "system"]:
            formatted.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    return formatted


def generate_somera_response(
    user_message: str,
    conversation_history: List[dict] = None,
    user_name: str = None,
    n_context_docs: int = 5
) -> dict:
    """
    Generate a SOMERA coaching response using RAG with coaching content.
    
    Args:
        user_message: The user's message
        conversation_history: Previous conversation messages
        user_name: Optional user name for personalization
        n_context_docs: Number of coaching documents to retrieve
    
    Returns:
        Dict with response, sources, and safety info
    """
    if conversation_history is None:
        conversation_history = []
    
    client = get_openai_client()
    if client is None:
        return {
            "response": "I'm temporarily unavailable. Please try again later or contact us at https://www.joveheal.com/contact for assistance.",
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
    
    relevant_docs = search_coaching_content(user_message, n_results=n_context_docs)
    context = format_coaching_context(relevant_docs)
    
    system_prompt = get_somera_system_prompt()
    
    personalization = ""
    if user_name:
        personalization = f"\nThe user's name is {user_name}. Use their name naturally in your response."
    
    augmented_prompt = f"""{system_prompt}
{personalization}

=== SHWETA'S COACHING WISDOM ===
The following is from Shweta's actual coaching content. Use these insights naturally in your response:

{context}

IMPORTANT: 
- Weave Shweta's teachings into your response naturally
- Don't quote sources directly, just use the wisdom
- Always start with empathy before sharing insights
- If the context doesn't cover the topic, still respond warmly using general coaching principles"""

    messages = [{"role": "system", "content": augmented_prompt}]
    
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
        
        sources = [
            {
                "source": doc.get("video_title", doc.get("source", "Unknown")),
                "topic": doc.get("topic", "general")
            }
            for doc in relevant_docs[:3]
        ]
        
        return {
            "response": filtered_response,
            "sources": sources,
            "safety_triggered": was_filtered,
            "safety_category": "output_filtered" if was_filtered else None
        }
        
    except Exception as e:
        print(f"Error generating SOMERA response: {e}")
        return {
            "response": "I'm having a moment of difficulty. Please try again, or reach out to us at https://www.joveheal.com/contact.",
            "sources": [],
            "safety_triggered": False,
            "error": str(e)
        }


def generate_somera_response_stream(
    user_message: str,
    conversation_history: List[dict] = None,
    user_name: str = None,
    n_context_docs: int = 5
) -> Generator[dict, None, None]:
    """
    Generate a streaming SOMERA coaching response.
    
    Yields chunks with type 'content' for text and 'done' when complete.
    """
    if conversation_history is None:
        conversation_history = []
    
    client = get_openai_client()
    if client is None:
        yield {
            "type": "error",
            "error": "SOMERA is temporarily unavailable. Please try again later."
        }
        return
    
    safety_result = apply_safety_filters(user_message)
    if safety_result["is_blocked"]:
        yield {
            "type": "content",
            "content": safety_result["redirect_message"]
        }
        yield {
            "type": "done",
            "sources": [],
            "safety_triggered": True,
            "full_response": safety_result["redirect_message"]
        }
        return
    
    relevant_docs = search_coaching_content(user_message, n_results=n_context_docs)
    context = format_coaching_context(relevant_docs)
    
    system_prompt = get_somera_system_prompt()
    
    personalization = ""
    if user_name:
        personalization = f"\nThe user's name is {user_name}. Use their name naturally in your response."
    
    augmented_prompt = f"""{system_prompt}
{personalization}

=== SHWETA'S COACHING WISDOM ===
The following is from Shweta's actual coaching content. Use these insights naturally in your response:

{context}

IMPORTANT: 
- Weave Shweta's teachings into your response naturally
- Don't quote sources directly, just use the wisdom
- Always start with empathy before sharing insights
- If the context doesn't cover the topic, still respond warmly using general coaching principles"""

    messages = [{"role": "system", "content": augmented_prompt}]
    
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
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield {
                    "type": "content",
                    "content": content
                }
        
        filtered_response, was_filtered = filter_response_for_safety(full_response)
        
        sources = [
            {
                "source": doc.get("video_title", doc.get("source", "Unknown")),
                "topic": doc.get("topic", "general")
            }
            for doc in relevant_docs[:3]
        ]
        
        yield {
            "type": "done",
            "sources": sources,
            "safety_triggered": was_filtered,
            "full_response": filtered_response if was_filtered else full_response
        }
        
    except Exception as e:
        print(f"Error in SOMERA stream: {e}")
        yield {
            "type": "error",
            "error": f"Error generating response: {str(e)}"
        }
