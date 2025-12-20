"""
GRESTA Chatbot Automated Test Harness
Runs golden dataset tests with assertion-based checking and Monte Carlo sampling.

Usage:
    python tests/chatbot_test_harness.py                 # Run all tests
    python tests/chatbot_test_harness.py --category pricing  # Run specific category
    python tests/chatbot_test_harness.py --samples 5     # Run 5 samples per test (Monte Carlo)
    python tests/chatbot_test_harness.py --verbose       # Show detailed output
"""

import sys
import os
import re
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Any
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from tests.golden_test_data import GOLDEN_TESTS, get_tests_by_category, get_multi_turn_sessions

API_URL = "http://localhost:8080/api/chat"
TIMEOUT = 30


def send_chat_request(message: str, session_id: str = None) -> Tuple[str, bool]:
    """Send a chat request and return response text and success flag."""
    try:
        payload = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        
        response = requests.post(API_URL, json=payload, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            return data.get("response", ""), True
        else:
            return f"HTTP Error: {response.status_code}", False
    except requests.exceptions.Timeout:
        return "Request timed out", False
    except requests.exceptions.ConnectionError:
        return "Connection error - is the server running?", False
    except Exception as e:
        return f"Error: {str(e)}", False


def extract_prices(text: str) -> List[int]:
    """Extract all prices (in rupees) from text."""
    prices = []
    patterns = [
        r'₹\s*([\d,]+)',
        r'Rs\.?\s*([\d,]+)',
        r'INR\s*([\d,]+)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                price = int(match.replace(',', ''))
                prices.append(price)
            except ValueError:
                pass
    return prices


def check_assertion(response: str, assertion: Dict) -> Tuple[bool, str]:
    """Check a single assertion against the response. Returns (passed, reason)."""
    assertion_type = assertion.get("type")
    
    if assertion_type == "contains":
        value = assertion.get("value", "")
        if value.lower() in response.lower():
            return True, f"Found '{value}'"
        return False, f"Missing '{value}'"
    
    elif assertion_type == "not_contains":
        value = assertion.get("value", "")
        if value.lower() not in response.lower():
            return True, f"Correctly excludes '{value}'"
        return False, f"Should not contain '{value}'"
    
    elif assertion_type == "contains_any":
        values = assertion.get("values", [])
        for v in values:
            if v.lower() in response.lower():
                return True, f"Found '{v}'"
        return False, f"Missing any of {values}"
    
    elif assertion_type == "contains_price":
        min_price = assertion.get("min", 0)
        max_price = assertion.get("max", float('inf'))
        prices = extract_prices(response)
        if prices:
            for price in prices:
                if min_price <= price <= max_price:
                    return True, f"Price ₹{price:,} in range [{min_price:,}-{max_price:,}]"
            return False, f"Prices {prices} not in range [{min_price:,}-{max_price:,}]"
        return False, f"No prices found (expected range [{min_price:,}-{max_price:,}])"
    
    elif assertion_type == "response_exists":
        if response and len(response.strip()) > 0:
            return True, "Response exists"
        return False, "Empty response"
    
    else:
        return False, f"Unknown assertion type: {assertion_type}"


def run_single_test(test: Dict, session_id: str = None) -> Dict:
    """Run a single test case and return results."""
    query = test.get("query", "")
    test_session = session_id or test.get("session_id", f"test_{test['id']}")
    
    start_time = time.time()
    response, success = send_chat_request(query, test_session)
    elapsed = time.time() - start_time
    
    if not success:
        return {
            "id": test["id"],
            "query": query,
            "passed": False,
            "error": response,
            "elapsed": elapsed,
            "assertions_passed": 0,
            "assertions_total": len(test.get("assertions", [])),
            "assertion_details": [],
            "response_preview": "",
        }
    
    assertions = test.get("assertions", [])
    assertion_results = []
    all_passed = True
    
    for assertion in assertions:
        passed, reason = check_assertion(response, assertion)
        assertion_results.append({
            "description": assertion.get("description", ""),
            "passed": passed,
            "reason": reason,
        })
        if not passed:
            all_passed = False
    
    return {
        "id": test["id"],
        "query": query,
        "passed": all_passed,
        "error": None,
        "elapsed": elapsed,
        "assertions_passed": sum(1 for a in assertion_results if a["passed"]),
        "assertions_total": len(assertions),
        "assertion_details": assertion_results,
        "response_preview": response[:300] + "..." if len(response) > 300 else response,
    }


def run_monte_carlo(test: Dict, num_samples: int = 3) -> Dict:
    """Run a test multiple times to detect variance."""
    results = []
    for i in range(num_samples):
        session_id = f"monte_carlo_{test['id']}_{i}_{time.time()}"
        result = run_single_test(test, session_id)
        results.append(result)
        time.sleep(0.5)  # Small delay between samples
    
    pass_count = sum(1 for r in results if r["passed"])
    variance_detected = pass_count > 0 and pass_count < num_samples
    
    return {
        "id": test["id"],
        "query": test.get("query", ""),
        "samples": num_samples,
        "passed_count": pass_count,
        "pass_rate": pass_count / num_samples,
        "variance_detected": variance_detected,
        "all_passed": pass_count == num_samples,
        "results": results,
    }


def run_multi_turn_session(tests: List[Dict]) -> List[Dict]:
    """Run a multi-turn conversation session."""
    session_id = f"multi_turn_{time.time()}"
    results = []
    
    for test in sorted(tests, key=lambda t: t["id"]):
        result = run_single_test(test, session_id)
        results.append(result)
        time.sleep(0.3)  # Small delay between turns
    
    return results


def run_all_tests(category_filter: str = None, num_samples: int = 1, verbose: bool = False) -> Dict:
    """Run all tests and return comprehensive results."""
    print("=" * 70)
    print("GRESTA CHATBOT AUTOMATED TEST SUITE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Monte Carlo samples per test: {num_samples}")
    if category_filter:
        print(f"Category filter: {category_filter}")
    print("=" * 70)
    
    # Check server availability
    print("\nChecking server availability...")
    response, success = send_chat_request("hello", "health_check")
    if not success:
        print(f"ERROR: Server not available - {response}")
        return {"error": "Server not available"}
    print("Server is running.\n")
    
    # Organize tests
    categories = get_tests_by_category()
    multi_turn_sessions = get_multi_turn_sessions()
    
    all_results = []
    category_stats = defaultdict(lambda: {"passed": 0, "failed": 0, "total": 0})
    
    # Run regular tests (non-multi-turn, non-skipped)
    regular_tests = [t for t in GOLDEN_TESTS if "depends_on" not in t and not t.get("skip")]
    if category_filter:
        regular_tests = [t for t in regular_tests if t["category"] == category_filter]
    
    print(f"Running {len(regular_tests)} test cases...\n")
    
    for i, test in enumerate(regular_tests):
        category = test["category"]
        
        if num_samples > 1:
            mc_result = run_monte_carlo(test, num_samples)
            passed = mc_result["all_passed"]
            result_summary = mc_result
            
            if mc_result["variance_detected"]:
                status = f"⚠️  VARIANCE ({mc_result['pass_rate']:.0%})"
            elif passed:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
        else:
            result = run_single_test(test)
            passed = result["passed"]
            result_summary = result
            status = "✅ PASS" if passed else "❌ FAIL"
        
        all_results.append(result_summary)
        category_stats[category]["total"] += 1
        if passed:
            category_stats[category]["passed"] += 1
        else:
            category_stats[category]["failed"] += 1
        
        print(f"[{i+1:3}/{len(regular_tests)}] {status} | {test['id']:15} | {test['query'][:40]}")
        
        if verbose and not passed:
            if "results" in result_summary:
                for r in result_summary["results"]:
                    if not r["passed"]:
                        print(f"         Failed assertions: {[a for a in r['assertion_details'] if not a['passed']]}")
            else:
                print(f"         Failed assertions: {[a for a in result_summary['assertion_details'] if not a['passed']]}")
    
    # Run multi-turn sessions
    print("\n" + "-" * 70)
    print("Running multi-turn conversation tests...")
    
    for session_name, session_tests in multi_turn_sessions.items():
        if category_filter and not any(t["category"] == category_filter for t in session_tests):
            continue
        
        print(f"\n  Session: {session_name}")
        session_results = run_multi_turn_session(session_tests)
        
        for result in session_results:
            passed = result["passed"]
            test_id = result["id"]
            query = result["query"][:40]
            status = "✅" if passed else "❌"
            print(f"    {status} {test_id}: {query}")
            
            all_results.append(result)
            
            # Find category for this test
            for t in session_tests:
                if t["id"] == test_id:
                    cat = t["category"]
                    category_stats[cat]["total"] += 1
                    if passed:
                        category_stats[cat]["passed"] += 1
                    else:
                        category_stats[cat]["failed"] += 1
                    break
    
    # Generate summary
    total_passed = sum(s["passed"] for s in category_stats.values())
    total_failed = sum(s["failed"] for s in category_stats.values())
    total_tests = total_passed + total_failed
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"\nOverall: {total_passed}/{total_tests} passed ({pass_rate:.1f}%)")
    print("\nBy Category:")
    for cat, stats in sorted(category_stats.items()):
        cat_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        indicator = "✅" if stats["failed"] == 0 else "❌"
        print(f"  {indicator} {cat:25} {stats['passed']:2}/{stats['total']:2} ({cat_rate:.0f}%)")
    
    # Show failed tests summary
    failed_tests = [r for r in all_results if not r.get("passed", False) and not r.get("all_passed", True)]
    if failed_tests:
        print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
        for ft in failed_tests[:10]:  # Show first 10
            test_id = ft.get("id", "unknown")
            query = ft.get("query", "")[:50]
            print(f"  - {test_id}: {query}")
        if len(failed_tests) > 10:
            print(f"  ... and {len(failed_tests) - 10} more")
    
    # Save detailed results to file
    report_path = f"tests/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": pass_rate,
        },
        "category_stats": dict(category_stats),
        "results": all_results,
    }
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\nDetailed report saved to: {report_path}")
    print("=" * 70)
    
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GRESTA Chatbot Test Harness")
    parser.add_argument("--category", "-c", help="Run tests for specific category only")
    parser.add_argument("--samples", "-s", type=int, default=1, help="Monte Carlo samples per test (default: 1)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    args = parser.parse_args()
    
    run_all_tests(
        category_filter=args.category,
        num_samples=args.samples,
        verbose=args.verbose
    )
