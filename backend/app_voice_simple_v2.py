"""
Simplified Voice Flask Application - FIXED WebSocket handling
"""
from flask import Flask, request
from flask_sock import Sock
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
import os
from dotenv import load_dotenv
import logging
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
    Receives messages in a loop until connection closes
    """
    logger.info("WebSocket connection opened")
    call_sid = None
    
    try:
        # Keep receiving messages
        while True:
            message = ws.receive(timeout=None)  # Block until message arrives
            
            if message is None:
                logger.info("WebSocket connection closed by client")
                break
                
            data = json.loads(message)
            event = data.get("event")
            
            logger.info(f"Received event: {event}")
            
            if event == "connected":
                logger.info("Twilio WebSocket connected")
                
            elif event == "start":
                call_sid = data["start"]["callSid"]
                stream_sid = data["start"]["streamSid"]
                logger.info(f"Stream started - Call: {call_sid}, Stream: {stream_sid}")
                
                # Import here to avoid circular imports
                import asyncio
                from voice.call_manager import CallManager
                
                # Create call manager
                call_manager = CallManager(
                    call_sid=call_sid,
                    openai_api_key=OPENAI_API_KEY
                )
                
                # Handle the call asynchronously
                # Note: This will block this thread, but that's okay
                # The WebSocket connection stays open
                try:
                    asyncio.run(call_manager.handle_call(ws))
                except Exception as e:
                    logger.error(f"Call manager error: {e}")
                    import traceback
                    traceback.print_exc()
                
            elif event == "media":
                # Media events are handled by call_manager
                # This won't be reached during active call
                pass
                
            elif event == "stop":
                logger.info(f"Stream stopped for call {call_sid}")
                break
                
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
