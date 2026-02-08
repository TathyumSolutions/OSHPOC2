"""
Voice Flask Application
Handles Twilio webhooks and WebSocket connections for phone calls.

Run this alongside app.py (different port) or integrate into main app.
"""
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
import asyncio
import websockets
import os
from dotenv import load_dotenv
import logging

from voice.call_manager import CallManager

load_dotenv()

app = Flask(__name__)

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
YOUR_DOMAIN = os.getenv("YOUR_DOMAIN", "your-ngrok-url.ngrok.io")


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
    """
    Twilio webhook - called when someone calls your Twilio number.
    
    Returns TwiML to:
    1. Greet the caller
    2. Connect to WebSocket stream for realtime conversation
    """
    logger.info("Incoming call received")
    
    # Get call info
    call_sid = request.values.get('CallSid', 'unknown')
    from_number = request.values.get('From', 'unknown')
    to_number = request.values.get('To', 'unknown')
    
    logger.info(f"Call {call_sid}: {from_number} → {to_number}")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Initial greeting (optional - OpenAI will also greet)
    # response.say("Welcome to the Insurance Eligibility Line. Please wait while we connect you.")
    
    # Connect to WebSocket for streaming audio
    connect = Connect()
    stream = Stream(url=f'wss://{YOUR_DOMAIN}/voice/stream')
    connect.append(stream)
    response.append(connect)
    
    return str(response), 200, {
    'Content-Type': 'text/xml',
    'ngrok-skip-browser-warning': 'true'
}


@app.route("/voice/status", methods=["POST"])
def call_status():
    """
    Twilio status callback - called when call status changes.
    Useful for tracking completed/failed calls.
    """
    call_sid = request.values.get('CallSid', 'unknown')
    call_status = request.values.get('CallStatus', 'unknown')
    
    logger.info(f"Call {call_sid} status: {call_status}")
    
    return "", 200


# ── WebSocket endpoint for Twilio Media Streams ──────────────────────────

# Store active call managers
active_calls = {}


async def handle_media_stream(websocket, path):
    """
    WebSocket handler for Twilio Media Streams.
    This is where the magic happens - bidirectional audio streaming.
    """
    call_sid = None
    
    try:
        # Wait for the 'start' message to get call_sid
        start_message = await websocket.recv()
        import json
        start_data = json.loads(start_message)
        
        if start_data.get("event") == "start":
            call_sid = start_data["start"]["callSid"]
            logger.info(f"Stream started for call {call_sid}")
            
            # Create call manager
            call_manager = CallManager(
                call_sid=call_sid,
                openai_api_key=OPENAI_API_KEY
            )
            active_calls[call_sid] = call_manager
            
            # Handle the call (this blocks until call ends)
            await call_manager.handle_call(websocket)
            
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"WebSocket closed for call {call_sid}")
    except Exception as e:
        logger.error(f"Error in media stream handler: {e}")
    finally:
        if call_sid and call_sid in active_calls:
            del active_calls[call_sid]


def start_websocket_server():
    """Start WebSocket server for Twilio streams"""
    return websockets.serve(
        handle_media_stream,
        "0.0.0.0",
        5001,  # WebSocket port (different from HTTP)
        ping_interval=20,
        ping_timeout=20
    )


# ── Startup ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Validate configuration
    if OPENAI_API_KEY == "your-api-key-here":
        logger.error("⚠️  OPENAI_API_KEY not set! Set it in .env")
        exit(1)
        
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("⚠️  Twilio credentials not set - voice features won't work")
        
    if YOUR_DOMAIN == "your-ngrok-url.ngrok.io":
        logger.warning("⚠️  YOUR_DOMAIN not set - update it after running ngrok")
    
    # Start WebSocket server in background
    asyncio_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(asyncio_loop)
    
    ws_server = asyncio_loop.run_until_complete(start_websocket_server())
    logger.info("✓ WebSocket server started on port 5001")
    
    # Start Flask HTTP server
    logger.info("✓ Starting Flask HTTP server on port 5002")
    logger.info("="*60)
    logger.info("  Voice Agent Ready!")
    logger.info("="*60)
    logger.info(f"  HTTP endpoints : http://0.0.0.0:5002")
    logger.info(f"  WebSocket      : ws://0.0.0.0:5001/voice/stream")
    logger.info(f"  Domain (ngrok) : {YOUR_DOMAIN}")
    logger.info("="*60)
    
    # Run Flask with threading
    from werkzeug.serving import run_simple
    
    try:
        run_simple(
            "0.0.0.0", 
            5002,  # HTTP port
            app, 
            threaded=True,
            use_reloader=False  # Important: reloader breaks asyncio
        )
    finally:
        ws_server.close()
        asyncio_loop.run_until_complete(ws_server.wait_closed())
        asyncio_loop.close()
