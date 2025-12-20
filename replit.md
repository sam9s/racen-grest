# GRESTA - GREST E-commerce Chatbot

## Overview
GRESTA is a RAG-based chatbot for GREST, India's premium refurbished iPhone and MacBook e-commerce platform. The chatbot serves as a front-line customer engagement tool, answering questions about products, pricing, warranty, and policies with bilingual support (English + Hinglish).

## Recent Updates (Dec 20, 2025)
- **Database Sync Fixed**: Optimized Shopify scraper with batch lookups and per-product commits
- **Product Coverage Expanded**: 1,425 variants now in database (was 939)
- **iPhone 14/15 Added**: All iPhone 14, 15, 15 Pro, 15 Pro Max variants now synced
- **LLM Parser Enhanced**: Now extracts color, category, spec_only, comparison_models with Hinglish support
- **Database Search Improved**: Color filtering, category fallback, product comparison functions added

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
- **Hybrid Pricing System**: LLM + PostgreSQL database for accurate pricing (98% accuracy target)
- **Bilingual Support**: English and Hinglish responses based on user language
- **Streaming Responses**: SSE-based real-time response display
- **Product Database**: 569 variants synced from Shopify with per-variant pricing
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
