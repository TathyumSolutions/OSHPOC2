"""
Twilio WebSocket Handler
Manages the WebSocket connection with Twilio for real-time audio streaming.
"""
import asyncio
import json
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TwilioStreamHandler:
    """
    Handles bidirectional audio streaming with Twilio Media Streams.
    
    Twilio sends audio in mulaw format at 8kHz.
    We need to convert to/from PCM16 for OpenAI.
    """
    
    def __init__(self, websocket):
        self.websocket = websocket
        self.stream_sid = None
        self.call_sid = None
        
    async def handle_message(self, message_str: str, openai_handler):
        """
        Handle incoming message from Twilio.
        
        Message types:
        - connected: Initial connection
        - start: Stream metadata
        - media: Audio payload
        - stop: Stream ended
        """
        try:
            message = json.loads(message_str)
            event = message.get("event")
            
            if event == "connected":
                logger.info("Twilio WebSocket connected")
                
            elif event == "start":
                self.stream_sid = message["start"]["streamSid"]
                self.call_sid = message["start"]["callSid"]
                logger.info(f"Stream started - SID: {self.stream_sid}, Call: {self.call_sid}")
                
            elif event == "media":
                # Get audio payload
                payload = message["media"]["payload"]
                
                # Twilio sends mulaw audio, base64 encoded
                audio_mulaw = base64.b64decode(payload)
                
                # Convert mulaw to PCM16 for OpenAI
                audio_pcm = self._mulaw_to_pcm16(audio_mulaw)
                
                # Send to OpenAI
                await openai_handler.send_audio(audio_pcm)
                
            elif event == "stop":
                logger.info("Stream stopped")
                await openai_handler.close()
                
        except Exception as e:
            logger.error(f"Error handling Twilio message: {e}")
            
    async def send_audio(self, audio_pcm: bytes):
        """
        Send audio to Twilio (from OpenAI).
        OpenAI sends PCM16, we need to convert to mulaw for Twilio.
        """
        # Convert PCM16 to mulaw
        audio_mulaw = self._pcm16_to_mulaw(audio_pcm)
        
        # Base64 encode
        audio_base64 = base64.b64encode(audio_mulaw).decode('utf-8')
        
        # Send to Twilio
        message = {
            "event": "media",
            "streamSid": self.stream_sid,
            "media": {
                "payload": audio_base64
            }
        }
        
        await self.websocket.send(json.dumps(message))
        
    def _mulaw_to_pcm16(self, mulaw_data: bytes) -> bytes:
        """
        Convert mulaw audio to PCM16.
        
        Mulaw: 8-bit compressed audio format
        PCM16: 16-bit linear audio format
        """
        import audioop
        return audioop.ulaw2lin(mulaw_data, 2)  # 2 = 16-bit samples
        
    def _pcm16_to_mulaw(self, pcm_data: bytes) -> bytes:
        """Convert PCM16 audio to mulaw"""
        import audioop
        return audioop.lin2ulaw(pcm_data, 2)  # 2 = 16-bit samples
        
    async def send_mark(self, mark_name: str):
        """Send a mark event to Twilio (for tracking/debugging)"""
        message = {
            "event": "mark",
            "streamSid": self.stream_sid,
            "mark": {
                "name": mark_name
            }
        }
        await self.websocket.send(json.dumps(message))
        
    async def clear_buffer(self):
        """Clear Twilio's audio buffer"""
        message = {
            "event": "clear",
            "streamSid": self.stream_sid
        }
        await self.websocket.send(json.dumps(message))
