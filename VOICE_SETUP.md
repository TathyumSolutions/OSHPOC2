# Voice Calling Setup Guide

Complete guide to set up voice calling with Twilio + OpenAI Realtime API.

---

## 🎯 What You'll Build

A working phone number that users can call to:
1. **Talk to an AI agent** that sounds natural
2. **Check insurance eligibility** by providing member ID and DOB
3. **Get instant results** spoken back in plain English

---

## 📋 Prerequisites

1. **OpenAI API key** - You already have this ✓
2. **Twilio account** - Free trial available ($15 credit)
3. **ngrok account** - Free tier works fine
4. **Phone** - To test by calling in

---

## 🚀 Step-by-Step Setup

### Step 1: Install Additional Dependencies

```bash
cd backend
pip install -r requirements_voice.txt
```

This installs:
- `twilio` - Twilio Python SDK
- `websockets` - WebSocket client/server
- `aiohttp` - Async HTTP client

### Step 2: Set Up Twilio Account

#### 2.1 Create Twilio Account

1. Go to https://www.twilio.com/try-twilio
2. Sign up (free $15 credit)
3. Verify your phone number

#### 2.2 Get Your Twilio Credentials

1. Go to https://console.twilio.com
2. Copy your **Account SID** and **Auth Token**
3. Add them to `.env`:

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
```

#### 2.3 Buy a Phone Number

1. In Twilio Console, go to **Phone Numbers** → **Buy a Number**
2. Choose your country (US, India, etc.)
3. Buy a number with **Voice** capability (~$1/month)
4. Copy the number (format: +1234567890)
5. Add to `.env`:

```bash
TWILIO_PHONE_NUMBER=+1234567890
```

**Cost:** ~$1-2/month + $0.01-0.02 per minute

### Step 3: Set Up ngrok (Public URL)

Your local server needs a public URL for Twilio to connect to.

#### 3.1 Install ngrok

**Windows:**
```powershell
# Download from https://ngrok.com/download
# Or use chocolatey:
choco install ngrok
```

**Mac/Linux:**
```bash
brew install ngrok
# Or download from https://ngrok.com/download
```

#### 3.2 Create ngrok Account

1. Go to https://dashboard.ngrok.com/signup
2. Sign up (free tier works)
3. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
4. Run: `ngrok config add-authtoken YOUR_TOKEN`

#### 3.3 Start ngrok Tunnel

```bash
ngrok http 5002
```

You'll see output like:
```
Forwarding   https://abc123.ngrok.io -> http://localhost:5002
```

**Copy the `abc123.ngrok.io` part** and add to `.env`:

```bash
YOUR_DOMAIN=abc123.ngrok.io
```

⚠️ **Important:** Don't include `https://` or `http://` - just the domain.

### Step 4: Configure Twilio Webhooks

Tell Twilio where to send incoming calls.

1. Go to Twilio Console → **Phone Numbers** → **Manage** → **Active Numbers**
2. Click on your phone number
3. Scroll to **Voice Configuration**
4. Set **A CALL COMES IN** to:
   - **Webhook**
   - URL: `https://your-ngrok-domain.ngrok.io/voice/incoming`
   - HTTP POST
5. Set **STATUS CALLBACK URL** (optional):
   - URL: `https://your-ngrok-domain.ngrok.io/voice/status`
   - HTTP POST
6. Click **Save**

Replace `your-ngrok-domain.ngrok.io` with your actual ngrok domain.

### Step 5: Start the Voice Server

```bash
cd backend
python app_voice.py
```

You should see:
```
============================================================
  Voice Agent Ready!
============================================================
  HTTP endpoints : http://0.0.0.0:5002
  WebSocket      : ws://0.0.0.0:5001/voice/stream
  Domain (ngrok) : abc123.ngrok.io
============================================================
```

### Step 6: Test the System

#### Test 1: Health Check

Open browser:
```
http://localhost:5002/voice/health
```

Should return:
```json
{
  "status": "healthy",
  "service": "Voice Agent",
  "openai_configured": true,
  "twilio_configured": true
}
```

#### Test 2: Make a Call!

1. **Call your Twilio number** from your phone
2. You should hear the AI assistant greet you
3. Try this conversation:

```
AI: "Hello! Thank you for calling the Insurance Eligibility Line. 
     How can I help you today?"

You: "I need to check if a patient is covered"

AI: "I'd be happy to help you with that. Can I start by getting 
     the patient's Member ID?"

You: "M B 1 2 3 4 5 6"

AI: "Great, and what is the patient's date of birth?"

You: "March 15, 1985"

AI: "Perfect. What procedure or medication are you checking eligibility for?"

You: "MRI"

AI: "Let me check that for you..."
    [Calls eligibility API]
    "Good news! The patient is eligible for coverage. They have 
     $1050 remaining on their deductible. Note: Prior authorization 
     is required for this procedure. The copay is $50."
```

---

## 🧪 Testing with Test Data

Use these test patients:

### Patient 1: Active, Partial Deductible
- **Member ID:** MB123456
- **DOB:** March 15, 1985
- **Result:** Eligible, $1,050 deductible remaining

### Patient 2: Active, Deductible Met
- **Member ID:** MB789012
- **DOB:** July 22, 1990
- **Result:** Eligible, deductible fully met

### Patient 3: Inactive Coverage
- **Member ID:** MB345678
- **DOB:** November 30, 1975
- **Result:** Not eligible (coverage terminated)

---

## 🔧 Troubleshooting

### Problem: "Can't connect to Twilio"

**Solution:**
1. Check ngrok is running: `ngrok http 5002`
2. Update Twilio webhook with current ngrok URL
3. Restart voice server

### Problem: "No audio/silence on call"

**Solution:**
1. Check OpenAI API key is set correctly
2. Check logs for WebSocket connection errors
3. Verify you have OpenAI API credits

### Problem: "Function not being called"

**Solution:**
1. Make sure you say clear phrases like "Member ID M B 1 2 3 4 5 6"
2. Speak slowly and clearly
3. Check logs - you'll see when function is triggered

### Problem: "Call drops immediately"

**Solution:**
1. Check Twilio webhook URL is correct (must be https)
2. Check ngrok is running and forwarding to 5002
3. Look at Twilio debugger: https://console.twilio.com/debugger

---

## 📊 Monitoring & Logs

### View Call Logs

The voice server logs everything:
```
[USER] I need to check eligibility
[ASSISTANT] I'd be happy to help...
[INFO] Checking eligibility with args: {'member_id': 'MB123456', ...}
[INFO] Call abc123 ended - Duration: 45.3s
```

### Twilio Debugger

View all calls and errors:
https://console.twilio.com/debugger

### OpenAI Usage

Track API usage:
https://platform.openai.com/usage

---

## 💰 Cost Breakdown

### For testing (10 minutes of calls):
- Twilio: ~$0.20
- OpenAI Realtime: ~$0.60
- **Total: ~$0.80**

### Monthly (100 hours of calls):
- Twilio phone number: $1/month
- Twilio usage: 6,000 mins × $0.015 = $90
- OpenAI Realtime: 6,000 mins × $0.06 = $360
- **Total: ~$451/month**

### Cost optimization for production:
- Use Deepgram STT ($0.0043/min) instead of OpenAI Realtime
- Use ElevenLabs TTS ($0.02/min)
- Can reduce to ~$0.03-0.04/min total

---

## 🔒 Security & Compliance

### For Production:

1. **HIPAA Compliance:**
   - Sign BAA with Twilio
   - Sign BAA with OpenAI (Enterprise tier)
   - Encrypt call recordings
   - Implement access controls

2. **Security:**
   - Use environment variables (never commit .env)
   - Enable Twilio request validation
   - Add authentication for webhooks
   - Rate limiting on endpoints

3. **Call Recording:**
   - Enable in Twilio settings if needed
   - Store securely (encrypted S3/Azure Blob)
   - Implement retention policies
   - Add audit logging

---

## 🎨 Customization

### Change Voice

Edit `voice/realtime_handler.py`:
```python
"voice": "shimmer",  # Options: alloy, echo, shimmer
```

### Adjust Conversation Style

Modify the system prompt in `realtime_handler.py`:
```python
system_prompt = """You are a [your style here]..."""
```

### Add More Function Calls

Add new tools to the `tools` array in `_configure_session()`.

---

## 🚀 Next Steps

### Immediate:
1. Test with all 3 test patients
2. Try different procedures (MRI, office visit, medications)
3. Test edge cases (wrong member ID, etc.)

### Production:
1. Set up production domain (not ngrok)
2. Implement call recording
3. Add database logging
4. Set up monitoring/alerts
5. Load test with volume

### Advanced Features:
1. Transfer to human agent
2. Voicemail detection
3. Multi-language support
4. IVR menu before AI
5. SMS follow-up with results

---

## 📞 Support

**Twilio Issues:**
- Docs: https://www.twilio.com/docs/voice
- Support: https://support.twilio.com

**OpenAI Realtime Issues:**
- Docs: https://platform.openai.com/docs/guides/realtime
- Forum: https://community.openai.com

**This Code:**
- Check logs in console
- Look for error stack traces
- Test individual components

---

## ✅ Checklist

Before going live:

- [ ] Twilio account created and verified
- [ ] Phone number purchased
- [ ] ngrok tunnel running
- [ ] Webhook URLs configured in Twilio
- [ ] `.env` file configured with all credentials
- [ ] Voice server running (`python app_voice.py`)
- [ ] Health check passing at `/voice/health`
- [ ] Successfully made test call
- [ ] Eligibility check working
- [ ] Logs showing complete conversation

---

**You're ready to test! Call your Twilio number and start talking to your AI agent!** 🎉
