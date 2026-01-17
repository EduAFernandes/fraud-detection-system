"""
Test OpenAI API Connection
Run this to verify your OpenAI API key is working
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Fix encoding for Windows
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

def test_openai_connection():
    """Test OpenAI API connection and key validity"""

    print("\n" + "="*70)
    print("🧪 TESTING OPENAI API CONNECTION")
    print("="*70)

    print("\n🧪 Test 1: Check API key is set")
    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        print("\n💡 Fix:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your OpenAI API key to .env")
        print("   3. Format: OPENAI_API_KEY=sk-...")
        return

    if not api_key.startswith('sk-'):
        print(f"⚠️ API key format looks incorrect: {api_key[:10]}...")
        print("   OpenAI keys should start with 'sk-'")
    else:
        print(f"✅ API key found: {api_key[:10]}...{api_key[-4:]}")

    print("\n🧪 Test 2: Try importing OpenAI library")
    try:
        import openai
        print("✅ OpenAI library imported successfully")
        print(f"   Version: {openai.__version__}")
    except ImportError as e:
        print(f"❌ OpenAI library not installed: {e}")
        print("\n💡 Fix:")
        print("   pip install openai")
        return

    print("\n🧪 Test 3: Make test API call")
    print("   ⚠️ This will consume a small amount of OpenAI credits")
    print("   Sending: 'Say hello in 3 words'")

    try:
        # Set the API key
        openai.api_key = api_key

        # Make a minimal test call
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say hello in 3 words"}
            ],
            max_tokens=10
        )

        message = response.choices[0].message.content
        print(f"✅ API call successful!")
        print(f"   Response: '{message}'")
        print(f"   Model: {response.model}")
        print(f"   Tokens used: {response.usage.total_tokens}")

    except openai.AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("\n💡 Fix:")
        print("   1. Verify your API key at https://platform.openai.com/api-keys")
        print("   2. Make sure the key is active and has credits")
        print("   3. Update OPENAI_API_KEY in .env file")
        return

    except openai.RateLimitError as e:
        print(f"❌ Rate limit exceeded: {e}")
        print("\n💡 Fix:")
        print("   1. Wait a few moments and try again")
        print("   2. Check your rate limits at https://platform.openai.com/account/limits")
        return

    except openai.APIError as e:
        print(f"❌ OpenAI API error: {e}")
        return

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "="*70)
    print("✅ ALL OPENAI CONNECTION TESTS PASSED!")
    print("="*70)

    print("\n💡 Your OpenAI API is configured correctly!")
    print("   You can now run tests that use AI agents:")
    print("   - python tests/test_agents.py")
    print("   - python tests/test_fraud_orchestrator.py")

if __name__ == "__main__":
    test_openai_connection()
