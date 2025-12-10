# RAG-Based Conversational Chatbot - Project Blueprint

**Purpose:** This document provides a complete blueprint for replicating this chatbot for a new client. A new AI assistant can read this file to understand the entire architecture and recreate it with different business data, personas, and guardrails.

**Original Project:** JoveHeal Wellness Chatbot (Jovee/RACEN)  
**Version:** 1.0  
**Last Updated:** December 10, 2025

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Diagram](#architecture-diagram)
4. [File Structure](#file-structure)
5. [Core Components](#core-components)
6. [Configuration Points](#configuration-points)
7. [Database Schema](#database-schema)
8. [API Endpoints](#api-endpoints)
9. [Widget Integration](#widget-integration)
10. [Setup Instructions](#setup-instructions)
11. [Deployment](#deployment)

---

## Project Overview

This is a **RAG (Retrieval Augmented Generation) chatbot** designed as a front-line customer engagement tool. It answers questions about a business's programs, services, and offerings by:

1. Ingesting website content and documents into a vector database
2. Retrieving relevant context based on user queries
3. Generating natural language responses using OpenAI's LLM
4. Streaming responses in real-time for a ChatGPT-like experience

### Key Features

| Feature | Description |
|---------|-------------|
| **Embeddable Widget** | JavaScript widget that can be embedded on any website with a single script tag |
| **Streaming Responses** | Real-time character-by-character response display using SSE |
| **Google OAuth** | Optional user sign-in for personalized experiences |
| **Conversation Memory** | Stores last 50 messages per session for context awareness |
| **Personalized Greetings** | Remembers returning users and their previous topics |
| **Safety Guardrails** | Filters for crisis content, medical/mental health queries |
| **Multi-Channel Ready** | Architecture supports WhatsApp (Twilio) and Instagram (Meta API) |
| **Context-Aware Follow-ups** | Understands "tell me more" type questions |
| **Automatic Link Injection** | Adds relevant program/service links to responses |

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
| PostgreSQL | Persistent storage (conversations, users, feedback) |
| ChromaDB | Vector storage (knowledge base embeddings) |

### External Services

| Service | Purpose |
|---------|---------|
| OpenAI | LLM provider (gpt-4o-mini) |
| Google OAuth | User authentication |
| Twilio (optional) | WhatsApp integration |
| Meta Graph API (optional) | Instagram integration |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT WEBSITE                               │
│  ┌───────────────┐                                                  │
│  │ widget.js     │ ← Single script tag embeds the chat widget       │
│  └───────────────┘                                                  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         NEXT.JS FRONTEND (Port 5000)                │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │ Main Chat UI  │  │ NextAuth.js   │  │ API Routes    │           │
│  │ (page.tsx)    │  │ (Google OAuth)│  │ (/api/chat)   │           │
│  └───────────────┘  └───────────────┘  └───────────────┘           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FLASK BACKEND (Port 8080)                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │ webhook_      │  │ chatbot_      │  │ safety_       │           │
│  │ server.py     │  │ engine.py     │  │ guardrails.py │           │
│  └───────────────┘  └───────────────┘  └───────────────┘           │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │ knowledge_    │  │ database.py   │  │ channel_      │           │
│  │ base.py       │  │               │  │ handlers.py   │           │
│  └───────────────┘  └───────────────┘  └───────────────┘           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│      POSTGRESQL         │     │       CHROMADB          │
│  - User accounts        │     │  - Document embeddings  │
│  - Chat sessions        │     │  - Semantic search      │
│  - Conversations        │     │                         │
│  - Feedback             │     │                         │
│  - Summaries            │     │                         │
└─────────────────────────┘     └─────────────────────────┘
```

---

## File Structure

```
project/
├── public/
│   ├── widget.js              # Embeddable chat widget (CRITICAL)
│   ├── jovee-logo.png         # Bot logo (rename for new client)
│   └── favicon.ico            # Site favicon
│
├── src/
│   └── app/
│       ├── page.tsx           # Main chat interface
│       ├── layout.tsx         # Root layout with metadata
│       ├── globals.css        # Global styles
│       ├── api/
│       │   ├── chat/
│       │   │   ├── stream/route.ts    # SSE streaming endpoint
│       │   │   ├── route.ts           # Non-streaming chat
│       │   │   └── reset/route.ts     # Reset conversation
│       │   ├── auth/
│       │   │   └── [...nextauth]/route.ts  # NextAuth config
│       │   └── feedback/route.ts      # User feedback
│       ├── auth/
│       │   └── signin/page.tsx        # Custom sign-in page
│       └── widget-test/page.tsx       # Widget testing page
│
├── knowledge_base/
│   └── documents/             # Text/PDF files for RAG
│       ├── website_homepage.txt
│       ├── website_services.txt
│       ├── website_about.txt
│       └── ... (other content files)
│
├── vector_db/                 # ChromaDB persistent storage
│
├── logs/                      # Application logs
│
├── webhook_server.py          # Flask API server (CRITICAL)
├── chatbot_engine.py          # RAG logic and LLM calls (CRITICAL)
├── safety_guardrails.py       # Persona and safety filters (CRITICAL)
├── knowledge_base.py          # ChromaDB operations
├── database.py                # SQLAlchemy models
├── channel_handlers.py        # WhatsApp/Instagram handlers
├── conversation_logger.py     # Logging utilities
│
├── start_production.sh        # Production startup script
├── package.json               # Node.js dependencies
├── pyproject.toml             # Python dependencies
└── replit.md                  # Project documentation
```

---

## Core Components

### 1. Chatbot Engine (`chatbot_engine.py`)

The brain of the system. Handles:

- **Query preprocessing** - Typo fixing with LLM
- **Context-aware queries** - Detects follow-up questions and adds context
- **RAG retrieval** - Searches ChromaDB for relevant documents
- **Response generation** - Calls OpenAI with context and persona
- **Link injection** - Adds relevant program/service links
- **Streaming** - Yields response chunks for real-time display

**Key Functions:**
```python
generate_response(user_message, conversation_history, ...)  # Non-streaming
generate_response_stream(user_message, conversation_history, ...)  # Streaming
fix_typos_with_llm(user_message)  # Typo correction
build_context_aware_query(message, history)  # Follow-up detection
```

### 2. Safety Guardrails (`safety_guardrails.py`)

Handles safety and persona. Contains:

- **Persona definitions** - Simple and detailed versions
- **Crisis keyword detection** - Suicide, self-harm triggers
- **Mental health filters** - Depression, anxiety, disorder mentions
- **Medical content filters** - Medication, diagnosis queries
- **Safe redirect responses** - Professional referral messages
- **Output filtering** - Catches unsafe LLM responses
- **Program URL mapping** - Maps program names to URLs

**Key Functions:**
```python
get_system_prompt()  # Returns persona based on RACEN_PERSONA_MODE env var
apply_safety_filters(message)  # Pre-filters user input
filter_response_for_safety(response)  # Post-filters LLM output
inject_program_links(response)  # Adds clickable links
```

### 3. Knowledge Base (`knowledge_base.py`)

Manages the vector database:

- **Document ingestion** - Text files, PDFs, web scraping
- **Chunking** - Splits documents into searchable segments
- **Embedding** - Uses ChromaDB's built-in embeddings
- **Search** - Semantic similarity search
- **Initialization** - Auto-rebuilds on cold starts

**Key Functions:**
```python
initialize_knowledge_base(force_refresh=False, enable_web_scrape=False)
search_knowledge_base(query, n_results=5)
ingest_text_file(file_path, original_filename)
ingest_pdf_file(file_path, original_filename)
```

### 4. Webhook Server (`webhook_server.py`)

Flask API server handling:

- **Chat endpoints** - `/api/chat`, `/api/chat/stream`
- **Health check** - `/health`
- **WhatsApp webhooks** - `/webhook/whatsapp`
- **Instagram webhooks** - `/webhook/instagram`
- **Conversation history management**

### 5. Widget (`public/widget.js`)

Self-contained JavaScript widget:

- **Floating chat bubble** - Opens/closes chat window
- **Resizable window** - Drag corners to resize
- **Streaming display** - Real-time response rendering
- **Session management** - Generates and stores session ID
- **XSS protection** - Safe text rendering
- **CORS ready** - Works on external domains

---

## Configuration Points

### Files to Modify for New Client

| File | What to Change |
|------|----------------|
| `safety_guardrails.py` | Persona text, program URLs, business rules |
| `knowledge_base/documents/*.txt` | All content files with new business data |
| `public/widget.js` | Bot name, colors, logo URL |
| `public/jovee-logo.png` | Replace with new logo |
| `src/app/page.tsx` | Branding, bot name, UI text |
| `src/app/layout.tsx` | Meta title, description |

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API access | Yes |
| `SESSION_SECRET` | NextAuth session encryption | Yes |
| `GOOGLE_CLIENT_ID` | Google OAuth | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth | Optional |
| `NEXTAUTH_URL` | Auth callback URL | For OAuth |
| `NEXTAUTH_SECRET` | Auth encryption | For OAuth |
| `TWILIO_ACCOUNT_SID` | WhatsApp | Optional |
| `TWILIO_AUTH_TOKEN` | WhatsApp | Optional |
| `TWILIO_WHATSAPP_NUMBER` | WhatsApp | Optional |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram | Optional |
| `INSTAGRAM_VERIFY_TOKEN` | Instagram | Optional |
| `RACEN_PERSONA_MODE` | "simple" or "detailed" | Optional |
| `INTERNAL_API_KEY` | Frontend-backend auth | Recommended |

### Persona Configuration

The persona is defined in `safety_guardrails.py` in two functions:

1. **`_get_simple_persona()`** - Concise version (~20 lines)
2. **`_get_detailed_persona()`** - Full version with examples (~100 lines)

**Key sections to customize:**
- Bot name and identity
- Business name and "we/us/our" language
- Program/service descriptions
- Pricing and booking workflows
- Safety disclaimers relevant to the industry
- Example conversations

### Safety Guardrails Configuration

Located in `safety_guardrails.py`:

1. **`JOVEHEAL_PROGRAM_URLS`** - Dictionary mapping program names to URLs
2. **`TOPIC_TO_PROGRAMS`** - Maps user topics to relevant programs
3. **`CRISIS_KEYWORDS`** - Words triggering crisis response
4. **`MENTAL_HEALTH_KEYWORDS`** - Mental health topic triggers
5. **`MEDICAL_KEYWORDS`** - Medical topic triggers
6. **`SAFE_REDIRECT_RESPONSE`** - Crisis response template
7. **`MEDICAL_REDIRECT_RESPONSE`** - Medical query response
8. **`THERAPY_REDIRECT_RESPONSE`** - Therapy boundary response

---

## Database Schema

### Tables

#### user_accounts
```sql
id              SERIAL PRIMARY KEY
channel         VARCHAR(50) NOT NULL      -- 'web', 'whatsapp', 'instagram'
external_id     VARCHAR(255) NOT NULL     -- OAuth ID or phone number
email           VARCHAR(255)
display_name    VARCHAR(255)
profile_image   VARCHAR(500)
created_at      TIMESTAMP
last_seen       TIMESTAMP
```

#### chat_sessions
```sql
id              SERIAL PRIMARY KEY
session_id      VARCHAR(100) UNIQUE       -- UUID for anonymous users
user_id         INTEGER REFERENCES user_accounts(id)
created_at      TIMESTAMP
last_activity   TIMESTAMP
channel         VARCHAR(50) DEFAULT 'web'
```

#### conversations
```sql
id              SERIAL PRIMARY KEY
session_id      VARCHAR(100) REFERENCES chat_sessions(session_id)
timestamp       TIMESTAMP
user_question   TEXT NOT NULL
bot_answer      TEXT NOT NULL
safety_flagged  BOOLEAN DEFAULT FALSE
safety_category VARCHAR(100)
sources_used    TEXT                      -- JSON array
response_time_ms INTEGER
```

#### response_feedback
```sql
id              SERIAL PRIMARY KEY
conversation_id INTEGER REFERENCES conversations(id) UNIQUE
rating          INTEGER NOT NULL          -- 1 (thumbs down) or 5 (thumbs up)
comment         TEXT
created_at      TIMESTAMP
```

#### conversation_summaries
```sql
id                  SERIAL PRIMARY KEY
user_id             INTEGER REFERENCES user_accounts(id) UNIQUE
emotional_themes    TEXT
recommended_programs TEXT
last_topics         TEXT
conversation_status TEXT
updated_at          TIMESTAMP
```

#### analytics_daily
```sql
id                  SERIAL PRIMARY KEY
date                TIMESTAMP UNIQUE
total_conversations INTEGER DEFAULT 0
unique_sessions     INTEGER DEFAULT 0
safety_flags        INTEGER DEFAULT 0
avg_response_time_ms FLOAT
positive_feedback   INTEGER DEFAULT 0
negative_feedback   INTEGER DEFAULT 0
```

---

## API Endpoints

### Frontend API (Next.js - Port 5000)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/stream` | POST | Streaming chat (SSE) |
| `/api/chat` | POST | Non-streaming chat |
| `/api/chat/reset` | POST | Reset conversation |
| `/api/feedback` | POST | Submit feedback |
| `/api/auth/[...nextauth]` | GET/POST | NextAuth handlers |

### Backend API (Flask - Port 8080)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/chat` | POST | Direct chat (internal) |
| `/api/chat/stream` | POST | Direct streaming (internal) |
| `/api/channels/status` | GET | Channel configuration status |
| `/webhook/whatsapp` | POST | WhatsApp incoming messages |
| `/webhook/instagram` | POST/GET | Instagram messages + verification |

### Request/Response Format

**Chat Request:**
```json
{
  "message": "What programs do you offer?",
  "session_id": "uuid-string",
  "user_info": {
    "name": "John",
    "email": "john@example.com",
    "isAuthenticated": true
  }
}
```

**Streaming Response (SSE):**
```
data: {"type": "content", "content": "We offer "}
data: {"type": "content", "content": "several "}
data: {"type": "content", "content": "programs..."}
data: {"type": "done", "sources": ["website_services.txt"], "links_added": true}
```

---

## Widget Integration

### Embedding on External Website

Add this single line to any HTML page:

```html
<script src="https://your-deployed-url.com/widget.js"></script>
```

### Widget Features

- **Floating bubble** - Bottom-right corner, opens chat window
- **Resizable** - Drag corners to resize (300x400 to 600px)
- **Responsive** - Adapts to mobile screens
- **Session persistence** - Maintains conversation across page loads
- **CORS-enabled** - Works on any domain (configure allowed origins)

### CORS Configuration

In `webhook_server.py`:
```python
CORS(app, origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
    "https://*.kajabi.com",  # If using Kajabi
])
```

In `next.config.js`, add headers for widget.js:
```javascript
headers: [
  {
    source: '/widget.js',
    headers: [
      { key: 'Access-Control-Allow-Origin', value: '*' }
    ]
  }
]
```

---

## Setup Instructions

### 1. Create New Replit Project

1. Fork this project or create new Python + Node.js project
2. Copy all files to new project

### 2. Configure Environment Variables

Set these in Replit Secrets:
- `DATABASE_URL` (create PostgreSQL database in Replit)
- `OPENAI_API_KEY` (from OpenAI dashboard)
- `SESSION_SECRET` (generate random string)

### 3. Prepare Knowledge Base

1. Delete existing files in `knowledge_base/documents/`
2. Add new client's content as `.txt` files:
   - `website_homepage.txt`
   - `website_services.txt`
   - `website_about.txt`
   - etc.

**Format for content files:**
```
Business Name - Page Title
Source: https://website.com/page-url

[Content from the page...]
```

### 4. Update Persona

Edit `safety_guardrails.py`:

1. Replace bot name (RACEN → new name)
2. Replace business name (JoveHeal → new name)
3. Update `JOVEHEAL_PROGRAM_URLS` dict
4. Update `TOPIC_TO_PROGRAMS` mapping
5. Customize persona text in `_get_simple_persona()` and `_get_detailed_persona()`
6. Adjust safety keywords if industry-specific

### 5. Update Branding

1. Replace `public/jovee-logo.png` with new logo
2. Update `public/widget.js`:
   - Bot name in UI text
   - Colors (`primaryColor`)
   - Any hardcoded branding
3. Update `src/app/page.tsx`:
   - Bot name
   - Welcome messages
   - UI text

### 6. Initialize Database

Run the application once - database tables are created automatically.

### 7. Test

1. Start the development server
2. Visit `/widget-test` to test the widget
3. Test various queries
4. Verify safety guardrails trigger appropriately

### 8. Deploy

1. Click "Publish" in Replit
2. Configure autoscaling if needed
3. Note the published URL for widget embedding

---

## Deployment

### Workflows Configuration

Two workflows should be configured:

1. **Frontend** - `npx next dev -p 5000 -H 0.0.0.0`
2. **Webhook Server** - `python webhook_server.py`

### Production Startup

Use `start_production.sh` for production:
```bash
#!/bin/bash
# Starts Flask first, waits for health, then starts Next.js
python webhook_server.py &
sleep 5
curl --retry 10 --retry-delay 2 http://localhost:8080/health
npx next start -p 5000 -H 0.0.0.0
```

### Health Checks

- Flask: `http://localhost:8080/health`
- Next.js: `http://localhost:5000`

---

## Common Customizations

### Change Bot Personality

Edit the persona in `safety_guardrails.py`:
- Tone (formal vs casual)
- Response length preferences
- Emoji usage
- Industry-specific language

### Add New Safety Categories

In `safety_guardrails.py`:
1. Add new keyword list
2. Create check function
3. Add to `apply_safety_filters()`

### Add New Program/Service Links

In `safety_guardrails.py`:
1. Add to `JOVEHEAL_PROGRAM_URLS`
2. Add topic mappings to `TOPIC_TO_PROGRAMS`

### Disable Authentication

If OAuth not needed:
1. Remove NextAuth configuration
2. Remove sign-in UI components
3. System still works with anonymous sessions

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Widget not loading | Check CORS headers, verify published URL |
| No responses | Check OpenAI API key, verify Flask is running |
| Empty knowledge base | Run `initialize_knowledge_base(force_refresh=True)` |
| Slow responses | Check OpenAI rate limits, consider caching |
| Database errors | Verify DATABASE_URL, check connection |

---

## Cost Estimation

See `COST_ASSESSMENT.md` for detailed cost breakdown including:
- Replit hosting costs
- OpenAI API costs by usage level
- Recommended client pricing tiers

---

*This blueprint should enable any AI assistant to replicate this chatbot system for a new client with minimal guidance.*
