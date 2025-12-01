"""
Webhook Server for Multi-Channel Messaging

Flask-based API server handling:
- WhatsApp webhooks (via Twilio)
- Instagram webhooks (via Meta Graph API)
- Direct API access for custom integrations
"""

import os
from flask import Flask, request, jsonify

from channel_handlers import (
    whatsapp_handler,
    instagram_handler,
    process_channel_message,
    get_channel_status
)

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "JoveHeal Webhook Server"})


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


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Direct API endpoint for chat integration."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    message = data.get("message")
    user_id = data.get("user_id", "anonymous")
    channel = data.get("channel", "api")
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    response = process_channel_message(
        channel=channel,
        user_id=user_id,
        message=message
    )
    
    return jsonify({
        "response": response,
        "user_id": user_id,
        "channel": channel
    })


@app.route("/api/chat/reset", methods=["POST"])
def api_chat_reset():
    """Reset conversation for a user."""
    from channel_handlers import ChannelSession
    
    data = request.get_json()
    user_id = data.get("user_id", "anonymous")
    channel = data.get("channel", "api")
    
    ChannelSession.clear_session(channel, user_id)
    
    return jsonify({
        "status": "success",
        "message": "Conversation reset"
    })


if __name__ == "__main__":
    port = int(os.environ.get("WEBHOOK_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
