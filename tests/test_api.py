"""
Test Script for Insurance Eligibility Agent API
Tests various scenarios and edge cases
"""
import requests
import json
from datetime import datetime


API_BASE_URL = "http://localhost:5000/api"


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def test_health_check():
    """Test the health check endpoint"""
    print_section("Test 1: Health Check")
    
    response = requests.get(f"{API_BASE_URL.replace('/api', '')}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    print("✓ Health check passed")


def test_get_test_members():
    """Test getting test member IDs"""
    print_section("Test 2: Get Test Members")
    
    response = requests.get(f"{API_BASE_URL}/test-members")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Available Test Members:")
    for member in data["test_members"]:
        print(f"  - {member['member_id']}: {member['name']} ({member['status']})")
    
    assert response.status_code == 200
    print("✓ Test members retrieved")


def test_direct_eligibility_check():
    """Test direct eligibility API call"""
    print_section("Test 3: Direct Eligibility Check")
    
    test_request = {
        "member_id": "MB123456",
        "date_of_birth": "1985-03-15",
        "procedure_code": "70553"
    }
    
    print(f"Request: {json.dumps(test_request, indent=2)}")
    
    response = requests.post(
        f"{API_BASE_URL}/direct-eligibility-check",
        json=test_request
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    print("✓ Direct eligibility check passed")


def test_conversation_flow():
    """Test full conversation flow"""
    print_section("Test 4: Conversation Flow")
    
    # Start conversation
    print("Step 1: Starting conversation...")
    start_response = requests.post(
        f"{API_BASE_URL}/conversation/start",
        json={"initial_message": "Is patient MB123456 eligible for an MRI?"}
    )
    
    assert start_response.status_code == 200
    start_data = start_response.json()
    conversation_id = start_data["conversation_id"]
    
    print(f"Conversation ID: {conversation_id}")
    print(f"Agent Response: {start_data['response']}")
    print(f"Eligibility Determined: {start_data.get('eligibility_determined', False)}")
    
    # Continue conversation with DOB
    print("\nStep 2: Providing date of birth...")
    continue_response = requests.post(
        f"{API_BASE_URL}/conversation/{conversation_id}/message",
        json={"message": "The patient's date of birth is March 15, 1985"}
    )
    
    assert continue_response.status_code == 200
    continue_data = continue_response.json()
    
    print(f"Agent Response: {continue_data['response']}")
    print(f"Eligibility Determined: {continue_data.get('eligibility_determined', False)}")
    
    if continue_data.get('api_response'):
        print(f"\nAPI Response Summary:")
        api_resp = continue_data['api_response']
        print(f"  Status: {api_resp.get('eligibility_status')}")
        if 'service_specific' in api_resp:
            service = api_resp['service_specific']
            print(f"  Procedure: {service.get('procedure_name')}")
            print(f"  Covered: {service.get('covered')}")
            print(f"  Requires Auth: {service.get('requires_prior_authorization')}")
    
    # Get conversation history
    print("\nStep 3: Getting conversation history...")
    history_response = requests.get(
        f"{API_BASE_URL}/conversation/{conversation_id}"
    )
    
    assert history_response.status_code == 200
    history_data = history_response.json()
    
    print(f"Total messages: {len(history_data['messages'])}")
    print(f"Collected info: {json.dumps(history_data['collected_info'], indent=2)}")
    
    print("✓ Conversation flow test passed")


def test_pharmacy_eligibility():
    """Test pharmacy/medication eligibility"""
    print_section("Test 5: Pharmacy Eligibility")
    
    test_request = {
        "member_id": "MB789012",
        "date_of_birth": "1990-07-22",
        "service_type": "pharmacy",
        "ndc_code": "50090-3568-00"  # Humira
    }
    
    print(f"Request: {json.dumps(test_request, indent=2)}")
    
    response = requests.post(
        f"{API_BASE_URL}/direct-eligibility-check",
        json=test_request
    )
    
    print(f"\nStatus Code: {response.status_code}")
    data = response.json()
    
    if 'pharmacy_specific' in data:
        pharmacy = data['pharmacy_specific']
        print(f"\nMedication: {pharmacy.get('medication_name')}")
        print(f"Covered: {pharmacy.get('covered')}")
        print(f"Tier: {pharmacy.get('formulary_tier')}")
        print(f"Copay: ${pharmacy.get('copay_amount', 0):.2f}")
        print(f"Requires Auth: {pharmacy.get('requires_prior_authorization')}")
    
    print("✓ Pharmacy eligibility test passed")


def test_inactive_coverage():
    """Test inactive coverage scenario"""
    print_section("Test 6: Inactive Coverage")
    
    test_request = {
        "member_id": "MB345678",
        "date_of_birth": "1975-11-30"
    }
    
    print(f"Request: {json.dumps(test_request, indent=2)}")
    
    response = requests.post(
        f"{API_BASE_URL}/direct-eligibility-check",
        json=test_request
    )
    
    print(f"\nStatus Code: {response.status_code}")
    data = response.json()
    
    print(f"Eligibility Status: {data.get('eligibility_status')}")
    print(f"Coverage Status: {data.get('coverage_info', {}).get('status')}")
    print(f"Message: {data.get('message')}")
    
    assert data.get('eligibility_status') == 'not_eligible'
    print("✓ Inactive coverage test passed")


def test_error_handling():
    """Test error handling"""
    print_section("Test 7: Error Handling")
    
    # Test missing member ID
    print("Testing missing member ID...")
    response = requests.post(
        f"{API_BASE_URL}/direct-eligibility-check",
        json={"date_of_birth": "1985-03-15"}
    )
    
    assert response.status_code == 200
    data = response.json()
    print(f"Response: {data.get('message')}")
    assert data.get('status') == 'error'
    
    # Test invalid member ID
    print("\nTesting invalid member ID...")
    response = requests.post(
        f"{API_BASE_URL}/direct-eligibility-check",
        json={
            "member_id": "INVALID123",
            "date_of_birth": "1985-03-15"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    print(f"Response: {data.get('message')}")
    assert data.get('status') == 'error'
    
    print("✓ Error handling test passed")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("  INSURANCE ELIGIBILITY AGENT - API TESTS")
    print("="*70)
    print(f"Testing API at: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        test_health_check()
        test_get_test_members()
        test_direct_eligibility_check()
        test_conversation_flow()
        test_pharmacy_eligibility()
        test_inactive_coverage()
        test_error_handling()
        
        print_section("ALL TESTS PASSED ✓")
        print("The Insurance Eligibility Agent API is working correctly!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {str(e)}")
        return False
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to API. Make sure the Flask backend is running on port 5000")
        print("   Run: cd backend && python app.py")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
