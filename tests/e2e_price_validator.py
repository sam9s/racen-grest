"""
End-to-End Price Validation Testing Framework

This test framework validates chatbot responses against the ACTUAL database values.
Unlike previous tests that used hardcoded expected values, this framework:

1. Pulls expected prices DIRECTLY from PostgreSQL (canonical source)
2. Extracts prices from chatbot responses
3. Compares with ZERO TOLERANCE - any mismatch is a failure
4. Tests all permutations systematically
5. Validates multi-turn session context
6. Produces structured artifacts for traceability

Run with: python tests/e2e_price_validator.py
"""

import os
import sys
import re
import json
import time
import uuid
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database import search_product_by_specs, get_db_session

CHATBOT_URL = "http://localhost:8080/api/chat"


@dataclass
class TestResult:
    test_id: str
    test_type: str
    query: str
    expected_price: int
    actual_price: Optional[int]
    price_match: bool
    expected_model: str
    expected_storage: str
    expected_condition: str
    response_snippet: str
    error: Optional[str] = None
    session_id: Optional[str] = None
    duration_ms: int = 0


@dataclass 
class TestSuite:
    name: str
    started_at: str
    completed_at: Optional[str] = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    results: List[TestResult] = field(default_factory=list)
    failures: List[Dict] = field(default_factory=list)


def extract_price_from_response(response: str) -> Optional[int]:
    """Extract price from chatbot response. Returns None if no price found."""
    price_patterns = [
        r'₹\s*([\d,]+)',
        r'Rs\.?\s*([\d,]+)',
        r'INR\s*([\d,]+)',
        r'\b([\d,]+)\s*rupees?\b',
    ]
    
    prices_found = []
    for pattern in price_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        for match in matches:
            try:
                price = int(match.replace(',', ''))
                if 10000 <= price <= 500000:
                    prices_found.append(price)
            except:
                pass
    
    if not prices_found:
        return None
    return min(prices_found)


def get_expected_price_from_db(model: str, storage: str = None, condition: str = None) -> Tuple[int, Dict]:
    """Get expected price directly from PostgreSQL database."""
    product = search_product_by_specs(model, storage, condition, None, "iPhone")
    if product:
        return int(product['price']), product
    return None, None


def send_chat_query(message: str, session_id: str = None) -> Tuple[str, int]:
    """Send query to chatbot and return response with duration."""
    if not session_id:
        session_id = f"test_{uuid.uuid4().hex[:8]}"
    
    start_time = time.time()
    try:
        response = requests.post(
            CHATBOT_URL,
            json={"message": message, "session_id": session_id},
            timeout=60
        )
        duration_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("response", ""), duration_ms, session_id
        else:
            return f"ERROR: HTTP {response.status_code}", duration_ms, session_id
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return f"ERROR: {str(e)}", duration_ms, session_id


def run_single_price_test(
    test_id: str,
    query: str, 
    model: str, 
    storage: str = None, 
    condition: str = None,
    session_id: str = None
) -> TestResult:
    """Run a single price validation test against the database."""
    
    expected_price, db_product = get_expected_price_from_db(model, storage, condition)
    
    if expected_price is None:
        return TestResult(
            test_id=test_id,
            test_type="price_validation",
            query=query,
            expected_price=0,
            actual_price=None,
            price_match=False,
            expected_model=model,
            expected_storage=storage or "any",
            expected_condition=condition or "any",
            response_snippet="",
            error=f"Product not found in database: {model} {storage} {condition}"
        )
    
    response, duration_ms, sess = send_chat_query(query, session_id)
    actual_price = extract_price_from_response(response)
    
    price_match = actual_price == expected_price
    
    return TestResult(
        test_id=test_id,
        test_type="price_validation",
        query=query,
        expected_price=expected_price,
        actual_price=actual_price,
        price_match=price_match,
        expected_model=model,
        expected_storage=storage or "cheapest",
        expected_condition=condition or "cheapest",
        response_snippet=response[:500],
        session_id=sess,
        duration_ms=duration_ms,
        error=None if price_match else f"Price mismatch: expected ₹{expected_price:,}, got ₹{actual_price:,}" if actual_price else "No price found in response"
    )


def get_all_testable_variants() -> List[Dict]:
    """Get all unique model+storage+condition combinations from database.
    Focus on clean iPhone models only (the chatbot's primary use case).
    """
    engine = create_engine(os.environ['DATABASE_URL'])
    
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT 
                REPLACE(name, 'Apple ', '') as model,
                storage,
                condition,
                MIN(price) as min_price
            FROM grest_products
            WHERE in_stock = true
            AND name ILIKE '%iPhone%'
            AND name NOT ILIKE '%New%'
            AND storage IS NOT NULL
            AND condition IS NOT NULL
            GROUP BY name, storage, condition
            ORDER BY 1, 2, 3
        ''')).fetchall()
    
    return [
        {"model": r[0], "storage": r[1], "condition": r[2], "expected_price": int(r[3])}
        for r in result
    ]


def generate_price_queries(model: str, storage: str = None, condition: str = None) -> List[str]:
    """Generate multiple query variations for the same product."""
    queries = []
    
    if storage and condition:
        queries.extend([
            f"{model} {storage} {condition} price",
            f"{model} {storage} {condition} kitne ka hai",
            f"What is the price of {model} {storage} in {condition} condition?",
        ])
    elif storage:
        queries.extend([
            f"{model} {storage} price",
            f"{model} {storage} ka price kya hai",
        ])
    else:
        queries.extend([
            f"{model} price",
            f"{model} kitne ka hai",
            f"How much is {model}?",
        ])
    
    return queries


def run_permutation_tests(max_variants: int = 50) -> TestSuite:
    """Run price validation tests across all product permutations."""
    suite = TestSuite(
        name="Permutation Price Validation",
        started_at=datetime.now().isoformat()
    )
    
    variants = get_all_testable_variants()
    
    print(f"\n{'='*60}")
    print(f"PERMUTATION PRICE VALIDATION")
    print(f"Total variants in database: {len(variants)}")
    print(f"Testing up to: {max_variants} variants")
    print(f"{'='*60}\n")
    
    import random
    random.seed(42)
    test_variants = random.sample(variants, min(max_variants, len(variants)))
    
    for i, variant in enumerate(test_variants):
        model = variant['model']
        storage = variant['storage']
        condition = variant['condition']
        
        query = f"{model} {storage} {condition} price"
        test_id = f"perm_{i+1:03d}"
        
        result = run_single_price_test(test_id, query, model, storage, condition)
        suite.results.append(result)
        
        status = "✓" if result.price_match else "✗"
        print(f"[{test_id}] {status} {model} {storage} {condition}")
        if not result.price_match:
            print(f"         Expected: ₹{result.expected_price:,}, Got: ₹{result.actual_price:,}" if result.actual_price else f"         {result.error}")
            suite.failures.append(asdict(result))
        
        suite.total_tests += 1
        if result.price_match:
            suite.passed += 1
        elif result.error and "not found" in result.error.lower():
            suite.errors += 1
        else:
            suite.failed += 1
        
        time.sleep(0.2)
    
    suite.completed_at = datetime.now().isoformat()
    return suite


def run_multi_turn_tests() -> TestSuite:
    """Test multi-turn conversations with session context."""
    suite = TestSuite(
        name="Multi-Turn Session Tests",
        started_at=datetime.now().isoformat()
    )
    
    print(f"\n{'='*60}")
    print("MULTI-TURN SESSION TESTS")
    print(f"{'='*60}\n")
    
    multi_turn_scenarios = [
        {
            "name": "iPhone 16 → 256GB variant",
            "turns": [
                {"query": "iPhone 16 price batao", "model": "iPhone 16", "storage": None, "condition": None},
                {"query": "256GB variant?", "model": "iPhone 16", "storage": "256 GB", "condition": None},
            ]
        },
        {
            "name": "iPhone 15 Pro → 512GB variant",
            "turns": [
                {"query": "iPhone 15 Pro price", "model": "iPhone 15 Pro", "storage": None, "condition": None},
                {"query": "iska 512GB wala", "model": "iPhone 15 Pro", "storage": "512 GB", "condition": None},
            ]
        },
        {
            "name": "iPhone 14 → Superb condition",
            "turns": [
                {"query": "iPhone 14 kitne ka hai", "model": "iPhone 14", "storage": None, "condition": None},
                {"query": "same product Superb condition mein", "model": "iPhone 14", "storage": None, "condition": "Superb"},
            ]
        },
        {
            "name": "iPhone 13 → 256GB → Good condition",
            "turns": [
                {"query": "iPhone 13 price", "model": "iPhone 13", "storage": None, "condition": None},
                {"query": "256GB variant", "model": "iPhone 13", "storage": "256 GB", "condition": None},
                {"query": "Good condition mein", "model": "iPhone 13", "storage": "256 GB", "condition": "Good"},
            ]
        },
    ]
    
    for scenario in multi_turn_scenarios:
        session_id = f"multiturn_{uuid.uuid4().hex[:8]}"
        print(f"\n[Scenario: {scenario['name']}]")
        
        for turn_idx, turn in enumerate(scenario['turns']):
            test_id = f"mt_{scenario['name'].replace(' ', '_')[:20]}_{turn_idx+1}"
            
            result = run_single_price_test(
                test_id=test_id,
                query=turn['query'],
                model=turn['model'],
                storage=turn.get('storage'),
                condition=turn.get('condition'),
                session_id=session_id
            )
            
            suite.results.append(result)
            suite.total_tests += 1
            
            status = "✓" if result.price_match else "✗"
            print(f"  Turn {turn_idx+1}: {status} '{turn['query']}' → Expected ₹{result.expected_price:,}, Got ₹{result.actual_price:,}" if result.actual_price else f"  Turn {turn_idx+1}: {status} '{turn['query']}' → {result.error}")
            
            if result.price_match:
                suite.passed += 1
            else:
                suite.failed += 1
                suite.failures.append(asdict(result))
            
            time.sleep(0.2)
    
    suite.completed_at = datetime.now().isoformat()
    return suite


def run_bilingual_tests() -> TestSuite:
    """Test that English and Hinglish queries return identical prices."""
    suite = TestSuite(
        name="Bilingual Consistency Tests",
        started_at=datetime.now().isoformat()
    )
    
    print(f"\n{'='*60}")
    print("BILINGUAL CONSISTENCY TESTS")
    print(f"{'='*60}\n")
    
    bilingual_pairs = [
        {
            "model": "iPhone 16",
            "storage": "256 GB",
            "english": "What is the price of iPhone 16 256GB?",
            "hinglish": "iPhone 16 256GB ka price kya hai?"
        },
        {
            "model": "iPhone 15 Pro",
            "storage": None,
            "english": "How much does iPhone 15 Pro cost?",
            "hinglish": "iPhone 15 Pro kitne ka hai?"
        },
        {
            "model": "iPhone 14",
            "storage": "128 GB",
            "english": "iPhone 14 128GB price please",
            "hinglish": "iPhone 14 128GB price batao"
        },
        {
            "model": "iPhone 13",
            "storage": None,
            "english": "What's the cheapest iPhone 13?",
            "hinglish": "Sabse sasta iPhone 13 kaunsa hai?"
        },
    ]
    
    for pair in bilingual_pairs:
        model = pair['model']
        storage = pair.get('storage')
        expected_price, _ = get_expected_price_from_db(model, storage)
        
        print(f"\n[{model} {storage or 'base'}]")
        
        en_resp, en_dur, _ = send_chat_query(pair['english'])
        en_price = extract_price_from_response(en_resp)
        
        time.sleep(0.2)
        
        hi_resp, hi_dur, _ = send_chat_query(pair['hinglish'])
        hi_price = extract_price_from_response(hi_resp)
        
        en_match = en_price == expected_price
        hi_match = hi_price == expected_price
        prices_consistent = en_price == hi_price
        
        suite.total_tests += 2
        
        en_status = "✓" if en_match else "✗"
        hi_status = "✓" if hi_match else "✗"
        
        print(f"  English:  {en_status} ₹{en_price:,} (expected ₹{expected_price:,})" if en_price else f"  English:  ✗ No price found")
        print(f"  Hinglish: {hi_status} ₹{hi_price:,} (expected ₹{expected_price:,})" if hi_price else f"  Hinglish: ✗ No price found")
        print(f"  Consistency: {'✓ MATCH' if prices_consistent else '✗ MISMATCH'}")
        
        if en_match:
            suite.passed += 1
        else:
            suite.failed += 1
            suite.failures.append({
                "test": f"english_{model}_{storage}",
                "expected": expected_price,
                "actual": en_price
            })
        
        if hi_match:
            suite.passed += 1
        else:
            suite.failed += 1
            suite.failures.append({
                "test": f"hinglish_{model}_{storage}",
                "expected": expected_price,
                "actual": hi_price
            })
    
    suite.completed_at = datetime.now().isoformat()
    return suite


def run_edge_case_tests() -> TestSuite:
    """Test edge cases and potential hallucination triggers."""
    suite = TestSuite(
        name="Edge Case Tests",
        started_at=datetime.now().isoformat()
    )
    
    print(f"\n{'='*60}")
    print("EDGE CASE TESTS")
    print(f"{'='*60}\n")
    
    edge_cases = [
        {
            "name": "Typo in query",
            "query": "iPhoen 16 price",
            "model": "iPhone 16",
            "should_find_price": True
        },
        {
            "name": "Missing space",
            "query": "iPhone16 256GB price",
            "model": "iPhone 16",
            "storage": "256 GB",
            "should_find_price": True
        },
        {
            "name": "Hinglish with typo",
            "query": "iPhone 15 Pro ka prise kaya hai",
            "model": "iPhone 15 Pro",
            "should_find_price": True
        },
        {
            "name": "Future product (should not hallucinate)",
            "query": "iPhone 17 price",
            "model": "iPhone 17",
            "should_find_price": False
        },
        {
            "name": "Non-existent storage",
            "query": "iPhone 16 2TB price",
            "model": "iPhone 16",
            "storage": "2 TB",
            "should_find_price": False
        },
    ]
    
    for case in edge_cases:
        print(f"\n[{case['name']}]")
        print(f"  Query: '{case['query']}'")
        
        response, duration, _ = send_chat_query(case['query'])
        price = extract_price_from_response(response)
        
        suite.total_tests += 1
        
        if case.get('should_find_price'):
            expected, _ = get_expected_price_from_db(
                case['model'], 
                case.get('storage'), 
                case.get('condition')
            )
            if expected and price == expected:
                print(f"  Result: ✓ Found correct price ₹{price:,}")
                suite.passed += 1
            elif expected:
                print(f"  Result: ✗ Expected ₹{expected:,}, got ₹{price:,}" if price else f"  Result: ✗ No price found")
                suite.failed += 1
            else:
                print(f"  Result: ? Product not in DB, got ₹{price:,}" if price else f"  Result: ? Product not in DB")
                suite.errors += 1
        else:
            if price is None or "not available" in response.lower() or "available nahi" in response.lower():
                print(f"  Result: ✓ Correctly indicated product unavailable")
                suite.passed += 1
            else:
                print(f"  Result: ✗ Hallucinated price ₹{price:,} for non-existent product!")
                suite.failed += 1
                suite.failures.append({
                    "test": case['name'],
                    "error": f"Hallucinated price for {case['model']}: ₹{price:,}"
                })
        
        time.sleep(0.2)
    
    suite.completed_at = datetime.now().isoformat()
    return suite


def generate_report(suites: List[TestSuite]) -> str:
    """Generate comprehensive test report."""
    total_tests = sum(s.total_tests for s in suites)
    total_passed = sum(s.passed for s in suites)
    total_failed = sum(s.failed for s in suites)
    total_errors = sum(s.errors for s in suites)
    
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    report = f"""
# End-to-End Price Validation Report
Generated: {datetime.now().isoformat()}

## Summary
| Metric | Value |
|--------|-------|
| Total Tests | {total_tests} |
| Passed | {total_passed} |
| Failed | {total_failed} |
| Errors | {total_errors} |
| **Pass Rate** | **{pass_rate:.1f}%** |
| **UAT Ready** | **{'✓ YES' if pass_rate == 100 else '✗ NO'}** |

## Test Suites
"""
    
    for suite in suites:
        suite_pass_rate = (suite.passed / suite.total_tests * 100) if suite.total_tests > 0 else 0
        report += f"""
### {suite.name}
- Tests: {suite.total_tests}
- Passed: {suite.passed}
- Failed: {suite.failed}
- Pass Rate: {suite_pass_rate:.1f}%
"""
        
        if suite.failures:
            report += "\n**Failures:**\n"
            for f in suite.failures[:10]:
                if isinstance(f, dict):
                    report += f"- {f.get('test_id', f.get('test', 'Unknown'))}: {f.get('error', 'Price mismatch')}\n"
    
    report += """
## Validation Methodology
1. **Database-First**: Expected prices pulled directly from PostgreSQL
2. **Zero Tolerance**: Exact price match required (no ±₹1000 tolerance)
3. **Price Extraction**: Multiple regex patterns for ₹ and Rs. formats
4. **Session Context**: Multi-turn queries validated with session continuity
5. **Bilingual**: Both English and Hinglish queries validated

## UAT Readiness Criteria
- [ ] 100% price accuracy on permutation tests
- [ ] 100% multi-turn session context accuracy
- [ ] Bilingual consistency confirmed
- [ ] No hallucinations on edge cases
"""
    
    return report


def main():
    """Run full end-to-end test suite."""
    print("\n" + "="*70)
    print("     GRESTA CHATBOT - END-TO-END PRICE VALIDATION TEST SUITE")
    print("="*70)
    print(f"Started: {datetime.now().isoformat()}")
    print("Database: PostgreSQL (canonical source)")
    print("Tolerance: ZERO (exact match required)")
    print("="*70)
    
    suites = []
    
    print("\n[1/4] Running Permutation Tests...")
    suites.append(run_permutation_tests(max_variants=30))
    
    print("\n[2/4] Running Multi-Turn Tests...")
    suites.append(run_multi_turn_tests())
    
    print("\n[3/4] Running Bilingual Tests...")
    suites.append(run_bilingual_tests())
    
    print("\n[4/4] Running Edge Case Tests...")
    suites.append(run_edge_case_tests())
    
    report = generate_report(suites)
    
    report_path = "tests/E2E_VALIDATION_REPORT.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    json_path = "tests/e2e_results.json"
    results_data = {
        "generated_at": datetime.now().isoformat(),
        "suites": [
            {
                "name": s.name,
                "total": s.total_tests,
                "passed": s.passed,
                "failed": s.failed,
                "pass_rate": (s.passed / s.total_tests * 100) if s.total_tests > 0 else 0
            }
            for s in suites
        ],
        "failures": [f for s in suites for f in s.failures]
    }
    with open(json_path, 'w') as f:
        json.dump(results_data, f, indent=2, default=str)
    
    total_tests = sum(s.total_tests for s in suites)
    total_passed = sum(s.passed for s in suites)
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"Total Tests:  {total_tests}")
    print(f"Passed:       {total_passed}")
    print(f"Failed:       {total_tests - total_passed}")
    print(f"Pass Rate:    {pass_rate:.1f}%")
    print(f"UAT Ready:    {'✓ YES' if pass_rate == 100 else '✗ NO - Fix failures before UAT'}")
    print(f"\nReports saved:")
    print(f"  - {report_path}")
    print(f"  - {json_path}")
    print("="*70 + "\n")
    
    return pass_rate == 100


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
