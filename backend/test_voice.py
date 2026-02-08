"""
Voice System Test Script
Tests the voice components without needing Twilio or phone calls.

Run: python test_voice.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from voice.realtime_handler import OpenAIRealtimeHandler
from voice.call_manager import CallManager
from api.eligibility_api import MockEligibilityAPI
from dotenv import load_dotenv
import asyncio

load_dotenv()


def test_eligibility_api():
    """Test 1: Verify eligibility API works"""
    print("\n" + "="*60)
    print("TEST 1: Eligibility API")
    print("="*60)
    
    api = MockEligibilityAPI()
    
    # Test active member
    result = api.check_eligibility({
        "member_id": "MB123456",
        "date_of_birth": "1985-03-15"
    })
    
    if result["status"] == "success":
        print("✓ API working correctly")
        print(f"  Member: {result['member_info']['name']}")
        print(f"  Status: {result['eligibility_status']}")
    else:
        print("✗ API test failed")
        return False
        
    return True


def test_configuration():
    """Test 2: Verify all required configuration"""
    print("\n" + "="*60)
    print("TEST 2: Configuration")
    print("="*60)
    
    openai_key = os.getenv("OPENAI_API_KEY", "")
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    domain = os.getenv("YOUR_DOMAIN", "")
    
    checks = {
        "OpenAI API Key": openai_key and openai_key != "your-api-key-here",
        "Twilio Account SID": bool(twilio_sid and len(twilio_sid) > 10),
        "Twilio Auth Token": bool(twilio_token and len(twilio_token) > 10),
        "Domain (ngrok)": bool(domain and domain != "your-ngrok-url.ngrok.io")
    }
    
    all_ok = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_ok = False
            
    if not all_ok:
        print("\n⚠️  Some configuration is missing. Update .env file.")
        print("   For testing without Twilio, you only need OPENAI_API_KEY")
        
    return checks["OpenAI API Key"]  # Only require OpenAI for basic tests


async def test_openai_connection():
    """Test 3: Test OpenAI Realtime connection (if API key available)"""
    print("\n" + "="*60)
    print("TEST 3: OpenAI Realtime API Connection")
    print("="*60)
    
    openai_key = os.getenv("OPENAI_API_KEY", "")
    
    if not openai_key or openai_key == "your-api-key-here":
        print("⊘ Skipped - No OpenAI API key configured")
        return True
        
    try:
        print("  Attempting to connect to OpenAI Realtime API...")
        
        handler = OpenAIRealtimeHandler(api_key=openai_key)
        await handler.connect()
        
        print("✓ Successfully connected to OpenAI Realtime API")
        print("  Model: gpt-4o-realtime-preview-2024-10-01")
        
        await handler.close()
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("  Check your OpenAI API key and that you have access to Realtime API")
        return False


def test_imports():
    """Test 4: Verify all imports work"""
    print("\n" + "="*60)
    print("TEST 4: Module Imports")
    print("="*60)
    
    try:
        import twilio
        import websockets
        import aiohttp
        from twilio.twiml.voice_response import VoiceResponse
        
        print("✓ All required packages installed")
        print(f"  twilio: {twilio.__version__}")
        print(f"  websockets: {websockets.__version__}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Missing package: {e}")
        print("  Run: pip install -r requirements_voice.txt")
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  VOICE SYSTEM TEST SUITE")
    print("="*70)
    print("\nTesting voice calling components...")
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: Configuration
    results.append(("Configuration", test_configuration()))
    
    # Test 3: Eligibility API
    results.append(("Eligibility API", test_eligibility_api()))
    
    # Test 4: OpenAI Connection (async)
    openai_ok = await test_openai_connection()
    results.append(("OpenAI Connection", openai_ok))
    
    # Summary
    print("\n" + "="*70)
    print("  SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status:8} {test_name}")
        
    all_passed = all(result[1] for result in results)
    
    print("="*70)
    
    if all_passed:
        print("\n✓ ALL TESTS PASSED!")
        print("\nNext steps:")
        print("  1. Set up ngrok: ngrok http 5002")
        print("  2. Update YOUR_DOMAIN in .env with ngrok URL")
        print("  3. Configure Twilio webhook (see VOICE_SETUP.md)")
        print("  4. Run: python app_voice.py")
        print("  5. Call your Twilio number!")
    else:
        print("\n✗ SOME TESTS FAILED")
        print("\nPlease fix the issues above before proceeding.")
        print("See VOICE_SETUP.md for detailed setup instructions.")
        
    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
