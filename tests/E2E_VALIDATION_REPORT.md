# GRESTA Chatbot - End-to-End Validation Report

**Generated:** December 21, 2025  
**Test Framework:** Database-Validated Price Testing (Zero Tolerance)  
**Database:** PostgreSQL (Canonical Source)

---

## Executive Summary

| Metric | Result |
|--------|--------|
| **Total Tests Run** | 19 |
| **Tests Passed** | 19 |
| **Tests Failed** | 0 |
| **Pass Rate** | **100%** |
| **UAT Ready** | **YES** |

### Key Validation Highlights
- **iPhone 16 256GB price now correctly returns ₹52,399** (matching website exactly)
- All prices validated against PostgreSQL database with ZERO tolerance
- Multi-turn session context working correctly
- Hinglish and English queries return identical prices
- No price hallucinations detected

---

## Test Categories

### 1. Direct Price Queries (Specific Variants)
| Query | Expected (DB) | Actual | Status |
|-------|---------------|--------|--------|
| iPhone 16 256GB price | ₹52,399 | ₹52,399 | ✓ PASS |
| iPhone 16 Pro Max 512GB price | ₹99,999 | ₹99,999 | ✓ PASS |
| iPhone 15 Pro 128GB price | ₹61,299 | ₹61,299 | ✓ PASS |
| iPhone 15 256GB price | ₹39,799 | ₹39,799 | ✓ PASS |
| iPhone 14 128GB Fair price | ₹30,299 | ₹30,299 | ✓ PASS |
| iPhone 14 Pro 256GB Superb price | ₹56,399 | ₹56,399 | ✓ PASS |
| iPhone 13 128GB Good price | ₹26,999 | ₹26,999 | ✓ PASS |
| iPhone 12 64GB price | ₹18,099 | ₹18,099 | ✓ PASS |

### 2. Hinglish Queries
| Query | Expected (DB) | Actual | Status |
|-------|---------------|--------|--------|
| iPhone 16 256GB ka price kya hai | ₹52,399 | ₹52,399 | ✓ PASS |
| iPhone 15 Pro 128GB kitne ka hai | ₹61,299 | ₹61,299 | ✓ PASS |
| iPhone 14 ka price batao | ₹30,299 | ₹30,299 | ✓ PASS |
| iPhone 13 128GB Good condition mein price | ₹26,999 | ₹26,999 | ✓ PASS |

### 3. Base Model Queries (Cheapest Variant)
| Query | Expected (DB) | Actual | Status |
|-------|---------------|--------|--------|
| iPhone 16 price | ₹48,799 | ₹48,799 | ✓ PASS |
| iPhone 15 Pro Max price | ₹70,499 | ₹70,499 | ✓ PASS |
| iPhone 14 price | ₹30,299 | ₹30,299 | ✓ PASS |

### 4. Multi-Turn Session Tests
| Turn 1 | Turn 2 (Follow-up) | Expected | Actual | Status |
|--------|-------------------|----------|--------|--------|
| "iPhone 16 price batao" | "256GB variant?" | ₹52,399 | ₹52,399 | ✓ PASS |
| "iPhone 15 Pro price" | "512GB wala" | ₹73,799 | ₹73,799 | ✓ PASS |
| "iPhone 14 ka price batao" | "isi ka Superb condition" | ₹34,799 | ₹34,799 | ✓ PASS |

---

## Sample Conversations

### Conversation 1: iPhone 16 256GB Price Query

**User:** iPhone 16 256GB price

**GRESTA:**
> The **Apple iPhones 16 (256GB)** is available at a **Starting Price:** ₹52,399.
>
> Here are some key specifications:
>
> ![iPhone 16](https://cdn.shopify.com/s/files/1/0639/4576/9191/files/Frame_2_21.png?v=1761804573)
>
> - **Storage Options:** 128 GB, 256 GB, 512 GB
> - **Display:** 6.1" Super Retina XDR OLED, 2556x1179 pixels, 460 ppi
> - **Processor:** Apple A18 chip
> - **Rear Camera:** Dual 48MP (wide f/1.6) + 12MP (ultra-wide f/2.4)
> - **Front Camera:** 12MP f/1.9
> - **Battery:** 3561 mAh
> - **Water Resistance:** IP68 (up to 6m for 30 min)
> - **5G:** Yes
>
> All our devices come with a **12-month warranty**, pass through **50+ quality checks**, and enjoy **free delivery** across India!
>
> [View iPhone 16](https://grest.in/products/iphone-16)

**Validation:** ✓ Price ₹52,399 matches database exactly

---

### Conversation 2: Hinglish Query - iPhone 15 Pro

**User:** iPhone 15 Pro 128GB kitne ka hai

**GRESTA:**
> iPhones 15 Pro 128GB ki **Starting Price** ₹61,299 hai! 📱
>
> Yahaan kuch key specifications hain:
>
> - **Display:** LTPO Super Retina XDR OLED, 120Hz, HDR10, Dolby Vision, 1000 nits (typ), 2000 nits
> - **Processor:** Apple A17 Pro
> - **Rear Camera:** 48MP, 12MP, 12MP
> - **Front Camera:** 12MP
> - **5G:** No (4G LTE)
> - **Design:** Titanium frame
>
> Aap [iPhone 15 Pro ko yahan dekh sakte hain](https://grest.in/products/refurbished-apple-iphone-15-pro?variant=51620244619495).
>
> Kya aapko aur information chahiye ya kisi aur model ke baare mein?

**Validation:** ✓ Price ₹61,299 matches database exactly

---

### Conversation 3: Fair Condition Query - iPhone 14

**User:** iPhone 14 128GB Fair price

**GRESTA:**
> The price for the **Apple iPhones 14 (128GB, Fair condition)** is **₹30,299**. 📱
>
> Here are the specifications:
>
> - **Display:** Super Retina XDR OLED, HDR10, Dolby Vision, 800 nits
> - **Processor:** Apple A15 Bionic
> - **Rear Camera:** 12MP, 12MP Dual LED dual-tone flash, HDR
> - **Front Camera:** 12 MP, f/1.9, 23mm
> - **5G:** No (4G LTE)
> - **Design:** Aluminum frame
>
> ![iPhone 14](https://cdn.shopify.com/s/files/1/0639/4576/9191/files/Frame_11_1.png?v=1761762198)
>
> All our devices come with a 12-month warranty and pass through 50+ quality checks!
>
> [View iPhone 14](https://grest.in/products/refurbished-apple-iphone-14?variant=51620254253287)

**Validation:** ✓ Price ₹30,299 matches database exactly

---

### Conversation 4: Multi-Turn Session (Follow-up Query)

**Turn 1:**
**User:** iPhone 16 price batao

**GRESTA:** (Shows base price ₹48,799 for 128GB Fair)

**Turn 2:**
**User:** 256GB variant?

**GRESTA:**
> Apple iPhones 16 ka **256 GB** variant ke liye price hai **₹52,399**. 🤩
>
> Here's the detailed information:
>
> ![iPhone 16](https://cdn.shopify.com/s/files/1/0639/4576/9191/files/Frame_2_21.png?v=1761804573)
>
> - **Starting Price:** ₹52,399 (256 GB, Fair condition)
> - **Storage Options:** 128 GB, 256 GB
> - **Display:** 6.1" Super Retina XDR OLED, 2556x1179 pixels, 460 ppi
> - **Processor:** Apple A18 chip
> - **Rear Camera:** Dual 48MP (wide f/1.6) + 12MP (ultra-wide f/2.4)
> - **Front Camera:** 12MP f/1.9
> - **Battery:** 3561 mAh
> - **Water Resistance:** IP68 (up to 6m for 30 min)
>
> Sabhi devices ke saath 12-month warranty aur 50+ quality checks hain!

**Validation:** ✓ Session context correctly resolved "iPhone 16" from previous turn, returned ₹52,399

---

## Validation Methodology

### Previous Approach (Flawed)
- Hardcoded expected prices in test files
- Used ±₹1,000 tolerance (allowing ₹100 errors to pass)
- Did not query actual database for validation
- Could not detect LLM price hallucinations

### New Approach (Rigorous)
1. **Database-First:** Expected prices pulled directly from PostgreSQL
2. **Zero Tolerance:** Exact price match required (no ±₹1,000 tolerance)
3. **Price Extraction:** Multiple regex patterns for ₹ and Rs. formats
4. **Session Validation:** Multi-turn queries tested with session continuity
5. **Bilingual Testing:** Same queries tested in English and Hinglish

---

## Critical Fix Applied

**Issue Found:** iPhone 16 256GB was returning ₹52,499 instead of ₹52,399 (₹100 difference)

**Root Cause:** LLM was hallucinating prices from its training data instead of using the database price

**Fix Applied:**
1. Strengthened price enforcement prompts with explicit warnings
2. Added "variant" to coreference detection for follow-up queries
3. Enhanced context building to emphasize EXACT database prices

**Verification:** 
- Database confirms: ₹52,399
- Website confirms: ₹52,399
- Chatbot now returns: ₹52,399 ✓

---

## UAT Readiness Checklist

- [x] 100% price accuracy on direct queries
- [x] 100% price accuracy on Hinglish queries
- [x] 100% price accuracy on base model queries
- [x] Multi-turn session context working
- [x] No price hallucinations detected
- [x] Specs displayed from database (not hardcoded)
- [x] Product images included in responses
- [x] Links to product pages included

---

## How to Run Pre-UAT Validation

```bash
# Quick validation (recommended before each UAT session)
python tests/run_uat_validation.py

# Comprehensive validation (all permutations)
python tests/e2e_price_validator.py
```

---

## Conclusion

The GRESTA chatbot has achieved **100% price accuracy** with zero tolerance validation against the PostgreSQL database. All tested queries (direct, Hinglish, base model, and multi-turn) return prices that exactly match the canonical database values.

**Recommendation:** Proceed with User Acceptance Testing (UAT)
