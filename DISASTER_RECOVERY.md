# GRESTA Chatbot - Disaster Recovery Guide

This document provides step-by-step instructions to rebuild the GRESTA chatbot application from scratch using only the Git repository backup.

## Prerequisites

Before starting, ensure you have:
- Python 3.11+
- Node.js 20+
- PostgreSQL database access
- OpenAI API key
- Google OAuth credentials (for user authentication)

## Environment Variables Required

Create these environment variables in your deployment environment:

### Required Secrets
```
DATABASE_URL=postgresql://user:password@host:5432/database
OPENAI_API_KEY=sk-xxx (or use Replit AI Integrations)
NEXTAUTH_SECRET=your-random-secret-string
NEXTAUTH_URL=https://your-domain.com
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
INTERNAL_API_KEY=your-internal-api-key
```

### Optional Secrets (for integrations)
```
TWILIO_ACCOUNT_SID=xxx (WhatsApp integration)
TWILIO_AUTH_TOKEN=xxx
TWILIO_WHATSAPP_NUMBER=xxx
META_ACCESS_TOKEN=xxx (Instagram integration)
META_VERIFY_TOKEN=xxx
SERPER_API_KEY=xxx (if using Serper for web search)
```

## Step-by-Step Recovery

### Step 1: Clone the Repository
```bash
git clone https://github.com/sam9s/racen-joveheal.git
cd racen-joveheal
```

### Step 2: Install Dependencies

**Node.js dependencies:**
```bash
npm install
```

**Python dependencies:**
```bash
pip install -r requirements.txt
# Or if using uv:
uv sync
```

### Step 3: Set Up PostgreSQL Database

Run the database initialization script:
```bash
python init_database.py
```

This will:
- Create all required tables (users, conversations, messages, feedback, grest_products)
- Set up indexes for performance

### Step 4: Populate Product Database

Scrape current products from GREST Shopify store:
```bash
python scrape_grest_products.py
```

This populates the `grest_products` table with current pricing and product info.

### Step 5: Rebuild Knowledge Base (ChromaDB)

The vector database rebuilds automatically on first startup. To force rebuild:
```bash
python -c "from knowledge_base import rebuild_knowledge_base; rebuild_knowledge_base()"
```

Or simply start the webhook server - it auto-initializes ChromaDB from documents in:
- `knowledge_base/documents/` folder
- `grest_*.txt` files in root directory

### Step 6: Build Next.js Frontend
```bash
npm run build
```

### Step 7: Start the Application

**Development mode:**
```bash
# Terminal 1: Start Flask backend
python webhook_server.py

# Terminal 2: Start Next.js frontend
npx next dev -p 5000 -H 0.0.0.0
```

**Production mode:**
```bash
bash start_production.sh
```

## File Structure Reference

```
├── src/                    # Next.js frontend source
├── public/                 # Static assets
├── chatbot_engine.py       # Core RAG chatbot logic
├── database.py             # PostgreSQL models & queries
├── knowledge_base.py       # ChromaDB vector store
├── safety_guardrails.py    # Content safety filters
├── webhook_server.py       # Flask API server
├── scrape_grest_products.py # Product data scraper
├── init_database.py        # Database initialization
├── grest_*.txt             # Knowledge base documents
├── package.json            # Node.js dependencies
├── pyproject.toml          # Python dependencies
└── start_production.sh     # Production startup script
```

## Verification Checklist

After recovery, verify these components work:

- [ ] Frontend loads at http://localhost:5000
- [ ] Chat API responds at http://localhost:8080/api/chat/stream
- [ ] Database has products: `SELECT COUNT(*) FROM grest_products;`
- [ ] ChromaDB has embeddings (check startup logs)
- [ ] User authentication works (Google OAuth)
- [ ] Warranty query returns "6 months extendable to 12 months"

## Common Issues

### ChromaDB not loading
```bash
# Delete and rebuild
rm -rf vector_db/
python webhook_server.py  # Will auto-rebuild
```

### Database connection failed
- Verify DATABASE_URL is correct
- Check PostgreSQL is running and accessible

### OpenAI API errors
- Verify OPENAI_API_KEY is set
- Check API quota/billing

### Google OAuth not working
- Verify NEXTAUTH_URL matches your domain
- Check Google Console redirect URIs include your domain

## Backup Schedule Recommendation

- **Daily**: Run `bash backup.sh` to push code changes
- **Weekly**: Export PostgreSQL database dump
- **Monthly**: Full system snapshot if on cloud provider

## Contact

For technical issues with this codebase, refer to `replit.md` for architecture details.
