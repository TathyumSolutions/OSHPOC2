"""
Call Manager
Orchestrates the entire voice call flow:
Twilio (phone) ↔ This Manager ↔ OpenAI Realtime ↔ Eligibility Agent
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from voice.twilio_handler import TwilioStreamHandler
from voice.realtime_handler import OpenAIRealtimeHandler
from api.eligibility_api import MockEligibilityAPI

logger = logging.getLogger(__name__)


class CallManager:
    """
    Manages a single phone call from start to finish.
    
    Responsibilities:
    - Connect Twilio audio stream to OpenAI Realtime
    - Handle function calls (eligibility checks)
    - Track call state and conversation
    - Log transcripts and results
    """
    
    def __init__(self, call_sid: str, openai_api_key: str):
        self.call_sid = call_sid
        self.start_time = datetime.now()
        self.transcript = []
        self.eligibility_results = []
        
        # Initialize components
        self.eligibility_api = MockEligibilityAPI()
        self.openai_handler = OpenAIRealtimeHandler(
            api_key=openai_api_key,
            on_function_call=self._handle_eligibility_check
        )
        self.twilio_handler = None
        
    async def handle_call(self, twilio_websocket):
        """
        Main entry point - handle the entire call lifecycle.
        
        Args:
            twilio_websocket: WebSocket connection from Twilio
        """
        self.twilio_handler = TwilioStreamHandler(twilio_websocket)
        
        try:
            # Connect to OpenAI Realtime API
            await self.openai_handler.connect()
            logger.info(f"Call {self.call_sid} - Both streams connected")
            
            # Create tasks for bidirectional streaming
            tasks = [
                asyncio.create_task(self._twilio_to_openai()),
                asyncio.create_task(self._openai_to_twilio()),
            ]
            
            # Run until call ends
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Call {self.call_sid} error: {e}")
            
        finally:
            await self._cleanup()
            
    async def _twilio_to_openai(self):
        """Forward audio from Twilio to OpenAI"""
        try:
            async for message in self.twilio_handler.websocket:
                await self.twilio_handler.handle_message(
                    message, 
                    self.openai_handler
                )
        except Exception as e:
            logger.error(f"Twilio→OpenAI error: {e}")
            
    async def _openai_to_twilio(self):
        """Forward audio from OpenAI to Twilio"""
        
        async def on_audio(audio_bytes: bytes):
            """Callback when OpenAI produces audio"""
            await self.twilio_handler.send_audio(audio_bytes)
            
        async def on_transcript(role: str, text: str):
            """Callback when we get transcript updates"""
            self._log_transcript(role, text)
            
        await self.openai_handler.receive_messages(on_audio, on_transcript)
        
    async def _handle_eligibility_check(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Called by OpenAI when it wants to check eligibility.
        
        This bridges the voice conversation to your existing eligibility logic.
        """
        logger.info(f"Checking eligibility with args: {args}")
        
        try:
            # Call the mock API (in production, use real API)
            result = self.eligibility_api.check_eligibility(args)
            
            # Log the result
            self.eligibility_results.append({
                "timestamp": datetime.now().isoformat(),
                "request": args,
                "response": result
            })
            
            # Return simplified result for AI to speak
            if result.get("status") == "success":
                summary = self._summarize_eligibility_result(result)
                return {
                    "success": True,
                    "summary": summary,
                    "full_result": result
                }
            else:
                return {
                    "success": False,
                    "error": result.get("message", "Unable to check eligibility")
                }
                
        except Exception as e:
            logger.error(f"Eligibility check error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def _summarize_eligibility_result(self, result: Dict[str, Any]) -> str:
        """
        Convert API response to a natural summary for the AI to speak.
        """
        status = result.get("eligibility_status", "unknown")
        
        if status == "eligible":
            member_info = result.get("member_info", {})
            financial = result.get("financial_info", {})
            
            summary = f"Good news! The patient is eligible for coverage. "
            
            # Add deductible info
            if financial:
                deductible = financial.get("deductible", {})
                remaining = deductible.get("remaining", 0)
                if remaining > 0:
                    summary += f"They have ${remaining:.0f} remaining on their deductible. "
                else:
                    summary += "Their deductible has been met. "
                    
            # Add procedure-specific info
            service_specific = result.get("service_specific")
            if service_specific:
                if service_specific.get("requires_prior_authorization"):
                    summary += "Note: Prior authorization is required for this procedure. "
                    
                benefit = service_specific.get("benefit_details", {})
                copay = benefit.get("copay_amount")
                if copay:
                    summary += f"The copay is ${copay:.0f}. "
                    
            return summary
            
        elif status == "not_eligible":
            return result.get("message", "The patient is not currently eligible for coverage.")
            
        else:
            return "I was able to check the eligibility, but received an unclear response."
            
    def _log_transcript(self, role: str, text: str):
        """Log conversation transcript"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "text": text
        }
        self.transcript.append(entry)
        logger.info(f"[{role.upper()}] {text}")
        
    async def _cleanup(self):
        """Clean up resources after call ends"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        logger.info(f"Call {self.call_sid} ended - Duration: {duration:.1f}s")
        logger.info(f"Transcript entries: {len(self.transcript)}")
        logger.info(f"Eligibility checks: {len(self.eligibility_results)}")
        
        # In production: save to database
        self._save_call_record()
        
        # Close connections
        await self.openai_handler.close()
        
    def _save_call_record(self):
        """
        Save complete call record to database.
        In production: Store in PostgreSQL/MongoDB for compliance.
        """
        call_record = {
            "call_sid": self.call_sid,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "transcript": self.transcript,
            "eligibility_results": self.eligibility_results
        }
        
        # For now, just log it
        # In production: INSERT INTO calls (call_sid, ...) VALUES (...)
        logger.info(f"Call record: {call_record}")
