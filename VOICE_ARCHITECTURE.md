# Voice Calling Architecture

## Complete System Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      USER'S PHONE                            │
│              (Calls Twilio Number)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ PSTN/VoIP
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  TWILIO CLOUD                               │
│                                                              │
│  1. Receives call on your phone number                     │
│  2. Executes TwiML (from /voice/incoming webhook)          │
│  3. Establishes WebSocket stream                           │
│                                                              │
│     TwiML Response:                                         │
│     <Response>                                              │
│       <Connect>                                             │
│         <Stream url="wss://your-domain/voice/stream"/>     │
│       </Connect>                                            │
│     </Response>                                             │
│                                                              │
└──────────┬────────────────────────────────┬─────────────────┘
           │                                │
           │ WebSocket                      │ HTTP Webhooks
           │ (bidirectional audio)          │ (call events)
           │                                │
┌──────────▼────────────────────────────────▼─────────────────┐
│              YOUR SERVER (Flask + WebSocket)                 │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │         app_voice.py (Port 5002 HTTP)            │       │
│  │                                                   │       │
│  │  Endpoints:                                       │       │
│  │  • POST /voice/incoming  ← TwiML webhook         │       │
│  │  • POST /voice/status    ← Status updates        │       │
│  │  • GET  /voice/health    ← Health check          │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │     WebSocket Server (Port 5001 WS)              │       │
│  │                                                   │       │
│  │  • Receives audio from Twilio (mulaw 8kHz)       │       │
│  │  • Converts to PCM16 for OpenAI                  │       │
│  │  • Sends audio to OpenAI                         │       │
│  │  • Receives audio from OpenAI (PCM16)            │       │
│  │  • Converts to mulaw for Twilio                  │       │
│  │  • Sends audio to Twilio                         │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │         CallManager (Orchestration)              │       │
│  │                                                   │       │
│  │  • Manages call lifecycle                        │       │
│  │  • Coordinates Twilio ↔ OpenAI                   │       │
│  │  • Handles function calls                        │       │
│  │  • Logs transcripts                              │       │
│  │  • Saves call records                            │       │
│  └──────────────────────────────────────────────────┘       │
└──────────┬────────────────────────────────┬─────────────────┘
           │                                │
           │ WebSocket (audio)              │ API calls
           │                                │
┌──────────▼────────────────────────┐  ┌────▼──────────────────┐
│    OpenAI Realtime API            │  │ Eligibility API        │
│    (gpt-4o-realtime)              │  │ (Mock or Real)         │
│                                   │  │                        │
│  • Speech-to-text                 │  │ • check_eligibility()  │
│  • Natural conversation           │  │ • Returns coverage     │
│  • Text-to-speech                 │  │ • Deductible info      │
│  • Function calling               │  │ • Copay details        │
│  • Context management             │  │                        │
└───────────────────────────────────┘  └────────────────────────┘
```

---

## Detailed Component Breakdown

### 1. Twilio Media Streams

**Input Format:**
- Audio: mulaw (8-bit compressed)
- Sample Rate: 8kHz
- Encoding: Base64

**Message Types:**
```json
// Connected
{"event": "connected", "protocol": "Call"}

// Stream Start
{
  "event": "start",
  "start": {
    "streamSid": "MZ...",
    "callSid": "CA...",
    "tracks": ["inbound", "outbound"]
  }
}

// Media (audio chunk)
{
  "event": "media",
  "media": {
    "track": "inbound",
    "chunk": "1",
    "timestamp": "5",
    "payload": "base64_audio_data"
  }
}

// Stream Stop
{"event": "stop"}
```

### 2. Audio Conversion Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                   Twilio → OpenAI                            │
└─────────────────────────────────────────────────────────────┘

Twilio mulaw (8kHz, 8-bit)
    ↓
[Base64 decode]
    ↓
mulaw bytes
    ↓
[audioop.ulaw2lin(data, 2)]  ← Convert to PCM16
    ↓
PCM16 bytes (16-bit)
    ↓
[Base64 encode]
    ↓
Send to OpenAI Realtime

┌─────────────────────────────────────────────────────────────┐
│                   OpenAI → Twilio                            │
└─────────────────────────────────────────────────────────────┘

OpenAI PCM16 (24kHz, 16-bit)
    ↓
[Base64 decode]
    ↓
PCM16 bytes
    ↓
[audioop.lin2ulaw(data, 2)]  ← Convert to mulaw
    ↓
mulaw bytes (8-bit)
    ↓
[Base64 encode]
    ↓
Send to Twilio
```

### 3. OpenAI Realtime Session Configuration

```python
{
  "type": "session.update",
  "session": {
    "modalities": ["text", "audio"],
    "instructions": "Your system prompt here...",
    "voice": "alloy",  # Voice selection
    "input_audio_format": "pcm16",
    "output_audio_format": "pcm16",
    "input_audio_transcription": {
      "model": "whisper-1"
    },
    "turn_detection": {
      "type": "server_vad",       # Voice Activity Detection
      "threshold": 0.5,            # Sensitivity
      "prefix_padding_ms": 300,    # Include audio before speech
      "silence_duration_ms": 500   # How long to wait for silence
    },
    "tools": [...],                # Function definitions
    "temperature": 0.8
  }
}
```

**Key Features:**
- **Server VAD:** OpenAI detects when user stops speaking
- **Interruption Handling:** User can interrupt AI mid-sentence
- **Function Calling:** AI can trigger eligibility checks
- **Transcription:** Get real-time transcripts of both sides

### 4. Function Call Flow

```
1. User speaks: "Check eligibility for member M B 1 2 3 4 5 6"
   ↓
2. OpenAI transcribes and understands intent
   ↓
3. OpenAI generates function call:
   {
     "type": "response.function_call_arguments.done",
     "call_id": "call_abc123",
     "name": "check_eligibility",
     "arguments": {
       "member_id": "MB123456",
       "date_of_birth": "1985-03-15"
     }
   }
   ↓
4. CallManager.on_function_call() is triggered
   ↓
5. eligibility_api.check_eligibility() is called
   ↓
6. Result sent back to OpenAI:
   {
     "type": "conversation.item.create",
     "item": {
       "type": "function_call_output",
       "call_id": "call_abc123",
       "output": "{\"success\": true, \"summary\": \"...\"}"
     }
   }
   ↓
7. OpenAI generates natural language response
   ↓
8. AI speaks: "Good news! The patient is eligible..."
```

### 5. Call State Management

```python
class CallManager:
    def __init__(self, call_sid, openai_api_key):
        self.call_sid = call_sid
        self.start_time = datetime.now()
        self.transcript = []           # Full conversation
        self.eligibility_results = []  # API responses
        
    async def handle_call(self, twilio_websocket):
        # Setup
        # ├─ Connect to OpenAI
        # ├─ Start bidirectional audio relay
        # └─ Wait for call to end
        
    async def _handle_eligibility_check(self, args):
        # Called when AI wants to check eligibility
        # ├─ Validate args
        # ├─ Call eligibility API
        # ├─ Log result
        # └─ Return summary to AI
```

---

## Data Flow Examples

### Example 1: Successful Eligibility Check

```
TIME   | EVENT                              | DATA
-------+------------------------------------+---------------------------
00:00  | Call connects                      | From: +1234567890
00:01  | Twilio → Your Server (WebSocket)  | Stream started
00:02  | Your Server → OpenAI              | Session configured
00:03  | OpenAI → User (TTS)               | "Hello! How can I help?"
00:05  | User → OpenAI (via Twilio)        | "Check eligibility..."
00:07  | OpenAI → Your Server              | Function call request
00:08  | Your Server → Eligibility API     | check_eligibility()
00:09  | Eligibility API → Your Server     | {status: eligible...}
00:10  | Your Server → OpenAI              | Function result
00:11  | OpenAI → User (TTS)               | "Good news! They're eligible..."
00:20  | User hangs up                      | Call ended
00:21  | Your Server                        | Save call record to DB
```

### Example 2: Missing Information Flow

```
USER: "I want to check insurance"
AI:   "I'd be happy to help. Can I get the Member ID?"
USER: "M B 1 2 3 4 5 6"
AI:   "Got it. And the date of birth?"
USER: "March 15, 1985"
AI:   [Calls function with both params]
      "Let me check... [Results]"
```

---

## File Structure

```
backend/
├── app_voice.py                 # Flask HTTP + WebSocket server
├── requirements_voice.txt       # Voice-specific dependencies
│
├── voice/
│   ├── __init__.py
│   ├── call_manager.py         # Main orchestrator
│   ├── twilio_handler.py       # Twilio WebSocket handling
│   └── realtime_handler.py     # OpenAI Realtime API handling
│
├── api/
│   └── eligibility_api.py      # Existing eligibility logic
│
└── agent/
    └── eligibility_agent.py    # Existing LangGraph agent
                                # (not used in voice, but could be)
```

---

## Latency Breakdown

Typical round-trip times:

```
User speaks → Twilio receives:        ~50ms   (network)
Twilio → Your Server:                 ~30ms   (WebSocket)
Your Server → OpenAI:                 ~40ms   (WebSocket)
OpenAI processing (VAD + STT):        ~200ms  (AI)
OpenAI LLM response:                  ~500ms  (generation)
OpenAI TTS:                          ~300ms  (synthesis)
OpenAI → Your Server:                 ~40ms   (WebSocket)
Your Server → Twilio:                 ~30ms   (WebSocket)
Twilio → User hears:                  ~50ms   (network)
────────────────────────────────────────────
TOTAL:                               ~1,240ms (~1.2 seconds)
```

**Perceived latency:** ~1-2 seconds from when user stops speaking to when AI starts responding. This is comparable to human conversation.

---

## Error Handling

### Network Errors
- **Twilio disconnects:** Call ends gracefully, logs saved
- **OpenAI disconnects:** Retry connection, fallback to "please hold"
- **Timeout:** Automatic cleanup after 5 minutes of silence

### API Errors
- **Eligibility API fails:** AI says "I'm having trouble accessing the system"
- **Invalid member ID:** AI relays error message naturally
- **Rate limits:** Implement exponential backoff

### Audio Issues
- **No input detected:** AI prompts "I didn't catch that, could you repeat?"
- **Garbled audio:** VAD detects poor quality, asks to repeat
- **Echo/feedback:** Twilio's echo cancellation handles this

---

## Security Considerations

### In Transit
- ✅ Twilio → Your Server: WSS (WebSocket Secure)
- ✅ Your Server → OpenAI: WSS (WebSocket Secure)
- ✅ All HTTP: HTTPS

### At Rest
- 🔒 Call recordings: Encrypted (AES-256)
- 🔒 Transcripts: Database encryption
- 🔒 API credentials: Environment variables, never in code

### Access Control
- 🔐 Webhook validation: Verify Twilio signatures
- 🔐 Rate limiting: Prevent abuse
- 🔐 Authentication: Add API keys if exposing publicly

---

## Production Deployment

### Infrastructure
```
                    ┌─ Backend (Flask)
Load Balancer  ──┬─ Backend (Flask)
                 └─ Backend (Flask)
                 
WebSocket sticky sessions required!
```

### Recommendations
- **AWS:** ECS with ALB (sticky sessions)
- **Azure:** App Service with WebSocket support
- **GCP:** Cloud Run with WebSocket enabled
- **Heroku:** Works but expensive

### Monitoring
- Track: Call duration, success rate, function calls
- Alerts: Failure rate > 5%, latency > 3s
- Logs: Store for 90 days (compliance)

---

## Cost at Scale

### 1,000 calls/month @ 3 min average:

| Component | Cost |
|-----------|------|
| Twilio phone number | $1/month |
| Twilio usage (3,000 mins) | $45 |
| OpenAI Realtime (3,000 mins) | $180 |
| **TOTAL** | **$226/month** |

**Per-call cost:** ~$0.23 per call (3 min avg)

### 10,000 calls/month @ 3 min average:

| Component | Cost |
|-----------|------|
| Twilio | $1 + $450 = $451 |
| OpenAI Realtime | $1,800 |
| **TOTAL** | **$2,251/month** |

**Per-call cost:** ~$0.23 per call

---

## Alternative: Cost-Optimized Stack

For high volume, switch to modular approach:

```
Phone → Twilio → Your Server → Deepgram (STT)
                             ├→ GPT-4 (Logic)
                             └→ ElevenLabs (TTS)
```

**Cost per minute:**
- Deepgram: $0.0043/min
- GPT-4: $0.003/min  (much cheaper than Realtime)
- ElevenLabs: $0.02/min
- Twilio: $0.015/min
- **Total: ~$0.042/min** (vs $0.076 with Realtime)

**Savings:** ~45% cheaper for high volume
**Trade-off:** More complex, higher latency (~2-3s vs 1-2s)

---

**This architecture gives you production-grade voice AI with minimal infrastructure!**
