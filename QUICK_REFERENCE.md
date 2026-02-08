# Quick Reference Guide - Insurance Eligibility Agent

## 🚀 Quick Start (30 seconds)

```bash
# 1. Clone/Download the project
cd insurance-eligibility-agent

# 2. Set up OpenAI API Key
cp backend/.env.example backend/.env
# Edit backend/.env and add your OpenAI API key

# 3. Run the quick start script
bash quickstart.sh
# Choose option 4: "Setup and Run Everything"
```

## 📝 Test Scenarios

### Scenario 1: Basic Eligibility Check
**User:** "Is patient MB123456 eligible for coverage?"
**Agent:** Asks for DOB
**User:** "March 15, 1985"
**Result:** Active coverage, PPO plan, $450 of $1,500 deductible met

### Scenario 2: Procedure-Specific
**User:** "Can patient MB789012 get an MRI?"
**Agent:** Asks for DOB
**User:** "07/22/1990"
**Result:** Eligible, requires prior authorization, $50 copay

### Scenario 3: Medication Coverage
**User:** "Is Humira covered for MB123456, DOB 1985-03-15?"
**Result:** Covered, Tier 3, $150 copay, prior authorization required

### Scenario 4: Inactive Coverage
**User:** "Check eligibility for MB345678"
**Agent:** Asks for DOB
**User:** "11/30/1975"
**Result:** Coverage inactive (terminated 2023-12-31)

## 🎯 Key Commands

### Backend
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python app.py              # Starts on port 5000
```

### Frontend
```bash
cd frontend
source venv/bin/activate  # Windows: venv\Scripts\activate
streamlit run streamlit_app.py  # Opens browser automatically
```

### Testing
```bash
cd tests
python test_api.py  # Run all API tests
```

## 🔑 Test Data

### Active Members
| Member ID | Name | DOB | Status | Deductible |
|-----------|------|-----|--------|------------|
| MB123456 | John Doe | 1985-03-15 | Active | $450/$1,500 |
| MB789012 | Jane Smith | 1990-07-22 | Active | Fully Met |
| MB345678 | Robert Johnson | 1975-11-30 | Inactive | N/A |

### Procedure Codes
| Code | Name | Covered | Auth Required |
|------|------|---------|---------------|
| 99213 | Office Visit | ✅ | ❌ |
| 70450 | CT Scan | ✅ | ✅ |
| 70553 | MRI | ✅ | ✅ |
| J9035 | Bevacizumab | ❌ | N/A |

### Medications (NDC Codes)
| Code | Name | Tier | Copay | Auth |
|------|------|------|-------|------|
| 00002-7510-01 | Atorvastatin | 1 | $10 | ❌ |
| 50090-3568-00 | Humira | 3 | $150 | ✅ |

## 📡 API Endpoints

### Start Conversation
```bash
curl -X POST http://localhost:5000/api/conversation/start \
  -H "Content-Type: application/json" \
  -d '{"initial_message": "Check eligibility for MB123456"}'
```

### Send Message
```bash
curl -X POST http://localhost:5000/api/conversation/{id}/message \
  -H "Content-Type: application/json" \
  -d '{"message": "DOB is 1985-03-15"}'
```

### Direct Check
```bash
curl -X POST http://localhost:5000/api/direct-eligibility-check \
  -H "Content-Type: application/json" \
  -d '{
    "member_id": "MB123456",
    "date_of_birth": "1985-03-15",
    "procedure_code": "70553"
  }'
```

## 🎨 UI Features

- **Chat Interface**: Real-time conversation with agent
- **Sidebar**: Shows collected information and test members
- **Results Display**: Color-coded eligibility results
- **Quick Examples**: One-click example queries
- **Message History**: Full conversation history
- **Reset**: Start new conversation anytime

## 🔧 Customization

### Change LLM Model
Edit `backend/agent/eligibility_agent.py`:
```python
self.llm = ChatOpenAI(
    api_key=openai_api_key,
    model="gpt-4o",  # Change model here
    temperature=0.3
)
```

### Add More Test Members
Edit `backend/api/eligibility_api.py`:
```python
self.mock_database = {
    "MB999999": {
        "member_id": "MB999999",
        # Add member details
    }
}
```

### Modify Agent Prompts
Edit `backend/agent/prompts.py` - customize system prompts

### Style Frontend
Edit CSS in `frontend/streamlit_app.py` in the `st.markdown()` section

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to API" | Ensure backend is running on port 5000 |
| "OpenAI API error" | Check API key in backend/.env |
| "Module not found" | Run `pip install -r requirements.txt` |
| "Port already in use" | Kill process: `lsof -ti:5000 \| xargs kill -9` |

## 📊 Agent Workflow

```
User Message 
    ↓
Extract Information (LLM)
    ↓
Check Missing Fields?
    ↓
Yes → Ask User → Loop Back
    ↓
No → Call API
    ↓
Validate Response
    ↓
Complete? No → Ask More → Loop Back
    ↓
Yes → Explain Result → Done
```

## 🎓 Understanding the Code

### Main Components

1. **Frontend** (`frontend/streamlit_app.py`)
   - User interface
   - Makes HTTP calls to Flask API
   - Displays results

2. **Flask API** (`backend/app.py`)
   - Receives HTTP requests
   - Manages conversation state
   - Calls agent

3. **Agent** (`backend/agent/eligibility_agent.py`)
   - LangGraph state machine
   - Information extraction
   - Conversation flow control

4. **Mock API** (`backend/api/eligibility_api.py`)
   - Simulates insurance API
   - Returns realistic eligibility responses

### Key Files

- `backend/agent/state.py` - Conversation state structure
- `backend/agent/prompts.py` - System prompts for LLM
- `backend/api/eligibility_api.py` - Mock insurance API

## 💡 Pro Tips

1. **Test First**: Use test_api.py to verify backend before UI
2. **Check Logs**: Backend prints useful debug information
3. **Example Queries**: Use the quick example buttons in UI
4. **Reset Often**: Start fresh conversations for testing
5. **Read Responses**: Agent explains what info it needs

## 🔐 Production Checklist

Before deploying to production:

- [ ] Replace mock API with real insurance API
- [ ] Add authentication (OAuth2/JWT)
- [ ] Implement database for state persistence
- [ ] Add rate limiting
- [ ] Enable HTTPS/SSL
- [ ] Add comprehensive logging
- [ ] Implement error tracking (Sentry)
- [ ] Add health checks and monitoring
- [ ] Ensure HIPAA compliance
- [ ] Add data encryption
- [ ] Implement backup strategy
- [ ] Add load balancing
- [ ] Set up CI/CD pipeline

## 📚 Resources

- LangGraph: https://langchain-ai.github.io/langgraph/
- Streamlit: https://docs.streamlit.io
- Flask: https://flask.palletsprojects.com
- OpenAI API: https://platform.openai.com/docs

## 🤝 Getting Help

1. Check README.md for detailed documentation
2. Review ARCHITECTURE.md for system design
3. Run tests/test_api.py to verify setup
4. Check Flask logs for errors
5. Examine conversation state in API responses

---

**Built with ❤️ for enterprise insurance eligibility verification**
