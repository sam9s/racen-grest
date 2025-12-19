# GRESTA - GREST E-commerce Chatbot

A RAG-based chatbot for GREST, India's premium refurbished iPhone and MacBook e-commerce platform. GRESTA serves as a front-line customer engagement tool, answering questions about products, pricing, warranty, and policies.

## Features

### GRESTA AI Assistant
- Bilingual support (English + Hinglish)
- Accurate pricing from PostgreSQL database
- Product recommendations based on budget
- Streaming responses for real-time display

### Product Database
- 569 product variants synced from Shopify
- Per-variant pricing (model × storage × condition × color)
- Automatic sync from GREST Shopify store

### Multi-Channel Support
- Web chat interface (Next.js)
- WhatsApp via Twilio
- Instagram via Meta Graph API
- Embeddable widget for external websites

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend API | Flask (Python) |
| Database | PostgreSQL |
| Vector DB | ChromaDB |
| LLM | OpenAI GPT-4o-mini |

## Project Structure

```
├── src/                    # Next.js frontend
│   ├── app/               # App router pages
│   └── components/        # React components
├── chatbot_engine.py      # Core RAG chatbot logic
├── webhook_server.py      # Flask API server
├── safety_guardrails.py   # GRESTA persona & safety filters
├── knowledge_base.py      # Vector storage
├── database.py            # SQLAlchemy models
├── scrape_grest_products.py # Shopify product sync
└── channel_handlers.py    # Multi-channel handlers
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/stream` | POST | Streaming chat (SSE) |
| `/api/chat` | POST | Non-streaming chat |
| `/health` | GET | Health check |
| `/webhook/whatsapp` | POST | Twilio webhook |
| `/webhook/instagram` | GET/POST | Meta webhook |

## Development

```bash
# Start Flask backend
python webhook_server.py

# Start Next.js frontend
npx next dev -p 5000 -H 0.0.0.0
```

## Environment Variables

Required secrets:
- `DATABASE_URL` - PostgreSQL connection
- `GITHUB_TOKEN` - For backups (optional)
- `TWILIO_*` - For WhatsApp integration
- `INSTAGRAM_*` - For Instagram integration

## Backup

```bash
bash backup.sh  # Push to GitHub
```

## License

Private - GREST India

---

Built with Replit Agent
