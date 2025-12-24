"""
Comprehensive Pricing Accuracy Test Suite for GRESTA Chatbot
=============================================================

This test suite validates that the chatbot returns correct database prices
for all types of product queries. It serves as a blueprint for testing
any e-commerce Shopify-based chatbot.

Test Categories:
1. Direct model queries (iPhone 13, MacBook Air, etc.)
2. Cheapest/budget queries (sasta phone, cheap mobile)
3. Premium/expensive queries (costly device, flagship)
4. Price range queries (under 30000, between 20-40k)
5. Hinglish queries (kya hai aapke pass, dikhao)
6. Vague/contextual queries (good phone, best camera)
7. Multi-turn context queries (same product, that one)

Usage:
    python test_pricing_accuracy.py
    
Results are saved to test_results.json for analysis.
"""

import json
import re
import sys
from datetime import datetime
from typing import Dict, List, Tuple

from database import get_db_session, GRESTProduct, search_product_by_specs, get_cheapest_product, get_premium_products
from chatbot_engine import get_product_context_from_database, generate_response


def get_database_prices() -> Dict[str, float]:
    """Get actual prices from database for validation."""
    prices = {}
    try:
        with get_db_session() as session:
            products = session.query(GRESTProduct).filter(GRESTProduct.in_stock == True).all()
            for p in products:
                key = f"{p.name}|{p.storage}|{p.condition}"
                prices[key] = float(p.price)
                
                model_key = p.name.lower().replace('apple ', '')
                if model_key not in prices:
                    prices[model_key] = float(p.price)
    except Exception as e:
        print(f"Error fetching prices: {e}")
    return prices


def extract_prices_from_response(response: str) -> List[int]:
    """Extract all Rs. prices from a response string."""
    patterns = [
        r'Rs\.?\s*([\d,]+)',
        r'₹\s*([\d,]+)',
        r'INR\s*([\d,]+)',
        r'starting.*?(\d{1,2},\d{3})',
        r'(\d{1,2},\d{3})\s*(?:rupees|rs)',
    ]
    
    prices = []
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        for match in matches:
            try:
                price = int(match.replace(',', ''))
                if 1000 <= price <= 200000:
                    prices.append(price)
            except:
                pass
    return list(set(prices))


def validate_price_in_database(price: int, tolerance: int = 100) -> bool:
    """Check if a price exists in our database (with tolerance)."""
    try:
        with get_db_session() as session:
            products = session.query(GRESTProduct).filter(
                GRESTProduct.in_stock == True,
                GRESTProduct.price.between(price - tolerance, price + tolerance)
            ).all()
            return len(products) > 0
    except:
        return False


def run_context_test(query: str, expected_keywords: List[str] = None) -> Dict:
    """Test if get_product_context_from_database returns expected content."""
    result = {
        "query": query,
        "passed": False,
        "context_length": 0,
        "has_prices": False,
        "prices_found": [],
        "expected_keywords_found": [],
        "missing_keywords": []
    }
    
    try:
        context = get_product_context_from_database(query)
        result["context_length"] = len(context)
        result["prices_found"] = extract_prices_from_response(context)
        result["has_prices"] = len(result["prices_found"]) > 0
        
        if expected_keywords:
            for kw in expected_keywords:
                if kw.lower() in context.lower():
                    result["expected_keywords_found"].append(kw)
                else:
                    result["missing_keywords"].append(kw)
            
            result["passed"] = len(result["missing_keywords"]) == 0 and result["has_prices"]
        else:
            result["passed"] = result["has_prices"]
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def run_response_test(query: str, expected_price_range: Tuple[int, int] = None) -> Dict:
    """Test if generate_response returns correct pricing."""
    result = {
        "query": query,
        "passed": False,
        "response_excerpt": "",
        "prices_found": [],
        "prices_valid": True,
        "expected_price_range": expected_price_range
    }
    
    try:
        response = generate_response(query)
        full_response = response.get("response", "")
        result["response_excerpt"] = full_response[:300] + "..." if len(full_response) > 300 else full_response
        result["prices_found"] = extract_prices_from_response(full_response)
        
        if result["prices_found"]:
            for price in result["prices_found"]:
                if not validate_price_in_database(price):
                    result["prices_valid"] = False
                    result["invalid_price"] = price
                    break
        
            if expected_price_range:
                min_p, max_p = expected_price_range
                result["passed"] = any(min_p <= p <= max_p for p in result["prices_found"]) and result["prices_valid"]
            else:
                result["passed"] = result["prices_valid"]
        else:
            result["passed"] = False
            result["error"] = "No prices found in response"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


TEST_CASES = [
    # Category 1: Direct model queries
    {"query": "iPhone 13 price", "category": "direct_model", "expected_keywords": ["iPhone 13", "Rs."]},
    {"query": "iPhone 11 kitne ka hai", "category": "direct_model", "expected_keywords": ["iPhone 11", "Rs."]},
    {"query": "iPhone XR cost", "category": "direct_model", "expected_keywords": ["iPhone XR", "Rs."]},
    {"query": "iPhone 14 Pro", "category": "direct_model", "expected_keywords": ["iPhone 14", "Rs."]},
    {"query": "iPhone 12 128GB price", "category": "direct_model", "expected_keywords": ["iPhone 12", "128", "Rs."]},
    {"query": "MacBook Air price", "category": "direct_model", "expected_keywords": ["MacBook", "Rs."]},
    {"query": "iPhone X kya price hai", "category": "direct_model", "expected_keywords": ["iPhone X", "Rs."]},
    {"query": "iPhone 15 available?", "category": "direct_model", "expected_keywords": ["iPhone 15"]},
    {"query": "iPhone 13 Pro Max", "category": "direct_model", "expected_keywords": ["iPhone 13 Pro", "Rs."]},
    {"query": "iPhone SE price", "category": "direct_model", "expected_keywords": ["iPhone SE", "Rs."]},
    
    # Category 2: Cheapest/budget queries
    {"query": "cheapest iPhone", "category": "cheapest", "expected_keywords": ["CHEAPEST", "Rs."]},
    {"query": "sabse sasta phone", "category": "cheapest", "expected_keywords": ["CHEAPEST", "Rs."]},
    {"query": "low budget mobile", "category": "cheapest", "expected_keywords": ["Rs."]},
    {"query": "any cheap mobile", "category": "cheapest", "expected_keywords": ["CHEAPEST", "Rs."]},
    {"query": "budget iPhone chahiye", "category": "cheapest", "expected_keywords": ["Rs."]},
    {"query": "sasta wala dikhao", "category": "cheapest", "expected_keywords": ["Rs."]},
    {"query": "cheapest MacBook", "category": "cheapest", "expected_keywords": ["CHEAPEST", "MacBook", "Rs."]},
    {"query": "kam budget mein kya milega", "category": "cheapest", "expected_keywords": ["Rs."]},
    {"query": "lowest price phone", "category": "cheapest", "expected_keywords": ["CHEAPEST", "Rs."]},
    {"query": "any low budget", "category": "cheapest", "expected_keywords": ["Rs."]},
    
    # Category 3: Premium/expensive queries
    {"query": "costly device", "category": "premium", "expected_keywords": ["PREMIUM", "Rs."]},
    {"query": "expensive iPhone", "category": "premium", "expected_keywords": ["PREMIUM", "Rs."]},
    {"query": "flagship phone", "category": "premium", "expected_keywords": ["PREMIUM", "Rs."]},
    {"query": "high end mobile", "category": "premium", "expected_keywords": ["PREMIUM", "Rs."]},
    {"query": "mehenga wala", "category": "premium", "expected_keywords": ["PREMIUM", "Rs."]},
    {"query": "premium MacBook", "category": "premium", "expected_keywords": ["PREMIUM", "MacBook", "Rs."]},
    {"query": "best flagship available", "category": "premium", "expected_keywords": ["PREMIUM", "Rs."]},
    
    # Category 4: Price range queries
    {"query": "iPhone under 20000", "category": "price_range", "expected_keywords": ["Rs."]},
    {"query": "phone under 30k", "category": "price_range", "expected_keywords": ["Rs."]},
    {"query": "iPhone between 25000 and 40000", "category": "price_range", "expected_keywords": ["Rs."]},
    {"query": "mobile 15000 se kam", "category": "price_range", "expected_keywords": ["Rs."]},
    {"query": "MacBook under 50000", "category": "price_range", "expected_keywords": ["Rs."]},
    {"query": "20-30k mein kya milega", "category": "price_range", "expected_keywords": ["Rs."]},
    
    # Category 5: Hinglish/conversational queries
    {"query": "kya hai fr aapke pass", "category": "hinglish", "expected_keywords": ["Rs."]},
    {"query": "dikhao kya kya hai", "category": "hinglish", "expected_keywords": ["Rs."]},
    {"query": "sab products batao", "category": "hinglish", "expected_keywords": ["Rs."]},
    {"query": "tumhare pass kya available hai", "category": "hinglish", "expected_keywords": ["Rs."]},
    {"query": "list karo sab", "category": "hinglish", "expected_keywords": ["Rs."]},
    {"query": "kaunsa lena chahiye", "category": "hinglish", "expected_keywords": ["Rs."]},
    {"query": "best wala suggest karo", "category": "hinglish", "expected_keywords": ["Rs."]},
    
    # Category 6: Recommendation queries
    {"query": "best phone for camera", "category": "recommendation", "expected_keywords": ["Rs."]},
    {"query": "suggest a good iPhone", "category": "recommendation", "expected_keywords": ["Rs."]},
    {"query": "which phone should I buy", "category": "recommendation", "expected_keywords": ["Rs."]},
    {"query": "recommend a device", "category": "recommendation", "expected_keywords": ["Rs."]},
    {"query": "help me choose", "category": "recommendation", "expected_keywords": ["Rs."]},
    {"query": "good phone for video", "category": "recommendation", "expected_keywords": ["Rs."]},
    
    # Category 7: Edge cases
    {"query": "iPhone", "category": "edge_case", "expected_keywords": ["Rs."]},
    {"query": "phone", "category": "edge_case", "expected_keywords": ["Rs."]},
    {"query": "mobile", "category": "edge_case", "expected_keywords": ["Rs."]},
    {"query": "refurbished phone", "category": "edge_case", "expected_keywords": ["Rs."]},
    {"query": "second hand iPhone", "category": "edge_case", "expected_keywords": ["Rs."]},
]


def run_all_tests(test_type: str = "context") -> Dict:
    """Run all test cases and return results."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "test_type": test_type,
        "total_tests": len(TEST_CASES),
        "passed": 0,
        "failed": 0,
        "by_category": {},
        "details": []
    }
    
    for i, test in enumerate(TEST_CASES):
        print(f"\n[{i+1}/{len(TEST_CASES)}] Testing: {test['query']}")
        
        if test_type == "context":
            result = run_context_test(test["query"], test.get("expected_keywords"))
        else:
            result = run_response_test(test["query"])
        
        result["category"] = test["category"]
        
        if result["passed"]:
            results["passed"] += 1
            print(f"  ✅ PASSED - Prices: {result.get('prices_found', [])}")
        else:
            results["failed"] += 1
            print(f"  ❌ FAILED - {result.get('error', result.get('missing_keywords', 'Unknown'))}")
        
        cat = test["category"]
        if cat not in results["by_category"]:
            results["by_category"][cat] = {"passed": 0, "failed": 0}
        
        if result["passed"]:
            results["by_category"][cat]["passed"] += 1
        else:
            results["by_category"][cat]["failed"] += 1
        
        results["details"].append(result)
    
    results["accuracy"] = round(results["passed"] / results["total_tests"] * 100, 2)
    
    return results


def print_summary(results: Dict):
    """Print a formatted summary of test results."""
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    print(f"Timestamp: {results['timestamp']}")
    print(f"Test Type: {results['test_type']}")
    print(f"\nOverall: {results['passed']}/{results['total_tests']} passed ({results['accuracy']}%)")
    print("\nBy Category:")
    for cat, stats in results["by_category"].items():
        total = stats["passed"] + stats["failed"]
        pct = round(stats["passed"] / total * 100, 1) if total > 0 else 0
        status = "✅" if pct == 100 else "⚠️" if pct >= 80 else "❌"
        print(f"  {status} {cat}: {stats['passed']}/{total} ({pct}%)")
    
    if results["failed"] > 0:
        print("\nFailed Tests:")
        for detail in results["details"]:
            if not detail["passed"]:
                print(f"  - {detail['query']}")
                if detail.get("missing_keywords"):
                    print(f"    Missing: {detail['missing_keywords']}")
                if detail.get("error"):
                    print(f"    Error: {detail['error']}")


if __name__ == "__main__":
    print("="*60)
    print("GRESTA Chatbot Pricing Accuracy Test Suite")
    print("="*60)
    
    test_type = sys.argv[1] if len(sys.argv) > 1 else "context"
    
    print(f"\nRunning {test_type} tests...")
    print("This will test if the chatbot injects correct database prices.\n")
    
    results = run_all_tests(test_type)
    
    print_summary(results)
    
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: test_results.json")
    print(f"\nFinal Accuracy: {results['accuracy']}%")
    
    if results['accuracy'] >= 95:
        print("✅ PASS: Accuracy meets 95% threshold")
        sys.exit(0)
    else:
        print("❌ FAIL: Accuracy below 95% threshold")
        sys.exit(1)
