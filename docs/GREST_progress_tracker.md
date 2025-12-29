# GREST Progress Tracker

## Project Overview
**Project Name:** GRESTA - AI Conversational Chatbot for GREST  
**Client:** GREST (India's premium refurbished iPhone & MacBook e-commerce platform)  
**Production URL:** https://gresta.sam9scloud.in  
**Developer:** Sam (Product Owner, Project Manager, Developer)  
**Start Date:** December 2024  
**Last Updated:** December 29, 2025 (Phase 8 Security Blueprint finalized)

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

### Phase 8: Security Implementation (Dec 27-29, 2025) - REUSABLE BLUEPRINT

> **BLUEPRINT NOTE**: This entire Phase 8 can be replicated for Joviheal or any other chatbot project. The same rate limiter, CAPTCHA system, and dashboard can be deployed with minimal modifications.

#### 8.1 Core Implementation
- [x] **Rate Limiter Module**: `rate_limiter.py` with IP-based throttling
- [x] **Database-Backed Persistence**: All rate limiting data stored in PostgreSQL (survives server restarts)
- [x] **Thresholds Configured**:
  - 10 requests/minute (soft limit)
  - 50 requests/hour (10-minute block)
  - 100 requests/day (24-hour block)
  - CAPTCHA after 20 messages per session (resets after solving)
  - **200 messages/day per session** (24h rolling window, friendly message)

#### 8.2 Protected Endpoints
- `/api/chat` - Direct chat API
- `/api/chat/stream` - Streaming chat (SSE)
- `/api/chat/manychat` - ManyChat/Instagram integration (greeting exempt)

#### 8.3 Database Tables (PostgreSQL)
```sql
-- Rate limit request logging
CREATE TABLE rate_limit_requests (
  id SERIAL PRIMARY KEY,
  ip_address VARCHAR(45) NOT NULL,
  session_id VARCHAR(255),
  endpoint VARCHAR(255),
  message_preview TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_rate_limit_ip_time ON rate_limit_requests(ip_address, created_at);
CREATE INDEX idx_rate_limit_session_time ON rate_limit_requests(session_id, created_at);

-- IP blocks
CREATE TABLE rate_limit_blocks (
  id SERIAL PRIMARY KEY,
  ip_address VARCHAR(45) UNIQUE NOT NULL,
  blocked_until TIMESTAMP NOT NULL,
  reason VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pending CAPTCHAs
CREATE TABLE rate_limit_captchas (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(255) UNIQUE NOT NULL,
  question VARCHAR(255) NOT NULL,
  answer VARCHAR(50) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CAPTCHA verifications (resets message counter)
CREATE TABLE rate_limit_captcha_verified (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(255) UNIQUE NOT NULL,
  verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 8.4 Monitoring & Dashboard
- [x] **Security Dashboard Tab** in Admin Panel
  - Summary metrics: Active IPs, Blocked IPs, Pending CAPTCHAs, Total Requests
  - Rate limit configuration display
  - Currently blocked IPs with countdown timers
  - Top active IPs with per-minute/hour/day request counts
  - Recent requests log with 10-second auto-refresh

#### 8.5 Debug Endpoints (Dev Only)
- Removed `/debug/headers` and `/debug/ratelimit` from production
- Available only in development for testing IP forwarding

---

### Phase 8 Issues Faced & Solutions (CRITICAL FOR REPLICATION)

#### Issue 1: In-Memory Rate Limiting Lost on Server Restart
**Problem**: Initial implementation used Python dictionaries to track requests. Data was lost every time the Flask server restarted.
**Solution**: Migrated to PostgreSQL-backed storage with 4 tables (rate_limit_requests, rate_limit_blocks, rate_limit_captchas, rate_limit_captcha_verified).
**Key Learning**: Never use in-memory storage for security features in production.

#### Issue 2: Database Connection Exhaustion
**Problem**: Original `check_rate_limit()` opened 3+ separate database connections per request (one for each time window check). Under load, this exhausted the connection pool.
**Solution**: Refactored to use a single database connection per rate limit check with batched queries using PostgreSQL `FILTER` clause:
```python
cur.execute(
    """SELECT 
        COUNT(*) FILTER (WHERE created_at > %s) as minute_count,
        COUNT(*) FILTER (WHERE created_at > %s) as hour_count,
        COUNT(*) as day_count
       FROM rate_limit_requests 
       WHERE ip_address = %s AND created_at > %s""",
    (minute_ago, hour_ago, ip, day_ago)
)
```

#### Issue 3: Multi-Layer Proxy IP Detection
**Problem**: Real client IPs were not being detected through the proxy chain (Caddy → Next.js → Flask). Rate limiter was seeing proxy IPs instead of real user IPs.
**Solution**: Ensured all layers forward `X-Forwarded-For` headers:
- **Caddy**: `header_up X-Forwarded-For {http.request.header.X-Forwarded-For}`
- **Next.js**: Extract from `request.headers.get('x-forwarded-for')` and forward to Flask
- **Flask**: Parse first IP from `X-Forwarded-For` header

#### Issue 4: CAPTCHA Not Displaying in Production
**Problem**: CAPTCHA was triggered (stored in database) but users saw "connection issue" instead of the math question.
**Root Cause**: Flask returns HTTP 429 for rate limit/CAPTCHA. Next.js API route was treating ANY non-2xx response as error and not passing through the CAPTCHA data.
**Solution**: Added special handling for 429 in Next.js stream route:
```typescript
if (response.status === 429) {
  const data = await response.json();
  return new Response(JSON.stringify(data), { 
    status: 429, 
    headers: { 'Content-Type': 'application/json', ...corsHeaders }
  });
}
```

#### Issue 5: Security Dashboard Authentication Mismatch
**Problem**: Dashboard Security tab returned "Unauthorized" even when logged in.
**Root Cause**: Login API set `admin_token` cookie, but security route checked for `admin_session` cookie.
**Solution**: Updated security route to use correct cookie name and decode the base64 token:
```typescript
const adminToken = cookieStore.get('admin_token');
const decoded = Buffer.from(adminToken.value, 'base64').toString('utf-8');
const [email] = decoded.split(':');
```

#### Issue 6: CAPTCHA Counter Not Resetting After Solve
**Problem**: After solving CAPTCHA, users expected 20 more messages before next CAPTCHA. Instead, CAPTCHA triggered immediately.
**Root Cause**: Counter was checking total session messages, not messages since last CAPTCHA verification.
**Solution**: Track `verified_at` timestamp in `rate_limit_captcha_verified` table. Count only messages AFTER that timestamp:
```python
if verified_result:
    cur.execute(
        "SELECT COUNT(*) FROM rate_limit_requests WHERE session_id = %s AND created_at > %s",
        (session_id, verified_result['verified_at'])
    )
```

#### Issue 7: Test Session CAPTCHA Already Solved
**Problem**: User tested but CAPTCHA didn't appear at message 21.
**Root Cause**: Developer had previously tested and solved CAPTCHA on the same session ID. The verification record persisted in database.
**Solution**: For fresh testing, clear the verification record:
```sql
DELETE FROM rate_limit_captcha_verified WHERE session_id = 'session_id_here';
```

---

### Phase 8 Replication Checklist for Joviheal

1. **Copy Files**:
   - `rate_limiter.py` (update thresholds as needed)
   - Database table creation SQL (run in PostgreSQL)
   
2. **Integrate into Flask/Backend**:
   - Import and initialize rate limiter in main server file
   - Add `check_rate_limit()` call before processing each chat request
   - Add `log_request()` call after successful processing
   
3. **Update Next.js API Routes** (if using Next.js frontend):
   - Add 429 status handling to pass through CAPTCHA data
   - Ensure `X-Forwarded-For` headers are forwarded
   
4. **Frontend CAPTCHA Handling**:
   - Check for `response.status === 429` and `captcha_required: true`
   - Show prompt/modal with CAPTCHA question
   - Resend message with `captcha_answer` parameter
   
5. **Admin Dashboard**:
   - Copy Security Dashboard component
   - Add `/api/admin/security` endpoint
   - Ensure authentication uses correct cookie name

6. **Testing Protocol**:
   - Send 21 messages rapidly → CAPTCHA should appear
   - Solve CAPTCHA → Should allow 20 more messages
   - Test from production with cleared verification records

---

### Phase 8 Test Verification
- [x] **CAPTCHA Triggered**: At 21st message, "What is 6 + 6?" popup appeared
- [x] **CAPTCHA Solved**: Entering "12" allowed conversation to continue
- [x] **Database Persistence**: Data survives server restarts
- [x] **Dashboard Display**: Security tab shows active IPs, requests, blocks
- [x] **IP Detection**: Real client IPs detected through Caddy → Next.js → Flask chain

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
