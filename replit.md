# GRESTA - GREST E-commerce Chatbot

## Overview
GRESTA is a RAG-based chatbot for GREST, India's premium refurbished iPhone and MacBook e-commerce platform. The chatbot serves as a front-line customer engagement tool, answering questions about products, pricing, warranty, and policies with bilingual support (English + Hinglish).

## Recent Updates (Dec 21, 2025)
- **ADMIN DASHBOARD ENHANCED**: Added 4-tab dashboard (Analytics, Conversations, Monitoring, Shopify Sync)
- **REAL-TIME SYNC PROGRESS**: Beautiful step-by-step progress UI with 6 stages (Connecting → Fetching → Processing → Upserting → Cleanup → Complete)
- **EMERALD GREEN BRANDING**: All dashboard UI updated to emerald green (#10b981) matching GRESTA theme
- **SYNC MANAGEMENT**: Manual sync button, verification panel, sync history with detailed metrics
- **MONITORING TAB**: UptimeRobot integration, sync health warnings for stale data
- **DASHBOARD LOGIN**: Email-based auth (samret.singh@grest.in / Samret@123)

### Previous Updates (Dec 20, 2025)
- **DATABASE-FIRST SPECS**: All product specs from database (Shopify metafields), not hardcoded
- **CANONICAL PIPELINE**: Shopify API → Scraper → Database → Chatbot (no hardcoded product data)
- **MULTI-TURN CONVERSATIONS**: Handles follow-up queries like "1TB variant for same product"
- **100% ACCURACY ACHIEVED**: 21/21 tests passed (including multi-turn) - exceeds 95% target
- **Product Coverage**: 2,205 variants from 104 Shopify products (all in-stock)

## Pending Dashboard Issues (To Address Later)
- Other UI anomalies noted by user - to be reviewed after DNS/production setup
- Production URL: gresta.sam9scloud.in (DNS entries pending)

## User Preferences
Focus on high-level features and architectural decisions. Prioritize clarity and conciseness. Direct communication style preferred. Do not make changes to existing file structure without explicit approval.

## System Architecture

### Technical Stack
| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend API | Flask (Python) on port 8080 |
| Database | PostgreSQL (product data, conversations, users) |
| Vector DB | ChromaDB (knowledge base embeddings) |
| LLM | OpenAI GPT-4o-mini via Replit AI Integrations |

### Key Features
- **Hybrid Pricing System**: LLM + PostgreSQL database for accurate pricing (100% accuracy achieved)
- **Multi-Turn Context**: Session-level tracking resolves "same product", "that one" references
- **Bilingual Support**: English and Hinglish responses based on user language
- **Streaming Responses**: SSE-based real-time response display
- **Product Database**: 2,205 variants synced from Shopify with per-variant pricing (all in-stock)
- **Embeddable Widget**: JavaScript widget for external websites
- **Multi-Channel Ready**: WhatsApp (Twilio), Instagram (Meta API) integration

### Database Tables
- `grest_products` - Product variants with pricing (model, storage, condition, color, price)
- `user_accounts` - User data from OAuth
- `chat_sessions` - Session management
- `conversations` - Chat logs
- `response_feedback` - User feedback

### Branding
- Primary Color: Emerald Green (#10b981)
- Bot Name: GRESTA
- Business: GREST (grest.in)

## External Dependencies
- OpenAI (via Replit AI Integrations)
- PostgreSQL (Replit managed)
- ChromaDB (local vector storage)
- Twilio (WhatsApp - optional)
- Meta Graph API (Instagram - optional)

## Key Files
| File | Purpose |
|------|---------|
| `chatbot_engine.py` | Core RAG logic, LLM calls, hybrid pricing |
| `webhook_server.py` | Flask API server |
| `safety_guardrails.py` | GRESTA persona, safety filters |
| `knowledge_base.py` | ChromaDB operations |
| `database.py` | PostgreSQL models and queries |
| `scrape_grest_products.py` | Shopify product sync |

## Disaster Recovery
See `DISASTER_RECOVERY.md` for full instructions:
1. Clone from `github.com/sam9s/racen-grest`
2. Run `init_database.py` to create tables
3. Run `scrape_grest_products.py` to populate products
4. ChromaDB auto-rebuilds on startup

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/stream` | POST | Streaming chat (SSE) |
| `/api/chat` | POST | Non-streaming chat |
| `/api/chat/manychat` | POST | ManyChat integration |
| `/health` | GET | Health check |
| `/webhook/whatsapp` | POST | Twilio webhook |
| `/webhook/instagram` | GET/POST | Meta webhook |

## Development
```bash
# Flask backend
python webhook_server.py

# Next.js frontend
npx next dev -p 5000 -H 0.0.0.0
```

## Backup
```bash
bash backup.sh  # Push to GitHub (racen-grest repo)
```
