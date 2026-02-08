"""
Flask API for Insurance Eligibility Agent
Provides REST endpoints for the Streamlit frontend
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import uuid
from typing import Dict

from agent.eligibility_agent import EligibilityAgent
from agent.state import ConversationState
from api.eligibility_api import MockEligibilityAPI

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize agent
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
agent = EligibilityAgent(openai_api_key=OPENAI_API_KEY)

# Store conversation states (in production, use Redis or database)
conversation_states: Dict[str, ConversationState] = {}


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "Insurance Eligibility Agent"}), 200


@app.route("/api/conversation/start", methods=["POST"])
def start_conversation():
    """
    Start a new conversation
    
    Request body:
    {
        "initial_message": "User's first message"
    }
    """
    try:
        data = request.get_json()
        initial_message = data.get("initial_message", "")
        
        if not initial_message:
            return jsonify({"error": "initial_message is required"}), 400
        
        # Generate conversation ID
        conversation_id = str(uuid.uuid4())
        
        # Process the initial message
        result = agent.process_message(
            conversation_id=conversation_id,
            user_message=initial_message
        )
        
        # Store state
        conversation_states[conversation_id] = result["state"]
        
        return jsonify({
            "conversation_id": conversation_id,
            "response": result["response"],
            "eligibility_determined": result.get("eligibility_determined", False),
            "api_response": result.get("api_response")
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversation/<conversation_id>/message", methods=["POST"])
def send_message(conversation_id: str):
    """
    Continue an existing conversation
    
    Request body:
    {
        "message": "User's message"
    }
    """
    try:
        # Check if conversation exists
        if conversation_id not in conversation_states:
            return jsonify({"error": "Conversation not found"}), 404
        
        data = request.get_json()
        message = data.get("message", "")
        
        if not message:
            return jsonify({"error": "message is required"}), 400
        
        # Get current state
        current_state = conversation_states[conversation_id]
        
        # Process the message
        result = agent.process_message(
            conversation_id=conversation_id,
            user_message=message,
            current_state=current_state
        )
        
        # Update state
        conversation_states[conversation_id] = result["state"]
        
        return jsonify({
            "response": result["response"],
            "eligibility_determined": result.get("eligibility_determined", False),
            "api_response": result.get("api_response"),
            "state_info": {
                "member_id": result["state"].get("member_id"),
                "procedure_name": result["state"].get("procedure_name"),
                "medication_name": result["state"].get("medication_name"),
                "missing_fields": result["state"].get("missing_fields", [])
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversation/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id: str):
    """Get conversation state and history"""
    try:
        if conversation_id not in conversation_states:
            return jsonify({"error": "Conversation not found"}), 404
        
        state = conversation_states[conversation_id]
        
        return jsonify({
            "conversation_id": conversation_id,
            "messages": state["messages"],
            "collected_info": {
                "member_id": state.get("member_id"),
                "date_of_birth": state.get("date_of_birth"),
                "procedure_name": state.get("procedure_name"),
                "medication_name": state.get("medication_name"),
                "service_type": state.get("service_type")
            },
            "eligibility_determined": state.get("eligibility_determined", False),
            "api_response": state.get("api_response")
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversation/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    try:
        if conversation_id in conversation_states:
            del conversation_states[conversation_id]
            return jsonify({"message": "Conversation deleted"}), 200
        else:
            return jsonify({"error": "Conversation not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/test-members", methods=["GET"])
def get_test_members():
    """Get list of test member IDs for testing"""
    try:
        mock_api = MockEligibilityAPI()
        members = mock_api.get_available_members()
        
        return jsonify({
            "test_members": members,
            "note": "These are test member IDs you can use for testing"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/direct-eligibility-check", methods=["POST"])
def direct_eligibility_check():
    """
    Direct eligibility check (bypassing conversation)
    For testing purposes
    
    Request body:
    {
        "member_id": "MB123456",
        "date_of_birth": "1985-03-15",
        "procedure_code": "99213" (optional),
        "ndc_code": "00002-7510-01" (optional)
    }
    """
    try:
        data = request.get_json()
        
        mock_api = MockEligibilityAPI()
        result = mock_api.check_eligibility(data)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Starting Insurance Eligibility Agent API...")
    print(f"OpenAI API Key configured: {'Yes' if OPENAI_API_KEY != 'your-api-key-here' else 'No - Please set OPENAI_API_KEY'}")
    app.run(debug=True, host="0.0.0.0", port=5000)
