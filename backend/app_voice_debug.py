"""Voice Server - Let OpenAI handle greeting naturally"""
from flask import Flask, request
from flask_sock import Sock
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
import os, json, threading, asyncio, base64, time, logging
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
sock = Sock(app)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
YOUR_DOMAIN = os.getenv("YOUR_DOMAIN")

@app.route("/voice/health")
def health():
    return {"status": "healthy"}, 200

@app.route("/voice/incoming", methods=["POST"])
def incoming_call():
    logger.info(f"📞 Incoming call from {request.values.get('From')}")
    response = VoiceResponse()
    # Add a brief greeting before connecting to AI
    response.say("Please wait while I connect you to our insurance assistant.")
    connect = Connect()
    stream = Stream(url=f'wss://{YOUR_DOMAIN}/voice/stream')
    connect.append(stream)
    response.append(connect)
    
    twiml = str(response)
    logger.info(f"Sending TwiML:\n{twiml}")
    
    return twiml, 200, {'Content-Type': 'text/xml'}

@app.route("/voice/status", methods=["POST"])
def call_status():
    return "", 200

class Handler:
    def __init__(self, stream_sid):
        self.stream_sid = stream_sid
        self.ws = None
        self.running = True
        self.audio_count = 0
        self.audio_sent_to_openai = 0
        
    async def openai_loop(self, twilio_ws):
        import websockets
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "OpenAI-Beta": "realtime=v1"}
        
        async with websockets.connect(url, extra_headers=headers) as ws:
            self.ws = ws
            logger.info("✓ OpenAI connected")
            
            # Configure - let VAD detect when user stops speaking
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": "You are a helpful insurance eligibility assistant. When the user first speaks, greet them warmly and ask how you can help them check their insurance coverage today.",
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 700
                    },
                    "input_audio_transcription": {"model": "whisper-1"}
                }
            }))
            logger.info("✓ Configured - waiting for user to speak...")
            
            # Listen for all events
            async for msg in ws:
                if not self.running:
                    break
                data = json.loads(msg)
                t = data.get("type")
                
                if t == "response.audio.delta":
                    audio = data.get("delta")
                    if audio:
                        self.audio_count += 1
                        if self.audio_count == 1:
                            logger.info("📤 Started sending audio to Twilio")
                        
                        # Decode PCM16 from OpenAI (likely 24kHz or 16kHz)
                        pcm = base64.b64decode(audio)
                        
                        # OpenAI sends 24kHz, we need 8kHz for Twilio
                        # First downsample 24k->8k (take every 3rd sample)
                        from resample import resample_16khz_to_8khz
                        import struct
                        
                        # Decode all samples
                        samples = [struct.unpack('<h', pcm[i:i+2])[0] for i in range(0, len(pcm), 2)]
                        # Downsample by 3 (24kHz -> 8kHz)
                        samples_8k = samples[::3]
                        # Re-encode
                        pcm_8khz = b''.join(struct.pack('<h', s) for s in samples_8k)
                        
                        # Convert to mulaw for Twilio
                        from audio_utils import lin2ulaw
                        mulaw = lin2ulaw(pcm_8khz, 2)
                        
                        twilio_ws.send(json.dumps({
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {"payload": base64.b64encode(mulaw).decode()}
                        }))
                        
                elif t == "response.audio_transcript.done":
                    logger.info(f"🤖 AI: {data.get('transcript', '')}")
                    
                elif t == "conversation.item.input_audio_transcription.completed":
                    logger.info(f"👤 User: {data.get('transcript', '')}")
                    
                elif t == "input_audio_buffer.speech_started":
                    logger.info("🎤 User started speaking")
                    
                elif t == "input_audio_buffer.speech_stopped":
                    logger.info("🎤 User stopped speaking")
                    
                elif t == "response.created":
                    logger.info("🤖 AI generating response...")
                    
                elif t == "error":
                    logger.error(f"❌ Error: {data}")
                    
    async def send_audio(self, audio_b64):
        if self.ws:
            self.audio_sent_to_openai += 1
            if self.audio_sent_to_openai == 1:
                logger.info("📤 Started sending audio TO OpenAI")
            if self.audio_sent_to_openai % 100 == 0:
                logger.info(f"📤 Sent {self.audio_sent_to_openai} chunks to OpenAI")
            await self.ws.send(json.dumps({"type": "input_audio_buffer.append", "audio": audio_b64}))

@sock.route('/voice/stream')
def stream(ws):
    logger.info("WebSocket opened")
    handler = None
    loop = None
    media_received = 0
    
    while True:
        msg = ws.receive(timeout=None)
        if not msg:
            break
        data = json.loads(msg)
        
        if data.get("event") == "start":
            sid = data["start"]["streamSid"]
            logger.info(f"✓ Stream started")
            handler = Handler(sid)
            loop = asyncio.new_event_loop()
            
            def run():
                asyncio.set_event_loop(loop)
                loop.run_until_complete(handler.openai_loop(ws))
            
            threading.Thread(target=run, daemon=True).start()
            time.sleep(0.5)
            
        elif data.get("event") == "media" and handler and loop:
            media_received += 1
            if media_received == 1:
                logger.info("📥 Started receiving audio from Twilio")
            if media_received % 100 == 0:
                logger.info(f"📥 Received {media_received} media packets from Twilio")
                
            payload = data["media"]["payload"]
            from audio_utils import ulaw2lin
            from resample import resample_8khz_to_16khz
            
            # Convert mulaw to PCM16 (8kHz)
            mulaw = base64.b64decode(payload)
            pcm_8khz = ulaw2lin(mulaw, 2)
            
            # Resample from 8kHz to 16kHz for OpenAI
            pcm_16khz = resample_8khz_to_16khz(pcm_8khz)
            
            # Send to OpenAI
            audio_b64 = base64.b64encode(pcm_16khz).decode('utf-8')
            asyncio.run_coroutine_threadsafe(
                handler.send_audio(audio_b64), loop
            )
            
        elif data.get("event") == "stop":
            logger.info(f"Call ended - Received {media_received} total media packets")
            if handler:
                handler.running = False
                logger.info(f"Total audio chunks sent: {handler.audio_count}")
            break
    
    if loop:
        loop.stop()
    logger.info("WebSocket closed")

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🎙️  Voice Agent Ready on port 5002")
    logger.info("="*60)
    app.run(host="0.0.0.0", port=5002, debug=False)