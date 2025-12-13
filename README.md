# Jovee - JoveHeal Wellness Chatbot

A RAG-based web chatbot for JoveHeal wellness coaching business. Jovee serves as a front-line information bot for website visitors, answering questions about programs, services, and offerings.

## Mobile App (Android/iOS)

This project includes Capacitor for building native mobile apps.

### Quick Start (Clone & Build)

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd <project-folder>

# 2. Install dependencies
npm install

# 3. Sync Capacitor with Android
npx cap sync android

# 4. Open in Android Studio
# Navigate to the 'android' folder and open it in Android Studio
# Build → Build Bundle(s) / APK(s) → Build APK(s)
```

### For iOS (requires Mac + Xcode)
```bash
npx cap add ios
npx cap sync ios
# Open ios/ folder in Xcode
```

## Live Demo

- **Production**: https://jove.sam9scloud.in
- **Replit**: https://jove-heal-chatbot--sam9s.replit.app

## Features

### RACEN AI Assistant
- Warm, empathetic conversational AI
- Multi-turn conversation with context awareness
- Automatic program link injection
- Safety guardrails for medical/mental health topics

### Knowledge Base
- Website content from 7+ JoveHeal pages
- PDF and text document ingestion
- ChromaDB vector storage for semantic search

### Multi-Channel Support
- Web chat interface (Next.js)
- WhatsApp via Twilio
- Instagram via Meta Graph API
- REST API for custom integrations

### Admin Panel
- Conversation logs and analytics
- Knowledge base management
- Feedback tracking
- Channel configuration

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend API | Flask (Python) |
| Admin Panel | Streamlit |
| LLM | OpenAI GPT-4o-mini |
| Vector DB | ChromaDB |
| Database | PostgreSQL |
| Messaging | Twilio (WhatsApp) |

## Project Structure

```
├── src/                    # Next.js frontend
│   ├── app/               # App router pages
│   └── components/        # React components
├── app.py                 # Streamlit admin panel
├── chatbot_engine.py      # Core RAG chatbot logic
├── webhook_server.py      # Flask API server
├── safety_guardrails.py   # Safety filters & RACEN persona
├── knowledge_base.py      # Vector storage
├── database.py            # SQLAlchemy models
└── channel_handlers.py    # Multi-channel handlers
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message, get response |
| `/api/chat/reset` | POST | Reset conversation |
| `/health` | GET | Health check |
| `/webhook/whatsapp` | POST | Twilio webhook |
| `/webhook/instagram` | GET/POST | Meta webhook |

## JoveHeal Programs

RACEN provides information about:
- Balance Mastery (3-month 1:1 coaching)
- Inner Mastery Lounge (membership community)
- Elevate 360 (5-month group program)
- Relationship Healing
- Career Healing
- Beyond the Hustle
- Inner Reset
- Shed & Shine

## Safety Guidelines

The chatbot follows strict safety policies:
- No medical, psychological, or therapeutic advice
- No diagnosis or treatment recommendations
- Safe redirection for crisis/distress situations
- Stays within mindset coaching boundaries

## Environment Variables

Required secrets:
- `DATABASE_URL` - PostgreSQL connection
- `GITHUB_TOKEN` - For backups (optional)
- `TWILIO_*` - For WhatsApp integration
- `INSTAGRAM_*` - For Instagram integration

## Development

```bash
# Start development servers
python webhook_server.py  # Flask API on port 8080
npx next dev -p 5000      # Next.js on port 5000

# Admin panel
streamlit run app.py --server.port 5001
```

## Backup

```bash
bash backup.sh  # Push to GitHub
```

## License

Private - JoveHeal Wellness Coaching

---

Built with Replit Agent
