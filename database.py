"""
Database Models and Connection for JoveHeal Chatbot

PostgreSQL database for:
- Conversation logs with analytics
- User feedback on responses
- Session tracking
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None

Base = declarative_base()


class ChatSession(Base):
    """Tracks individual chat sessions."""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    channel = Column(String(50), default="web")
    
    conversations = relationship("Conversation", back_populates="session")


class Conversation(Base):
    """Stores individual conversation exchanges."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("chat_sessions.session_id"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_question = Column(Text, nullable=False)
    bot_answer = Column(Text, nullable=False)
    safety_flagged = Column(Boolean, default=False, index=True)
    safety_category = Column(String(100), nullable=True)
    sources_used = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    session = relationship("ChatSession", back_populates="conversations")
    feedback = relationship("ResponseFeedback", back_populates="conversation", uselist=False)


class ResponseFeedback(Base):
    """Stores user feedback on bot responses."""
    __tablename__ = "response_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), unique=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="feedback")


class AnalyticsDaily(Base):
    """Pre-aggregated daily analytics for performance."""
    __tablename__ = "analytics_daily"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, unique=True, index=True)
    total_conversations = Column(Integer, default=0)
    unique_sessions = Column(Integer, default=0)
    safety_flags = Column(Integer, default=0)
    avg_response_time_ms = Column(Float, nullable=True)
    positive_feedback = Column(Integer, default=0)
    negative_feedback = Column(Integer, default=0)


def init_database():
    """Initialize database tables."""
    if engine:
        Base.metadata.create_all(bind=engine)
        return True
    return False


@contextmanager
def get_db_session():
    """Get a database session with automatic cleanup."""
    if SessionLocal is None:
        yield None
        return
    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def is_database_available():
    """Check if database connection is available."""
    return engine is not None and DATABASE_URL is not None
