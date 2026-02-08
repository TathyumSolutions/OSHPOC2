# System Architecture Documentation

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                            │
│                                                                    │
│  ┌────────────────────────────────────────────────────────┐      │
│  │         Streamlit Frontend (Port 8501)                 │      │
│  │  • Professional UI with chat interface                 │      │
│  │  • Voice input (planned) + Text input                  │      │
│  │  • Real-time conversation display                      │      │
│  │  • Eligibility results visualization                   │      │
│  │  • Session state management                            │      │
│  └────────────────────┬───────────────────────────────────┘      │
└───────────────────────┼──────────────────────────────────────────┘
                        │ HTTP/REST
                        │
┌───────────────────────▼──────────────────────────────────────────┐
│                      API LAYER (Flask)                            │
│                                                                    │
│  ┌────────────────────────────────────────────────────────┐      │
│  │         Flask API Server (Port 5000)                   │      │
│  │                                                         │      │
│  │  Endpoints:                                             │      │
│  │  • POST /api/conversation/start                        │      │
│  │  • POST /api/conversation/{id}/message                 │      │
│  │  • GET  /api/conversation/{id}                         │      │
│  │  • GET  /api/test-members                              │      │
│  │  • POST /api/direct-eligibility-check                  │      │
│  │                                                         │      │
│  │  Features:                                              │      │
│  │  • Conversation state management                       │      │
│  │  • Request/Response handling                           │      │
│  │  • Error handling & validation                         │      │
│  └────────────────────┬───────────────────────────────────┘      │
└───────────────────────┼──────────────────────────────────────────┘
                        │
                        │
┌───────────────────────▼──────────────────────────────────────────┐
│                    AGENT LAYER (LangGraph)                        │
│                                                                    │
│  ┌────────────────────────────────────────────────────────┐      │
│  │           Eligibility Agent (State Machine)            │      │
│  │                                                         │      │
│  │  State Flow:                                            │      │
│  │                                                         │      │
│  │  1. Extract Information                                │      │
│  │     ├─> Parse user message                             │      │
│  │     ├─> Extract: member_id, DOB, procedure, etc.       │      │
│  │     └─> Update conversation state                      │      │
│  │                                                         │      │
│  │  2. Determine Next Action                              │      │
│  │     ├─> Check missing fields                           │      │
│  │     ├─> Decide: gather_info | call_api | complete      │      │
│  │     └─> Route to appropriate node                      │      │
│  │                                                         │      │
│  │  3. Gather More Info (if needed)                       │      │
│  │     ├─> Generate conversational prompt                 │      │
│  │     ├─> Ask for missing information                    │      │
│  │     └─> Return to user                                 │      │
│  │                                                         │      │
│  │  4. Call Eligibility API (when ready)                  │      │
│  │     ├─> Build API request                              │      │
│  │     ├─> Call insurance API                             │      │
│  │     └─> Store response                                 │      │
│  │                                                         │      │
│  │  5. Validate Response                                  │      │
│  │     ├─> Check if query answered                        │      │
│  │     ├─> If not: loop back to gather more info          │      │
│  │     └─> If yes: proceed to final response              │      │
│  │                                                         │      │
│  │  6. Generate Final Response                            │      │
│  │     ├─> Explain eligibility result                     │      │
│  │     ├─> Include costs, conditions, etc.                │      │
│  │     └─> Return to user                                 │      │
│  └────────────────────┬───────────────────────────────────┘      │
└───────────────────────┼──────────────────────────────────────────┘
                        │
            ┌───────────┼───────────┐
            │           │           │
            ▼           ▼           ▼
┌─────────────┐  ┌──────────┐  ┌──────────────┐
│             │  │          │  │              │
│  OpenAI API │  │  State   │  │  Prompts &   │
│  (GPT-4)    │  │  Manager │  │  Templates   │
│             │  │          │  │              │
│  • Info     │  │  • Track │  │  • System    │
│    Extract  │  │    convo │  │    prompts   │
│  • Response │  │  • Store │  │  • Extraction│
│    Generate │  │    fields│  │    prompts   │
│  • Validate │  │  • Update│  │  • Validation│
│             │  │    state │  │    prompts   │
└─────────────┘  └──────────┘  └──────────────┘
                        │
                        │
┌───────────────────────▼──────────────────────────────────────────┐
│                 INSURANCE ELIGIBILITY API                         │
│                                                                    │
│  ┌────────────────────────────────────────────────────────┐      │
│  │         Mock Eligibility API                           │      │
│  │         (Simulates X12 270/271 Transactions)           │      │
│  │                                                         │      │
│  │  Data Store:                                            │      │
│  │  • Mock patient database (3 test patients)             │      │
│  │  • Procedure coverage rules (CPT codes)                │      │
│  │  • Medication coverage (NDC codes)                     │      │
│  │  • Benefit calculations                                │      │
│  │                                                         │      │
│  │  Functions:                                             │      │
│  │  • check_eligibility(request)                          │      │
│  │  • validate_member(member_id, dob)                     │      │
│  │  • check_coverage(service_type, code)                  │      │
│  │  • calculate_benefits(member, service)                 │      │
│  │                                                         │      │
│  │  Response Types:                                        │      │
│  │  • Active coverage with benefits                       │      │
│  │  • Coverage with conditions (prior auth)               │      │
│  │  • Not covered                                         │      │
│  │  • Inactive coverage                                   │      │
│  │  • Error responses                                     │      │
│  └────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
User Input → Extract Info → Missing Fields? ──Yes──> Ask User → [Loop]
                                    │
                                    No
                                    │
                                    ▼
                            Build API Request
                                    │
                                    ▼
                          Call Eligibility API
                                    │
                                    ▼
                            Get API Response
                                    │
                                    ▼
                        Validate Response Complete? ──No──> Ask More → [Loop]
                                    │
                                   Yes
                                    │
                                    ▼
                        Generate User-Friendly Response
                                    │
                                    ▼
                            Display to User
```

## State Transitions

```
┌────────────────┐
│  Initial State │
│  (User Query)  │
└────────┬───────┘
         │
         ▼
┌────────────────────┐
│ Extract Information│
└────────┬───────────┘
         │
         ▼
┌────────────────────┐      ┌──────────────────┐
│ Determine Action   │─────>│ Missing Required │
└────────┬───────────┘      │    Fields?       │
         │                  └─────────┬────────┘
         │                            │
         │                           Yes
         │                            │
         │                            ▼
         │                  ┌──────────────────┐
         │                  │ Gather More Info │
         │                  └─────────┬────────┘
         │                            │
         │                            │ [Back to Extract]
         │                            │
        No                            │
         │                            │
         ▼                            │
┌────────────────┐                   │
│   Call API     │<──────────────────┘
└────────┬───────┘
         │
         ▼
┌────────────────────┐
│ Validate Response  │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐      ┌──────────────────┐
│ Query Answered?    │─────>│  Need More Info? │
└────────┬───────────┘      └─────────┬────────┘
         │                            │
        Yes                          Yes
         │                            │
         ▼                            │ [Back to Gather]
┌────────────────────┐                │
│ Generate Response  │                │
└────────┬───────────┘                │
         │                            │
         ▼                            │
┌────────────────┐                   │
│  Return to User│<───────────────────┘
└────────────────┘
```

## Component Interactions

```
┌────────────┐       HTTP        ┌──────────┐
│  Streamlit │ ◄─────────────────┤  Flask   │
│  Frontend  │────────────────── │  API     │
└────────────┘       JSON        └────┬─────┘
                                      │
                                      │ Python
                                      │ Function
                                      │ Calls
                                      ▼
                              ┌───────────────┐
                              │   Agent       │
                              │  (LangGraph)  │
                              └───────┬───────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
            ┌───────────┐    ┌────────────┐    ┌──────────┐
            │  OpenAI   │    │   State    │    │   Mock   │
            │    API    │    │  Manager   │    │   API    │
            └───────────┘    └────────────┘    └──────────┘
```

## Key Design Patterns

### 1. State Machine Pattern (LangGraph)
- Manages conversation flow
- Handles conditional routing
- Maintains conversation state
- Enables complex multi-turn dialogues

### 2. Agent Pattern
- Autonomous decision making
- Information extraction
- Dynamic query generation
- Response validation

### 3. API Gateway Pattern (Flask)
- Single entry point
- Request routing
- State persistence
- Error handling

### 4. Mock Service Pattern
- Realistic test data
- Deterministic responses
- Easy transition to real API

## Technology Stack

**Backend:**
- Flask 3.0 - Web framework
- LangChain 0.1.9 - LLM orchestration
- LangGraph 0.0.25 - State machine
- OpenAI GPT-4 - Language model
- Pydantic 2.6 - Data validation

**Frontend:**
- Streamlit 1.31 - Web UI
- Requests - HTTP client
- Custom CSS - Styling

**Infrastructure:**
- Python 3.9+
- Virtual environments
- Environment variables
