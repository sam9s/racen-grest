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
from tests.golden_test_data import GOLDEN_TESTS, get_tests_by_category, get_multi_turn_sessions, get_test_count, CATEGORY_DESCRIPTIONS

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
    
    elif assertion_type == "exact_db_price":
        expected_price = assertion.get("price", 0)
        tolerance = assertion.get("tolerance", 500)
        prices = extract_prices(response)
        if prices:
            for price in prices:
                if abs(price - expected_price) <= tolerance:
                    return True, f"Price ₹{price:,} matches DB (expected ₹{expected_price:,} ±{tolerance:,})"
            return False, f"Prices {prices} don't match DB (expected ₹{expected_price:,} ±{tolerance:,})"
        return False, f"No prices found (expected ₹{expected_price:,})"
    
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
        "category": test.get("category", "unknown"),
        "passed": all_passed,
        "error": None,
        "elapsed": elapsed,
        "assertions_passed": sum(1 for a in assertion_results if a["passed"]),
        "assertions_total": len(assertions),
        "assertion_details": assertion_results,
        "response_preview": response[:300] + "..." if len(response) > 300 else response,
        "full_response": response,
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
    
    # Save detailed results to JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_report_path = f"tests/test_report_{timestamp}.json"
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
    
    with open(json_report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    # Generate comprehensive markdown report
    md_report_path = f"TEST_RESULTS_REPORT.md"
    generate_markdown_report(report, md_report_path, category_stats)
    
    print(f"\nJSON report saved to: {json_report_path}")
    print(f"Markdown report saved to: {md_report_path}")
    print("=" * 70)
    
    return report


def generate_markdown_report(report: Dict, filepath: str, category_stats: Dict):
    """Generate a comprehensive markdown report with all conversations."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    summary = report["summary"]
    results = report["results"]
    
    lines = []
    lines.append("# GRESTA Chatbot Test Results Report")
    lines.append(f"\n**Generated:** {timestamp}")
    lines.append(f"\n**Pass Rate:** {summary['pass_rate']:.1f}% ({summary['passed']}/{summary['total']} tests passed)")
    lines.append("")
    
    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Tests | {summary['total']} |")
    lines.append(f"| Passed | {summary['passed']} |")
    lines.append(f"| Failed | {summary['failed']} |")
    lines.append(f"| Pass Rate | {summary['pass_rate']:.1f}% |")
    lines.append("")
    
    # Category breakdown
    lines.append("## Results by Category")
    lines.append("")
    lines.append("| Category | Passed | Total | Rate |")
    lines.append("|----------|--------|-------|------|")
    
    for cat, stats in sorted(category_stats.items()):
        cat_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        status = "✅" if stats["failed"] == 0 else "❌"
        cat_desc = CATEGORY_DESCRIPTIONS.get(cat, cat)
        lines.append(f"| {status} {cat_desc} | {stats['passed']} | {stats['total']} | {cat_rate:.0f}% |")
    lines.append("")
    
    # Group results by category
    results_by_category = defaultdict(list)
    for r in results:
        cat = r.get("category", "unknown")
        results_by_category[cat].append(r)
    
    # Detailed conversations by category
    lines.append("## Detailed Conversations")
    lines.append("")
    
    for cat in sorted(results_by_category.keys()):
        cat_results = results_by_category[cat]
        cat_desc = CATEGORY_DESCRIPTIONS.get(cat, cat)
        lines.append(f"### {cat_desc}")
        lines.append("")
        
        for r in cat_results:
            test_id = r.get("id", "unknown")
            query = r.get("query", "")
            passed = r.get("passed", False)
            response = r.get("full_response", r.get("response_preview", ""))
            elapsed = r.get("elapsed", 0)
            
            status = "✅ PASS" if passed else "❌ FAIL"
            lines.append(f"#### Test: {test_id} {status}")
            lines.append("")
            lines.append(f"**Query:** `{query}`")
            lines.append("")
            lines.append(f"**Response:** ({elapsed:.2f}s)")
            lines.append("")
            lines.append("```")
            lines.append(response[:1500] if len(response) > 1500 else response)
            lines.append("```")
            lines.append("")
            
            # Show assertion details
            assertions = r.get("assertion_details", [])
            if assertions:
                lines.append("**Assertions:**")
                for a in assertions:
                    a_status = "✅" if a["passed"] else "❌"
                    lines.append(f"- {a_status} {a['description']}: {a['reason']}")
                lines.append("")
            
            lines.append("---")
            lines.append("")
    
    # Failed tests summary
    failed = [r for r in results if not r.get("passed", False)]
    if failed:
        lines.append("## Failed Tests Summary")
        lines.append("")
        lines.append("| Test ID | Query | Reason |")
        lines.append("|---------|-------|--------|")
        for f in failed:
            test_id = f.get("id", "unknown")
            query = f.get("query", "")[:50]
            failed_assertions = [a for a in f.get("assertion_details", []) if not a["passed"]]
            reasons = "; ".join([a["reason"] for a in failed_assertions[:2]])
            lines.append(f"| {test_id} | {query} | {reasons} |")
        lines.append("")
    
    with open(filepath, "w") as f:
        f.write("\n".join(lines))
    
    print(f"Comprehensive markdown report generated: {filepath}")


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
