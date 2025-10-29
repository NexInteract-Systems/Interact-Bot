#!/usr/bin/env python3
"""
API Connection Test Script
Tests all configured AI APIs to ensure they're working properly
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_handler import (
    get_openai_response, 
    get_gemini_response, 
    get_anthropic_response,
    get_openrouter_response
)
from model_manager import model_manager
from config import OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY

async def test_api(api_name: str, api_function, prompt: str, **kwargs):
    """Test a single API"""
    print(f"\n🧪 Testing {api_name}...")
    try:
        response = await api_function(prompt, **kwargs)
        if response:
            print(f"✅ {api_name}: SUCCESS")
            print(f"   Response: {response[:100]}{'...' if len(response) > 100 else ''}")
            return True
        else:
            print(f"❌ {api_name}: No response received")
            return False
    except Exception as e:
        print(f"❌ {api_name}: ERROR - {str(e)}")
        return False

async def test_model_manager():
    """Test the model manager"""
    print(f"\n🧪 Testing Model Manager...")
    try:
        response, model_used = await model_manager.get_chat_response(
            prompt="Hello! Please respond with 'Model Manager working' to confirm.",
            user_id="test_user",
            is_nsfw=False
        )
        if response:
            print(f"✅ Model Manager: SUCCESS")
            print(f"   Model Used: {model_used}")
            print(f"   Response: {response[:100]}{'...' if len(response) > 100 else ''}")
            return True
        else:
            print(f"❌ Model Manager: No response received")
            return False
    except Exception as e:
        print(f"❌ Model Manager: ERROR - {str(e)}")
        return False

async def test_health_check():
    """Test model health check"""
    print(f"\n🧪 Testing Health Check...")
    try:
        await model_manager.health_check()
        stats = model_manager.get_model_stats()
        
        print(f"✅ Health Check: SUCCESS")
        print(f"   Total Models: {stats['total_models']}")
        print(f"   Online Models: {stats['online_models']}")
        print(f"   Offline Models: {stats['offline_models']}")
        print(f"   Degraded Models: {stats['degraded_models']}")
        
        # Show online models
        online_models = [name for name, info in stats['models'].items() if info['status'] == 'online']
        if online_models:
            print(f"   Online: {', '.join(online_models)}")
        
        return True
    except Exception as e:
        print(f"❌ Health Check: ERROR - {str(e)}")
        return False

def check_api_keys():
    """Check if API keys are configured"""
    print("🔑 Checking API Key Configuration...")
    
    apis = [
        ("OpenAI", OPENAI_API_KEY),
        ("Gemini", GEMINI_API_KEY),
        ("Anthropic", ANTHROPIC_API_KEY),
        ("OpenRouter", OPENROUTER_API_KEY)
    ]
    
    configured_apis = []
    for name, key in apis:
        if key and key.strip():
            print(f"✅ {name}: Configured")
            configured_apis.append(name)
        else:
            print(f"❌ {name}: Not configured")
    
    return configured_apis

async def main():
    """Main test function"""
    print("=" * 60)
    print("🚀 AI Discord Bot - API Connection Test")
    print("=" * 60)
    
    # Check API keys
    configured_apis = check_api_keys()
    
    if not configured_apis:
        print("\n❌ No API keys configured! Please set up at least one API key in config.py")
        print("\n📖 See API-Connection-Guide.md for setup instructions")
        return
    
    print(f"\n📊 Testing {len(configured_apis)} configured APIs...")
    
    # Test prompt
    test_prompt = "Hello! Please respond with 'API working' to confirm the connection is successful."
    
    # Test individual APIs
    results = []
    
    if "OpenAI" in configured_apis:
        result = await test_api("OpenAI", get_openai_response, test_prompt, safe=True)
        results.append(("OpenAI", result))
    
    if "Gemini" in configured_apis:
        result = await test_api("Gemini", get_gemini_response, test_prompt, safe=True)
        results.append(("Gemini", result))
    
    if "Anthropic" in configured_apis:
        result = await test_api("Anthropic", get_anthropic_response, test_prompt, safe=True)
        results.append(("Anthropic", result))
    
    if "OpenRouter" in configured_apis:
        result = await test_api("OpenRouter", get_openrouter_response, test_prompt, safe=True)
        results.append(("OpenRouter", result))
    
    # Test model manager
    manager_result = await test_model_manager()
    results.append(("Model Manager", manager_result))
    
    # Test health check
    health_result = await test_health_check()
    results.append(("Health Check", health_result))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    successful = 0
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name:15} {status}")
        if success:
            successful += 1
    
    print(f"\nOverall: {successful}/{total} tests passed")
    
    if successful == total:
        print("🎉 All tests passed! Your multi-model system is ready to use.")
        print("\n🚀 Next steps:")
        print("   1. Start the bot: python start_bot.py")
        print("   2. Test Discord commands: !model, !models")
        print("   3. Access dashboard: http://localhost:5000")
    else:
        print("⚠️  Some tests failed. Please check your API keys and configuration.")
        print("\n🔧 Troubleshooting:")
        print("   1. Verify API keys are correct in config.py")
        print("   2. Check API quotas and limits")
        print("   3. Ensure internet connection is working")
        print("   4. See API-Connection-Guide.md for detailed setup")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check your configuration and try again.")

