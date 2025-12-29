# GREST Progress Tracker

## Project Overview
**Project Name:** GRESTA - AI Conversational Chatbot for GREST  
**Client:** GREST (India's premium refurbished iPhone & MacBook e-commerce platform)  
**Production URL:** https://gresta.sam9scloud.in  
**Developer:** Sam (Product Owner, Project Manager, Developer)  
**Start Date:** December 2024  
**Last Updated:** December 29, 2025

---

## Completed Tasks

### Phase 1: Core Chatbot Development
- [x] Rebranded chatbot from coaching to GREST e-commerce platform
- [x] Implemented bilingual support (English + Hinglish)
- [x] Integrated PostgreSQL database for product data
- [x] Set up Shopify Admin API integration for product sync
- [x] Emerald green branding (#10b981) applied throughout

### Phase 2: Anti-Hallucination Architecture (Blueprint)
- [x] **Option A Implementation**: Always inject compact product summary into LLM context
- [x] Database-first pricing: All prices come from PostgreSQL, not LLM memory
- [x] Canonical data pipeline: Shopify API → Scraper → Database → Chatbot
- [x] No hardcoded product data anywhere in the system
- [x] Multi-turn conversation support (handles "same product", "that one" references)

### Phase 3: Pricing Accuracy
- [x] Created comprehensive test suite (`test_pricing_accuracy.py`)
- [x] 51 test cases across 7 categories
- [x] Achieved 98.04% accuracy (up from 84.31% baseline)
- [x] Product coverage: 2,205 variants from 104 Shopify products

### Phase 4: Natural Conversation Flow (Dec 27, 2025)
- [x] Removed "PROACTIVE PRODUCT RECOMMENDATIONS" hardcoding
- [x] LLM now behaves naturally:
  - Vague queries → Asks for clarification
  - Clear intent → Returns 100% accurate database prices
- [x] Follows ChatGPT-like behavior: If any doubt, ask for clarification

### Phase 5: Admin Dashboard
- [x] 4-tab dashboard (Analytics, Conversations, Monitoring, Shopify Sync)
- [x] Real-time sync progress UI with 6 stages
- [x] Manual sync button and verification panel
- [x] Sync history tracking
- [x] UptimeRobot integration for monitoring
- [x] Dashboard login: samret.singh@grest.in / Samret@123

### Phase 6: Deployment
- [x] Production deployed on Reserved VM (99.9% uptime guarantee)
- [x] Custom domain configured: gresta.sam9scloud.in
- [x] Caddy reverse proxy setup
- [x] 24/7 availability - no sleep mode

### Phase 7: Automated Sync
- [x] APScheduler running every 6 hours
- [x] Automatic Shopify product sync
- [x] Sync logs captured in database

### Phase 8: Security Implementation (Dec 27-29, 2025)
- [x] **Rate Limiter Module**: `rate_limiter.py` with IP-based throttling
- [x] **Thresholds Configured**:
  - 10 requests/minute (soft limit)
  - 50 requests/hour (10-minute block)
  - 100 requests/day (24-hour block)
  - CAPTCHA after 20 messages per session (resets after solving)
  - **200 messages/day per session** (24h rolling window, friendly message)
- [x] **Protected Endpoints**:
  - `/api/chat` - Direct chat API
  - `/api/chat/stream` - Streaming chat (SSE)
  - `/api/chat/manychat` - ManyChat/Instagram integration (greeting exempt)
- [x] **Frontend CAPTCHA Handling**: 429 response triggers math CAPTCHA prompt
- [x] **Monitoring Endpoints**:
  - `/api/admin/rate-limiter/stats` - View active IPs, blocked IPs, pending CAPTCHAs
  - `/api/admin/rate-limiter/ip/<ip>` - Check specific IP activity
  - `/api/admin/security` - Comprehensive security dashboard data
- [x] **Security Dashboard Tab** (Dec 29, 2025):
  - Summary metrics: Active IPs, Blocked IPs, Pending CAPTCHAs, Total Requests
  - Rate limit configuration display (all thresholds including session limit)
  - Currently blocked IPs with countdown timers
  - Top active IPs with per-minute/hour/day request counts
  - Recent requests log with 10-second auto-refresh
- [x] **Debug Endpoints Removed** (Dec 29, 2025):
  - Removed `/debug/headers` and `/debug/ratelimit` from production
  - Cleaned up Next.js rewrites
- [x] **Multi-Layer Proxy IP Forwarding Fixed**:
  - Caddy → Next.js → Flask all properly forward X-Forwarded-For headers
  - Real client IPs now correctly identified through entire chain
- [x] **Protects Against**:
  - DDoS attacks (API flooding)
  - API cost abuse (OpenAI credit drain)
  - Automated scripts and bots
  - Excessive single-session usage (200/day soft cap)
- [x] **Test Verified**: Rate limiting blocks at 11th request in production

#### Rate Limit Reset Timing
| Limit | Threshold | Reset Behavior |
|-------|-----------|----------------|
| Per Minute | 10 requests | Resets after **1 minute** from first request |
| Per Hour | 50 requests | If exceeded → **10-minute block**, then resets |
| Per Day | 100 requests | If exceeded → **24-hour block** |
| Session Daily | 200 messages | **24-hour rolling window** - old messages age out |
| CAPTCHA | 20 messages | Resets after solving, preserves daily limit |

#### Layered Security Architecture
```
Request Received
       ↓
┌──────────────────────────────────────────┐
│ Layer 1: IP Rate Limit Check             │
│ - 10 requests/minute per IP              │
│ - 50 requests/hour per IP                │
│ - 100 requests/day per IP                │
│ If exceeded → 429 "Too many requests"    │
└──────────────────────────────────────────┘
       ↓ (if passed)
┌──────────────────────────────────────────┐
│ Layer 2: Session Daily Limit             │
│ - 200 messages/day per session           │
│ - Rolling 24h window (auto-resets)       │
│ If exceeded → Friendly support message   │
└──────────────────────────────────────────┘
       ↓ (if passed)
┌──────────────────────────────────────────┐
│ Layer 3: CAPTCHA Check                   │
│ - Triggers after 20 messages since last  │
│ - Math CAPTCHA (e.g., "What is 7 + 5?")  │
│ - Solving resets counter, not daily limit│
└──────────────────────────────────────────┘
       ↓ (if passed or solved)
┌──────────────────────────────────────────┐
│ Layer 4: Process Message                 │
│ - LLM generates response                 │
│ - Conversation saved to database         │
└──────────────────────────────────────────┘
```

#### Use Case Scenarios
| Scenario | Behavior |
|----------|----------|
| **Rapid spam** (10+ messages in under 1 min) | Blocked at 11th message, wait 1 minute to resume |
| **Slow but persistent** (under 10/min) | CAPTCHA triggers at 21st message |
| **Bot attack** (100+ requests/day) | 24-hour IP block |
| **Very long conversation** (200+ messages) | Friendly message: "Contact support@grest.in" |
| **Normal user** (occasional queries) | No interruption, smooth experience |

---

## Current Status

### Production Health
| Component | Status |
|-----------|--------|
| Chatbot | Live |
| Database | Synced (2,205 variants) |
| Dashboard | Operational |
| Auto-Sync | Running (6-hour intervals) |
| Rate Limiter | Active (10 req/min limit) |
| Uptime | 99.9% guaranteed (Reserved VM) |

### Recent Conversations
- Last activity: Dec 25, 2025 (UAT testing)
- Conversations being captured correctly in database
- Dashboard displaying all conversations

---

## Pending / Next Steps

### Immediate (Awaiting UAT Feedback)
- [ ] Address UAT feedback from deployment team
- [ ] Fix any incorrect/failed responses reported
- [ ] Comprehensive testing report review

### Dashboard UI Issues
- [ ] Review and fix dashboard anomalies (per user feedback)

### Serper API Integration
- [ ] Check how GRESTA accesses internet for web searches
- [ ] Verify Serper API configuration

### Future Enhancements
- [ ] WhatsApp integration (Twilio) - ready but optional
- [ ] Instagram integration (Meta API) - ready but optional
- [ ] ManyChat integration refinement

---

## Architecture Summary

```
User Query
    ↓
┌─────────────────────────────────────────┐
│ ALWAYS: Inject product context          │ ← Option A (data available)
│ (compact catalog with database prices)  │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ LLM Decision (Natural)                  │
│ - Clear intent? → Use database prices   │
│ - Vague intent? → Ask for clarification │
└─────────────────────────────────────────┘
    ↓
Response (100% accurate when answering)
```

---

## Key Principle
> "If context is vague → LLM asks counter questions. If intent is clear → Output must be 100% accurate from database. No hallucination allowed."

---

## Contact
- **Developer:** Sam
- **Client Contact:** care@grest.in
- **Support Phone:** +91 92665 22338
