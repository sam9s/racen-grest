"""
GRESTA Chatbot Golden Test Dataset - Jovehill Framework
100+ test cases covering all 12 categories with exact DB price validation

Categories:
1. Exact Match - Full specs provided (model + storage + color + condition)
2. Partial Match - Some specs missing
3. Model Only - Just model name
4. Category Search - No specific model (e.g., "Cheapest 256GB iPhone")
5. Budget Range - Price constraint (e.g., "iPhone under 30000")
6. Cheapest - Global minimum
7. Comparison - Two products
8. Specifications - Specs query
9. Availability - Stock check
10. Hinglish - Natural language (including color matching)
11. Negative - Product not available
12. General FAQ - Non-product query

Validation types:
- exact_db_price: Validates price matches exact database value
- contains_price: Validates price within range
- contains: Text contains value
- contains_any: Text contains any of values
- not_contains: Text does not contain value
"""

GOLDEN_TESTS = [
    # ===========================================
    # CATEGORY 1: EXACT MATCH (Full specs)
    # ===========================================
    {
        "id": "exact_001",
        "query": "iPhone 16 Pro Max 256GB Fair condition price",
        "category": "exact_match",
        "expected_model": "iPhone 16 Pro Max",
        "expected_storage": "256 GB",
        "expected_condition": "Fair",
        "expected_db_price": 95399,
        "assertions": [
            {"type": "exact_db_price", "price": 95399, "tolerance": 1000, "description": "Price matches DB"},
            {"type": "contains", "value": "16 Pro Max", "description": "Mentions correct model"},
        ]
    },
    {
        "id": "exact_002",
        "query": "iPhone 16 Pro Max 1TB Superb condition price",
        "category": "exact_match",
        "expected_model": "iPhone 16 Pro Max",
        "expected_storage": "1 TB",
        "expected_condition": "Superb",
        "expected_db_price": 112999,
        "assertions": [
            {"type": "exact_db_price", "price": 112999, "tolerance": 1000, "description": "Price matches DB"},
            {"type": "contains", "value": "16 Pro Max", "description": "Mentions model"},
        ]
    },
    {
        "id": "exact_003",
        "query": "iPhone 15 128GB Fair price",
        "category": "exact_match",
        "expected_db_price": 37999,
        "assertions": [
            {"type": "exact_db_price", "price": 37999, "tolerance": 1000, "description": "Price matches DB"},
            {"type": "contains", "value": "15", "description": "Mentions iPhone 15"},
        ]
    },
    {
        "id": "exact_004",
        "query": "iPhone 14 256GB Superb condition price",
        "category": "exact_match",
        "expected_db_price": 35999,
        "assertions": [
            {"type": "exact_db_price", "price": 35999, "tolerance": 1000, "description": "Price matches DB"},
            {"type": "contains", "value": "14", "description": "Mentions iPhone 14"},
        ]
    },
    {
        "id": "exact_005",
        "query": "iPhone 13 Pro 512GB Superb price",
        "category": "exact_match",
        "expected_db_price": 47999,
        "assertions": [
            {"type": "exact_db_price", "price": 47999, "tolerance": 1000, "description": "Price matches DB"},
            {"type": "contains", "value": "13 Pro", "description": "Mentions model"},
        ]
    },
    {
        "id": "exact_006",
        "query": "iPhone 12 64GB Fair condition kitne ka hai",
        "category": "exact_match",
        "expected_db_price": 18099,
        "assertions": [
            {"type": "exact_db_price", "price": 18099, "tolerance": 1000, "description": "Price matches DB"},
            {"type": "contains", "value": "12", "description": "Mentions iPhone 12"},
        ]
    },
    {
        "id": "exact_007",
        "query": "iPhone 11 128GB Good condition price",
        "category": "exact_match",
        "expected_db_price": 16299,
        "assertions": [
            {"type": "exact_db_price", "price": 16299, "tolerance": 1000, "description": "Price matches DB"},
            {"type": "contains", "value": "11", "description": "Mentions iPhone 11"},
        ]
    },
    {
        "id": "exact_008",
        "query": "iPhone 16 Pro Max 512GB Good price",
        "category": "exact_match",
        "expected_db_price": 99399,
        "assertions": [
            {"type": "exact_db_price", "price": 99399, "tolerance": 2000, "description": "Price matches DB"},
            {"type": "contains", "value": "16 Pro Max", "description": "Mentions model"},
        ]
    },
    {
        "id": "exact_009",
        "query": "iPhone 13 Pro Max 1TB Fair price",
        "category": "exact_match",
        "expected_db_price": 46499,
        "assertions": [
            {"type": "exact_db_price", "price": 46499, "tolerance": 2000, "description": "Price matches DB"},
            {"type": "contains", "value": "13 Pro Max", "description": "Mentions model"},
        ]
    },
    {
        "id": "exact_010",
        "query": "iPhone 15 Plus 256GB Fair condition price",
        "category": "exact_match",
        "expected_db_price": 45999,
        "assertions": [
            {"type": "exact_db_price", "price": 45999, "tolerance": 1000, "description": "Price matches DB"},
            {"type": "contains", "value": "15 Plus", "description": "Mentions model"},
        ]
    },

    # ===========================================
    # CATEGORY 2: PARTIAL MATCH (Some specs missing)
    # ===========================================
    {
        "id": "partial_001",
        "query": "iPhone 16 Pro Max price",
        "category": "partial_match",
        "assertions": [
            {"type": "contains_price", "min": 90000, "max": 120000, "description": "Starting price shown"},
            {"type": "contains", "value": "16 Pro Max", "description": "Mentions model"},
            {"type": "contains_any", "values": ["256", "512", "1 TB", "storage"], "description": "Shows variants"},
        ]
    },
    {
        "id": "partial_002",
        "query": "iPhone 15 Pro 256GB price",
        "category": "partial_match",
        "assertions": [
            {"type": "contains_price", "min": 60000, "max": 80000, "description": "Price in range"},
            {"type": "contains", "value": "15 Pro", "description": "Mentions model"},
        ]
    },
    {
        "id": "partial_003",
        "query": "iPhone 14 Fair condition price",
        "category": "partial_match",
        "assertions": [
            {"type": "contains_price", "min": 30000, "max": 40000, "description": "Fair price shown"},
            {"type": "contains", "value": "14", "description": "Mentions iPhone 14"},
        ]
    },
    {
        "id": "partial_004",
        "query": "iPhone 13 Pro 256GB price",
        "category": "partial_match",
        "assertions": [
            {"type": "contains_price", "min": 40000, "max": 50000, "description": "Price in range"},
            {"type": "contains", "value": "13 Pro", "description": "Mentions model"},
        ]
    },
    {
        "id": "partial_005",
        "query": "iPhone 12 128GB price",
        "category": "partial_match",
        "assertions": [
            {"type": "contains_price", "min": 19000, "max": 25000, "description": "Price in range"},
            {"type": "contains", "value": "12", "description": "Mentions iPhone 12"},
        ]
    },
    {
        "id": "partial_006",
        "query": "iPhone 11 Superb condition price",
        "category": "partial_match",
        "assertions": [
            {"type": "contains_price", "min": 14000, "max": 22000, "description": "Superb price shown"},
            {"type": "contains", "value": "11", "description": "Mentions iPhone 11"},
        ]
    },
    {
        "id": "partial_007",
        "query": "iPhone 16 256GB price",
        "category": "partial_match",
        "assertions": [
            {"type": "contains_price", "min": 50000, "max": 60000, "description": "Price in range"},
            {"type": "contains", "value": "16", "description": "Mentions iPhone 16"},
        ]
    },
    {
        "id": "partial_008",
        "query": "iPhone 15 Plus Fair price",
        "category": "partial_match",
        "assertions": [
            {"type": "contains_price", "min": 43000, "max": 50000, "description": "Price in range"},
            {"type": "contains", "value": "15 Plus", "description": "Mentions model"},
        ]
    },

    # ===========================================
    # CATEGORY 3: MODEL ONLY (Just model name)
    # ===========================================
    {
        "id": "model_001",
        "query": "iPhone 16 Pro Max",
        "category": "model_only",
        "assertions": [
            {"type": "contains_price", "min": 90000, "max": 120000, "description": "Shows price range"},
            {"type": "contains", "value": "16 Pro Max", "description": "Mentions model"},
        ]
    },
    {
        "id": "model_002",
        "query": "iPhone 15 Pro",
        "category": "model_only",
        "assertions": [
            {"type": "contains_price", "min": 60000, "max": 90000, "description": "Shows price range"},
            {"type": "contains", "value": "15 Pro", "description": "Mentions model"},
        ]
    },
    {
        "id": "model_003",
        "query": "iPhone 14 Pro Max",
        "category": "model_only",
        "assertions": [
            {"type": "contains_any", "values": ["14 Pro", "available", "price"], "description": "Shows product info"},
        ]
    },
    {
        "id": "model_004",
        "query": "iPhone 13",
        "category": "model_only",
        "assertions": [
            {"type": "contains_price", "min": 20000, "max": 45000, "description": "Shows price range"},
            {"type": "contains", "value": "13", "description": "Mentions iPhone 13"},
        ]
    },
    {
        "id": "model_005",
        "query": "iPhone 12 Mini",
        "category": "model_only",
        "assertions": [
            {"type": "contains", "value": "12 Mini", "description": "Mentions model"},
        ]
    },
    {
        "id": "model_006",
        "query": "iPhone 11 Pro",
        "category": "model_only",
        "assertions": [
            {"type": "contains_price", "min": 15000, "max": 40000, "description": "Shows price range"},
            {"type": "contains", "value": "11 Pro", "description": "Mentions model"},
        ]
    },
    {
        "id": "model_007",
        "query": "iPhone SE 2020",
        "category": "model_only",
        "assertions": [
            {"type": "contains_any", "values": ["SE", "available", "price", "₹"], "description": "Shows product info"},
        ]
    },
    {
        "id": "model_008",
        "query": "iPhone 14 kitna ka hai",
        "category": "model_only",
        "assertions": [
            {"type": "contains_price", "min": 30000, "max": 45000, "description": "Shows price"},
            {"type": "contains", "value": "14", "description": "Mentions iPhone 14"},
        ]
    },

    # ===========================================
    # CATEGORY 4: CATEGORY SEARCH (No specific model)
    # ===========================================
    {
        "id": "category_001",
        "query": "Cheapest 256GB iPhone",
        "category": "category_search",
        "assertions": [
            {"type": "contains_price", "min": 10000, "max": 30000, "description": "Shows cheapest 256GB"},
            {"type": "contains_any", "values": ["256", "GB", "iPhone"], "description": "Mentions 256GB iPhone"},
        ]
    },
    {
        "id": "category_002",
        "query": "Best camera iPhone under 50000",
        "category": "category_search",
        "assertions": [
            {"type": "contains_any", "values": ["camera", "MP", "Pro", "iPhone"], "description": "Recommends camera phone"},
            {"type": "contains_price", "min": 20000, "max": 50000, "description": "Within budget"},
        ]
    },
    {
        "id": "category_003",
        "query": "512GB storage iPhone available",
        "category": "category_search",
        "assertions": [
            {"type": "contains_any", "values": ["512", "GB", "storage"], "description": "Shows 512GB options"},
        ]
    },
    {
        "id": "category_004",
        "query": "Superb condition iPhones dikhao",
        "category": "category_search",
        "assertions": [
            {"type": "contains_any", "values": ["Superb", "superb", "condition"], "description": "Shows Superb options"},
        ]
    },
    {
        "id": "category_005",
        "query": "Latest iPhone model available",
        "category": "category_search",
        "assertions": [
            {"type": "contains_any", "values": ["16", "latest", "newest", "Pro Max"], "description": "Shows latest model"},
        ]
    },
    {
        "id": "category_006",
        "query": "1TB storage iPhone",
        "category": "category_search",
        "assertions": [
            {"type": "contains_any", "values": ["1 TB", "1TB", "Pro", "Max"], "description": "Shows 1TB options"},
        ]
    },
    {
        "id": "category_007",
        "query": "Good condition iPhone under 25000",
        "category": "category_search",
        "assertions": [
            {"type": "contains_price", "min": 10000, "max": 25000, "description": "Within budget"},
            {"type": "contains_any", "values": ["Good", "iPhone", "₹"], "description": "Shows Good condition"},
        ]
    },
    {
        "id": "category_008",
        "query": "Blue color iPhone available",
        "category": "category_search",
        "assertions": [
            {"type": "contains_any", "values": ["Blue", "blue", "color", "available"], "description": "Shows blue options"},
        ]
    },

    # ===========================================
    # CATEGORY 5: BUDGET RANGE (Price constraint)
    # ===========================================
    {
        "id": "budget_001",
        "query": "iPhone under 20000",
        "category": "budget_range",
        "assertions": [
            {"type": "contains_price", "min": 5000, "max": 20000, "description": "Within budget"},
            {"type": "contains", "value": "iPhone", "description": "Shows iPhones"},
        ]
    },
    {
        "id": "budget_002",
        "query": "iPhone under 30000",
        "category": "budget_range",
        "assertions": [
            {"type": "contains_price", "min": 5000, "max": 30000, "description": "Within budget"},
            {"type": "contains", "value": "iPhone", "description": "Shows iPhones"},
        ]
    },
    {
        "id": "budget_003",
        "query": "iPhone under 50000",
        "category": "budget_range",
        "assertions": [
            {"type": "contains_price", "min": 10000, "max": 50000, "description": "Within budget"},
            {"type": "contains", "value": "iPhone", "description": "Shows iPhones"},
        ]
    },
    {
        "id": "budget_004",
        "query": "20000 se 30000 ke beech mein iPhone",
        "category": "budget_range",
        "assertions": [
            {"type": "contains_price", "min": 18000, "max": 32000, "description": "Within budget range"},
            {"type": "contains", "value": "iPhone", "description": "Shows iPhones"},
        ]
    },
    {
        "id": "budget_005",
        "query": "iPhone 10000 ke andar",
        "category": "budget_range",
        "assertions": [
            {"type": "contains_price", "min": 5000, "max": 10000, "description": "Within budget"},
            {"type": "contains_any", "values": ["iPhone", "6", "7", "available"], "description": "Shows budget iPhones"},
        ]
    },
    {
        "id": "budget_006",
        "query": "Best iPhone under 40000",
        "category": "budget_range",
        "assertions": [
            {"type": "contains_price", "min": 20000, "max": 40000, "description": "Within budget"},
            {"type": "contains", "value": "iPhone", "description": "Shows iPhones"},
        ]
    },
    {
        "id": "budget_007",
        "query": "iPhone 15000 mein milega?",
        "category": "budget_range",
        "assertions": [
            {"type": "contains_any", "values": ["iPhone", "₹", "available", "11", "12"], "description": "Shows budget options"},
        ]
    },
    {
        "id": "budget_008",
        "query": "Premium iPhone above 80000",
        "category": "budget_range",
        "assertions": [
            {"type": "contains_price", "min": 80000, "max": 130000, "description": "Premium range"},
            {"type": "contains_any", "values": ["Pro Max", "16", "15 Pro"], "description": "Shows premium models"},
        ]
    },

    # ===========================================
    # CATEGORY 6: CHEAPEST (Global minimum)
    # ===========================================
    {
        "id": "cheapest_001",
        "query": "Sabse sasta iPhone",
        "category": "cheapest",
        "assertions": [
            {"type": "contains_price", "min": 5000, "max": 10000, "description": "Shows cheapest"},
            {"type": "contains", "value": "iPhone", "description": "Shows iPhone"},
        ]
    },
    {
        "id": "cheapest_002",
        "query": "Cheapest iPhone available",
        "category": "cheapest",
        "assertions": [
            {"type": "contains_price", "min": 5000, "max": 10000, "description": "Shows cheapest"},
            {"type": "contains", "value": "iPhone", "description": "Shows iPhone"},
        ]
    },
    {
        "id": "cheapest_003",
        "query": "Most affordable iPhone",
        "category": "cheapest",
        "assertions": [
            {"type": "contains_price", "min": 5000, "max": 15000, "description": "Shows affordable"},
            {"type": "contains", "value": "iPhone", "description": "Shows iPhone"},
        ]
    },
    {
        "id": "cheapest_004",
        "query": "Budget friendly iPhone dikhao",
        "category": "cheapest",
        "assertions": [
            {"type": "contains_price", "min": 5000, "max": 20000, "description": "Shows budget option"},
            {"type": "contains", "value": "iPhone", "description": "Shows iPhone"},
        ]
    },
    {
        "id": "cheapest_005",
        "query": "Kam price wala iPhone",
        "category": "cheapest",
        "assertions": [
            {"type": "contains_price", "min": 5000, "max": 15000, "description": "Shows low price"},
            {"type": "contains", "value": "iPhone", "description": "Shows iPhone"},
        ]
    },
    {
        "id": "cheapest_006",
        "query": "Entry level iPhone",
        "category": "cheapest",
        "assertions": [
            {"type": "contains_any", "values": ["iPhone", "affordable", "budget", "₹"], "description": "Shows entry option"},
        ]
    },

    # ===========================================
    # CATEGORY 7: COMPARISON (Two products)
    # ===========================================
    {
        "id": "compare_001",
        "query": "iPhone 15 Pro vs iPhone 15 Pro Max",
        "category": "comparison",
        "assertions": [
            {"type": "contains", "value": "15 Pro", "description": "Mentions both models"},
            {"type": "contains_any", "values": ["display", "screen", "camera", "battery", "vs"], "description": "Compares features"},
        ]
    },
    {
        "id": "compare_002",
        "query": "iPhone 14 vs iPhone 15",
        "category": "comparison",
        "assertions": [
            {"type": "contains", "value": "14", "description": "Mentions iPhone 14"},
            {"type": "contains", "value": "15", "description": "Mentions iPhone 15"},
        ]
    },
    {
        "id": "compare_003",
        "query": "iPhone 16 Pro Max vs iPhone 15 Pro Max",
        "category": "comparison",
        "assertions": [
            {"type": "contains", "value": "16 Pro Max", "description": "Mentions iPhone 16 Pro Max"},
            {"type": "contains", "value": "15 Pro Max", "description": "Mentions iPhone 15 Pro Max"},
        ]
    },
    {
        "id": "compare_004",
        "query": "Which is better: iPhone 14 Pro or iPhone 15?",
        "category": "comparison",
        "assertions": [
            {"type": "contains", "value": "14 Pro", "description": "Mentions iPhone 14 Pro"},
            {"type": "contains", "value": "15", "description": "Mentions iPhone 15"},
        ]
    },
    {
        "id": "compare_005",
        "query": "iPhone 13 aur iPhone 14 mein kya farak hai?",
        "category": "comparison",
        "assertions": [
            {"type": "contains", "value": "13", "description": "Mentions iPhone 13"},
            {"type": "contains", "value": "14", "description": "Mentions iPhone 14"},
        ]
    },
    {
        "id": "compare_006",
        "query": "iPhone 12 vs iPhone 13 comparison",
        "category": "comparison",
        "assertions": [
            {"type": "contains", "value": "12", "description": "Mentions iPhone 12"},
            {"type": "contains", "value": "13", "description": "Mentions iPhone 13"},
        ]
    },

    # ===========================================
    # CATEGORY 8: SPECIFICATIONS
    # ===========================================
    {
        "id": "specs_001",
        "query": "iPhone 16 Pro Max specs",
        "category": "specifications",
        "assertions": [
            {"type": "contains_any", "values": ["6.3", "6.9", "display"], "description": "Display info"},
            {"type": "contains", "value": "A18", "description": "Processor info"},
        ]
    },
    {
        "id": "specs_002",
        "query": "iPhone 15 Pro specifications",
        "category": "specifications",
        "assertions": [
            {"type": "contains", "value": "A17", "description": "A17 Pro processor"},
            {"type": "contains_any", "values": ["Titanium", "titanium", "Pro"], "description": "Design info"},
        ]
    },
    {
        "id": "specs_003",
        "query": "iPhone 14 Pro camera details",
        "category": "specifications",
        "assertions": [
            {"type": "contains", "value": "48", "description": "48MP camera"},
            {"type": "contains_any", "values": ["camera", "Camera", "MP"], "description": "Camera info"},
        ]
    },
    {
        "id": "specs_004",
        "query": "iPhone 13 display size",
        "category": "specifications",
        "assertions": [
            {"type": "contains_any", "values": ["6.1", "display", "inch", "screen"], "description": "Display size"},
        ]
    },
    {
        "id": "specs_005",
        "query": "Does iPhone 13 support 5G?",
        "category": "specifications",
        "assertions": [
            {"type": "contains", "value": "5G", "description": "Mentions 5G"},
        ]
    },
    {
        "id": "specs_006",
        "query": "iPhone 11 mein 5G hai kya?",
        "category": "specifications",
        "assertions": [
            {"type": "contains_any", "values": ["4G", "nahi", "no", "doesn't", "LTE"], "description": "Clarifies no 5G"},
        ]
    },
    {
        "id": "specs_007",
        "query": "iPhone 16 Pro Max processor",
        "category": "specifications",
        "assertions": [
            {"type": "contains", "value": "A18", "description": "A18 Pro processor"},
        ]
    },
    {
        "id": "specs_008",
        "query": "iPhone 15 battery life",
        "category": "specifications",
        "assertions": [
            {"type": "contains_any", "values": ["battery", "hour", "video", "playback"], "description": "Battery info"},
        ]
    },
    {
        "id": "specs_009",
        "query": "iPhone 15 water resistant hai?",
        "category": "specifications",
        "assertions": [
            {"type": "contains_any", "values": ["IP68", "water", "resistant", "haan", "yes"], "description": "Water resistance"},
        ]
    },
    {
        "id": "specs_010",
        "query": "iPhone 14 Pro Max ka display type",
        "category": "specifications",
        "assertions": [
            {"type": "contains_any", "values": ["OLED", "Super Retina", "ProMotion", "display"], "description": "Display type"},
        ]
    },

    # ===========================================
    # CATEGORY 9: AVAILABILITY
    # ===========================================
    {
        "id": "avail_001",
        "query": "Is iPhone 16 Pro Max available?",
        "category": "availability",
        "assertions": [
            {"type": "contains_any", "values": ["available", "stock", "yes", "₹"], "description": "Confirms availability"},
        ]
    },
    {
        "id": "avail_002",
        "query": "iPhone 15 Pro Max stock check",
        "category": "availability",
        "assertions": [
            {"type": "contains_any", "values": ["available", "stock", "15 Pro Max", "₹"], "description": "Stock info"},
        ]
    },
    {
        "id": "avail_003",
        "query": "iPhone 14 available colors",
        "category": "availability",
        "assertions": [
            {"type": "contains_any", "values": ["color", "Blue", "Black", "Purple", "Yellow", "Midnight"], "description": "Lists colors"},
        ]
    },
    {
        "id": "avail_004",
        "query": "iPhone 16 storage options",
        "category": "availability",
        "assertions": [
            {"type": "contains_any", "values": ["128", "256", "512", "GB", "storage"], "description": "Lists storage"},
        ]
    },
    {
        "id": "avail_005",
        "query": "Do you have MacBook?",
        "category": "availability",
        "assertions": [
            {"type": "contains_any", "values": ["MacBook", "macbook", "available", "laptop"], "description": "MacBook info"},
        ]
    },
    {
        "id": "avail_006",
        "query": "iPhone 15 kaunse colors mein available hai?",
        "category": "availability",
        "assertions": [
            {"type": "contains_any", "values": ["color", "Blue", "Pink", "Black", "Yellow", "Green"], "description": "Lists colors"},
        ]
    },
    {
        "id": "avail_007",
        "query": "iPhone 13 Pro Max available hai?",
        "category": "availability",
        "assertions": [
            {"type": "contains_any", "values": ["available", "stock", "13 Pro Max", "₹", "haan"], "description": "Availability info"},
        ]
    },

    # ===========================================
    # CATEGORY 10: HINGLISH (Natural language + Color matching)
    # ===========================================
    {
        "id": "hinglish_001",
        "query": "Neela wala iPhone 15 dikhao",
        "category": "hinglish_color",
        "expected_color": "Blue",
        "assertions": [
            {"type": "contains_any", "values": ["Blue", "blue", "15"], "description": "Shows blue iPhone 15"},
        ]
    },
    {
        "id": "hinglish_002",
        "query": "Kaala iPhone 16 price",
        "category": "hinglish_color",
        "expected_color": "Black",
        "assertions": [
            {"type": "contains_any", "values": ["Black", "black", "16", "₹"], "description": "Shows black iPhone 16"},
        ]
    },
    {
        "id": "hinglish_003",
        "query": "Gulabi iPhone chahiye",
        "category": "hinglish_color",
        "expected_color": "Pink",
        "assertions": [
            {"type": "contains_any", "values": ["Pink", "pink", "iPhone"], "description": "Shows pink iPhone"},
        ]
    },
    {
        "id": "hinglish_004",
        "query": "Safed color ka iPhone",
        "category": "hinglish_color",
        "expected_color": "White",
        "assertions": [
            {"type": "contains_any", "values": ["White", "white", "Starlight", "iPhone"], "description": "Shows white iPhone"},
        ]
    },
    {
        "id": "hinglish_005",
        "query": "Golden iPhone dikhao",
        "category": "hinglish_color",
        "expected_color": "Gold",
        "assertions": [
            {"type": "contains_any", "values": ["Gold", "gold", "Desert", "iPhone"], "description": "Shows gold iPhone"},
        ]
    },
    {
        "id": "hinglish_006",
        "query": "Mujhe accha camera wala phone chahiye",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["camera", "Pro", "48MP", "MP"], "description": "Recommends camera phone"},
        ]
    },
    {
        "id": "hinglish_007",
        "query": "Warranty kitne din ki hai?",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["12", "month", "mahine", "warranty", "year"], "description": "Warranty info"},
        ]
    },
    {
        "id": "hinglish_008",
        "query": "Yeh phone original hai ya duplicate?",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["original", "genuine", "authentic", "Apple"], "description": "Authenticity"},
        ]
    },
    {
        "id": "hinglish_009",
        "query": "Store kahan hai aapka?",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["store", "online", "website", "grest.in"], "description": "Store info"},
        ]
    },
    {
        "id": "hinglish_010",
        "query": "EMI option available hai?",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["EMI", "emi", "payment", "available"], "description": "EMI info"},
        ]
    },
    {
        "id": "hinglish_011",
        "query": "Delivery kitne din mein hoti hai?",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["delivery", "days", "din", "shipping"], "description": "Delivery info"},
        ]
    },
    {
        "id": "hinglish_012",
        "query": "COD available hai?",
        "category": "hinglish",
        "assertions": [
            {"type": "contains_any", "values": ["COD", "cash", "delivery", "haan", "yes"], "description": "COD info"},
        ]
    },

    # ===========================================
    # CATEGORY 11: NEGATIVE (Product not available)
    # ===========================================
    {
        "id": "negative_001",
        "query": "iPhone 20 price",
        "category": "negative",
        "assertions": [
            {"type": "contains_any", "values": ["not available", "don't have", "available", "doesn't exist"], "description": "Handles non-existent"},
        ]
    },
    {
        "id": "negative_002",
        "query": "iPhone 99 kitne ka hai",
        "category": "negative",
        "assertions": [
            {"type": "contains_any", "values": ["not available", "available", "don't have", "exist"], "description": "Handles non-existent"},
        ]
    },
    {
        "id": "negative_003",
        "query": "Samsung Galaxy S24 price",
        "category": "negative",
        "assertions": [
            {"type": "contains_any", "values": ["iPhone", "Apple", "GREST", "don't", "only"], "description": "Stays on topic"},
        ]
    },
    {
        "id": "negative_004",
        "query": "OnePlus 12 available hai?",
        "category": "negative",
        "assertions": [
            {"type": "contains_any", "values": ["iPhone", "Apple", "GREST", "refurbished"], "description": "Stays on topic"},
        ]
    },
    {
        "id": "negative_005",
        "query": "iPad Pro 2024",
        "category": "negative",
        "assertions": [
            {"type": "contains_any", "values": ["iPad", "available", "check", "iPhone"], "description": "Handles iPad query"},
        ]
    },
    {
        "id": "negative_006",
        "query": "iPhone 17 Pro release date",
        "category": "negative",
        "assertions": [
            {"type": "contains_any", "values": ["not available", "available", "current", "16"], "description": "Handles future model"},
        ]
    },

    # ===========================================
    # CATEGORY 12: GENERAL FAQ (Non-product queries)
    # ===========================================
    {
        "id": "faq_001",
        "query": "What is your warranty policy?",
        "category": "general_faq",
        "assertions": [
            {"type": "contains_any", "values": ["12 month", "12-month", "warranty", "year"], "description": "Warranty info"},
        ]
    },
    {
        "id": "faq_002",
        "query": "Return policy kya hai?",
        "category": "general_faq",
        "assertions": [
            {"type": "contains_any", "values": ["7 day", "7-day", "return", "refund", "replacement"], "description": "Return policy"},
        ]
    },
    {
        "id": "faq_003",
        "query": "How is delivery done?",
        "category": "general_faq",
        "assertions": [
            {"type": "contains_any", "values": ["delivery", "shipping", "free", "days"], "description": "Delivery info"},
        ]
    },
    {
        "id": "faq_004",
        "query": "What payment methods do you accept?",
        "category": "general_faq",
        "assertions": [
            {"type": "contains_any", "values": ["payment", "UPI", "card", "COD", "pay"], "description": "Payment info"},
        ]
    },
    {
        "id": "faq_005",
        "query": "Tell me about GREST",
        "category": "general_faq",
        "assertions": [
            {"type": "contains_any", "values": ["GREST", "refurbished", "iPhone", "quality"], "description": "About GREST"},
        ]
    },
    {
        "id": "faq_006",
        "query": "Why should I buy from GREST?",
        "category": "general_faq",
        "assertions": [
            {"type": "contains_any", "values": ["warranty", "quality", "refurbished", "checked"], "description": "GREST benefits"},
        ]
    },
    {
        "id": "faq_007",
        "query": "Fair aur Superb condition mein kya farak hai?",
        "category": "general_faq",
        "assertions": [
            {"type": "contains", "value": "Fair", "description": "Explains Fair"},
            {"type": "contains", "value": "Superb", "description": "Explains Superb"},
        ]
    },
    {
        "id": "faq_008",
        "query": "What is the difference between Good and Superb condition?",
        "category": "general_faq",
        "assertions": [
            {"type": "contains_any", "values": ["Good", "Superb", "condition", "battery"], "description": "Condition info"},
        ]
    },
    {
        "id": "faq_009",
        "query": "Do you sell original Apple products?",
        "category": "general_faq",
        "assertions": [
            {"type": "contains_any", "values": ["original", "Apple", "genuine", "authentic", "refurbished"], "description": "Authenticity"},
        ]
    },
    {
        "id": "faq_010",
        "query": "Hello",
        "category": "general_faq",
        "assertions": [
            {"type": "contains_any", "values": ["Hello", "Hi", "help", "GREST", "welcome"], "description": "Greeting"},
        ]
    },
    {
        "id": "faq_011",
        "query": "Thank you for your help",
        "category": "general_faq",
        "assertions": [
            {"type": "contains_any", "values": ["welcome", "pleasure", "help", "happy", "anytime"], "description": "Polite response"},
        ]
    },

    # ===========================================
    # EDGE CASES / SAFETY
    # ===========================================
    {
        "id": "edge_001",
        "query": "What is the capital of France?",
        "category": "edge_case",
        "assertions": [
            {"type": "contains_any", "values": ["GREST", "iPhone", "help", "product"], "description": "Stays on topic"},
        ]
    },
    {
        "id": "edge_002",
        "query": "Can you write code for me?",
        "category": "edge_case",
        "assertions": [
            {"type": "not_contains", "value": "def ", "description": "No code"},
            {"type": "not_contains", "value": "function", "description": "No code"},
        ]
    },
    {
        "id": "edge_003",
        "query": "Tell me a joke",
        "category": "edge_case",
        "assertions": [
            {"type": "contains_any", "values": ["GREST", "iPhone", "help", "product", "refurbished"], "description": "Stays on topic"},
        ]
    },
    {
        "id": "edge_004",
        "query": "",
        "category": "edge_case",
        "skip": True,
        "assertions": [
            {"type": "response_exists", "description": "Handles empty query"},
        ]
    },

    # ===========================================
    # MULTI-TURN CONVERSATIONS
    # ===========================================
    {
        "id": "multi_001a",
        "query": "iPhone 16 Pro Max 256GB Fair price",
        "category": "multi_turn",
        "session_id": "multi_session_1",
        "assertions": [
            {"type": "exact_db_price", "price": 95399, "tolerance": 1000, "description": "Price matches DB"},
            {"type": "contains", "value": "16 Pro Max", "description": "Mentions model"},
        ]
    },
    {
        "id": "multi_001b",
        "query": "What about the 512GB variant?",
        "category": "multi_turn",
        "session_id": "multi_session_1",
        "depends_on": "multi_001a",
        "assertions": [
            {"type": "contains", "value": "16 Pro Max", "description": "Remembers model"},
            {"type": "contains_any", "values": ["512", "GB"], "description": "Shows 512GB"},
        ]
    },
    {
        "id": "multi_002a",
        "query": "Show me iPhone 15 Pro",
        "category": "multi_turn",
        "session_id": "multi_session_2",
        "assertions": [
            {"type": "contains", "value": "15 Pro", "description": "Shows iPhone 15 Pro"},
        ]
    },
    {
        "id": "multi_002b",
        "query": "Same in Superb condition",
        "category": "multi_turn",
        "session_id": "multi_session_2",
        "depends_on": "multi_002a",
        "assertions": [
            {"type": "contains", "value": "15 Pro", "description": "Remembers model"},
            {"type": "contains_any", "values": ["Superb", "superb"], "description": "Shows Superb"},
        ]
    },
    {
        "id": "multi_003a",
        "query": "iPhone 14 price batao",
        "category": "multi_turn",
        "session_id": "multi_session_3",
        "assertions": [
            {"type": "contains", "value": "14", "description": "Shows iPhone 14"},
        ]
    },
    {
        "id": "multi_003b",
        "query": "Iska 512GB wala?",
        "category": "multi_turn",
        "session_id": "multi_session_3",
        "depends_on": "multi_003a",
        "assertions": [
            {"type": "contains", "value": "14", "description": "Remembers iPhone 14"},
            {"type": "contains_any", "values": ["512", "GB"], "description": "Shows 512GB"},
        ]
    },
]

# Group tests by category for reporting
def get_tests_by_category():
    categories = {}
    for test in GOLDEN_TESTS:
        if test.get("skip"):
            continue
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

# Get test count
def get_test_count():
    return len([t for t in GOLDEN_TESTS if not t.get("skip")])

# Category descriptions for reporting
CATEGORY_DESCRIPTIONS = {
    "exact_match": "Exact Match - Full specs (model + storage + condition)",
    "partial_match": "Partial Match - Some specs missing",
    "model_only": "Model Only - Just model name",
    "category_search": "Category Search - No specific model",
    "budget_range": "Budget Range - Price constraint",
    "cheapest": "Cheapest - Global minimum price",
    "comparison": "Comparison - Two products",
    "specifications": "Specifications - Tech specs queries",
    "availability": "Availability - Stock check",
    "hinglish_color": "Hinglish Color - Color matching in Hindi",
    "hinglish": "Hinglish - Natural language Hindi-English",
    "negative": "Negative - Product not available",
    "general_faq": "General FAQ - Non-product queries",
    "edge_case": "Edge Cases - Safety and bounds",
    "multi_turn": "Multi-turn - Conversation context",
}
