"""
Insurance Eligibility Verification Agent - Streamlit Frontend
Professional UI with voice and text input capabilities
"""
import streamlit as st
import requests
from datetime import datetime
import json
from typing import Optional, Dict, Any

# Page configuration
st.set_page_config(
    page_title="Insurance Eligibility Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .assistant-message {
        background-color: #f5f5f5;
        border-left: 4px solid #4caf50;
    }
    .info-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #28a745;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #dc3545;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        border-radius: 5px;
        padding: 0.5rem;
        font-weight: bold;
    }
    .eligibility-result {
        font-size: 1.1rem;
        padding: 1.5rem;
        border-radius: 10px;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Backend API configuration
API_BASE_URL = "http://localhost:5000/api"

# Initialize session state
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "eligibility_result" not in st.session_state:
    st.session_state.eligibility_result = None
if "collected_info" not in st.session_state:
    st.session_state.collected_info = {}


def start_new_conversation(initial_message: str) -> Optional[Dict[str, Any]]:
    """Start a new conversation with the agent"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/conversation/start",
            json={"initial_message": initial_message},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to start conversation: {str(e)}")
        return None


def send_message(conversation_id: str, message: str) -> Optional[Dict[str, Any]]:
    """Send a message in an existing conversation"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/conversation/{conversation_id}/message",
            json={"message": message},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to send message: {str(e)}")
        return None


def get_test_members() -> Optional[Dict[str, Any]]:
    """Get list of test member IDs"""
    try:
        response = requests.get(f"{API_BASE_URL}/test-members", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to get test members: {str(e)}")
        return None


def display_message(role: str, content: str):
    """Display a chat message"""
    if role == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>👤 You:</strong><br>
            {content}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <strong>🤖 Assistant:</strong><br>
            {content}
        </div>
        """, unsafe_allow_html=True)


def display_eligibility_result(api_response: Dict[str, Any]):
    """Display eligibility result in a formatted way"""
    if not api_response:
        return
    
    status = api_response.get("eligibility_status", "unknown")
    
    if status == "eligible":
        box_class = "success-box"
        icon = "✅"
        title = "Coverage Confirmed"
    elif status == "eligible_with_conditions":
        box_class = "info-box"
        icon = "⚠️"
        title = "Eligible with Conditions"
    else:
        box_class = "error-box"
        icon = "❌"
        title = "Not Covered"
    
    st.markdown(f"""
    <div class="{box_class}">
        <h3>{icon} {title}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Display detailed information in expandable sections
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Member Information")
        member_info = api_response.get("member_info", {})
        if member_info:
            st.write(f"**Member ID:** {member_info.get('member_id', 'N/A')}")
            st.write(f"**Name:** {member_info.get('name', 'N/A')}")
            st.write(f"**Date of Birth:** {member_info.get('dob', 'N/A')}")
        
        st.subheader("🏥 Coverage Details")
        coverage_info = api_response.get("coverage_info", {})
        if coverage_info:
            st.write(f"**Plan Type:** {coverage_info.get('plan_type', 'N/A')}")
            st.write(f"**Status:** {coverage_info.get('status', 'N/A')}")
            st.write(f"**Effective Date:** {coverage_info.get('effective_date', 'N/A')}")
    
    with col2:
        st.subheader("💰 Financial Information")
        financial_info = api_response.get("financial_info", {})
        if financial_info:
            deductible = financial_info.get("deductible", {})
            st.write(f"**Deductible Remaining:** ${deductible.get('remaining', 0):.2f}")
            
            oop = financial_info.get("out_of_pocket", {})
            st.write(f"**Out-of-Pocket Remaining:** ${oop.get('remaining', 0):.2f}")
            
            copays = financial_info.get("copays", {})
            if copays:
                st.write(f"**Primary Care Copay:** ${copays.get('primary_care', 0):.2f}")
                st.write(f"**Specialist Copay:** ${copays.get('specialist', 0):.2f}")
    
    # Service-specific information
    service_specific = api_response.get("service_specific")
    pharmacy_specific = api_response.get("pharmacy_specific")
    
    if service_specific:
        with st.expander("🔍 Service Details", expanded=True):
            st.write(f"**Procedure:** {service_specific.get('procedure_name', 'N/A')}")
            st.write(f"**Code:** {service_specific.get('procedure_code', 'N/A')}")
            st.write(f"**Covered:** {'Yes' if service_specific.get('covered') else 'No'}")
            if service_specific.get('requires_prior_authorization'):
                st.warning("⚠️ Prior Authorization Required")
            
            benefit_details = service_specific.get('benefit_details', {})
            if benefit_details:
                st.write(f"**Patient Responsibility:** {benefit_details.get('patient_responsibility', 'N/A')}")
    
    if pharmacy_specific:
        with st.expander("💊 Medication Details", expanded=True):
            st.write(f"**Medication:** {pharmacy_specific.get('medication_name', 'N/A')}")
            st.write(f"**NDC Code:** {pharmacy_specific.get('ndc_code', 'N/A')}")
            st.write(f"**Covered:** {'Yes' if pharmacy_specific.get('covered') else 'No'}")
            if pharmacy_specific.get('formulary_tier'):
                st.write(f"**Formulary Tier:** {pharmacy_specific.get('formulary_tier')}")
            if pharmacy_specific.get('copay_amount'):
                st.write(f"**Copay:** ${pharmacy_specific.get('copay_amount'):.2f}")
            if pharmacy_specific.get('requires_prior_authorization'):
                st.warning("⚠️ Prior Authorization Required")


# Main app layout
st.markdown('<div class="main-header">🏥 Insurance Eligibility Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Powered Insurance Coverage Verification</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("ℹ️ Information")
    
    st.markdown("""
    ### How it works:
    1. Ask about insurance eligibility
    2. Provide patient information when asked
    3. Get instant eligibility verification
    
    ### What you need:
    - Member/Patient ID
    - Date of Birth
    - Procedure or medication details (optional)
    """)
    
    st.divider()
    
    # Test members section
    st.subheader("🧪 Test Member IDs")
    if st.button("Show Test Members"):
        test_data = get_test_members()
        if test_data:
            for member in test_data.get("test_members", []):
                status_icon = "✅" if member["status"] == "active" else "❌"
                st.write(f"{status_icon} **{member['member_id']}** - {member['name']}")
    
    st.divider()
    
    # Display collected information
    if st.session_state.collected_info:
        st.subheader("📝 Collected Information")
        for key, value in st.session_state.collected_info.items():
            if value:
                display_key = key.replace("_", " ").title()
                st.write(f"**{display_key}:** {value}")
    
    st.divider()
    
    # Reset conversation
    if st.button("🔄 Start New Conversation"):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.session_state.eligibility_result = None
        st.session_state.collected_info = {}
        st.rerun()

# Main chat interface
st.subheader("💬 Chat with the Assistant")

# Display chat history
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        display_message(message["role"], message["content"])

# Display eligibility result if available
if st.session_state.eligibility_result:
    st.divider()
    st.subheader("📊 Eligibility Result")
    display_eligibility_result(st.session_state.eligibility_result)

# Input section
st.divider()

# Tabs for different input methods
tab1, tab2 = st.tabs(["💬 Text Input", "🎤 Voice Input (Coming Soon)"])

with tab1:
    # Text input
    col1, col2 = st.columns([5, 1])
    
    with col1:
        user_input = st.text_input(
            "Type your message:",
            placeholder="e.g., Is patient MB123456 eligible for an MRI?",
            label_visibility="collapsed",
            key="text_input"
        )
    
    with col2:
        send_button = st.button("Send", type="primary", use_container_width=True)
    
    # Quick start examples
    st.caption("**Quick Examples:**")
    example_col1, example_col2, example_col3 = st.columns(3)
    
    with example_col1:
        if st.button("Check General Eligibility", use_container_width=True):
            user_input = "I want to check if a patient is eligible for coverage"
            send_button = True
    
    with example_col2:
        if st.button("Check for MRI", use_container_width=True):
            user_input = "Is the patient covered for an MRI?"
            send_button = True
    
    with example_col3:
        if st.button("Check Medication", use_container_width=True):
            user_input = "Is Humira covered under the patient's plan?"
            send_button = True
    
    # Process input
    if send_button and user_input:
        # Add user message to display
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Show processing indicator
        with st.spinner("🤔 Processing..."):
            # Start new conversation or continue existing
            if st.session_state.conversation_id is None:
                result = start_new_conversation(user_input)
                if result:
                    st.session_state.conversation_id = result.get("conversation_id")
                    response_text = result.get("response", "")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Update collected info
                    if result.get("eligibility_determined"):
                        st.session_state.eligibility_result = result.get("api_response")
            else:
                result = send_message(st.session_state.conversation_id, user_input)
                if result:
                    response_text = result.get("response", "")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Update collected info
                    state_info = result.get("state_info", {})
                    st.session_state.collected_info = {
                        k: v for k, v in state_info.items() if v and k != "missing_fields"
                    }
                    
                    # Update eligibility result
                    if result.get("eligibility_determined"):
                        st.session_state.eligibility_result = result.get("api_response")
        
        st.rerun()

with tab2:
    st.info("🎤 Voice input feature is under development. Coming soon!")
    st.markdown("""
    **Planned features:**
    - Real-time speech-to-text
    - Voice response playback
    - Multi-language support
    """)

# Footer
st.divider()
st.caption("💡 **Tip:** This is a demo system using mock data. In production, it would connect to real insurance eligibility APIs.")
