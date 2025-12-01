"""
Safety Guardrails Module for JoveHeal Chatbot

This module implements strict safety filters to ensure the chatbot:
- Does NOT provide medical, psychological, psychiatric, or therapeutic advice
- Detects and redirects high-risk emotional/mental health queries
- Stays within the realm of general mindset coaching and wellness information
"""

import re
from typing import Tuple

CRISIS_KEYWORDS = [
    "suicide", "suicidal", "kill myself", "end my life", "want to die", 
    "don't want to live", "self-harm", "self harm", "hurt myself",
    "cutting myself", "overdose", "ending it all", "no reason to live",
    "better off dead", "can't go on", "goodbye forever"
]

MENTAL_HEALTH_KEYWORDS = [
    "depression", "depressed", "anxiety disorder", "panic attack",
    "ptsd", "post-traumatic", "bipolar", "schizophrenia", "psychosis",
    "eating disorder", "anorexia", "bulimia", "ocd", "obsessive compulsive",
    "borderline personality", "dissociative", "hallucination", "delusion",
    "manic episode", "mental illness", "mental disorder", "psychiatric"
]

MEDICAL_KEYWORDS = [
    "medication", "medicine", "prescription", "dosage", "side effects",
    "symptoms", "diagnosis", "diagnose", "treatment", "therapy",
    "antidepressant", "antipsychotic", "benzodiazepine", "ssri",
    "blood pressure", "heart condition", "diabetes", "cancer",
    "chronic pain", "disease", "medical condition", "doctor said",
    "should i stop taking", "should i start taking", "drug interaction"
]

ABUSE_VIOLENCE_KEYWORDS = [
    "abuse", "abused", "abusive", "domestic violence", "being hit",
    "physical abuse", "sexual abuse", "emotional abuse", "assault",
    "rape", "molest", "threatening me", "violence", "violent"
]

EXTREME_DISTRESS_KEYWORDS = [
    "can't cope", "breaking down", "complete breakdown", "losing my mind",
    "going crazy", "can't take it anymore", "overwhelmed", "desperate",
    "hopeless", "helpless", "worthless", "no way out", "trapped",
    "scared for my life", "in danger"
]

SAFE_REDIRECT_RESPONSE = """I hear you, and I'm really sorry you're going through this. What you're describing sounds like something that deserves real, professional support.

I'm here to share information about JoveHeal's programs and general mindset coaching, but I'm not equipped to provide medical or mental health guidance.

**Please reach out to qualified professionals:**
- **Emergency:** Call 911 or your local emergency services
- **Crisis Support:** National Suicide Prevention Lifeline: 988 (US)
- **Mental Health:** Contact a licensed therapist or counselor
- **Medical Concerns:** Please consult with your doctor

You deserve proper care and support. Is there anything about JoveHeal's programs I can help you with?"""

MEDICAL_REDIRECT_RESPONSE = """I appreciate you sharing that with me. However, I'm not able to provide medical advice, diagnose conditions, or make recommendations about medications or treatments.

For any health-related concerns, please consult with a qualified healthcare professional who can give you personalized guidance.

I'm here to share information about JoveHeal's wellness programs, coaching services, and mindset-focused offerings. Is there something specific about our services I can help you with?"""

THERAPY_REDIRECT_RESPONSE = """Thank you for sharing that. What you're describing sounds like it would benefit from professional support from a licensed therapist or counselor.

While JoveHeal offers mindset coaching and wellness programs, we're not a substitute for professional mental health care when it's needed.

I'd encourage you to reach out to a mental health professional who can provide proper support.

In the meantime, I'm happy to share information about JoveHeal's programs if you'd like to know more about our mindset coaching and wellness offerings."""


def check_for_crisis_content(message: str) -> Tuple[bool, str]:
    """
    Check if the message contains crisis-related content.
    Returns (is_crisis, redirect_response)
    """
    message_lower = message.lower()
    
    for keyword in CRISIS_KEYWORDS:
        if keyword in message_lower:
            return True, SAFE_REDIRECT_RESPONSE
    
    return False, ""


def check_for_mental_health_content(message: str) -> Tuple[bool, str]:
    """
    Check if the message is asking for mental health advice.
    Returns (is_mental_health, redirect_response)
    """
    message_lower = message.lower()
    
    advice_patterns = [
        r"how (do|can|should) i (deal|cope|handle|manage|treat|fix|cure)",
        r"what should i do about my",
        r"how to (get rid of|overcome|treat|cure|heal from)",
        r"am i (depressed|anxious|mentally ill|crazy)",
        r"do i have (depression|anxiety|ptsd|bipolar|ocd)"
    ]
    
    for keyword in MENTAL_HEALTH_KEYWORDS:
        if keyword in message_lower:
            for pattern in advice_patterns:
                if re.search(pattern, message_lower):
                    return True, THERAPY_REDIRECT_RESPONSE
            if any(q in message_lower for q in ["help me with", "what should", "how do i", "can you help"]):
                return True, THERAPY_REDIRECT_RESPONSE
    
    return False, ""


def check_for_medical_content(message: str) -> Tuple[bool, str]:
    """
    Check if the message is asking for medical advice.
    Returns (is_medical, redirect_response)
    """
    message_lower = message.lower()
    
    for keyword in MEDICAL_KEYWORDS:
        if keyword in message_lower:
            if any(q in message_lower for q in ["should i", "can i", "is it safe", "what happens if", "recommend", "suggest"]):
                return True, MEDICAL_REDIRECT_RESPONSE
    
    return False, ""


def check_for_abuse_violence(message: str) -> Tuple[bool, str]:
    """
    Check if the message describes abuse or violence.
    Returns (is_abuse, redirect_response)
    """
    message_lower = message.lower()
    
    for keyword in ABUSE_VIOLENCE_KEYWORDS:
        if keyword in message_lower:
            return True, SAFE_REDIRECT_RESPONSE
    
    return False, ""


def check_for_extreme_distress(message: str) -> Tuple[bool, str]:
    """
    Check if the message indicates extreme emotional distress.
    Returns (is_distress, redirect_response)
    """
    message_lower = message.lower()
    
    distress_count = sum(1 for keyword in EXTREME_DISTRESS_KEYWORDS if keyword in message_lower)
    
    if distress_count >= 2:
        return True, SAFE_REDIRECT_RESPONSE
    
    return False, ""


def apply_safety_filters(message: str) -> Tuple[bool, str]:
    """
    Apply all safety filters to the message.
    Returns (should_redirect, redirect_response)
    
    If should_redirect is True, the chatbot should return the redirect_response
    instead of processing the query through the RAG system.
    """
    is_crisis, crisis_response = check_for_crisis_content(message)
    if is_crisis:
        return True, crisis_response
    
    is_abuse, abuse_response = check_for_abuse_violence(message)
    if is_abuse:
        return True, abuse_response
    
    is_distress, distress_response = check_for_extreme_distress(message)
    if is_distress:
        return True, distress_response
    
    is_mental_health, mental_health_response = check_for_mental_health_content(message)
    if is_mental_health:
        return True, mental_health_response
    
    is_medical, medical_response = check_for_medical_content(message)
    if is_medical:
        return True, medical_response
    
    return False, ""


def get_system_prompt() -> str:
    """
    Return the system prompt that enforces safety guidelines for the LLM.
    This is RACEN's core persona and behavioral guidelines.
    """
    return """You are RACEN — Real-time Advisor for Coaching, Education & Navigation for JoveHeal.

Your role: Provide helpful, honest, empathetic, and clear information to visitors asking about JoveHeal's programs, healing/coaching philosophy, membership options, community, and related inquiries.

--- PERSONALITY & TONE ---

- Speak with warmth, empathy, and respect — like a trusted guide, not a salesperson.
- Use plain, human-friendly language. Avoid psychological jargon or therapy-speak.
- Keep sentences and paragraphs short for readability.
- Be inclusive and culturally respectful. Avoid assumptions about backgrounds or beliefs.
- Maintain a calm, gentle, supportive tone.
- Be honest about what you know — and importantly, what you do NOT know.
- Speak as RACEN, but if directly asked whether you are an AI, answer honestly.

--- GREETING BEHAVIOR ---

When someone says a simple greeting like "Hi", "Hello", "Hey", or similar, respond warmly and personally — NOT with a generic assistant reply. Introduce yourself as RACEN and invite them to share what brings them here.

Example:
User: Hi
RACEN: "Hi there! I'm RACEN, your guide for exploring JoveHeal's healing and coaching programs. What brings you here today? Whether you're curious about our offerings, looking for support, or just browsing — I'm happy to help."

Never respond to greetings with cold, generic lines like "Hello! How can I assist you today?" — that's not RACEN's voice.

--- WHAT YOU CAN DO ---

- Share information about JoveHeal's programs, services, and offerings
- Explain mindset coaching concepts (general, non-clinical)
- Describe workshops, memberships, pricing, and how to join
- Answer questions about fees, schedules, and policies
- Provide general motivation and goal-setting inspiration
- Share productivity habits and daily routine suggestions

--- RESPONSE FORMATTING ---

- For factual/informational answers: 2-5 short sentences. If more detail is needed, use small paragraphs or bullet points.
- For emotional or sensitive queries: Start with an empathetic acknowledgment, then answer with warmth, clarity, and reassurance.
- Offer next-step clarity: If you cannot fully help, gently redirect to a human coach or JoveHeal's contact form.
- Avoid pressure or sales-tone. No aggressive upsell or emotional manipulation.

--- CONVERSATION STYLE ---

- Use "people-first" language. Avoid labeling or diagnostic terms.
- Be patient, non-judgmental, and inclusive.
- When uncertain about an answer, admit it openly: "I don't have that information right now." Then offer to connect them with JoveHeal's team.

--- BOUNDARIES (Code-level safety filters handle specifics) ---

- Do not provide medical, psychological, or therapeutic advice.
- Do not diagnose conditions or recommend treatments.
- Do not guarantee outcomes or over-promise transformation.
- For high-risk topics (crisis, self-harm, severe distress), respond with empathy and strongly advise seeking professional help.

--- EXAMPLE RESPONSE PATTERNS ---

Emotional/Sensitive Query:
"I'm sorry to hear you're going through that. It's completely valid to feel this way. While I'm not a licensed therapist, I can share what kind of support JoveHeal offers — and if you'd like, I can help you connect with our team for more personal guidance."

Information Request:
"Great question! [Answer in 2-3 sentences]. Let me know if you'd like more details or want to explore other options."

Out-of-Scope Request:
"I appreciate you sharing that with me. That's outside what I'm able to help with, but I'd encourage you to speak with a qualified professional. In the meantime, I'm happy to share information about JoveHeal's programs if that would be helpful."

--- REMEMBER ---

You are RACEN — a helpful, honest guide for JoveHeal. Stay within the knowledge base provided. Be genuine, be warm, and always prioritize the visitor's wellbeing over making a sale."""


def log_high_risk_message(message: str, category: str) -> dict:
    """
    Create a log entry for high-risk messages.
    Returns a dict that can be stored for review.
    """
    return {
        "message": message,
        "category": category,
        "flagged": True
    }


OUTPUT_SAFETY_REDIRECT = """I want to be helpful, but I'm not able to provide guidance on that topic as it falls outside what I can safely address.

For health, mental wellness, or personal challenges, please reach out to qualified professionals who can give you the support you deserve.

I'm here to share information about JoveHeal's wellness coaching programs. Is there anything about our services I can help you with?"""

OUTPUT_FORBIDDEN_PATTERNS = [
    r"you (should|must|need to) (take|stop taking|start|try) .*(medication|medicine|drug|supplement|pill)",
    r"(diagnos|sounds like you have|you (might|may|probably) have) .*(disorder|condition|disease|syndrome)",
    r"(treatment|therapy) for .*(depression|anxiety|ptsd|trauma|bipolar|schizophrenia)",
    r"(prescribe|recommend|suggest).*(medication|medicine|drug|antidepressant|antipsychotic)",
    r"if you.*(self.?harm|suicid|hurt yourself|end your life)",
    r"(symptoms? of|signs? of) .*(mental|psychological|psychiatric)",
]


def filter_response_for_safety(response: str) -> Tuple[str, bool]:
    """
    Filter LLM response for safety concerns.
    Returns (filtered_response, was_filtered)
    
    If the response contains forbidden content, it will be replaced
    with a safe redirect message.
    """
    response_lower = response.lower()
    
    for keyword in CRISIS_KEYWORDS + MEDICAL_KEYWORDS[:10]:
        if keyword in response_lower:
            advice_indicators = [
                "you should", "i recommend", "try to", "you need to",
                "you must", "take some", "here's how", "steps to",
                "treatment", "prescribe", "diagnose"
            ]
            for indicator in advice_indicators:
                if indicator in response_lower:
                    return OUTPUT_SAFETY_REDIRECT, True
    
    import re
    for pattern in OUTPUT_FORBIDDEN_PATTERNS:
        if re.search(pattern, response_lower):
            return OUTPUT_SAFETY_REDIRECT, True
    
    return response, False
