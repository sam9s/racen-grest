# RAG-Based E-commerce Chatbot - Project Blueprint

**Purpose:** This document provides a complete blueprint for replicating this chatbot for a new client.

**Current Project:** GRESTA - GREST E-commerce Chatbot  
**Version:** 2.0  
**Last Updated:** December 19, 2025

---

## Project Overview

This is a **RAG (Retrieval Augmented Generation) chatbot** with a **hybrid database approach** designed for e-commerce. It answers questions about products, pricing, and policies by:

1. Querying PostgreSQL for accurate pricing data
2. Searching ChromaDB for policy and general knowledge
3. Generating natural language responses using OpenAI's LLM
4. Streaming responses in real-time

### Key Features

| Feature | Description |
|---------|-------------|
| **Hybrid Pricing** | LLM + Database for 98% pricing accuracy |
| **Bilingual Support** | English + Hinglish responses |
| **Streaming Responses** | Real-time SSE display |
| **Product Database** | Synced from Shopify with per-variant pricing |
| **Embeddable Widget** | JavaScript widget for external websites |
| **Multi-Channel** | Web, WhatsApp (Twilio), Instagram (Meta API) |

---

## Technology Stack

### Frontend (Port 5000)

| Technology | Purpose |
|------------|---------|
| Next.js 14 | React framework with App Router |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| NextAuth.js | Google OAuth authentication |

### Backend (Port 8080)

| Technology | Purpose |
|------------|---------|
| Flask | API server and webhook handler |
| Flask-CORS | Cross-origin requests for widget |
| OpenAI API | LLM for response generation (gpt-4o-mini) |
| ChromaDB | Vector database for semantic search |
| SQLAlchemy | PostgreSQL ORM |

### Database

| Technology | Purpose |
|------------|---------|
| PostgreSQL | Product data, conversations, users |
| ChromaDB | Knowledge base embeddings |

---

## File Structure

```
project/
├── src/
│   └── app/
│       ├── page.tsx           # Main chat interface
│       ├── layout.tsx         # Root layout
│       ├── api/
│       │   ├── chat/
│       │   │   ├── stream/route.ts    # SSE streaming
│       │   │   └── route.ts           # Non-streaming
│       │   └── feedback/route.ts
│
├── public/
│   └── widget.js              # Embeddable chat widget
│
├── knowledge_base/
│   └── documents/             # Text/PDF files for RAG
│
├── webhook_server.py          # Flask API server
├── chatbot_engine.py          # RAG logic and LLM calls
├── safety_guardrails.py       # Persona and safety filters
├── knowledge_base.py          # ChromaDB operations
├── database.py                # SQLAlchemy models
├── scrape_grest_products.py   # Shopify product sync
└── channel_handlers.py        # WhatsApp/Instagram handlers
```

---

## Configuration Points

### Files to Modify for New Client

| File | What to Change |
|------|----------------|
| `safety_guardrails.py` | Persona text, URLs, business rules |
| `knowledge_base/documents/*.txt` | Content files with business data |
| `public/widget.js` | Bot name, colors, logo URL |
| `src/app/page.tsx` | Branding, bot name, UI text |
| `scrape_grest_products.py` | Shopify store URL |

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection | Yes |
| `OPENAI_API_KEY` | OpenAI API access | Yes |
| `NEXTAUTH_SECRET` | Auth encryption | For OAuth |
| `GOOGLE_CLIENT_ID` | Google OAuth | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth | Optional |

---

## Setup Instructions

1. Clone repository
2. Install dependencies (`npm install`, `pip install`)
3. Set environment variables
4. Run `init_database.py` to create tables
5. Run product sync script
6. Start servers

---

*This blueprint enables replication of this chatbot for new clients.*
