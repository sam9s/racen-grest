"""
Targeted Stress Test for Hybrid LLM Query Parser

Tests edge cases that deterministic regex cannot handle:
- Hinglish condition synonyms (theek si, acchi, ekdum mast)
- Budget ranges in Hindi/Hinglish
- Natural language queries without explicit keywords
- Mixed language queries
"""

import requests
import json
import time
import re
from datetime import datetime

API_URL = "http://localhost:8080/api/chat"

EDGE_CASE_QUERIES = [
    {
        "id": 1,
        "query": "20000 ke budget mein koi superb condition ka phone hai",
        "expected_behavior": "Search for Superb condition phones under 20000",
        "expected_condition": "Superb",
        "budget_max": 20000,
        "category": "hinglish_budget_condition"
    },
    {
        "id": 2,
        "query": "eak theek si condition ka iphone 30, 40000 ka hai koi",
        "expected_behavior": "Search for Fair condition iPhones between 30000-40000",
        "expected_condition": "Fair",
        "budget_min": 30000,
        "budget_max": 40000,
        "category": "hinglish_condition_synonym"
    },
    {
        "id": 3,
        "query": "acchi condition mein kaunsa phone milega 25000 tak",
        "expected_behavior": "Good condition phones under 25000",
        "expected_condition": "Good",
        "budget_max": 25000,
        "category": "hinglish_condition_synonym"
    },
    {
        "id": 4,
        "query": "ekdum mast condition wala iPhone chahiye",
        "expected_behavior": "Show Superb condition iPhones",
        "expected_condition": "Superb",
        "category": "hinglish_condition_synonym"
    },
    {
        "id": 5,
        "query": "sasti wali iPhone dikhao",
        "expected_behavior": "Show cheapest/Fair condition iPhones",
        "expected_condition": "Fair",
        "category": "hinglish_condition_synonym"
    },
    {
        "id": 6,
        "query": "badhiya condition ka 12 wala iPhone",
        "expected_behavior": "iPhone 12 in Good condition",
        "model": "iPhone 12",
        "expected_condition": "Good",
        "category": "hinglish_model_condition"
    },
    {
        "id": 7,
        "query": "premium quality wala phone 50000 ke andar",
        "expected_behavior": "Superb condition under 50000",
        "expected_condition": "Superb",
        "budget_max": 50000,
        "category": "hinglish_quality_synonym"
    },
    {
        "id": 8,
        "query": "basic wala chalega, 15000 tak",
        "expected_behavior": "Fair condition under 15000",
        "expected_condition": "Fair",
        "budget_max": 15000,
        "category": "hinglish_condition_synonym"
    },
    {
        "id": 9,
        "query": "iPhone 12 Superb condition price",
        "expected_behavior": "iPhone 12 Superb exact price",
        "model": "iPhone 12",
        "expected_condition": "Superb",
        "expected_price": 19599,
        "category": "specific_variant"
    },
    {
        "id": 10,
        "query": "decent condition ka iPhone 13 128GB",
        "expected_behavior": "iPhone 13 128GB Good condition",
        "model": "iPhone 13",
        "storage": "128 GB",
        "expected_condition": "Good",
        "category": "hinglish_full_spec"
    },
    {
        "id": 11,
        "query": "A1 condition wala sabse sasta",
        "expected_behavior": "Cheapest Superb condition phone",
        "expected_condition": "Superb",
        "category": "hinglish_quality_synonym"
    },
    {
        "id": 12,
        "query": "25 se 35 hazar mein accha phone",
        "expected_behavior": "Good phones between 25000-35000",
        "expected_condition": "Good",
        "budget_min": 25000,
        "budget_max": 35000,
        "category": "hinglish_budget_range"
    },
    {
        "id": 13,
        "query": "normal condition ka iPad available hai?",
        "expected_behavior": "iPad in Good condition",
        "model": "iPad",
        "expected_condition": "Good",
        "category": "hinglish_ipad"
    },
    {
        "id": 14,
        "query": "shandar quality wala MacBook",
        "expected_behavior": "MacBook in Superb condition",
        "model": "MacBook",
        "expected_condition": "Superb",
        "category": "hinglish_macbook"
    },
    {
        "id": 15,
        "query": "first class condition ka 13 Pro Max",
        "expected_behavior": "iPhone 13 Pro Max Superb",
        "model": "iPhone 13 Pro Max",
        "expected_condition": "Superb",
        "category": "hinglish_pro_variant"
    },
    {
        "id": 16,
        "query": "kam price wala phone batao",
        "expected_behavior": "Show cheapest/Fair phones",
        "expected_condition": "Fair",
        "category": "hinglish_cheapest"
    },
    {
        "id": 17,
        "query": "zabardast condition me iPhone 11 milega?",
        "expected_behavior": "iPhone 11 in Superb condition",
        "model": "iPhone 11",
        "expected_condition": "Superb",
        "category": "hinglish_model_condition"
    },
    {
        "id": 18,
        "query": "ok ok condition chalega, 20k budget",
        "expected_behavior": "Fair condition under 20000",
        "expected_condition": "Fair",
        "budget_max": 20000,
        "category": "hinglish_casual"
    },
    {
        "id": 19,
        "query": "iPhone 12 128GB theek thaak condition",
        "expected_behavior": "iPhone 12 128GB Good condition",
        "model": "iPhone 12",
        "storage": "128 GB",
        "expected_condition": "Good",
        "category": "hinglish_full_spec"
    },
    {
        "id": 20,
        "query": "budget wali iPhone 64GB mein",
        "expected_behavior": "64GB iPhone in Fair condition",
        "storage": "64 GB",
        "expected_condition": "Fair",
        "category": "hinglish_storage_condition"
    }
]


def extract_prices(text):
    """Extract all prices from response text."""
    patterns = [
        r'₹\s*([\d,]+)',
        r'Rs\.?\s*([\d,]+)',
        r'INR\s*([\d,]+)',
        r'([\d,]+)\s*rupees?',
    ]
    prices = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                price = int(match.replace(',', ''))
                if 1000 <= price <= 500000:
                    prices.append(price)
            except:
                pass
    return list(set(prices))


def extract_conditions(text):
    """Extract condition mentions from response, including Hinglish synonyms."""
    conditions = []
    text_lower = text.lower()
    
    superb_indicators = ['superb', 'ekdum', 'mast', 'premium', 'zabardast', 'shandar', 'first class', 'a1']
    good_indicators = ['good', 'acchi', 'accha', 'badhiya', 'decent', 'normal']
    fair_indicators = ['fair', 'theek', 'basic', 'sasti', 'budget', 'chalega', 'kam price']
    
    for indicator in superb_indicators:
        if indicator in text_lower:
            conditions.append('Superb')
            break
    
    for indicator in good_indicators:
        if indicator in text_lower:
            conditions.append('Good')
            break
    
    for indicator in fair_indicators:
        if indicator in text_lower:
            conditions.append('Fair')
            break
    
    return list(set(conditions))


def run_test(test):
    """Run a single test query."""
    try:
        response = requests.post(
            API_URL,
            json={"message": test["query"], "session_id": f"hybrid-test-{test['id']}"},
            timeout=30
        )
        result = response.json()
        return result.get("response", "")
    except Exception as e:
        return f"ERROR: {str(e)}"


def analyze_result(test, response):
    """Analyze if the response matches expected behavior."""
    issues = []
    passes = []
    
    expected_condition = test.get("expected_condition")
    if expected_condition:
        response_conditions = extract_conditions(response)
        if expected_condition in response_conditions or expected_condition.lower() in response.lower():
            passes.append(f"Condition '{expected_condition}' mentioned")
        else:
            issues.append(f"Expected condition '{expected_condition}' not found in response")
    
    expected_price = test.get("expected_price")
    if expected_price:
        prices = extract_prices(response)
        if expected_price in prices:
            passes.append(f"Exact price ₹{expected_price:,} found")
        elif prices:
            issues.append(f"Expected ₹{expected_price:,}, found {prices}")
        else:
            issues.append(f"Expected ₹{expected_price:,}, no prices found")
    
    budget_max = test.get("budget_max")
    if budget_max:
        prices = extract_prices(response)
        if prices:
            over_budget = [p for p in prices if p > budget_max]
            if not over_budget:
                passes.append(f"All prices within budget ₹{budget_max:,}")
            else:
                issues.append(f"Prices {over_budget} exceed budget ₹{budget_max:,}")
    
    model = test.get("model")
    if model:
        if model.lower() in response.lower() or model.replace(" ", "").lower() in response.lower():
            passes.append(f"Model '{model}' mentioned")
        else:
            issues.append(f"Expected model '{model}' not found")
    
    if "out of stock" in response.lower() or "not available" in response.lower() or "don't have" in response.lower():
        return "WARNING", "Product out of stock", passes, issues
    
    if issues:
        return "FAIL", "; ".join(issues), passes, issues
    elif passes:
        return "PASS", "; ".join(passes), passes, issues
    else:
        return "INFO", "Response generated (manual review needed)", passes, issues


def run_stress_test():
    """Run all edge case tests."""
    print("=" * 70)
    print("HYBRID QUERY PARSER - EDGE CASE STRESS TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Tests: {len(EDGE_CASE_QUERIES)}")
    print("=" * 70)
    
    results = []
    passed = 0
    failed = 0
    warnings = 0
    
    for test in EDGE_CASE_QUERIES:
        print(f"\n[{test['id']}/{len(EDGE_CASE_QUERIES)}] {test['category']}")
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected_behavior']}")
        
        response = run_test(test)
        verdict, notes, passes, issues = analyze_result(test, response)
        
        if verdict == "PASS":
            passed += 1
            print(f"✅ PASS: {notes}")
        elif verdict == "WARNING":
            warnings += 1
            print(f"⚠️ WARNING: {notes}")
        elif verdict == "FAIL":
            failed += 1
            print(f"❌ FAIL: {notes}")
        else:
            print(f"ℹ️ INFO: {notes}")
        
        results.append({
            "id": test["id"],
            "query": test["query"],
            "category": test["category"],
            "expected_behavior": test["expected_behavior"],
            "expected_condition": test.get("expected_condition"),
            "expected_price": test.get("expected_price"),
            "budget_max": test.get("budget_max"),
            "model": test.get("model"),
            "response": response[:600] if len(response) > 600 else response,
            "verdict": verdict,
            "notes": notes,
            "passes": passes,
            "issues": issues
        })
        
        time.sleep(0.3)
    
    generate_report(results, passed, failed, warnings)
    
    print("\n" + "=" * 70)
    print("STRESS TEST COMPLETE")
    print(f"Passed: {passed} | Failed: {failed} | Warnings: {warnings}")
    total = len(EDGE_CASE_QUERIES)
    accuracy = (passed / total) * 100 if total > 0 else 0
    print(f"Accuracy: {accuracy:.1f}%")
    print("Report saved to: stress_test/stress_test_md_output/hybrid_edge_case_report.md")
    print("=" * 70)
    
    return results, passed, failed, warnings


def generate_report(results, passed, failed, warnings):
    """Generate detailed Markdown report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(results)
    accuracy = (passed / total) * 100 if total > 0 else 0
    
    report = f"""# Hybrid Query Parser - Edge Case Stress Test

**Generated:** {timestamp}  
**Total Tests:** {total}  
**Passed:** {passed} ({passed*100//total}%)  
**Failed:** {failed} ({failed*100//total}%)  
**Warnings:** {warnings} ({warnings*100//total}%)  
**Accuracy:** {accuracy:.1f}%

---

## Purpose

This stress test validates the hybrid LLM query parser's ability to handle:
1. **Hinglish condition synonyms** - "theek si" (Fair), "acchi" (Good), "ekdum mast" (Superb)
2. **Budget parsing in Hindi** - "20k tak", "30 se 40 hazar", "ke andar"
3. **Natural language queries** - No explicit keywords like "price" or "kitna"
4. **Mixed language queries** - English models with Hindi conditions

---

## Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| Passed | {passed} | {passed*100//total}% |
| Failed | {failed} | {failed*100//total}% |
| Warnings | {warnings} | {warnings*100//total}% |

---

## Detailed Results

"""
    
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)
    
    for cat, tests in categories.items():
        report += f"\n### Category: {cat}\n\n"
        for r in tests:
            verdict_icon = "✅" if r["verdict"] == "PASS" else ("⚠️" if r["verdict"] == "WARNING" else "❌")
            report += f"""#### Test {r['id']}: {verdict_icon} {r['verdict']}

**Query:** `{r['query']}`  
**Expected:** {r['expected_behavior']}  
**Expected Condition:** {r.get('expected_condition', 'N/A')}  
**Expected Price:** {r.get('expected_price', 'N/A')}  
**Budget Max:** {r.get('budget_max', 'N/A')}  

**Verdict:** {r['verdict']}  
**Notes:** {r['notes']}

**Response (truncated):**
```
{r['response'][:400]}...
```

---

"""
    
    failed_tests = [r for r in results if r["verdict"] == "FAIL"]
    if failed_tests:
        report += """## Failed Tests Summary

| # | Query | Expected Condition | Issue |
|---|-------|-------------------|-------|
"""
        for r in failed_tests:
            query_short = r["query"][:35] + "..." if len(r["query"]) > 35 else r["query"]
            report += f"| {r['id']} | {query_short} | {r.get('expected_condition', 'N/A')} | {r['notes'][:50]} |\n"
    
    report += f"""

---

## Conclusion

The hybrid query parser achieves **{accuracy:.1f}% accuracy** on edge case queries.

### Key Findings:
- **Hinglish Condition Mapping:** {"Working" if any(r["verdict"] == "PASS" and "condition" in r["category"] for r in results) else "Needs improvement"}
- **Budget Parsing:** {"Working" if any(r["verdict"] == "PASS" and "budget" in r["category"] for r in results) else "Needs improvement"}
- **Model Detection:** {"Working" if any(r["verdict"] == "PASS" and r.get("model") for r in results) else "Needs improvement"}

"""
    
    with open('stress_test/stress_test_md_output/hybrid_edge_case_report.md', 'w') as f:
        f.write(report)


if __name__ == "__main__":
    run_stress_test()
