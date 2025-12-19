"""
GRESTA Chatbot Stress Test Suite
Tests 50+ queries across various permutations of iPhone models, storage, conditions, and query styles.
Validates each response against the PostgreSQL database for accuracy.
"""

import requests
import re
import json
import time
from datetime import datetime
from database import get_db_session, GRESTProduct

API_URL = "http://localhost:8080/api/chat"

TEST_CASES = [
    {"id": 1, "query": "iPhone 12 price", "model": "iPhone 12", "storage": None, "condition": None, "type": "general"},
    {"id": 2, "query": "iPhone 12 specs and price", "model": "iPhone 12", "storage": None, "condition": None, "type": "general"},
    {"id": 3, "query": "iPhone 13 price", "model": "iPhone 13", "storage": None, "condition": None, "type": "general"},
    {"id": 4, "query": "iPhone 14 price", "model": "iPhone 14", "storage": None, "condition": None, "type": "general"},
    {"id": 5, "query": "iPhone 11 price", "model": "iPhone 11", "storage": None, "condition": None, "type": "general"},
    
    {"id": 6, "query": "iPhone 12 Pro price", "model": "iPhone 12 Pro", "storage": None, "condition": None, "type": "pro_variant"},
    {"id": 7, "query": "iPhone 12 Pro Max price", "model": "iPhone 12 Pro Max", "storage": None, "condition": None, "type": "pro_variant"},
    {"id": 8, "query": "iPhone 13 Pro price", "model": "iPhone 13 Pro", "storage": None, "condition": None, "type": "pro_variant"},
    {"id": 9, "query": "iPhone 13 Pro Max price", "model": "iPhone 13 Pro Max", "storage": None, "condition": None, "type": "pro_variant"},
    {"id": 10, "query": "iPhone 11 Pro price", "model": "iPhone 11 Pro", "storage": None, "condition": None, "type": "pro_variant"},
    {"id": 11, "query": "iPhone 11 Pro Max price", "model": "iPhone 11 Pro Max", "storage": None, "condition": None, "type": "pro_variant"},
    
    {"id": 12, "query": "iPhone 12 mini price", "model": "iPhone 12 Mini", "storage": None, "condition": None, "type": "mini_variant"},
    {"id": 13, "query": "iPhone 13 mini price", "model": "iPhone 13 Mini", "storage": None, "condition": None, "type": "mini_variant"},
    
    {"id": 14, "query": "iPhone 12 64GB price", "model": "iPhone 12", "storage": "64 GB", "condition": None, "type": "storage_specific"},
    {"id": 15, "query": "iPhone 12 128GB price", "model": "iPhone 12", "storage": "128 GB", "condition": None, "type": "storage_specific"},
    {"id": 16, "query": "iPhone 13 128GB price", "model": "iPhone 13", "storage": "128 GB", "condition": None, "type": "storage_specific"},
    {"id": 17, "query": "iPhone 13 256GB price", "model": "iPhone 13", "storage": "256 GB", "condition": None, "type": "storage_specific"},
    {"id": 18, "query": "iPhone 14 128GB price", "model": "iPhone 14", "storage": "128 GB", "condition": None, "type": "storage_specific"},
    {"id": 19, "query": "iPhone 12 Pro 128GB price", "model": "iPhone 12 Pro", "storage": "128 GB", "condition": None, "type": "storage_specific"},
    {"id": 20, "query": "iPhone 12 Pro Max 256GB price", "model": "iPhone 12 Pro Max", "storage": "256 GB", "condition": None, "type": "storage_specific"},
    
    {"id": 21, "query": "iPhone 12 Fair condition price", "model": "iPhone 12", "storage": None, "condition": "Fair", "type": "condition_specific"},
    {"id": 22, "query": "iPhone 12 Good condition price", "model": "iPhone 12", "storage": None, "condition": "Good", "type": "condition_specific"},
    {"id": 23, "query": "iPhone 12 Superb condition price", "model": "iPhone 12", "storage": None, "condition": "Superb", "type": "condition_specific"},
    {"id": 24, "query": "iPhone 13 Fair price", "model": "iPhone 13", "storage": None, "condition": "Fair", "type": "condition_specific"},
    {"id": 25, "query": "iPhone 13 Good price", "model": "iPhone 13", "storage": None, "condition": "Good", "type": "condition_specific"},
    
    {"id": 26, "query": "iPhone 12 64GB Fair price", "model": "iPhone 12", "storage": "64 GB", "condition": "Fair", "type": "full_variant"},
    {"id": 27, "query": "iPhone 12 64GB Good price", "model": "iPhone 12", "storage": "64 GB", "condition": "Good", "type": "full_variant"},
    {"id": 28, "query": "iPhone 12 64GB Superb price", "model": "iPhone 12", "storage": "64 GB", "condition": "Superb", "type": "full_variant"},
    {"id": 29, "query": "iPhone 12 128GB Fair condition price", "model": "iPhone 12", "storage": "128 GB", "condition": "Fair", "type": "full_variant"},
    {"id": 30, "query": "iPhone 12 128GB Good price", "model": "iPhone 12", "storage": "128 GB", "condition": "Good", "type": "full_variant"},
    {"id": 31, "query": "iPhone 13 128GB Fair price", "model": "iPhone 13", "storage": "128 GB", "condition": "Fair", "type": "full_variant"},
    {"id": 32, "query": "iPhone 12 Pro 128GB Fair price", "model": "iPhone 12 Pro", "storage": "128 GB", "condition": "Fair", "type": "full_variant"},
    {"id": 33, "query": "iPhone 12 mini 64GB Fair price", "model": "iPhone 12 Mini", "storage": "64 GB", "condition": "Fair", "type": "full_variant"},
    
    {"id": 34, "query": "iPhone 12 ka price kya hai", "model": "iPhone 12", "storage": None, "condition": None, "type": "hinglish"},
    {"id": 35, "query": "iPhone 13 kitne ka hai", "model": "iPhone 13", "storage": None, "condition": None, "type": "hinglish"},
    {"id": 36, "query": "iPhone 12 Pro ka rate batao", "model": "iPhone 12 Pro", "storage": None, "condition": None, "type": "hinglish"},
    {"id": 37, "query": "sabse sasta iPhone", "model": None, "storage": None, "condition": None, "type": "cheapest"},
    {"id": 38, "query": "cheapest iPhone available", "model": None, "storage": None, "condition": None, "type": "cheapest"},
    {"id": 39, "query": "lowest price iPhone", "model": None, "storage": None, "condition": None, "type": "cheapest"},
    
    {"id": 40, "query": "iPhone under 20000", "model": None, "storage": None, "condition": None, "type": "price_range"},
    {"id": 41, "query": "iPhone under 25000", "model": None, "storage": None, "condition": None, "type": "price_range"},
    {"id": 42, "query": "iPhone under 30000", "model": None, "storage": None, "condition": None, "type": "price_range"},
    {"id": 43, "query": "iPhone between 20000 and 30000", "model": None, "storage": None, "condition": None, "type": "price_range"},
    {"id": 44, "query": "iPhones between 25000 to 35000", "model": None, "storage": None, "condition": None, "type": "price_range"},
    
    {"id": 45, "query": "What is the cost of iPhone 12", "model": "iPhone 12", "storage": None, "condition": None, "type": "natural_language"},
    {"id": 46, "query": "How much does iPhone 13 cost", "model": "iPhone 13", "storage": None, "condition": None, "type": "natural_language"},
    {"id": 47, "query": "Tell me iPhone 12 Pro pricing", "model": "iPhone 12 Pro", "storage": None, "condition": None, "type": "natural_language"},
    {"id": 48, "query": "Show me iPhone 14 price details", "model": "iPhone 14", "storage": None, "condition": None, "type": "natural_language"},
    {"id": 49, "query": "I want to know iPhone 13 Pro Max price", "model": "iPhone 13 Pro Max", "storage": None, "condition": None, "type": "natural_language"},
    {"id": 50, "query": "Give me the price for iPhone 11 128GB", "model": "iPhone 11", "storage": "128 GB", "condition": None, "type": "natural_language"},
    
    {"id": 51, "query": "iPhone 12 pro price", "model": "iPhone 12 Pro", "storage": None, "condition": None, "type": "case_sensitivity"},
    {"id": 52, "query": "iphone 12 PRO MAX price", "model": "iPhone 12 Pro Max", "storage": None, "condition": None, "type": "case_sensitivity"},
    {"id": 53, "query": "IPHONE 13 MINI price", "model": "iPhone 13 Mini", "storage": None, "condition": None, "type": "case_sensitivity"},
    
    {"id": 54, "query": "iPhone SE price", "model": "iPhone SE", "storage": None, "condition": None, "type": "edge_case"},
    {"id": 55, "query": "iPhone 15 price", "model": "iPhone 15", "storage": None, "condition": None, "type": "edge_case"},
]


def get_db_ground_truth(model: str, storage: str = None, condition: str = None):
    """Query database for ground truth pricing."""
    if not model:
        return None
    
    with get_db_session() as db:
        if db is None:
            return None
        
        model_normalized = model.strip()
        model_lower = model_normalized.lower()
        
        all_suffixes = ['mini', 'pro max', 'pro', 'plus', 'ultra', 'se', 'new', 'max', 'air']
        exclude_suffixes = []
        for suffix in all_suffixes:
            if suffix not in model_lower:
                exclude_suffixes.append(suffix)
        
        if 'pro max' in model_lower:
            if 'pro' in exclude_suffixes:
                exclude_suffixes.remove('pro')
            if 'max' in exclude_suffixes:
                exclude_suffixes.remove('max')
        
        query = db.query(GRESTProduct).filter(
            GRESTProduct.name.ilike(f"%{model_normalized}%"),
            GRESTProduct.in_stock == True
        )
        
        for suffix in exclude_suffixes:
            query = query.filter(~GRESTProduct.name.ilike(f"% {suffix}%"))
        
        if storage:
            storage_clean = storage.upper().replace(' ', '').replace('GB', ' GB').replace('TB', ' TB').strip()
            query = query.filter(GRESTProduct.storage.ilike(f"%{storage_clean}%"))
        
        if condition:
            query = query.filter(GRESTProduct.condition.ilike(f"%{condition}%"))
        
        product = query.order_by(GRESTProduct.price.asc()).first()
        
        if product:
            return {
                'name': product.name,
                'storage': product.storage,
                'condition': product.condition,
                'price': float(product.price),
                'in_stock': product.in_stock
            }
        return None


def get_cheapest_iphone():
    """Get the cheapest in-stock iPhone."""
    with get_db_session() as db:
        if db is None:
            return None
        
        product = db.query(GRESTProduct).filter(
            GRESTProduct.category == 'iPhone',
            GRESTProduct.in_stock == True
        ).order_by(GRESTProduct.price.asc()).first()
        
        if product:
            return {
                'name': product.name,
                'storage': product.storage,
                'condition': product.condition,
                'price': float(product.price)
            }
        return None


def get_iphones_under_price(max_price: float):
    """Get iPhones under a certain price."""
    with get_db_session() as db:
        if db is None:
            return []
        
        products = db.query(GRESTProduct).filter(
            GRESTProduct.category == 'iPhone',
            GRESTProduct.in_stock == True,
            GRESTProduct.price <= max_price
        ).order_by(GRESTProduct.price.asc()).limit(5).all()
        
        return [{'name': p.name, 'price': float(p.price), 'storage': p.storage, 'condition': p.condition} for p in products]


def extract_price_from_response(response: str) -> list:
    """Extract all prices mentioned in the response."""
    patterns = [
        r'₹\s*([\d,]+)',
        r'Rs\.?\s*([\d,]+)',
        r'INR\s*([\d,]+)',
        r'starting.*?(\d{1,2},?\d{3})',
        r'price.*?(\d{1,2},?\d{3})',
    ]
    
    prices = []
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        for match in matches:
            try:
                price = float(match.replace(',', ''))
                if 5000 <= price <= 200000:
                    prices.append(price)
            except:
                pass
    
    return list(set(prices))


def call_chatbot(query: str, session_id: str) -> str:
    """Call the GRESTA chatbot API."""
    try:
        response = requests.post(
            API_URL,
            json={"message": query, "session_id": session_id},
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get('response', '')
        return f"ERROR: Status {response.status_code}"
    except Exception as e:
        return f"ERROR: {str(e)}"


def run_stress_test():
    """Run all stress tests and generate report."""
    print("=" * 70)
    print("GRESTA STRESS TEST - Starting...")
    print(f"Total test cases: {len(TEST_CASES)}")
    print("=" * 70)
    
    results = []
    passed = 0
    failed = 0
    warnings = 0
    
    for i, test in enumerate(TEST_CASES):
        print(f"\nTest {test['id']}/{len(TEST_CASES)}: {test['query'][:50]}...")
        
        session_id = f"stress-test-{test['id']}-{int(time.time())}"
        response = call_chatbot(test['query'], session_id)
        
        extracted_prices = extract_price_from_response(response)
        
        db_result = None
        expected_price = None
        
        if test['type'] == 'cheapest':
            db_result = get_cheapest_iphone()
            if db_result:
                expected_price = db_result['price']
        elif test['type'] == 'price_range':
            match = re.search(r'under\s*(\d+)', test['query'], re.IGNORECASE)
            if match:
                max_price = float(match.group(1))
                products = get_iphones_under_price(max_price)
                if products:
                    db_result = products[0]
                    expected_price = products[0]['price']
        elif test['model']:
            db_result = get_db_ground_truth(test['model'], test['storage'], test['condition'])
            if db_result:
                expected_price = db_result['price']
        
        verdict = "UNKNOWN"
        notes = ""
        
        if "ERROR" in response:
            verdict = "FAIL"
            notes = "API call failed"
            failed += 1
        elif not db_result and test['model']:
            verdict = "WARN"
            notes = "Product not found in database (may be out of stock)"
            warnings += 1
        elif expected_price and extracted_prices:
            if expected_price in extracted_prices:
                verdict = "PASS"
                notes = f"Price ₹{int(expected_price):,} correctly shown"
                passed += 1
            else:
                closest = min(extracted_prices, key=lambda x: abs(x - expected_price))
                diff = abs(closest - expected_price)
                if diff <= 500:
                    verdict = "PASS"
                    notes = f"Price within tolerance (expected ₹{int(expected_price):,}, got ₹{int(closest):,})"
                    passed += 1
                else:
                    verdict = "FAIL"
                    notes = f"Price mismatch: expected ₹{int(expected_price):,}, got {[f'₹{int(p):,}' for p in extracted_prices]}"
                    failed += 1
        elif not extracted_prices and db_result:
            verdict = "WARN"
            notes = "Could not extract price from response"
            warnings += 1
        else:
            verdict = "PASS"
            notes = "Response generated (no specific price validation needed)"
            passed += 1
        
        result = {
            'id': test['id'],
            'query': test['query'],
            'type': test['type'],
            'model': test['model'],
            'storage': test['storage'],
            'condition': test['condition'],
            'response': response[:500] + "..." if len(response) > 500 else response,
            'extracted_prices': extracted_prices,
            'db_result': db_result,
            'expected_price': expected_price,
            'verdict': verdict,
            'notes': notes
        }
        results.append(result)
        
        print(f"  Verdict: {verdict} - {notes}")
        
        time.sleep(0.2)
    
    generate_markdown_report(results, passed, failed, warnings)
    
    print("\n" + "=" * 70)
    print("STRESS TEST COMPLETE")
    print(f"Passed: {passed} | Failed: {failed} | Warnings: {warnings}")
    print("Report saved to: stress_test/stress_test_md_output/stress_test_report.md")
    print("=" * 70)
    
    return results, passed, failed, warnings


def generate_markdown_report(results, passed, failed, warnings):
    """Generate a detailed Markdown report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""# GRESTA Stress Test Report

**Generated:** {timestamp}  
**Total Tests:** {len(results)}  
**Passed:** {passed} ({passed*100//len(results)}%)  
**Failed:** {failed} ({failed*100//len(results)}%)  
**Warnings:** {warnings} ({warnings*100//len(results)}%)  

---

## Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| Passed | {passed} | {passed*100//len(results)}% |
| Failed | {failed} | {failed*100//len(results)}% |
| Warnings | {warnings} | {warnings*100//len(results)}% |

---

## Test Results by Category

"""
    
    categories = {}
    for r in results:
        cat = r['type']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)
    
    for cat, tests in categories.items():
        cat_passed = sum(1 for t in tests if t['verdict'] == 'PASS')
        cat_failed = sum(1 for t in tests if t['verdict'] == 'FAIL')
        cat_warn = sum(1 for t in tests if t['verdict'] == 'WARN')
        
        report += f"""### {cat.replace('_', ' ').title()} ({len(tests)} tests)

| Passed | Failed | Warnings |
|--------|--------|----------|
| {cat_passed} | {cat_failed} | {cat_warn} |

"""
    
    report += """---

## Detailed Results

"""
    
    for r in results:
        status_emoji = "✅" if r['verdict'] == 'PASS' else ("❌" if r['verdict'] == 'FAIL' else "⚠️")
        
        report += f"""### Test #{r['id']}: {r['query']}

**Type:** {r['type']}  
**Status:** {status_emoji} {r['verdict']}  
**Notes:** {r['notes']}

**Expected (from DB):**
"""
        if r['db_result']:
            report += f"""- Model: {r['db_result'].get('name', 'N/A')}
- Storage: {r['db_result'].get('storage', 'N/A')}
- Condition: {r['db_result'].get('condition', 'N/A')}
- Price: ₹{int(r['expected_price']):,}
"""
        else:
            report += "- No matching product found in database\n"
        
        report += f"""
**Extracted Prices:** {[f'₹{int(p):,}' for p in r['extracted_prices']] if r['extracted_prices'] else 'None found'}

**GRESTA Response:**
```
{r['response']}
```

---

"""
    
    failed_tests = [r for r in results if r['verdict'] == 'FAIL']
    if failed_tests:
        report += """## Failed Tests Summary

| # | Query | Expected | Got | Notes |
|---|-------|----------|-----|-------|
"""
        for r in failed_tests:
            exp = f"₹{int(r['expected_price']):,}" if r['expected_price'] else "N/A"
            got = ", ".join([f"₹{int(p):,}" for p in r['extracted_prices']]) if r['extracted_prices'] else "N/A"
            report += f"| {r['id']} | {r['query'][:40]} | {exp} | {got} | {r['notes'][:50]} |\n"
    
    report += """
---

## Conclusion

This stress test validates GRESTA's pricing accuracy across multiple query permutations.
Review any failed tests and warnings to ensure database and chatbot logic are aligned.
"""
    
    with open('stress_test/stress_test_md_output/stress_test_report.md', 'w') as f:
        f.write(report)


if __name__ == "__main__":
    run_stress_test()
