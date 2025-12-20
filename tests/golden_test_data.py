"""
Golden Test Dataset for GRESTA Chatbot
Contains test scenarios with expected assertions for automated testing.

Each test case has:
- query: The user message
- assertions: List of checks that must pass
- category: Type of test for reporting
- session_id: For multi-turn tests
"""

GOLDEN_TESTS = [
    # ===========================================
    # CATEGORY: PRICING - Basic Price Queries
    # ===========================================
    {
        "id": "price_001",
        "query": "iPhone 16 Pro Max price",
        "category": "pricing",
        "assertions": [
            {"type": "contains", "value": "95,399", "description": "Contains base price"},
            {"type": "contains", "value": "16 Pro Max", "description": "Mentions correct model"},
            {"type": "contains", "value": "grest.in", "description": "Contains product link"},
        ]
    },
    {
        "id": "price_002",
        "query": "iPhone 15 Pro 256GB price",
        "category": "pricing",
        "assertions": [
            {"type": "contains_price", "min": 50000, "max": 90000, "description": "Price in reasonable range"},
            {"type": "contains", "value": "15 Pro", "description": "Mentions correct model"},
        ]
    },
    {
        "id": "price_003",
        "query": "iPhone 14 kitna ka hai",
        "category": "pricing_hinglish",
        "assertions": [
            {"type": "contains_price", "min": 30000, "max": 60000, "description": "Price in reasonable range"},
            {"type": "contains", "value": "14", "description": "Mentions iPhone 14"},
        ]
    },
    {
        "id": "price_004",
        "query": "iPhone 13 Pro Max 512GB Superb condition price",
        "category": "pricing",
        "assertions": [
            {"type": "contains_price", "min": 50000, "max": 80000, "description": "Price in reasonable range"},
            {"type": "contains", "value": "13 Pro Max", "description": "Mentions correct model"},
        ]
    },
    {
        "id": "price_005",
        "query": "What is the price of iPhone 12?",
        "category": "pricing",
        "assertions": [
            {"type": "contains_price", "min": 20000, "max": 45000, "description": "Price in reasonable range"},
            {"type": "contains", "value": "12", "description": "Mentions iPhone 12"},
        ]
    },
    {
        "id": "price_006",
        "query": "iPhone 11 Pro price kya hai",
        "category": "pricing_hinglish",
        "assertions": [
            {"type": "contains_price", "min": 20000, "max": 50000, "description": "Price in reasonable range"},
            {"type": "contains", "value": "11 Pro", "description": "Mentions correct model"},
        ]
    },
    {
        "id": "price_007",
        "query": "cheapest iPhone available",
        "category": "pricing",
        "assertions": [
            {"type": "contains_price", "min": 10000, "max": 30000, "description": "Shows budget option"},
            {"type": "contains", "value": "grest.in", "description": "Contains link"},
        ]
    },
    {
        "id": "price_008",
        "query": "iPhone 16 Pro Max 1TB Superb price",
        "category": "pricing",
        "assertions": [
            {"type": "contains", "value": "1", "description": "Mentions 1TB or storage"},
            {"type": "contains_price", "min": 100000, "max": 150000, "description": "Premium price range"},
        ]
    },
    
    # ===========================================
    # CATEGORY: SPECIFICATIONS
    # ===========================================
    {
        "id": "specs_001",
        "query": "iPhone 16 Pro Max specs",
        "category": "specifications",
        "assertions": [
            {"type": "contains", "value": "6.3", "description": "Correct display size"},
            {"type": "contains", "value": "A18 Pro", "description": "Correct processor"},
            {"type": "contains", "value": "48", "description": "48MP camera"},
        ]
    },
    {
        "id": "specs_002",
        "query": "iPhone 15 Pro specifications",
        "category": "specifications",
        "assertions": [
            {"type": "contains", "value": "A17", "description": "A17 Pro processor"},
            {"type": "contains", "value": "Titanium", "description": "Titanium design"},
        ]
    },
    {
        "id": "specs_003",
        "query": "What is the display size of iPhone 16 Pro Max?",
        "category": "specifications",
        "assertions": [
            {"type": "contains", "value": "6.3", "description": "Correct display size"},
            {"type": "contains", "value": "OLED", "description": "Display type"},
        ]
    },
    {
        "id": "specs_004",
        "query": "iPhone 14 Pro camera details",
        "category": "specifications",
        "assertions": [
            {"type": "contains", "value": "48", "description": "48MP main camera"},
            {"type": "contains", "value": "camera", "description": "Discusses camera"},
        ]
    },
    {
        "id": "specs_005",
        "query": "Does iPhone 13 support 5G?",
        "category": "specifications",
        "assertions": [
            {"type": "contains_any", "values": ["5G", "yes", "Yes", "supports"], "description": "Confirms 5G support"},
        ]
    },
    {
        "id": "specs_006",
        "query": "iPhone 11 mein 5G hai kya?",
        "category": "specifications_hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["4G", "LTE", "no", "No", "nahi", "doesn't"], "description": "Clarifies no 5G"},
        ]
    },
    {
        "id": "specs_007",
        "query": "iPhone 16 Pro Max processor kaisa hai",
        "category": "specifications_hinglish",
        "assertions": [
            {"type": "contains", "value": "A18", "description": "A18 Pro processor"},
        ]
    },
    {
        "id": "specs_008",
        "query": "iPhone 15 water resistant hai?",
        "category": "specifications_hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["IP68", "water", "resistant", "haan", "yes", "Yes"], "description": "Confirms water resistance"},
        ]
    },
    
    # ===========================================
    # CATEGORY: MULTI-TURN CONVERSATIONS
    # ===========================================
    {
        "id": "multi_001a",
        "query": "iPhone 16 Pro Max 256GB Fair price",
        "category": "multi_turn",
        "session_id": "multi_test_1",
        "assertions": [
            {"type": "contains", "value": "95,399", "description": "Correct base price"},
        ]
    },
    {
        "id": "multi_001b",
        "query": "What about the 1TB variant?",
        "category": "multi_turn",
        "session_id": "multi_test_1",
        "depends_on": "multi_001a",
        "assertions": [
            {"type": "contains", "value": "16 Pro Max", "description": "Remembers model from context"},
            {"type": "contains", "value": "1", "description": "References 1TB"},
            {"type": "contains_price", "min": 100000, "max": 120000, "description": "Higher price for 1TB"},
        ]
    },
    {
        "id": "multi_002a",
        "query": "Show me iPhone 15 Pro",
        "category": "multi_turn",
        "session_id": "multi_test_2",
        "assertions": [
            {"type": "contains", "value": "15 Pro", "description": "Shows iPhone 15 Pro"},
        ]
    },
    {
        "id": "multi_002b",
        "query": "same product in Superb condition",
        "category": "multi_turn",
        "session_id": "multi_test_2",
        "depends_on": "multi_002a",
        "assertions": [
            {"type": "contains", "value": "15 Pro", "description": "Remembers iPhone 15 Pro"},
            {"type": "contains_any", "values": ["Superb", "superb"], "description": "Shows Superb condition"},
        ]
    },
    {
        "id": "multi_003a",
        "query": "iPhone 14 price batao",
        "category": "multi_turn_hinglish",
        "session_id": "multi_test_3",
        "assertions": [
            {"type": "contains", "value": "14", "description": "Shows iPhone 14"},
        ]
    },
    {
        "id": "multi_003b",
        "query": "aur iska 512GB variant?",
        "category": "multi_turn_hinglish",
        "session_id": "multi_test_3",
        "depends_on": "multi_003a",
        "assertions": [
            {"type": "contains", "value": "14", "description": "Remembers iPhone 14"},
            {"type": "contains", "value": "512", "description": "Shows 512GB variant"},
        ]
    },
    
    # ===========================================
    # CATEGORY: POLICY & WARRANTY
    # ===========================================
    {
        "id": "policy_001",
        "query": "What is your warranty policy?",
        "category": "policy",
        "assertions": [
            {"type": "contains_any", "values": ["12 month", "12-month", "1 year", "warranty"], "description": "Mentions warranty duration"},
        ]
    },
    {
        "id": "policy_002",
        "query": "Do you have return policy?",
        "category": "policy",
        "assertions": [
            {"type": "contains_any", "values": ["7 day", "7-day", "return", "refund"], "description": "Mentions return policy"},
        ]
    },
    {
        "id": "policy_003",
        "query": "How is delivery done?",
        "category": "policy",
        "assertions": [
            {"type": "contains_any", "values": ["delivery", "shipping", "days", "free"], "description": "Mentions delivery info"},
        ]
    },
    {
        "id": "policy_004",
        "query": "COD available hai?",
        "category": "policy_hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["COD", "cash", "delivery", "available", "haan", "yes"], "description": "Addresses COD query"},
        ]
    },
    {
        "id": "policy_005",
        "query": "What payment methods do you accept?",
        "category": "policy",
        "assertions": [
            {"type": "contains_any", "values": ["payment", "UPI", "card", "COD", "pay"], "description": "Mentions payment options"},
        ]
    },
    
    # ===========================================
    # CATEGORY: CONDITION GRADES
    # ===========================================
    {
        "id": "condition_001",
        "query": "What is the difference between Fair and Superb condition?",
        "category": "condition",
        "assertions": [
            {"type": "contains", "value": "Fair", "description": "Explains Fair condition"},
            {"type": "contains", "value": "Superb", "description": "Explains Superb condition"},
        ]
    },
    {
        "id": "condition_002",
        "query": "Fair condition mein kya milta hai?",
        "category": "condition_hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["Fair", "scratch", "marks", "80%", "battery"], "description": "Explains Fair condition"},
        ]
    },
    {
        "id": "condition_003",
        "query": "Best condition phone chahiye",
        "category": "condition_hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["Superb", "best", "excellent"], "description": "Recommends Superb condition"},
        ]
    },
    
    # ===========================================
    # CATEGORY: PRODUCT AVAILABILITY
    # ===========================================
    {
        "id": "avail_001",
        "query": "Is iPhone 16 Pro Max available?",
        "category": "availability",
        "assertions": [
            {"type": "contains_any", "values": ["available", "stock", "yes", "Yes", "₹"], "description": "Confirms availability"},
        ]
    },
    {
        "id": "avail_002",
        "query": "Do you have MacBook?",
        "category": "availability",
        "assertions": [
            {"type": "contains_any", "values": ["MacBook", "macbook", "laptop", "available", "yes"], "description": "Addresses MacBook query"},
        ]
    },
    {
        "id": "avail_003",
        "query": "iPhone 16 available colors?",
        "category": "availability",
        "assertions": [
            {"type": "contains_any", "values": ["color", "Black", "White", "Titanium", "Natural", "Desert"], "description": "Lists colors"},
        ]
    },
    {
        "id": "avail_004",
        "query": "Storage options for iPhone 15 Pro Max",
        "category": "availability",
        "assertions": [
            {"type": "contains_any", "values": ["256", "512", "1TB", "GB", "storage"], "description": "Lists storage options"},
        ]
    },
    
    # ===========================================
    # CATEGORY: COMPARISON
    # ===========================================
    {
        "id": "compare_001",
        "query": "iPhone 15 Pro vs iPhone 15 Pro Max",
        "category": "comparison",
        "assertions": [
            {"type": "contains", "value": "15 Pro", "description": "Discusses both models"},
            {"type": "contains_any", "values": ["display", "screen", "size", "battery", "camera"], "description": "Compares features"},
        ]
    },
    {
        "id": "compare_002",
        "query": "Which is better: iPhone 14 Pro or iPhone 15?",
        "category": "comparison",
        "assertions": [
            {"type": "contains", "value": "14 Pro", "description": "Mentions iPhone 14 Pro"},
            {"type": "contains", "value": "15", "description": "Mentions iPhone 15"},
        ]
    },
    
    # ===========================================
    # CATEGORY: GENERAL QUERIES
    # ===========================================
    {
        "id": "general_001",
        "query": "Tell me about GREST",
        "category": "general",
        "assertions": [
            {"type": "contains_any", "values": ["GREST", "refurbished", "iPhone", "quality"], "description": "Describes GREST"},
        ]
    },
    {
        "id": "general_002",
        "query": "Why should I buy from GREST?",
        "category": "general",
        "assertions": [
            {"type": "contains_any", "values": ["warranty", "quality", "refurbished", "checked", "tested"], "description": "Explains GREST benefits"},
        ]
    },
    {
        "id": "general_003",
        "query": "Hello",
        "category": "general",
        "assertions": [
            {"type": "contains_any", "values": ["Hello", "Hi", "help", "GREST", "welcome", "assist"], "description": "Friendly greeting"},
        ]
    },
    {
        "id": "general_004",
        "query": "Thank you",
        "category": "general",
        "assertions": [
            {"type": "contains_any", "values": ["welcome", "pleasure", "help", "happy", "glad", "anytime"], "description": "Polite response"},
        ]
    },
    
    # ===========================================
    # CATEGORY: EDGE CASES / SAFETY
    # ===========================================
    {
        "id": "edge_001",
        "query": "What is the capital of France?",
        "category": "edge_case",
        "assertions": [
            {"type": "contains_any", "values": ["GREST", "iPhone", "help", "product", "refurbished", "sorry"], "description": "Stays on topic or politely declines"},
        ]
    },
    {
        "id": "edge_002",
        "query": "Can you write code for me?",
        "category": "edge_case",
        "assertions": [
            {"type": "not_contains", "value": "def ", "description": "Does not write code"},
            {"type": "not_contains", "value": "function", "description": "Does not write code"},
        ]
    },
    {
        "id": "edge_003",
        "query": "iPhone 99 price",
        "category": "edge_case",
        "assertions": [
            {"type": "contains_any", "values": ["not available", "don't have", "doesn't exist", "available", "iPhone"], "description": "Handles non-existent model"},
        ]
    },
    {
        "id": "edge_004",
        "query": "",
        "category": "edge_case",
        "assertions": [
            {"type": "response_exists", "description": "Handles empty query gracefully"},
        ]
    },
    
    # ===========================================
    # CATEGORY: HINGLISH COMPREHENSIVE
    # ===========================================
    {
        "id": "hinglish_001",
        "query": "sabse sasta iPhone konsa hai?",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_price", "min": 10000, "max": 30000, "description": "Shows budget option"},
            {"type": "contains", "value": "iPhone", "description": "Recommends an iPhone"},
        ]
    },
    {
        "id": "hinglish_002",
        "query": "Mujhe accha camera wala phone chahiye",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["camera", "Pro", "48MP", "MP"], "description": "Recommends camera-focused phone"},
        ]
    },
    {
        "id": "hinglish_003",
        "query": "warranty kitne din ki hai?",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["12", "month", "mahine", "warranty", "year", "saal"], "description": "Explains warranty"},
        ]
    },
    {
        "id": "hinglish_004",
        "query": "yeh phone original hai ya duplicate?",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["original", "genuine", "authentic", "refurbished", "Apple", "quality"], "description": "Clarifies authenticity"},
        ]
    },
    {
        "id": "hinglish_005",
        "query": "store kahan hai aapka?",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["store", "location", "address", "Delhi", "Mumbai", "visit", "grest.in"], "description": "Provides store info"},
        ]
    },
]

# Group tests by category for reporting
def get_tests_by_category():
    categories = {}
    for test in GOLDEN_TESTS:
        cat = test["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(test)
    return categories

# Get all unique session IDs for multi-turn tests
def get_multi_turn_sessions():
    sessions = {}
    for test in GOLDEN_TESTS:
        if "session_id" in test:
            sid = test["session_id"]
            if sid not in sessions:
                sessions[sid] = []
            sessions[sid].append(test)
    return sessions
