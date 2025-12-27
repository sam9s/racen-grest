"""
Webhook Server for Multi-Channel Messaging

Flask-based API server handling:
- WhatsApp webhooks (via Twilio)
- Instagram webhooks (via Meta Graph API)
- Direct API access for custom integrations
- React frontend API endpoints
"""

import os
import json
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from channel_handlers import (
    whatsapp_handler,
    instagram_handler,
    process_channel_message,
    get_channel_status
)
from chatbot_engine import generate_response, generate_response_stream, generate_conversation_summary, fix_typos_with_llm
from conversation_logger import log_feedback, log_conversation, ensure_session_exists
from database import get_or_create_user, get_user_conversation_history, get_conversation_summary, upsert_conversation_summary
from knowledge_base import initialize_knowledge_base, get_knowledge_base_stats
from sync_manager import start_sync_manager, get_sync_manager
from rate_limiter import rate_limiter, get_client_ip

app = Flask(__name__)
CORS(app)

def init_knowledge_base_on_startup():
    """Initialize knowledge base on startup if empty (for autoscale cold starts)."""
    try:
        stats = get_knowledge_base_stats()
        if stats["total_chunks"] == 0:
            print("[Startup] Knowledge base is empty, rebuilding from website...")
            initialize_knowledge_base(force_refresh=False, enable_web_scrape=True)
            stats = get_knowledge_base_stats()
            print(f"[Startup] Knowledge base rebuilt with {stats['total_chunks']} chunks")
        else:
            print(f"[Startup] Knowledge base ready with {stats['total_chunks']} chunks")
    except Exception as e:
        print(f"[Startup] Warning: Failed to initialize knowledge base: {e}")

init_knowledge_base_on_startup()

def init_sync_manager():
    """Initialize the sync manager to run automatic syncs every 6 hours."""
    try:
        start_sync_manager(run_immediately=False)
        print("[Startup] SyncManager started - syncing every 6 hours")
    except Exception as e:
        print(f"[Startup] Warning: Failed to start SyncManager: {e}")

init_sync_manager()

conversation_histories = {}

# Global storage for sync progress (thread-safe via GIL for simple operations)
sync_progress = {}


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "GRESTA API Server"})


@app.route("/api/channels/status", methods=["GET"])
def channel_status():
    """Get configuration status of all messaging channels."""
    return jsonify(get_channel_status())


def get_canonical_webhook_url(endpoint: str) -> str:
    """Get the canonical webhook URL for signature validation.
    
    Priority:
    1. WEBHOOK_BASE_URL - Trusted, explicitly configured base URL (most secure)
    2. REPLIT_DEV_DOMAIN - Replit's trusted domain environment variable
    3. Fallback error - Requires explicit configuration for security
    """
    webhook_base = os.environ.get("WEBHOOK_BASE_URL")
    if webhook_base:
        return f"{webhook_base.rstrip('/')}/{endpoint}"
    
    replit_domain = os.environ.get("REPLIT_DEV_DOMAIN")
    if replit_domain:
        return f"https://{replit_domain}/{endpoint}"
    
    return None


@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages via Twilio."""
    if not whatsapp_handler.is_configured():
        return "WhatsApp not configured", 503
    
    signature = request.headers.get("X-Twilio-Signature", "")
    
    if not signature:
        print(f"WhatsApp webhook: Rejected request - missing X-Twilio-Signature header. Remote: {request.remote_addr}")
        return "Missing signature", 403
    
    canonical_url = get_canonical_webhook_url("webhook/whatsapp")
    if not canonical_url:
        print("WhatsApp webhook: WEBHOOK_BASE_URL or REPLIT_DEV_DOMAIN must be set for signature validation")
        return "Server configuration error", 500
    
    if not whatsapp_handler.validate_request(signature, canonical_url, request.form.to_dict()):
        print(f"WhatsApp webhook: Rejected request - invalid signature. URL: {canonical_url}, Remote: {request.remote_addr}")
        return "Invalid signature", 403
    
    twiml_response = whatsapp_handler.handle_webhook(request.form.to_dict())
    
    return twiml_response, 200, {"Content-Type": "application/xml"}


@app.route("/webhook/instagram", methods=["GET"])
def instagram_verify():
    """Handle Instagram webhook verification."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    success, response = instagram_handler.verify_webhook(mode, token, challenge)
    
    if success:
        return response, 200
    return response, 403


@app.route("/webhook/instagram", methods=["POST"])
def instagram_webhook():
    """Handle incoming Instagram messages."""
    if not instagram_handler.is_configured():
        return jsonify({"error": "Instagram not configured"}), 503
    
    data = request.get_json()
    
    result = instagram_handler.handle_webhook(data)
    
    return jsonify(result), 200


def validate_internal_api_key():
    """Validate the internal API key from trusted Next.js server."""
    expected_key = os.environ.get("INTERNAL_API_KEY")
    if not expected_key:
        return False
    provided_key = request.headers.get("X-Internal-Api-Key", "")
    return provided_key == expected_key


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Direct API endpoint for chat integration - used by React frontend."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    message = data.get("message")
    session_id = data.get("session_id", "anonymous")
    
    client_ip = get_client_ip(request)
    
    captcha_answer = data.get("captcha_answer")
    if captcha_answer:
        if not rate_limiter.verify_captcha(session_id, captcha_answer):
            return jsonify({"error": "Incorrect answer", "captcha_failed": True}), 400
    
    allowed, reason, captcha = rate_limiter.check_rate_limit(client_ip, session_id)
    if not allowed:
        if captcha:
            return jsonify({"error": reason, "captcha_required": True, "captcha": captcha}), 429
        return jsonify({"error": reason, "rate_limited": True}), 429
    
    rate_limiter.log_request(client_ip, session_id, "/api/chat", message[:50] if message else "")
    rate_limiter.record_request(client_ip, session_id)
    conversation_history = data.get("conversation_history", [])
    
    is_trusted_request = validate_internal_api_key()
    verified_user = data.get("verified_user") if is_trusted_request else None
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    original_message = message
    message = fix_typos_with_llm(message)
    
    user_id = None
    is_returning_user = False
    user_name = None
    
    if verified_user and session_id.startswith("user_"):
        email = verified_user.get("email")
        name = verified_user.get("name")
        image = verified_user.get("image")
        
        if email:
            user_data, created = get_or_create_user(
                channel="google",
                external_id=email,
                email=email,
                display_name=name,
                profile_image=image
            )
            if user_data:
                user_id = user_data['id']
                user_name = name.split()[0] if name else None
                is_returning_user = not created and session_id not in conversation_histories
    
    ensure_session_exists(session_id, channel="web", user_id=user_id)
    
    last_topic_summary = None
    stored_summary = None
    
    if session_id not in conversation_histories:
        conversation_histories[session_id] = []
        
        if is_returning_user and user_id:
            stored_summary = get_conversation_summary(user_id)
            
            past_history = get_user_conversation_history(user_id, limit=50)
            if past_history:
                for conv in past_history:
                    conversation_histories[session_id].append({"role": "user", "content": conv['question']})
                    conversation_histories[session_id].append({"role": "assistant", "content": conv['answer']})
            
            if stored_summary:
                summary_parts = []
                if stored_summary.get('emotional_themes'):
                    summary_parts.append(f"emotional issues: {stored_summary['emotional_themes']}")
                if stored_summary.get('recommended_programs'):
                    summary_parts.append(f"programs suggested: {stored_summary['recommended_programs']}")
                if stored_summary.get('last_topics'):
                    summary_parts.append(f"topic: {stored_summary['last_topics']}")
                last_topic_summary = " | ".join(summary_parts) if summary_parts else None
                
                if last_topic_summary:
                    conversation_histories[session_id] = conversation_histories[session_id][-4:]
    
    if conversation_history and not conversation_histories[session_id]:
        conversation_histories[session_id] = conversation_history
    
    result = generate_response(
        message, 
        conversation_histories[session_id],
        user_name=user_name,
        is_returning_user=is_returning_user,
        last_topic_summary=last_topic_summary,
        session_id=session_id
    )
    
    response_text = result.get("response", "")
    
    log_conversation(
        session_id=session_id,
        user_question=message,
        bot_answer=response_text,
        safety_flagged=result.get("safety_triggered", False),
        safety_category=result.get("safety_category"),
        sources=result.get("sources", []),
        channel="web"
    )
    
    conversation_histories[session_id].append({"role": "user", "content": message})
    conversation_histories[session_id].append({"role": "assistant", "content": response_text})
    
    if len(conversation_histories[session_id]) > 100:
        conversation_histories[session_id] = conversation_histories[session_id][-100:]
    
    if user_id and len(conversation_histories[session_id]) >= 4:
        try:
            summary = generate_conversation_summary(conversation_histories[session_id])
            if summary:
                upsert_conversation_summary(
                    user_id=user_id,
                    emotional_themes=summary.get('emotional_themes'),
                    recommended_programs=summary.get('recommended_programs'),
                    last_topics=summary.get('last_topics'),
                    conversation_status=summary.get('conversation_status')
                )
        except Exception as e:
            print(f"Error updating conversation summary: {e}")
    
    return jsonify({
        "response": result.get("response", "I apologize, but I encountered an issue. Please try again."),
        "sources": result.get("sources", []),
        "safety_triggered": result.get("safety_triggered", False),
        "session_id": session_id,
        "user_id": user_id,
        "is_returning_user": is_returning_user
    })


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    """Streaming chat endpoint using Server-Sent Events."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    message = data.get("message")
    session_id = data.get("session_id", "anonymous")
    
    client_ip = get_client_ip(request)
    
    captcha_answer = data.get("captcha_answer")
    if captcha_answer:
        if not rate_limiter.verify_captcha(session_id, captcha_answer):
            return jsonify({"error": "Incorrect answer", "captcha_failed": True}), 400
    
    allowed, reason, captcha = rate_limiter.check_rate_limit(client_ip, session_id)
    if not allowed:
        if captcha:
            return jsonify({"error": reason, "captcha_required": True, "captcha": captcha}), 429
        return jsonify({"error": reason, "rate_limited": True}), 429
    
    rate_limiter.log_request(client_ip, session_id, "/api/chat/stream", message[:50] if message else "")
    rate_limiter.record_request(client_ip, session_id)
    
    conversation_history = data.get("conversation_history", [])
    
    is_trusted_request = validate_internal_api_key()
    verified_user = data.get("verified_user") if is_trusted_request else None
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    original_message = message
    message = fix_typos_with_llm(message)
    
    user_id = None
    is_returning_user = False
    user_name = None
    
    if verified_user and session_id.startswith("user_"):
        email = verified_user.get("email")
        name = verified_user.get("name")
        image = verified_user.get("image")
        
        if email:
            user_data, created = get_or_create_user(
                channel="google",
                external_id=email,
                email=email,
                display_name=name,
                profile_image=image
            )
            if user_data:
                user_id = user_data['id']
                user_name = name.split()[0] if name else None
                is_returning_user = not created and session_id not in conversation_histories
    
    ensure_session_exists(session_id, channel="web", user_id=user_id)
    
    last_topic_summary = None
    stored_summary = None
    
    if session_id not in conversation_histories:
        conversation_histories[session_id] = []
        
        if is_returning_user and user_id:
            stored_summary = get_conversation_summary(user_id)
            
            past_history = get_user_conversation_history(user_id, limit=50)
            if past_history:
                for conv in past_history:
                    conversation_histories[session_id].append({"role": "user", "content": conv['question']})
                    conversation_histories[session_id].append({"role": "assistant", "content": conv['answer']})
            
            if stored_summary:
                summary_parts = []
                if stored_summary.get('emotional_themes'):
                    summary_parts.append(f"emotional issues: {stored_summary['emotional_themes']}")
                if stored_summary.get('recommended_programs'):
                    summary_parts.append(f"programs suggested: {stored_summary['recommended_programs']}")
                if stored_summary.get('last_topics'):
                    summary_parts.append(f"topic: {stored_summary['last_topics']}")
                last_topic_summary = " | ".join(summary_parts) if summary_parts else None
                
                if last_topic_summary:
                    conversation_histories[session_id] = conversation_histories[session_id][-4:]
    
    if conversation_history and not conversation_histories[session_id]:
        conversation_histories[session_id] = conversation_history
    
    def generate():
        full_response = ""
        sources = []
        safety_triggered = False
        
        for chunk in generate_response_stream(
            message, 
            conversation_histories[session_id],
            user_name=user_name,
            is_returning_user=is_returning_user,
            last_topic_summary=last_topic_summary,
            session_id=session_id
        ):
            if chunk["type"] == "content":
                full_response += chunk["content"]
                yield f"data: {json.dumps(chunk)}\n\n"
            elif chunk["type"] == "done":
                sources = chunk.get("sources", [])
                safety_triggered = chunk.get("safety_triggered", False)
                full_response = chunk.get("full_response", full_response)
                yield f"data: {json.dumps(chunk)}\n\n"
            elif chunk["type"] == "error":
                yield f"data: {json.dumps(chunk)}\n\n"
                return
        
        log_conversation(
            session_id=session_id,
            user_question=message,
            bot_answer=full_response,
            safety_flagged=safety_triggered,
            sources=sources,
            channel="web"
        )
        
        conversation_histories[session_id].append({"role": "user", "content": message})
        conversation_histories[session_id].append({"role": "assistant", "content": full_response})
        
        if len(conversation_histories[session_id]) > 100:
            conversation_histories[session_id] = conversation_histories[session_id][-100:]
        
        if user_id and len(conversation_histories[session_id]) >= 4:
            try:
                summary = generate_conversation_summary(conversation_histories[session_id])
                if summary:
                    upsert_conversation_summary(
                        user_id=user_id,
                        emotional_themes=summary.get('emotional_themes'),
                        recommended_programs=summary.get('recommended_programs'),
                        last_topics=summary.get('last_topics'),
                        conversation_status=summary.get('conversation_status')
                    )
            except Exception as e:
                print(f"Error updating conversation summary: {e}")
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route("/api/chat/manychat", methods=["POST"])
def api_chat_manychat():
    """ManyChat Dynamic Content endpoint for Instagram/Facebook integration."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "version": "v2",
            "content": {
                "messages": [{"type": "text", "text": "Sorry, I couldn't process your request."}],
                "actions": [],
                "quick_replies": []
            }
        })
    
    message = data.get("message", "").strip()
    user_id = data.get("user_id", "anonymous")
    first_name = data.get("first_name", "")
    session_id = f"manychat_{user_id}"
    
    if not message:
        return jsonify({
            "version": "v2",
            "content": {
                "messages": [{"type": "text", "text": "Namaste! I'm GRESTA, your assistant for GREST's premium refurbished iPhones & MacBooks. How can I help you today?"}],
                "actions": [],
                "quick_replies": []
            }
        })
    
    client_ip = get_client_ip(request)
    
    allowed, reason, captcha = rate_limiter.check_rate_limit(client_ip, session_id)
    if not allowed:
        return jsonify({
            "version": "v2",
            "content": {
                "messages": [{"type": "text", "text": f"Please slow down. {reason}"}],
                "actions": [],
                "quick_replies": []
            }
        })
    
    rate_limiter.log_request(client_ip, session_id, "/api/chat/manychat", message[:50] if message else "")
    rate_limiter.record_request(client_ip, session_id)
    
    original_message = message
    message = fix_typos_with_llm(message)
    
    if session_id not in conversation_histories:
        conversation_histories[session_id] = []
    
    ensure_session_exists(session_id, channel="instagram", user_id=None)
    
    try:
        result = generate_response(
            message, 
            conversation_histories[session_id],
            user_name=first_name if first_name else None,
            is_returning_user=len(conversation_histories[session_id]) > 0,
            last_topic_summary=None,
            session_id=session_id
        )
        
        answer = result.get("response", "I'm sorry, I couldn't generate a response.")
        sources = result.get("sources", [])
        safety_triggered = result.get("safety_triggered", False)
        
        conversation_histories[session_id].append({"role": "user", "content": message})
        conversation_histories[session_id].append({"role": "assistant", "content": answer})
        
        if len(conversation_histories[session_id]) > 20:
            conversation_histories[session_id] = conversation_histories[session_id][-20:]
        
        log_conversation(
            session_id=session_id,
            user_question=original_message,
            bot_answer=answer,
            sources=sources,
            safety_flagged=safety_triggered
        )
        
        return jsonify({
            "version": "v2",
            "content": {
                "messages": [{"type": "text", "text": answer}],
                "actions": [],
                "quick_replies": []
            }
        })
        
    except Exception as e:
        print(f"ManyChat endpoint error: {e}")
        return jsonify({
            "version": "v2",
            "content": {
                "messages": [{"type": "text", "text": "I'm having trouble right now. Please try again in a moment."}],
                "actions": [],
                "quick_replies": []
            }
        })


@app.route("/api/chat/reset", methods=["POST"])
def api_chat_reset():
    """Reset conversation for a session."""
    data = request.get_json()
    session_id = data.get("session_id", "anonymous")
    
    if session_id in conversation_histories:
        del conversation_histories[session_id]
    
    return jsonify({
        "status": "success",
        "message": "Conversation reset"
    })


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    """Submit feedback for a response."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    session_id = data.get("session_id", "anonymous")
    message_id = data.get("message_id", "")
    feedback = data.get("feedback", "")
    comment = data.get("comment", "")
    
    if feedback not in ["up", "down"]:
        return jsonify({"error": "Invalid feedback value"}), 400
    
    is_positive = feedback == "up"
    
    try:
        log_feedback(
            session_id=session_id,
            is_positive=is_positive,
            comment=comment if comment else None
        )
        
        return jsonify({
            "status": "success",
            "message": "Feedback recorded"
        })
    except Exception as e:
        print(f"Error logging feedback: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to record feedback"
        }), 500


# =============================================================================
# Admin Dashboard API Endpoints
# =============================================================================

from conversation_logger import (
    get_conversation_stats, get_analytics_by_date, get_feedback_summary,
    get_recent_logs, get_session_history
)
from database import ChatSession, Conversation, UserAccount, get_db_session, is_database_available
from sqlalchemy import func, desc

@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    """Get dashboard statistics."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    range_param = request.args.get("range", "7d")
    
    days = 7
    if range_param == "24h":
        days = 1
    elif range_param == "30d":
        days = 30
    
    try:
        stats = get_conversation_stats()
        daily_data = get_analytics_by_date(days)
        feedback = get_feedback_summary()
        
        total_feedback = feedback.get("positive", 0) + feedback.get("negative", 0)
        satisfaction = 0
        if total_feedback > 0:
            satisfaction = round((feedback.get("positive", 0) / total_feedback) * 100)
        
        channel_dist = []
        if is_database_available():
            with get_db_session() as db:
                if db:
                    channels = db.query(
                        ChatSession.channel,
                        func.count(ChatSession.id).label('count')
                    ).group_by(ChatSession.channel).all()
                    channel_dist = [{"channel": c.channel or "web", "count": c.count} for c in channels]
        
        conversations_by_day = []
        for d in daily_data:
            date_str = d.get("date", "")
            if date_str:
                from datetime import datetime
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                    formatted = dt.strftime("%b %d")
                except:
                    formatted = date_str
                conversations_by_day.append({
                    "date": formatted,
                    "count": d.get("conversations", 0)
                })
        
        top_queries = []
        
        return jsonify({
            "totalConversations": stats.get("total_conversations", 0),
            "totalSessions": stats.get("unique_sessions", 0),
            "avgResponseTime": round((stats.get("avg_response_time_ms") or 0) / 1000, 1),
            "positiveRating": satisfaction,
            "conversationsByDay": conversations_by_day,
            "channelDistribution": channel_dist if channel_dist else [{"channel": "Widget", "count": stats.get("total_conversations", 0)}],
            "topQueries": top_queries
        })
    except Exception as e:
        print(f"Admin stats error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/conversations", methods=["GET"])
def admin_conversations():
    """Get list of chat sessions for the conversation viewer."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    range_param = request.args.get("range", "7d")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 50))
    
    days = 7
    if range_param == "24h":
        days = 1
    elif range_param == "30d":
        days = 30
    
    if not is_database_available():
        return jsonify({"sessions": [], "total": 0})
    
    try:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with get_db_session() as db:
            if db is None:
                return jsonify({"sessions": [], "total": 0})
            
            total = db.query(func.count(ChatSession.id)).filter(
                ChatSession.created_at >= cutoff
            ).scalar() or 0
            
            sessions = db.query(ChatSession).filter(
                ChatSession.created_at >= cutoff
            ).order_by(desc(ChatSession.last_activity)).offset((page - 1) * limit).limit(limit).all()
            
            result = []
            for s in sessions:
                msg_count = db.query(func.count(Conversation.id)).filter(
                    Conversation.session_id == s.session_id
                ).scalar() or 0
                
                first_msg = db.query(Conversation.user_question).filter(
                    Conversation.session_id == s.session_id
                ).order_by(Conversation.timestamp).first()
                
                user_name = "Anonymous"
                user_email = None
                if s.user_id:
                    user = db.query(UserAccount).filter(UserAccount.id == s.user_id).first()
                    if user:
                        user_name = user.display_name or user.email or "User"
                        user_email = user.email
                
                result.append({
                    "sessionId": s.session_id,
                    "userName": user_name,
                    "userEmail": user_email,
                    "channel": s.channel or "web",
                    "messageCount": msg_count,
                    "firstMessage": first_msg[0][:100] + "..." if first_msg and len(first_msg[0]) > 100 else (first_msg[0] if first_msg else ""),
                    "createdAt": s.created_at.isoformat() if s.created_at else None,
                    "lastActivity": s.last_activity.isoformat() if s.last_activity else None
                })
            
            return jsonify({
                "sessions": result,
                "total": total,
                "page": page,
                "limit": limit,
                "totalPages": (total + limit - 1) // limit
            })
    except Exception as e:
        print(f"Admin conversations error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/conversations/<session_id>", methods=["GET"])
def admin_conversation_detail(session_id):
    """Get full conversation history for a specific session."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    if not is_database_available():
        return jsonify({"messages": [], "session": None})
    
    try:
        with get_db_session() as db:
            if db is None:
                return jsonify({"messages": [], "session": None})
            
            session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not session:
                return jsonify({"error": "Session not found"}), 404
            
            user_name = "Anonymous"
            user_email = None
            if session.user_id:
                user = db.query(UserAccount).filter(UserAccount.id == session.user_id).first()
                if user:
                    user_name = user.display_name or user.email or "User"
                    user_email = user.email
            
            messages = db.query(Conversation).filter(
                Conversation.session_id == session_id
            ).order_by(Conversation.timestamp).all()
            
            message_list = []
            for m in messages:
                message_list.append({
                    "id": m.id,
                    "userQuestion": m.user_question,
                    "botAnswer": m.bot_answer,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    "safetyFlagged": m.safety_flagged,
                    "responseTimeMs": m.response_time_ms
                })
            
            return jsonify({
                "session": {
                    "sessionId": session.session_id,
                    "userName": user_name,
                    "userEmail": user_email,
                    "channel": session.channel or "web",
                    "createdAt": session.created_at.isoformat() if session.created_at else None,
                    "lastActivity": session.last_activity.isoformat() if session.last_activity else None
                },
                "messages": message_list
            })
    except Exception as e:
        print(f"Admin conversation detail error: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# SYNC MANAGEMENT ENDPOINTS
# =============================================================================

@app.route("/api/admin/sync/status", methods=["GET"])
def admin_sync_status():
    """Get current sync status and last run info."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        from sync_manager import get_sync_manager
        from database import SyncRun, GRESTProduct
        
        manager = get_sync_manager()
        status = manager.get_status()
        
        with get_db_session() as db:
            if db is None:
                return jsonify({"error": "Database unavailable"}), 500
            
            running_sync = db.query(SyncRun).filter(
                SyncRun.status == 'running'
            ).first()
            
            last_run = db.query(SyncRun).filter(
                SyncRun.status.in_(['success', 'failed', 'warning'])
            ).order_by(SyncRun.started_at.desc()).first()
            
            product_count = db.query(func.count(GRESTProduct.id)).scalar() or 0
            
            return jsonify({
                "isRunning": running_sync is not None,
                "currentRunId": running_sync.id if running_sync else None,
                "schedulerActive": status.get("is_running", False),
                "intervalHours": status.get("interval_hours", 6),
                "nextSync": status.get("next_sync"),
                "productCount": product_count,
                "lastRun": {
                    "id": last_run.id,
                    "status": last_run.status,
                    "startedAt": last_run.started_at.isoformat() if last_run.started_at else None,
                    "finishedAt": last_run.finished_at.isoformat() if last_run.finished_at else None,
                    "productsCreated": last_run.products_created or 0,
                    "productsUpdated": last_run.products_updated or 0,
                    "productsDeleted": last_run.products_deleted or 0,
                    "duration": str(last_run.finished_at - last_run.started_at) if last_run.finished_at and last_run.started_at else None
                } if last_run else None
            })
    except Exception as e:
        print(f"Sync status error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/sync/history", methods=["GET"])
def admin_sync_history():
    """Get sync run history."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        from database import SyncRun
        
        limit = request.args.get('limit', 20, type=int)
        
        with get_db_session() as db:
            if db is None:
                return jsonify({"runs": []})
            
            runs = db.query(SyncRun).order_by(
                SyncRun.started_at.desc()
            ).limit(limit).all()
            
            result = []
            for run in runs:
                duration = None
                if run.finished_at and run.started_at:
                    delta = run.finished_at - run.started_at
                    duration = f"{int(delta.total_seconds())}s"
                
                result.append({
                    "id": run.id,
                    "triggerSource": run.trigger_source,
                    "triggeredBy": run.triggered_by,
                    "startedAt": run.started_at.isoformat() if run.started_at else None,
                    "finishedAt": run.finished_at.isoformat() if run.finished_at else None,
                    "status": run.status,
                    "productsCreated": run.products_created or 0,
                    "productsUpdated": run.products_updated or 0,
                    "productsDeleted": run.products_deleted or 0,
                    "shopifyCount": run.shopify_product_count,
                    "dbCount": run.db_product_count,
                    "duration": duration,
                    "errorLog": run.error_log
                })
            
            return jsonify({"runs": result})
    except Exception as e:
        print(f"Sync history error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/sync/run", methods=["POST"])
def admin_sync_run():
    """Trigger a manual sync."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        from database import SyncRun, SyncRunEvent
        from scrape_grest_products import populate_database
        from threading import Thread
        
        data = request.get_json() or {}
        triggered_by = data.get('triggeredBy', 'admin')
        
        with get_db_session() as db:
            if db is None:
                return jsonify({"error": "Database unavailable"}), 500
            
            running = db.query(SyncRun).filter(SyncRun.status == 'running').first()
            if running:
                return jsonify({
                    "error": "Sync already in progress",
                    "currentRunId": running.id
                }), 409
            
            sync_run = SyncRun(
                trigger_source='manual',
                triggered_by=triggered_by,
                status='running'
            )
            db.add(sync_run)
            db.flush()
            run_id = sync_run.id
            
            event = SyncRunEvent(
                sync_run_id=run_id,
                event_type='sync_started',
                message='Manual sync initiated'
            )
            db.add(event)
        
        def run_sync_async(run_id):
            try:
                _execute_sync(run_id)
            except Exception as e:
                print(f"Async sync error: {e}")
        
        thread = Thread(target=run_sync_async, args=(run_id,))
        thread.start()
        
        return jsonify({
            "syncRunId": run_id,
            "status": "started",
            "message": "Sync initiated"
        })
    except Exception as e:
        print(f"Sync run error: {e}")
        return jsonify({"error": str(e)}), 500


def _execute_sync(run_id: int):
    """Execute the actual sync and update run record."""
    from database import SyncRun, SyncRunEvent, GRESTProduct
    from scrape_grest_products import populate_database, get_shopify_product_count
    from datetime import datetime
    
    def progress_callback(step, message, progress_pct):
        """Store progress for SSE streaming."""
        sync_progress[run_id] = {
            "step": step,
            "message": message,
            "progress": progress_pct,
            "timestamp": datetime.utcnow().isoformat()
        }
        # Also log to database for persistence
        try:
            with get_db_session() as db:
                event = SyncRunEvent(
                    sync_run_id=run_id,
                    event_type=step,
                    message=message
                )
                db.add(event)
        except:
            pass
    
    try:
        progress_callback("starting", "Initializing sync...", 0)
        
        result = populate_database(hard_delete_stale=True, progress_callback=progress_callback)
        
        with get_db_session() as db:
            event = SyncRunEvent(
                sync_run_id=run_id,
                event_type='fetch_complete',
                message=f"Fetched {result.get('variants_processed', 0)} variants"
            )
            db.add(event)
        
        shopify_count = result.get('variants_processed', 0)
        created_count = result.get('variants_created', 0)
        updated_count = result.get('variants_updated', 0)
        deleted_count = result.get('variants_deleted', 0)
        
        with get_db_session() as db:
            db_count = db.query(func.count(GRESTProduct.id)).scalar() or 0
        
        is_matched = abs(shopify_count - db_count) <= 5
        status = 'success' if result.get('success') and is_matched else ('warning' if result.get('success') else 'failed')
        
        with get_db_session() as db:
            sync_run = db.query(SyncRun).filter(SyncRun.id == run_id).first()
            if sync_run:
                sync_run.finished_at = datetime.utcnow()
                sync_run.status = status
                sync_run.products_created = created_count
                sync_run.products_updated = updated_count
                sync_run.products_deleted = deleted_count
                sync_run.shopify_product_count = shopify_count
                sync_run.db_product_count = db_count
            
            event = SyncRunEvent(
                sync_run_id=run_id,
                event_type='sync_complete',
                message=f"Sync completed: {status}"
            )
            db.add(event)
        
        # Mark progress as complete
        sync_progress[run_id] = {
            "step": "complete",
            "message": f"Sync completed! {created_count} new, {updated_count} updated, {deleted_count} removed",
            "progress": 100,
            "status": status,
            "result": {
                "variantsProcessed": shopify_count,
                "variantsCreated": created_count,
                "variantsUpdated": updated_count,
                "variantsDeleted": deleted_count,
                "dbCount": db_count,
            }
        }
            
    except Exception as e:
        sync_progress[run_id] = {
            "step": "error",
            "message": str(e),
            "progress": 0,
            "status": "failed"
        }
        with get_db_session() as db:
            sync_run = db.query(SyncRun).filter(SyncRun.id == run_id).first()
            if sync_run:
                sync_run.finished_at = datetime.utcnow()
                sync_run.status = 'failed'
                sync_run.error_log = str(e)
            
            event = SyncRunEvent(
                sync_run_id=run_id,
                event_type='sync_error',
                message=str(e)
            )
            db.add(event)


@app.route("/api/admin/sync/run/<int:run_id>/events", methods=["GET"])
def admin_sync_events(run_id):
    """Get events for a specific sync run."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        from database import SyncRunEvent
        
        with get_db_session() as db:
            if db is None:
                return jsonify({"events": []})
            
            events = db.query(SyncRunEvent).filter(
                SyncRunEvent.sync_run_id == run_id
            ).order_by(SyncRunEvent.created_at).all()
            
            return jsonify({
                "events": [{
                    "eventType": e.event_type,
                    "message": e.message,
                    "createdAt": e.created_at.isoformat() if e.created_at else None
                } for e in events]
            })
    except Exception as e:
        print(f"Sync events error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/sync/events", methods=["GET"])
def admin_all_sync_events():
    """Get all recent sync events across all runs for log viewing."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        from database import SyncRunEvent, SyncRun
        
        limit = request.args.get('limit', 50, type=int)
        
        with get_db_session() as db:
            if db is None:
                return jsonify({"events": []})
            
            events = db.query(SyncRunEvent, SyncRun).join(
                SyncRun, SyncRunEvent.sync_run_id == SyncRun.id
            ).order_by(SyncRunEvent.created_at.desc()).limit(limit).all()
            
            return jsonify({
                "events": [{
                    "runId": e.SyncRunEvent.sync_run_id,
                    "triggerSource": e.SyncRun.trigger_source,
                    "eventType": e.SyncRunEvent.event_type,
                    "message": e.SyncRunEvent.message,
                    "createdAt": e.SyncRunEvent.created_at.isoformat() if e.SyncRunEvent.created_at else None
                } for e in events]
            })
    except Exception as e:
        print(f"All sync events error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/sync/run/<int:run_id>/progress", methods=["GET"])
def admin_sync_progress(run_id):
    """Get real-time progress for a specific sync run."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    progress = sync_progress.get(run_id)
    if progress:
        return jsonify(progress)
    
    # Check if sync run exists and get its status from database
    from database import SyncRun
    with get_db_session() as db:
        if db:
            sync_run = db.query(SyncRun).filter(SyncRun.id == run_id).first()
            if sync_run:
                if sync_run.status == 'running':
                    return jsonify({
                        "step": "running",
                        "message": "Sync in progress...",
                        "progress": 50
                    })
                elif sync_run.status == 'success':
                    return jsonify({
                        "step": "complete",
                        "message": "Sync completed successfully",
                        "progress": 100,
                        "status": "success"
                    })
                elif sync_run.status == 'failed':
                    return jsonify({
                        "step": "error",
                        "message": sync_run.error_log or "Sync failed",
                        "progress": 0,
                        "status": "failed"
                    })
    
    return jsonify({"step": "unknown", "message": "Sync run not found", "progress": 0})


@app.route("/api/admin/sync/verification", methods=["GET"])
def admin_sync_verification():
    """Get sync verification - compare Shopify vs database counts."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        from database import GRESTProduct
        from scrape_grest_products import get_shopify_product_count
        
        with get_db_session() as db:
            if db is None:
                return jsonify({"error": "Database unavailable"}), 500
            
            db_count = db.query(func.count(GRESTProduct.id)).scalar() or 0
        
        try:
            shopify_count = get_shopify_product_count()
        except Exception as e:
            print(f"Shopify API error: {e}")
            shopify_count = None
        
        if shopify_count is not None:
            difference = abs(shopify_count - db_count)
            is_matched = difference <= 5
        else:
            difference = None
            is_matched = None
        
        return jsonify({
            "shopifyCount": shopify_count,
            "databaseCount": db_count,
            "isMatched": is_matched,
            "difference": difference,
            "lastChecked": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"Sync verification error: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# MONITORING ENDPOINTS
# =============================================================================

@app.route("/api/admin/monitoring", methods=["GET"])
def admin_monitoring():
    """Get service monitoring status including UptimeRobot."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        from database import SyncRun
        
        services = []
        
        services.append({
            "name": "Chatbot API",
            "status": "up",
            "uptime": 100,
            "lastCheck": datetime.utcnow().isoformat()
        })
        
        uptimerobot_key = os.environ.get('UPTIMEROBOT_API_KEY')
        if uptimerobot_key:
            try:
                import requests as req
                response = req.post(
                    'https://api.uptimerobot.com/v2/getMonitors',
                    data={'api_key': uptimerobot_key, 'format': 'json'},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    for monitor in data.get('monitors', []):
                        status_map = {0: 'paused', 1: 'not_checked', 2: 'up', 8: 'seems_down', 9: 'down'}
                        services.append({
                            "name": monitor.get('friendly_name', 'Unknown'),
                            "status": status_map.get(monitor.get('status'), 'unknown'),
                            "uptime": float(monitor.get('all_time_uptime_ratio', 0)),
                            "lastCheck": datetime.utcnow().isoformat(),
                            "url": monitor.get('url', '')
                        })
            except Exception as e:
                print(f"UptimeRobot error: {e}")
        
        sync_health = {"lastSuccessfulSync": None, "hoursAgo": None, "isHealthy": False}
        with get_db_session() as db:
            if db:
                last_success = db.query(SyncRun).filter(
                    SyncRun.status == 'success'
                ).order_by(SyncRun.finished_at.desc()).first()
                
                if last_success and last_success.finished_at:
                    sync_health["lastSuccessfulSync"] = last_success.finished_at.isoformat()
                    hours_ago = (datetime.utcnow() - last_success.finished_at).total_seconds() / 3600
                    sync_health["hoursAgo"] = round(hours_ago, 1)
                    sync_health["isHealthy"] = hours_ago < 8
        
        return jsonify({
            "services": services,
            "syncHealth": sync_health
        })
    except Exception as e:
        print(f"Monitoring error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/rate-limiter/stats", methods=["GET"])
def rate_limiter_stats():
    """Get rate limiter statistics for monitoring."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    return jsonify(rate_limiter.get_stats())


@app.route("/api/admin/rate-limiter/ip/<ip>", methods=["GET"])
def rate_limiter_ip_activity(ip):
    """Get rate limiter activity for a specific IP."""
    if not validate_internal_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    return jsonify(rate_limiter.get_ip_activity(ip))


if __name__ == "__main__":
    port = int(os.environ.get("WEBHOOK_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
