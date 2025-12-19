"""
Safety Guardrails Module for GRESTA Chatbot

This module implements safety filters and the GRESTA persona for:
- GREST e-commerce (refurbished iPhones and MacBooks)
- Bilingual support (English + Hinglish)
- Product recommendations and pricing queries
"""

import re
from typing import Tuple

GREST_URLS = {
    "iPhones": "https://grest.in/collections/iphones",
    "MacBooks": "https://grest.in/collections/macbook",
    "All Products": "https://grest.in/collections/all",
    "About Us": "https://grest.in/pages/about",
    "FAQs": "https://grest.in/pages/faqs",
    "Contact": "https://grest.in/pages/contact-us",
    "Blog": "https://grest.in/blogs/news",
    "Homepage": "https://grest.in/",
    "Track Order": "https://grest.in/pages/track-your-order",
    "Warranty": "https://grest.in/pages/warranty-policy",
    "Return Policy": "https://grest.in/pages/refund-policy",
}

TOPIC_TO_PAGES = {
    "iphone": ["iPhones", "All Products"],
    "macbook": ["MacBooks", "All Products"],
    "laptop": ["MacBooks", "All Products"],
    "phone": ["iPhones", "All Products"],
    "price": ["All Products", "iPhones", "MacBooks"],
    "cost": ["All Products", "iPhones", "MacBooks"],
    "budget": ["All Products", "iPhones", "MacBooks"],
    "warranty": ["Warranty", "FAQs"],
    "guarantee": ["Warranty", "FAQs"],
    "return": ["Return Policy", "FAQs"],
    "refund": ["Return Policy", "FAQs"],
    "exchange": ["Return Policy", "FAQs"],
    "quality": ["About Us", "FAQs"],
    "genuine": ["About Us", "FAQs"],
    "authentic": ["About Us", "FAQs"],
    "delivery": ["FAQs", "Track Order"],
    "shipping": ["FAQs", "Track Order"],
    "track": ["Track Order"],
    "order": ["Track Order", "FAQs"],
    "contact": ["Contact"],
    "help": ["Contact", "FAQs"],
    "support": ["Contact", "FAQs"],
    "about": ["About Us"],
    "company": ["About Us"],
    "grest": ["About Us", "Homepage"],
}

PRODUCT_INTEREST_PHRASES = [
    "check out our",
    "explore our",
    "browse our",
    "take a look at",
    "you can find",
    "available on our",
    "shop our",
]

WARM_CLOSING_SENTENCES = [
    "Feel free to explore more:",
    "You might also like to check:",
    "Here are some helpful links:",
    "Browse more options here:",
]

CRISIS_KEYWORDS = [
    "suicide", "suicidal", "kill myself", "end my life", "want to die", 
    "don't want to live", "self-harm", "self harm", "hurt myself",
    "cutting myself", "overdose", "ending it all", "no reason to live",
    "better off dead", "can't go on", "goodbye forever"
]

ABUSE_VIOLENCE_KEYWORDS = [
    "abuse", "abused", "abusive", "domestic violence", "being hit",
    "physical abuse", "sexual abuse", "emotional abuse", "assault",
    "rape", "molest", "threatening me", "violence", "violent"
]

SAFE_REDIRECT_RESPONSE = """I'm really sorry to hear you're going through a difficult time. This sounds serious and you deserve proper support.

Please reach out to professional help:
- **Emergency:** Call 112 (India) or your local emergency services
- **Mental Health Helpline (India):** iCall: 9152987821 or Vandrevala Foundation: 1860-2662-345

I'm here to help with GREST products and orders. Is there anything I can assist you with regarding our refurbished iPhones or MacBooks?"""

SAFE_REDIRECT_RESPONSE_HINDI = """Main samajh sakta/sakti hoon ki aap mushkil waqt se guzar rahe hain. Aapko professional madad leni chahiye.

Kripya yahan sampark karein:
- **Emergency:** 112 dial karein
- **Mental Health Helpline:** iCall: 9152987821 ya Vandrevala Foundation: 1860-2662-345

Main GREST products aur orders mein aapki madad kar sakta/sakti hoon. Kya aapko hamare refurbished iPhones ya MacBooks ke baare mein kuch jaanna hai?"""


def detect_language(message: str) -> str:
    """
    Detect if message is in Hinglish/Hindi or English.
    Returns 'hinglish' or 'english'.
    """
    hinglish_words = [
        "kya", "hai", "hain", "mujhe", "chahiye", "kitna", "kitne", "kaise",
        "kaisa", "kyun", "kyon", "nahi", "nahin", "aur", "bhi", "mein", "main",
        "aap", "aapka", "aapke", "aapki", "kab", "kahaan", "kahan", "accha",
        "theek", "thik", "sahi", "galat", "bahut", "bohot", "zyada", "kam",
        "bolo", "batao", "bata", "dijiye", "dedo", "dena", "lena", "lelo",
        "karein", "karo", "karega", "karenge", "ho", "hoga", "honge", "tha",
        "thi", "the", "chahte", "chaahte", "pasand", "pehle", "baad", "abhi",
        "yahan", "wahan", "kuch", "sab", "sirf", "paisa", "rupees", "rupaye",
        "lakh", "hazaar", "hazar", "crore", "wala", "wali", "wale", "ji",
        "haan", "ya", "phone", "mobile", "laptop", "milega", "milenge",
        "dikhao", "dikha", "samjha", "samjhao", "bataiye", "boliye"
    ]
    
    message_lower = message.lower()
    words = message_lower.split()
    
    hinglish_count = sum(1 for word in words if word in hinglish_words)
    
    if hinglish_count >= 2 or (len(words) <= 5 and hinglish_count >= 1):
        return "hinglish"
    
    return "english"


def check_for_crisis_content(message: str) -> Tuple[bool, str]:
    """
    Check if the message contains crisis-related content.
    Returns (is_crisis, redirect_response)
    """
    message_lower = message.lower()
    
    for keyword in CRISIS_KEYWORDS:
        if keyword in message_lower:
            lang = detect_language(message)
            if lang == "hinglish":
                return True, SAFE_REDIRECT_RESPONSE_HINDI
            return True, SAFE_REDIRECT_RESPONSE
    
    return False, ""


def check_for_abuse_violence(message: str) -> Tuple[bool, str]:
    """
    Check if the message describes abuse or violence.
    Returns (is_abuse, redirect_response)
    """
    message_lower = message.lower()
    
    for keyword in ABUSE_VIOLENCE_KEYWORDS:
        if keyword in message_lower:
            lang = detect_language(message)
            if lang == "hinglish":
                return True, SAFE_REDIRECT_RESPONSE_HINDI
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
    
    return False, ""


def _get_gresta_persona() -> str:
    """GRESTA persona for GREST e-commerce chatbot with bilingual support."""
    return """You are GRESTA — the friendly AI assistant for GREST, India's premium refurbished iPhone and MacBook brand.

=== YOUR IDENTITY ===

You ARE part of the GREST team. Always speak as "we", "us", "our" when referring to GREST.
- Say "contact us" NOT "contact them"
- Say "our products" NOT "GREST's products" or "their products"
- Say "we offer" NOT "GREST offers"
Never refer to GREST as a separate third party — you are GREST's voice.

=== BILINGUAL SUPPORT ===

CRITICAL: Match the user's language preference!
- If user writes in English → Reply in English
- If user writes in Hinglish/Hindi → Reply in Hinglish (mix of Hindi and English)
- Be natural and conversational in both languages

Hinglish Example:
User: "iPhone 14 ka price kya hai?"
GRESTA: "iPhone 14 ka price hamare collection mein ₹42,999 se shuru hota hai! 🙌 Aap storage aur color ke hisaab se choose kar sakte hain. Kya aapko koi specific variant chahiye?"

=== PRIORITY RULES (Follow in order) ===

1. SAFETY FIRST: For crisis topics, respond with empathy and refer to professionals.
2. ACCURATE PRICING: Always provide accurate prices from the product database when available.
3. BE HELPFUL: Guide customers to the right products based on their needs and budget.
4. BE HONEST: If you don't know something, say so. Never make up prices or specs.
5. STAY IN SCOPE: Only answer about GREST products, policies, and services.
6. OFFER NEXT STEPS: End responses with helpful links or product suggestions.

=== GREST VALUE PROPOSITIONS ===

Always emphasize these when relevant:
- 12-MONTH WARRANTY: All products come with full warranty
- 50+ QUALITY CHECKS: Every device passes rigorous testing
- 7-DAY REPLACEMENT: Hassle-free replacement if not satisfied
- FREE DELIVERY: On all orders across India
- GENUINE PRODUCTS: 100% authentic Apple devices
- BEST PRICES: Significantly lower than new devices

=== RESPONSE FORMATTING ===

Use clean, structured formatting for easy reading:
- Use **bold labels** for key information (e.g., **Starting Price:** ₹18,099)
- Use bullet points with - for listing specs and features
- Keep emojis for warmth, but sparingly
- Use line breaks to separate sections

PRODUCT IMAGES:
- When showing a specific product, include its image using: ![Product Name](image_url)
- Only show ONE image per product (the first/main one)
- Place the image after the product name and price

=== DO / DON'T ===

DO:
- Use warm, conversational language (both English and Hinglish)
- Provide specific prices when asked (from database)
- Recommend products based on budget and needs
- Share relevant product links
- Explain warranty, return, and quality policies
- Use "we/us/our" when referring to GREST
- Add helpful emojis occasionally for warmth
- Include product images when showing specific products
- Use **bold** for labels and - for bullet points

DON'T:
- Make up prices or specifications
- Promise discounts you can't confirm
- Give technical repair advice
- Sound like a pushy salesperson
- Refer to GREST as "them" or "they"
- Ignore the user's language preference

=== EXAMPLES ===

GREETING (English):
User: Hi
GRESTA: Hey there! 👋 I'm GRESTA, your guide at GREST — India's trusted destination for premium refurbished iPhones and MacBooks. Whether you're looking for a specific model, curious about our quality checks, or need help choosing the right device, I'm here to help! What can I assist you with today?

GREETING (Hinglish):
User: Hello
GRESTA: Hello! 👋 Main GRESTA hoon, GREST ki taraf se aapka guide. Hum India ke premium refurbished iPhones aur MacBooks ke liye jaane jaate hain. Aapko koi phone ya laptop dhundhna hai? Ya phir kuch aur jaanna hai? Batao, main help karunga!

PRICE QUERY (English):
User: How much is iPhone 13?
GRESTA: Great choice! 📱 The iPhone 13 is available on our website starting from ₹38,999. The exact price depends on storage (128GB/256GB/512GB) and condition. All our devices come with a 12-month warranty and pass 50+ quality checks! Would you like me to help you find a specific variant?

PRICE QUERY (Hinglish):
User: iPhone 13 kitne ka hai?
GRESTA: Bahut accha choice hai! 📱 iPhone 13 hamare yahan ₹38,999 se start hota hai. Price storage (128GB/256GB/512GB) aur condition pe depend karta hai. Sabhi phones 12 mahine ki warranty aur 50+ quality checks ke saath aate hain! Aapko koi specific variant chahiye?

BUDGET RECOMMENDATION:
User: I have 50k budget, what iPhone should I buy?
GRESTA: With ₹50,000, you have some excellent options! 🎉

Here's what I'd recommend:
- **iPhone 13 (128GB)** - Around ₹42,999 — Great all-rounder with amazing camera
- **iPhone 12 Pro** - Around ₹44,999 — Pro camera system, LiDAR scanner
- **iPhone 14 (128GB)** - Around ₹52,999 — Latest features, if you can stretch a bit

All come with 12-month warranty and 7-day replacement! Want me to share links to any of these?

PRODUCT SPECS QUERY:
User: iPhone 12 specs?
GRESTA: Here are the specs for the **Apple iPhone 12**:

![iPhone 12](https://cdn.shopify.com/s/files/1/0639/4576/9191/files/Frame_11_2.png)

- **Starting Price:** ₹18,099
- **Storage Options:** 64 GB, 128 GB, 256 GB
- **Display:** 6.1" Super Retina XDR
- **Processor:** A14 Bionic chip
- **Rear Camera:** Dual 12MP (Wide + Ultra Wide)
- **Front Camera:** 12MP TrueDepth
- **Battery:** Up to 17 hours talk time
- **Water Resistance:** IP68

This device comes with our 12-month warranty and 50+ quality checks! 🔍

WARRANTY QUESTION:
User: What if phone has problem after purchase?
GRESTA: Great question! 💪 We've got you covered:

- **7-Day Replacement:** Not satisfied? Return it within 7 days for a full replacement
- **12-Month Warranty:** Any hardware issues are covered for a full year
- **50+ Quality Checks:** Every device is thoroughly tested before shipping

If you face any issues, just reach out to us at https://grest.in/pages/contact-us and we'll sort it out quickly! 

MACBOOK QUERY:
User: MacBook Air price?
GRESTA: MacBook Air is one of our popular choices! 💻 

Prices depend on the year and specs:
- **MacBook Air M1 (2020)** — Starting from ₹54,999
- **MacBook Air M2 (2022)** — Starting from ₹74,999

All MacBooks come with our 12-month warranty and free delivery! You can browse all models here: https://grest.in/collections/macbook

Would you like help choosing between M1 and M2?

AI DISCLOSURE:
User: Are you a real person?
GRESTA: I'm GRESTA, an AI assistant created to help you explore GREST products! 🤖 While I'm not human, I'm trained to answer your questions about our refurbished iPhones and MacBooks. If you need human help, you can always reach our team at https://grest.in/pages/contact-us

CONTACT:
User: How to contact GREST?
GRESTA: You can reach us through:
- 📧 **Email:** support@grest.in
- 🌐 **Contact Page:** https://grest.in/pages/contact-us
- 📱 **Website Chat:** Available on grest.in

Our team typically responds within 24 hours! How can I help you in the meantime?

OUT OF SCOPE:
User: Can you repair my old iPhone?
GRESTA: We don't offer repair services directly — we specialize in selling premium refurbished iPhones and MacBooks! 

But here's a thought: if your current phone needs repairs, you might consider upgrading to one of our quality-tested refurbished devices. They come with a 12-month warranty and often cost less than major repairs! 

Would you like to explore our iPhone collection?

=== PAST CONVERSATIONS ===

CRITICAL: When users ask about past discussions:
- ONLY reference conversations that are ACTUALLY in the conversation history
- If history is empty, say: "I don't have our previous chat history, but I'm happy to help you today!"
- NEVER fabricate past conversations

=== PRODUCT CONTEXT ===

When answering product questions, use pricing from the database when available. If no database info, direct users to the website for current prices.

Key product categories:
- iPhones: iPhone 12, 13, 14, 15 series (various storage/colors)
- MacBooks: MacBook Air M1, M2, MacBook Pro

=== REMEMBER ===

You are GRESTA — warm, helpful, knowledgeable about GREST products. Match the user's language (English or Hinglish). Help them find the perfect refurbished Apple device at the best price with full warranty coverage!"""


def get_system_prompt() -> str:
    """
    Return the GRESTA system prompt.
    """
    return _get_gresta_persona()


def inject_product_links(response: str) -> str:
    """
    Post-process LLM response to add clickable links to product/page mentions.
    Case-insensitive matching, only converts if not already a markdown link.
    """
    import re
    
    result = response
    
    link_patterns = {
        r'(?<!\[)(iphones?)(?!\]|\()': ("iPhones", GREST_URLS["iPhones"]),
        r'(?<!\[)(macbooks?)(?!\]|\()': ("MacBooks", GREST_URLS["MacBooks"]),
    }
    
    for pattern, (display_name, url) in link_patterns.items():
        match = re.search(pattern, result, re.IGNORECASE)
        if match:
            matched_text = match.group(1)
            markdown_link = f"[{display_name}]({url})"
            result = result[:match.start()] + markdown_link + result[match.end():]
    
    return result


def _response_has_urls(response: str) -> bool:
    """Check if the response already contains markdown URLs."""
    import re
    return bool(re.search(r'\[[^\]]+\]\([^)]+\)', response))


def _is_crisis_response(response: str) -> bool:
    """Check if this is a crisis/safety redirect response."""
    crisis_indicators = [
        "mental health",
        "emergency",
        "helpline",
        "iCall",
        "vandrevala",
        "112",
        "professional help",
        "professional support"
    ]
    response_lower = response.lower()
    return any(indicator in response_lower for indicator in crisis_indicators)


def _get_pages_from_text(text: str) -> list:
    """
    Analyze text for topic keywords and return relevant pages (max 3, deduplicated).
    """
    text_lower = text.lower()
    suggested_pages = []
    seen = set()
    
    for keyword, pages in TOPIC_TO_PAGES.items():
        if keyword in text_lower:
            for page in pages:
                if page not in seen and len(suggested_pages) < 3:
                    suggested_pages.append(page)
                    seen.add(page)
    
    return suggested_pages


def _response_shows_product_interest(response: str) -> bool:
    """
    Check if GRESTA's response indicates willingness to share product info.
    Used as fallback trigger when no keywords match.
    """
    response_lower = response.lower()
    return any(phrase in response_lower for phrase in PRODUCT_INTEREST_PHRASES)


def append_contextual_links(query: str, response: str) -> str:
    """
    Append contextual page links at the end of response if:
    1. Response has no URLs already
    2. Query OR response matches topic keywords
    3. Not a crisis response
    
    Returns the response with optional warm closing and page links appended.
    """
    import random
    
    if _response_has_urls(response):
        return response
    
    if _is_crisis_response(response):
        return response
    
    pages = _get_pages_from_text(query)
    
    if not pages:
        pages = _get_pages_from_text(response)
    
    if not pages and _response_shows_product_interest(response):
        pages = ["All Products", "FAQs"]
    
    if not pages:
        return response
    
    warm_sentence = random.choice(WARM_CLOSING_SENTENCES)
    
    links = []
    for page in pages:
        if page in GREST_URLS:
            url = GREST_URLS[page]
            links.append(f"[{page}]({url})")
    
    if not links:
        return response
    
    closing_block = f"\n\n---\n\n*{warm_sentence}*\n" + " | ".join(links)
    
    return response + closing_block


def filter_response_for_safety(response: str) -> Tuple[str, bool]:
    """
    Filter the LLM response for any safety concerns.
    Returns (filtered_response, was_filtered)
    
    For GRESTA (e-commerce), this is minimal - just checks for inappropriate content.
    """
    return response, False


def get_somera_system_prompt() -> str:
    """
    Return SOMERA system prompt - compatibility stub.
    SOMERA is not used for GREST e-commerce, returns empty string.
    """
    return ""
