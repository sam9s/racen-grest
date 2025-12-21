#!/usr/bin/env python3
"""
UAT Pre-Validation Test Suite
Run this before User Acceptance Testing to ensure 100% price accuracy.

Usage: python tests/run_uat_validation.py
"""

import sys
import os
import time
import uuid
import json
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import search_product_by_specs

CHATBOT_URL = "http://localhost:8080/api/chat"


def extract_price(response: str) -> int:
    """Extract price from chatbot response."""
    import re
    matches = re.findall(r'₹\s*([\d,]+)', response)
    for m in matches:
        try:
            price = int(m.replace(',', ''))
            if 10000 <= price <= 500000:
                return price
        except:
            pass
    return None


def get_db_price(model: str, storage: str = None, condition: str = None) -> int:
    """Get expected price from database."""
    product = search_product_by_specs(model, storage, condition, None, "iPhone")
    return int(product['price']) if product else None


def send_query(message: str, session_id: str = None) -> str:
    """Send chat query."""
    if not session_id:
        session_id = f"uat_{uuid.uuid4().hex[:8]}"
    try:
        resp = requests.post(CHATBOT_URL, json={"message": message, "session_id": session_id}, timeout=60)
        return resp.json().get("response", ""), session_id
    except Exception as e:
        return f"ERROR: {e}", session_id


def run_tests():
    """Run UAT validation tests."""
    results = {"timestamp": datetime.now().isoformat(), "tests": [], "passed": 0, "failed": 0}
    
    print("\n" + "="*70)
    print("   GRESTA CHATBOT - UAT PRE-VALIDATION TEST SUITE")
    print("   Database: PostgreSQL | Tolerance: ZERO (exact match)")
    print("="*70 + "\n")
    
    test_cases = [
        ("Direct Price Queries", [
            ("iPhone 16 256GB price", "iPhone 16", "256 GB", None),
            ("iPhone 16 Pro Max 512GB price", "iPhone 16 Pro Max", "512 GB", None),
            ("iPhone 15 Pro 128GB price", "iPhone 15 Pro", "128 GB", None),
            ("iPhone 15 256GB price", "iPhone 15", "256 GB", None),
            ("iPhone 14 128GB Fair price", "iPhone 14", "128 GB", "Fair"),
            ("iPhone 14 Pro 256GB Superb price", "iPhone 14 Pro", "256 GB", "Superb"),
            ("iPhone 13 128GB Good price", "iPhone 13", "128 GB", "Good"),
            ("iPhone 13 Pro Max 256GB price", "iPhone 13 Pro Max", "256 GB", None),
            ("iPhone 12 64GB price", "iPhone 12", "64 GB", None),
            ("iPhone 12 Pro 128GB price", "iPhone 12 Pro", "128 GB", None),
        ]),
        ("Hinglish Queries", [
            ("iPhone 16 256GB ka price kya hai", "iPhone 16", "256 GB", None),
            ("iPhone 15 Pro 128GB kitne ka hai", "iPhone 15 Pro", "128 GB", None),
            ("iPhone 14 128GB Fair condition mein price batao", "iPhone 14", "128 GB", "Fair"),
        ]),
        ("Base Model Queries (cheapest variant)", [
            ("iPhone 16 price", "iPhone 16", None, None),
            ("iPhone 15 Pro Max price", "iPhone 15 Pro Max", None, None),
            ("iPhone 14 price", "iPhone 14", None, None),
        ]),
    ]
    
    for category, tests in test_cases:
        print(f"\n[{category}]")
        for query, model, storage, condition in tests:
            expected = get_db_price(model, storage, condition)
            if not expected:
                print(f"  SKIP: {query} - Not in DB")
                continue
            
            response, _ = send_query(query)
            actual = extract_price(response)
            match = actual == expected
            
            status = "✓" if match else "✗"
            results["tests"].append({
                "query": query, "model": model, "storage": storage, "condition": condition,
                "expected": expected, "actual": actual, "passed": match
            })
            
            if match:
                results["passed"] += 1
                print(f"  {status} {query} → ₹{actual:,}")
            else:
                results["failed"] += 1
                err = f"Expected ₹{expected:,}, Got ₹{actual:,}" if actual else "No price found"
                print(f"  {status} {query} → {err}")
            
            time.sleep(0.15)
    
    print("\n[Multi-Turn Session Tests]")
    multi_turn = [
        ("iPhone 16 price batao", "256GB variant ka price?", "iPhone 16", "256 GB"),
        ("iPhone 15 Pro price", "512GB wala kitne ka hai?", "iPhone 15 Pro", "512 GB"),
        ("iPhone 14 ka price batao", "same product Superb condition mein", "iPhone 14", None, "Superb"),
    ]
    
    for turn1, turn2, model, storage, *rest in multi_turn:
        condition = rest[0] if rest else None
        session = f"mt_{uuid.uuid4().hex[:8]}"
        
        send_query(turn1, session)
        time.sleep(0.1)
        response, _ = send_query(turn2, session)
        
        expected = get_db_price(model, storage, condition)
        actual = extract_price(response)
        match = actual == expected
        
        status = "✓" if match else "✗"
        results["tests"].append({
            "query": f"{turn1} → {turn2}", "model": model, "storage": storage,
            "expected": expected, "actual": actual, "passed": match
        })
        
        if match:
            results["passed"] += 1
            print(f"  {status} {turn1} → {turn2} = ₹{actual:,}")
        else:
            results["failed"] += 1
            print(f"  {status} {turn1} → {turn2} = Expected ₹{expected:,}, Got ₹{actual:,}" if actual else f"  {status} No price")
        
        time.sleep(0.15)
    
    total = results["passed"] + results["failed"]
    rate = (results["passed"] / total * 100) if total > 0 else 0
    
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"  Total Tests:  {total}")
    print(f"  Passed:       {results['passed']}")
    print(f"  Failed:       {results['failed']}")
    print(f"  Pass Rate:    {rate:.1f}%")
    print(f"  UAT READY:    {'✓ YES - Proceed with UAT' if rate == 100 else '✗ NO - Fix failures first'}")
    print("="*70 + "\n")
    
    with open("tests/uat_validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: tests/uat_validation_results.json\n")
    
    return rate == 100


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
