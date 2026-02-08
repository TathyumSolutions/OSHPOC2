"""
Voice Server - Final Working Version
Uses threading to bridge sync flask-sock with async OpenAI Realtime API
"""
from flask import Flask, request
from flask_sock import Sock
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
import os
from dotenv import load_dotenv
import logging
import json
import threading
import asyncio
import base64
import time

load_dotenv()

app = Flask(__name__)
sock = Sock(app)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
YOUR_DOMAIN = os.getenv("YOUR_DOMAIN", "your-domain.com")


@app.route("/voice/health", methods=["GET"])
def health():
    return {"status": "healthy", "service": "Voice Agent"}, 200


@app.route("/voice/incoming", methods=["POST"])
def incoming_call():
    logger.info("Incoming call received")
    call_sid = request.values.get('CallSid', 'unknown')
    logger.info(f"Call {call_sid}")
    
    response = VoiceResponse()
    connect = Connect()
    stream = Stream(url=f'wss://{YOUR_DOMAIN}/voice/stream')
    connect.append(stream)
    response.append(connect)
    
    return str(response), 200, {'Content-Type': 'text/xml'}


@app.route("/voice/status", methods=["POST"])
def call_status():
    call_sid = request.values.get('CallSid', 'unknown')
    status = request.values.get('CallStatus', 'unknown')
    logger.info(f"Call {call_sid} status: {status}")
    return "", 200


class VoiceCallHandler:
    def __init__(self, call_sid, stream_sid):
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.openai_ws = None
        self.running = True
        
    async def run_openai(self, twilio_ws):
        """Connect to OpenAI and handle bidirectional audio"""
        import websockets
        
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        try:
            async with websockets.connect(url, extra_headers=headers) as ws:
                self.openai_ws = ws
                logger.info("Connected to OpenAI Realtime")
                
                # Configure session
                config = {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text", "audio"],
                        "instructions": "You are a helpful insurance eligibility assistant. Greet the user warmly and help them check their insurance coverage. Ask for their member ID and date of birth.",
                        "voice": "alloy",
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "turn_detection": {"type": "server_vad"}
                    }
                }
                await ws.send(json.dumps(config))
                
                # Receive from OpenAI and send to Twilio
                async for message in ws:
                    if not self.running:
                        break
                        
                    data = json.loads(message)
                    event_type = data.get("type")
                    
                    if event_type == "response.audio.delta":
                        audio_base64 = data.get("delta", "")
                        if audio_base64:
                            # Convert PCM16 to mulaw
                            audio_pcm = base64.b64decode(audio_base64)
                            from audio_utils import lin2ulaw
                            audio_mulaw = lin2ulaw(audio_pcm, 2)
                            audio_mulaw_b64 = base64.b64encode(audio_mulaw).decode('utf-8')
                            
                            # Send to Twilio
                            msg = {
                                "event": "media",
                                "streamSid": self.stream_sid,
                                "media": {"payload": audio_mulaw_b64}
                            }
                            twilio_ws.send(json.dumps(msg))
                            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            import traceback
            traceback.print_exc()
            
    async def send_to_openai(self, audio_base64):
        """Send audio to OpenAI"""
        if self.openai_ws:
            msg = {"type": "input_audio_buffer.append", "audio": audio_base64}
            await self.openai_ws.send(json.dumps(msg))


@sock.route('/voice/stream')
def voice_stream(ws):
    logger.info("WebSocket opened")
    call_sid = None
    handler = None
    loop = None
    
    try:
        while True:
            message = ws.receive(timeout=None)
            if message is None:
                break
                
            data = json.loads(message)
            event = data.get("event")
            
            if event == "start":
                call_sid = data["start"]["callSid"]
                stream_sid = data["start"]["streamSid"]
                logger.info(f"Call {call_sid} started")
                
                handler = VoiceCallHandler(call_sid, stream_sid)
                
                # Start OpenAI in background thread
                loop = asyncio.new_event_loop()
                
                def openai_thread():
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(handler.run_openai(ws))
                    
                thread = threading.Thread(target=openai_thread, daemon=True)
                thread.start()
                time.sleep(0.5)  # Let OpenAI connect
                
            elif event == "media" and handler and loop:
                payload = data["media"]["payload"]
                
                # Convert mulaw to PCM16
                from audio_utils import ulaw2lin
                audio_mulaw = base64.b64decode(payload)
                audio_pcm = ulaw2lin(audio_mulaw, 2)
                audio_b64 = base64.b64encode(audio_pcm).decode('utf-8')
                
                # Send to OpenAI
                asyncio.run_coroutine_threadsafe(
                    handler.send_to_openai(audio_b64), loop
                )
                
            elif event == "stop":
                logger.info("Call ended")
                if handler:
                    handler.running = False
                break
                
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if loop:
            loop.stop()
        logger.info(f"WebSocket closed")


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("  Voice Agent Ready!")
    logger.info(f"  Domain: {YOUR_DOMAIN}")
    logger.info("="*60)
    app.run(host="0.0.0.0", port=5002, debug=False)
