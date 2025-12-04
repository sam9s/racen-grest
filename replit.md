# JoveHeal Wellness Chatbot

## Overview
The JoveHeal Wellness Chatbot is a RAG-based web chatbot designed for the JoveHeal wellness coaching business. Its primary purpose is to act as a front-line information source for website visitors, answering questions about programs, services, and offerings by leveraging a knowledge base derived from website content and uploaded documents. This MVP aims to enhance user engagement and provide immediate, accurate information about JoveHeal's services.

## User Preferences
I want the agent to focus on high-level features and architectural decisions, avoiding granular implementation specifics unless directly related to a core architectural choice. Please consolidate redundant information and prioritize clarity and conciseness. I prefer a clear, direct communication style. Do not make changes to the existing file structure without explicit approval.

## System Architecture

### UI/UX Decisions
The chatbot, named RACEN (Real-time Advisor for Coaching, Education & Navigation), has a defined personality: warm, empathetic, and guide-like, using plain, human-friendly language. Responses are formatted for readability (short sentences, 2-5 sentences for facts) with empathy prioritized for emotional queries. The frontend is built with Next.js 14, TypeScript, and Tailwind CSS, featuring a branded R.A.C.E.N interface. Streaming responses are implemented using Server-Sent Events (SSE) for a real-time, ChatGPT-like user experience. Clickable links are automatically generated for mentioned JoveHeal programs and pages.

### Technical Implementations
The core system uses a Retrieval Augmented Generation (RAG) approach.
- **Persistent Conversation Memory**: Users can sign in with Google to save conversations to a PostgreSQL database, allowing RACEN to remember past interactions and provide personalized greetings and context-aware responses.
- **Personalized Greetings**: For signed-in users, RACEN offers first-name addressing, welcome-back messages with context from previous conversations, and new user introductions.
- **Smart Conversation Summaries**: LLM-powered summaries of conversations are generated and stored, enabling RACEN to recall specific topics and recommendations for returning users.
- **LLM-Powered Typo Fixer**: Utilizes GPT-3.5-turbo to correct user typos before RAG retrieval, ensuring accurate search results from the ChromaDB vector store.
- **Knowledge Base**: Supports PDF and text document uploads, and ingests website content. ChromaDB is used for vector storage to enable semantic search.
- **Safety Guardrails**: Includes strict filtering for medical/mental health content, crisis keyword detection with safe redirection, and logging of flagged conversations.
- **Multi-Channel Support**: Integrates with WhatsApp (via Twilio) and Instagram (via Meta Graph API), along with a direct API for custom integrations, maintaining session management and unified logging across channels.
- **Google OAuth Authentication**: Implemented using NextAuth.js for user sign-in, linking conversations to user accounts in PostgreSQL. Server-side session verification and an internal API key secure communication between Next.js and Flask.
- **Production Reliability**: Includes retry logic on the frontend, a robust startup script (`start_production.sh`) to ensure Flask is healthy before Next.js, a Flask `/health` endpoint, and an auto-rebuild mechanism for the ChromaDB knowledge base on cold starts to ensure data persistence.

### Feature Specifications
- Natural language Q&A with multi-turn context awareness.
- Source attribution for answers.
- User feedback (thumbs up/down with comments).
- Admin Panel for knowledge base management, document upload, conversation logs, analytics, and multi-channel configuration.
- Strict safety policies: no medical/psychological advice, crisis redirection.

### System Design Choices
The architecture separates concerns into a Next.js frontend (port 5000), a Flask backend for webhooks and chat API (port 8080), and a Streamlit admin panel (port 5001). PostgreSQL is the chosen relational database for persistent storage, with SQLAlchemy ORM for data modeling. OpenAI's `gpt-4o-mini` is used as the primary LLM via Replit AI Integrations. ChromaDB handles vector storage. The system is designed to be resilient to Replit's autoscale features through robust startup procedures and knowledge base re-initialization.

## External Dependencies
- **LLM Provider**: OpenAI (via Replit AI Integrations, specifically `gpt-4o-mini`)
- **Vector Database**: ChromaDB
- **Relational Database**: PostgreSQL
- **Frontend Framework**: Next.js (with React, TypeScript, Tailwind CSS)
- **Backend Framework**: Flask
- **Admin Panel Framework**: Streamlit
- **Authentication**: NextAuth.js (with Google OAuth provider)
- **PDF Processing**: PyPDF
- **WhatsApp Integration**: Twilio SDK
- **Instagram Integration**: Meta Graph API
- **Data Analysis**: Pandas (for analytics dashboard)