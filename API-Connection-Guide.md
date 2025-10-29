# API Connection Guide for Multi-Model LLM System

This guide will help you connect all the various AI APIs to make your Discord bot fully functional.

## 🔑 Required API Keys

### 1. OpenAI API (GPT Models)
**Required for:** GPT-4o, GPT-4o-mini, GPT-3.5-turbo

**Steps:**
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to "API Keys" in the left sidebar
4. Click "Create new secret key"
5. Copy the key (starts with `sk-`)
6. Add to `config.py`:
   ```python
   OPENAI_API_KEY = "sk-your_key_here"
   ```

**Cost:** Pay-per-use, very affordable for testing
**Free Tier:** $5 credit for new accounts

### 2. Google Gemini API (Gemini Models)
**Required for:** Gemini 2.0 Flash, Gemini 1.5 Flash, Gemini Pro

**Steps:**
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API Key" in the left sidebar
4. Create a new API key
5. Copy the key (starts with `AIza`)
6. Add to `config.py`:
   ```python
   GEMINI_API_KEY = "AIza_your_key_here"
   ```

**Cost:** Free tier available, then pay-per-use
**Free Tier:** 15 requests per minute, 1M tokens per day

### 3. Anthropic API (Claude Models)
**Required for:** Claude 3.5 Sonnet, Claude 3 Haiku

**Steps:**
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign up for an account
3. Navigate to "API Keys"
4. Create a new API key
5. Copy the key (starts with `sk-ant-`)
6. Add to `config.py`:
   ```python
   ANTHROPIC_API_KEY = "sk-ant-your_key_here"
   ```

**Cost:** Pay-per-use
**Free Tier:** $5 credit for new accounts

### 4. OpenRouter API (Multiple Providers)
**Required for:** Llama, Mistral, and other models

**Steps:**
1. Go to [OpenRouter](https://openrouter.ai/)
2. Sign up for an account
3. Go to "Keys" in the dashboard
4. Create a new API key
5. Copy the key (starts with `sk-or-`)
6. Add to `config.py`:
   ```python
   OPENROUTER_API_KEY = "sk-or-your_key_here"
   ```

**Cost:** Pay-per-use, often cheaper than direct APIs
**Free Tier:** Some free models available

## 🔧 Configuration Setup

### Update config.py

Add all your API keys to `config.py`:

```python
# AI Model API Keys
OPENAI_API_KEY = "sk-your_openai_key_here"
GEMINI_API_KEY = "AIza_your_gemini_key_here"
ANTHROPIC_API_KEY = "sk-ant-your_anthropic_key_here"
OPENROUTER_API_KEY = "sk-or-your_openrouter_key_here"

# Optional: Additional API configurations
OPENROUTER_SITE_URL = "https://your-website.com"  # Optional
OPENROUTER_APP_NAME = "AI Discord Bot"
```

### Environment Variables (Recommended for Production)

For security, use environment variables instead of hardcoding keys:

```python
import os

# Load from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
```

Create a `.env` file:
```
OPENAI_API_KEY=sk-your_openai_key_here
GEMINI_API_KEY=AIza_your_gemini_key_here
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here
OPENROUTER_API_KEY=sk-or-your_openrouter_key_here
```

## 🚀 Testing API Connections

### 1. Test Individual APIs

Create a test script to verify each API:

```python
# test_apis.py
import asyncio
from api_handler import get_openai_response, get_gemini_response
from model_manager import model_manager

async def test_apis():
    test_prompt = "Hello! Please respond with 'API working' to confirm connection."
    
    print("Testing OpenAI API...")
    openai_response = await get_openai_response(test_prompt, safe=True)
    print(f"OpenAI: {openai_response}")
    
    print("\nTesting Gemini API...")
    gemini_response = await get_gemini_response(test_prompt, safe=True)
    print(f"Gemini: {gemini_response}")
    
    print("\nTesting Model Manager...")
    response, model_used = await model_manager.get_chat_response(
        prompt=test_prompt,
        user_id="test_user",
        is_nsfw=False
    )
    print(f"Model Manager: {response} (used: {model_used})")

if __name__ == "__main__":
    asyncio.run(test_apis())
```

### 2. Run Health Check

Use the Discord command:
```
!modelhealth
```

Or test via web dashboard at http://localhost:5000

## 🔌 API Integration Implementation

### Update api_handler.py

Add the missing API handlers:

```python
# Add to api_handler.py

async def get_anthropic_response(prompt: str, safe: bool, history: Optional[List[Dict[str, str]]] = None, system_override: Optional[str] = None) -> Optional[str]:
    """Call Anthropic Claude API if configured."""
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY.strip() == "":
        return None
    
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        system_msg = (
            "You are a helpful assistant. Keep responses safe for work."
            if safe
            else "You are a helpful assistant. Be direct but adhere to safety policies."
        )
        if system_override:
            system_msg = system_override
        
        # Build messages
        messages = []
        if history:
            for turn in history:
                messages.append({
                    "role": turn["role"],
                    "content": turn["content"]
                })
        messages.append({"role": "user", "content": prompt})
        
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            system=system_msg,
            messages=messages
        )
        
        return response.content[0].text if response.content else None
        
    except Exception as e:
        print(f"[Anthropic] Error: {e}")
        return None

async def get_openrouter_response(prompt: str, safe: bool, history: Optional[List[Dict[str, str]]] = None, system_override: Optional[str] = None, model: str = "meta-llama/llama-3.1-70b-instruct") -> Optional[str]:
    """Call OpenRouter API for various models."""
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == "":
        return None
    
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": OPENROUTER_SITE_URL or "https://interactdevelopments.me",
            "X-Title": OPENROUTER_APP_NAME or "AI Discord Bot"
        }
        
        system_msg = (
            "You are a helpful assistant. Keep responses safe for work."
            if safe
            else "You are a helpful assistant. Be direct but adhere to safety policies."
        )
        if system_override:
            system_msg = system_override
        
        messages = [{"role": "system", "content": system_msg}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                return data["choices"][0]["message"]["content"] if data.get("choices") else None
                
    except Exception as e:
        print(f"[OpenRouter] Error: {e}")
        return None
```

### Update model_manager.py

Update the model manager to use the new API handlers:

```python
# Update the _try_model method in model_manager.py

async def _try_model(self, model_id: str, prompt: str, is_nsfw: bool, history: Optional[List[Dict[str, str]]] = None, system_override: Optional[str] = None) -> Optional[str]:
    """Try to get response from a specific model"""
    if model_id not in self.models:
        return None
    
    model = self.models[model_id]
    start_time = time.time()
    
    try:
        # Route to appropriate API handler based on provider
        if model.provider == ModelProvider.OPENAI:
            response = await get_openai_response(prompt, safe=not is_nsfw, history=history, system_override=system_override)
        elif model.provider == ModelProvider.GEMINI:
            response = await get_gemini_response(prompt, safe=not is_nsfw, history=history, system_override=system_override)
        elif model.provider == ModelProvider.ANTHROPIC:
            response = await get_anthropic_response(prompt, safe=not is_nsfw, history=history, system_override=system_override)
        elif model.provider == ModelProvider.OPENROUTER:
            response = await get_openrouter_response(prompt, safe=not is_nsfw, history=history, system_override=system_override, model=model_id)
        else:
            return None
        
        if response:
            response_time = time.time() - start_time
            self._update_model_stats(model_id, True, response_time)
            return response
        else:
            self._update_model_stats(model_id, False, time.time() - start_time)
            return None
            
    except Exception as e:
        print(f"Error with model {model_id}: {e}")
        self._update_model_stats(model_id, False, time.time() - start_time)
        return None
```

## 📦 Install Additional Dependencies

Update `requirements.txt`:

```
discord.py>=2.3.0
openai>=1.45.0
google-generativeai>=0.7.2
anthropic>=0.7.0
spotipy>=2.24.0
wavelink>=3.4.1
aiohttp>=3.9.5
flask>=2.3.0
python-dotenv>=1.0.0
```

Install the new dependencies:
```bash
pip install anthropic python-dotenv
```

## 🔒 Security Best Practices

### 1. Never Commit API Keys
Add to `.gitignore`:
```
config.py
.env
*.key
secrets/
```

### 2. Use Environment Variables
```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
```

### 3. Rate Limiting
Implement rate limiting to avoid API quota issues:

```python
import asyncio
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
    
    async def wait_if_needed(self, api_name: str, max_requests: int = 60, window: int = 60):
        now = time.time()
        # Remove old requests
        self.requests[api_name] = [req_time for req_time in self.requests[api_name] if now - req_time < window]
        
        if len(self.requests[api_name]) >= max_requests:
            sleep_time = window - (now - self.requests[api_name][0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.requests[api_name].append(now)

rate_limiter = RateLimiter()
```

## 🧪 Testing Your Setup

### 1. Start the System
```bash
python start_bot.py
```

### 2. Test Discord Commands
```
!model
!models
!model gpt-4o-mini
!chat Hello, test the API connection
```

### 3. Test Web Dashboard
- Go to http://localhost:5000
- Login with demo/demo
- Select different models
- Test model comparison

### 4. Check Logs
Monitor the console for any API errors or connection issues.

## 🚨 Troubleshooting

### Common Issues:

**"API key not found"**
- Check that API keys are correctly set in config.py
- Verify the keys are valid and active

**"Model not responding"**
- Check API quotas and limits
- Verify model names are correct
- Check internet connection

**"Rate limit exceeded"**
- Implement rate limiting
- Reduce concurrent requests
- Check API usage in provider dashboards

**"Import errors"**
- Install missing dependencies: `pip install -r requirements.txt`
- Check Python version compatibility

### Debug Mode
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Monitoring API Usage

### Track Usage in Dashboard
The web dashboard shows:
- Token usage per model
- Cost per request
- Response times
- Error rates

### API Provider Dashboards
Monitor usage in each provider's dashboard:
- [OpenAI Usage](https://platform.openai.com/usage)
- [Google AI Studio](https://aistudio.google.com/)
- [Anthropic Console](https://console.anthropic.com/)
- [OpenRouter Dashboard](https://openrouter.ai/)

## 🎯 Next Steps

1. **Set up API keys** for all providers you want to use
2. **Test each API** individually to ensure they work
3. **Configure rate limiting** to avoid quota issues
4. **Monitor usage** to control costs
5. **Set up alerts** for API failures or quota limits

Your multi-model LLM system is now ready to use with full API integration!

