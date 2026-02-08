"""
OpenAI Realtime API Handler
Manages the WebSocket connection to OpenAI's Realtime API for voice conversations.
"""
import asyncio
import json
import base64
import websockets
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class OpenAIRealtimeHandler:
    """
    Handles bidirectional audio streaming with OpenAI Realtime API.
    
    Features:
    - Speech-to-speech with GPT-4o-realtime
    - Function calling for eligibility checks
    - Conversation state management
    - Interruption handling
    """
    
    def __init__(self, api_key: str, on_function_call: Optional[Callable] = None):
        self.api_key = api_key
        self.on_function_call = on_function_call
        self.ws = None
        self.conversation_id = None
        
    async def connect(self):
        """Establish WebSocket connection to OpenAI Realtime API"""
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        self.ws = await websockets.connect(url, extra_headers=headers)
        logger.info("Connected to OpenAI Realtime API")
        
        # Configure the session
        await self._configure_session()
        
    async def _configure_session(self):
        """Configure the realtime session with system prompt and tools"""
        
        system_prompt = """You are a helpful and professional insurance eligibility verification assistant.

Your role is to:
1. Greet the caller warmly and ask how you can help them
2. Gather required information through natural conversation:
   - Member ID or Patient ID
   - Date of Birth (format: month day year, like March 15 1985)
   - What medical procedure or medication they're asking about
3. Once you have member_id and date_of_birth, call the check_eligibility function
4. Explain the results clearly in simple terms
5. Ask if they need anything else

Guidelines:
- Be conversational and friendly
- Ask for ONE piece of information at a time
- Confirm information back to the caller
- Speak clearly and at a moderate pace
- If the caller seems confused, clarify patiently

Example flow:
"Hello! Thank you for calling the Insurance Eligibility Line. How can I help you today?"
[Caller mentions checking eligibility]
"I'd be happy to help you check that. Can I start by getting the patient's Member ID?"
[Get member ID]
"Great, and what is the patient's date of birth?"
[Get DOB]
"Perfect. What procedure or medication are you checking eligibility for?"
[Get procedure/medication]
[Call function]
"Let me check that for you... [Results] Does that answer your question?"
"""
        
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": system_prompt,
                "voice": "alloy",  # Options: alloy, echo, shimmer
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",  # Voice Activity Detection
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "tools": [
                    {
                        "type": "function",
                        "name": "check_eligibility",
                        "description": "Check insurance eligibility for a patient. Call this when you have collected the member_id and date_of_birth from the caller.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "member_id": {
                                    "type": "string",
                                    "description": "The patient's member ID or patient ID"
                                },
                                "date_of_birth": {
                                    "type": "string",
                                    "description": "Date of birth in YYYY-MM-DD format"
                                },
                                "procedure_code": {
                                    "type": "string",
                                    "description": "CPT code if checking for a specific procedure"
                                },
                                "medication_name": {
                                    "type": "string",
                                    "description": "Medication name if checking drug coverage"
                                }
                            },
                            "required": ["member_id", "date_of_birth"]
                        }
                    }
                ],
                "tool_choice": "auto",
                "temperature": 0.8
            }
        }
        
        await self.ws.send(json.dumps(config))
        
    async def send_audio(self, audio_data: bytes):
        """Send audio chunk to OpenAI (from Twilio)"""
        if not self.ws:
            return
            
        # OpenAI expects base64 encoded PCM16
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }
        
        await self.ws.send(json.dumps(message))
        
    async def receive_messages(self, on_audio: Callable, on_transcript: Callable):
        """
        Receive messages from OpenAI and handle them.
        
        Args:
            on_audio: Callback for audio data to send to Twilio
            on_transcript: Callback for transcript updates
        """
        try:
            async for message in self.ws:
                data = json.loads(message)
                event_type = data.get("type")
                
                # Audio output from OpenAI
                if event_type == "response.audio.delta":
                    audio_base64 = data.get("delta", "")
                    if audio_base64:
                        audio_bytes = base64.b64decode(audio_base64)
                        await on_audio(audio_bytes)
                
                # Transcript of what AI is saying
                elif event_type == "response.audio_transcript.delta":
                    transcript = data.get("delta", "")
                    if transcript:
                        await on_transcript("assistant", transcript)
                
                # Transcript of what user said
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = data.get("transcript", "")
                    if transcript:
                        await on_transcript("user", transcript)
                
                # Function call from OpenAI
                elif event_type == "response.function_call_arguments.done":
                    await self._handle_function_call(data)
                
                # Error handling
                elif event_type == "error":
                    logger.error(f"OpenAI Realtime error: {data}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error receiving from OpenAI: {e}")
            
    async def _handle_function_call(self, data):
        """Handle function call from OpenAI (eligibility check)"""
        call_id = data.get("call_id")
        function_name = data.get("name")
        arguments = json.loads(data.get("arguments", "{}"))
        
        logger.info(f"Function call: {function_name} with args: {arguments}")
        
        if function_name == "check_eligibility" and self.on_function_call:
            # Call the eligibility API
            result = await self.on_function_call(arguments)
            
            # Send result back to OpenAI
            response = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result)
                }
            }
            await self.ws.send(json.dumps(response))
            
            # Tell OpenAI to generate a response based on the function result
            await self.ws.send(json.dumps({"type": "response.create"}))
            
    async def close(self):
        """Close the WebSocket connection"""
        if self.ws:
            await self.ws.close()
            logger.info("Closed OpenAI WebSocket connection")
