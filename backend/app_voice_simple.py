"""
Simplified Voice Flask Application
Uses flask-sock for WebSocket handling on the same port
"""
from flask import Flask, request
from flask_sock import Sock
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
import os
from dotenv import load_dotenv
import logging
import asyncio
import json

load_dotenv()

app = Flask(__name__)
sock = Sock(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
YOUR_DOMAIN = os.getenv("YOUR_DOMAIN", "your-domain.com")


@app.route("/voice/health", methods=["GET"])
def health():
    """Health check for voice service"""
    return {
        "status": "healthy",
        "service": "Voice Agent",
        "openai_configured": OPENAI_API_KEY != "your-api-key-here",
        "twilio_configured": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)
    }, 200


@app.route("/voice/incoming", methods=["POST"])
def incoming_call():
    """Twilio webhook - called when someone calls your Twilio number"""
    logger.info("Incoming call received")
    
    # Get call info
    call_sid = request.values.get('CallSid', 'unknown')
    from_number = request.values.get('From', 'unknown')
    to_number = request.values.get('To', 'unknown')
    
    logger.info(f"Call {call_sid}: {from_number} → {to_number}")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Connect to WebSocket for streaming audio (same domain, same port)
    connect = Connect()
    stream = Stream(url=f'wss://{YOUR_DOMAIN}/voice/stream')
    connect.append(stream)
    response.append(connect)
    
    return str(response), 200, {'Content-Type': 'text/xml'}


@app.route("/voice/status", methods=["POST"])
def call_status():
    """Twilio status callback"""
    call_sid = request.values.get('CallSid', 'unknown')
    call_status = request.values.get('CallStatus', 'unknown')
    
    logger.info(f"Call {call_sid} status: {call_status}")
    
    return "", 200


@sock.route('/voice/stream')
def voice_stream(ws):
    """
    WebSocket handler for Twilio Media Streams
    This runs on the SAME PORT as Flask (5002)
    """
    logger.info("WebSocket connection opened")
    call_sid = None
    
    try:
        # Import here to avoid issues
        from voice.call_manager import CallManager
        
        # Wait for start message
        message = ws.receive()
        if message:
            data = json.loads(message)
            
            if data.get("event") == "start":
                call_sid = data["start"]["callSid"]
                logger.info(f"Stream started for call {call_sid}")
                
                # Create and run call manager
                call_manager = CallManager(
                    call_sid=call_sid,
                    openai_api_key=OPENAI_API_KEY
                )
                
                # Handle the call (this blocks until call ends)
                asyncio.run(call_manager.handle_call(ws))
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info(f"WebSocket closed for call {call_sid}")


if __name__ == "__main__":
    # Validate configuration
    if OPENAI_API_KEY == "your-api-key-here":
        logger.error("⚠️  OPENAI_API_KEY not set! Set it in .env")
        exit(1)
        
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("⚠️  Twilio credentials not set")
        
    if YOUR_DOMAIN in ["your-ngrok-url.ngrok.io", "your-domain.com"]:
        logger.warning("⚠️  YOUR_DOMAIN not set - update it in .env")
    
    logger.info("="*60)
    logger.info("  Voice Agent Ready!")
    logger.info("="*60)
    logger.info(f"  HTTP & WebSocket : http://0.0.0.0:5002")
    logger.info(f"  Domain           : {YOUR_DOMAIN}")
    logger.info("="*60)
    
    # Run Flask (handles both HTTP and WebSocket on same port)
    app.run(host="0.0.0.0", port=5002, debug=False)
