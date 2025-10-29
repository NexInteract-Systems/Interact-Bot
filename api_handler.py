import asyncio
from typing import Optional, List, Dict
import io
import base64
from config import GEMINI_API_KEY
from config import OPENROUTER_API_KEY, OPENROUTER_SITE_URL, OPENROUTER_APP_NAME, OPENROUTER_IMAGE_MODEL
import json

# Import BentoML image generation
try:
    from bentoml_image_service import generate_image_with_bentoml
    BENTOML_AVAILABLE = True
except ImportError:
    BENTOML_AVAILABLE = False
    print("[API Handler] BentoML not available. Install bentoml, diffusers, and torch to enable local image generation.")

# OpenAI removed - using OpenRouter for all models

try:
    import google.generativeai as genai
except Exception:
    genai = None  # type: ignore

try:
    import aiohttp
except Exception:
    aiohttp = None

# Anthropic removed - using OpenRouter for all models

# In a real application, you would use libraries like 'requests' or 'aiohttp'
# to make calls to actual external APIs.

async def get_sfw_response(prompt: str) -> str:
    """
    Placeholder for a Safe-for-Work chat API call.
    This simulates a friendly and helpful AI.
    """
    print(f"[SFW API] Received prompt: {prompt}")
    # Simulate API call delay
    await asyncio.sleep(0.5)
    
    responses = [
        f"That's a great question about '{prompt}'! I'm here to help with that.",
        f"I've processed your query about '{prompt}'. Here is some safe and friendly information.",
        f"Thinking about '{prompt}'... I can certainly provide a standard response.",
    ]
    import random
    return random.choice(responses)

async def get_nsfw_response(prompt: str) -> str:
    """
    Placeholder for a Not-Safe-for-Work (18+) chat API call.
    This simulates a more unrestricted AI.
    NOTE: This is a placeholder. You would need to integrate a real API
    that allows for 18+ content.
    """
    print(f"[NSFW API] Received prompt: {prompt}")
    # Simulate API call delay
    await asyncio.sleep(0.5)

    responses = [
        f"Alright, you asked about '{prompt}'. Here's the unrestricted take on it.",
        f"Regarding '{prompt}', the 18+ mode allows for a more direct answer.",
        f"Since we're in 18+ mode, let's talk about '{prompt}' without the usual filters."
    ]
    import random
    return random.choice(responses)


# OpenAI function removed - using OpenRouter for all models


async def get_gemini_response(prompt: str, safe: bool, history: Optional[List[Dict[str, str]]] = None, system_override: Optional[str] = None) -> Optional[str]:
    """Call Gemini 2.5 Flash via google-generativeai if configured.

    Returns a string on success, or None on error/not configured.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY.strip() == "":
        return None
    if genai is None:
        return None

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Use a stable model name supported by the SDK; try newest first and fallback
        preferred_models = ["gemini-2.0-flash", "gemini-1.5-flash"]
        system_instruction = (
            "You are a helpful assistant. Keep responses safe for work. Do NOT prefix replies with 'Assistant:' or any role labels."
            if safe
            else "You are a helpful assistant. Be direct but adhere to safety policies. Do NOT prefix replies with role labels."
        )
        if system_override:
            system_instruction = system_override
        last_err = None
        for model_name in preferred_models:
            try:
                model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
                # Build structured contents with roles
                contents = []
                if history:
                    for turn in history:
                        role = turn.get("role", "user")
                        content = turn.get("content", "")
                        contents.append({"role": role, "parts": [content]})
                contents.append({"role": "user", "parts": [prompt]})
                # google-generativeai is sync; run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: model.generate_content(contents)
                )
                if hasattr(result, "text") and result.text:
                    return result.text
            except Exception as inner:
                last_err = inner
                continue
        if last_err:
            print(f"[Gemini] Fallback after error: {last_err}")
        return None
        if hasattr(result, "text") and result.text:
            return result.text
        # Fallback: concatenate parts if present
        try:
            parts = []
            for cand in getattr(result, "candidates", []) or []:
                for part in getattr(cand, "content", {}).get("parts", []) or []:
                    if isinstance(part, dict) and "text" in part:
                        parts.append(part["text"]) 
            return "\n".join(parts) if parts else None
        except Exception:
            return None
    except Exception as e:
        print(f"[Gemini] Error: {e}")
        return None


async def generate_image_with_gemini(prompt: str) -> Optional[bytes]:
    """Generate an image using Gemini/Imagen via google-generativeai SDK.

    Returns raw image bytes if successful, else None.
    """
    if genai is None:
        return None
    if not GEMINI_API_KEY or GEMINI_API_KEY.strip() == "":
        return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)

        # Discover available models and pick an Imagen model that supports image generation
        try:
            models = genai.list_models()
        except Exception as list_err:
            print(f"[Gemini Image] list_models failed: {list_err}")
            models = []

        selected_model = None
        for m in models or []:
            name = getattr(m, "name", "") or ""
            methods = set(getattr(m, "supported_generation_methods", []) or [])
            if "imagen" in name and ("generateContent" in methods or "create" in methods or "generateImages" in methods):
                selected_model = name
                break

        # Fallback to known public names (if the account has access)
        if not selected_model:
            for fallback in ["models/imagen-3.0-generate", "models/imagen-3.0"]:
                try:
                    # Probe by trying to instantiate; if it fails, continue
                    genai.GenerativeModel(fallback)
                    selected_model = fallback
                    break
                except Exception:
                    continue

        if not selected_model:
            print("[Gemini Image] No accessible Imagen model found for this API key.")
            return None

        model = genai.GenerativeModel(selected_model)
        loop = asyncio.get_event_loop()
        # Prefer generate_content if available
        if hasattr(model, "generate_content"):
            result = await loop.run_in_executor(None, lambda: model.generate_content({"text": prompt}))
        elif hasattr(model, "generate_images"):
            result = await loop.run_in_executor(None, lambda: model.generate_images(prompt=prompt))
        else:
            print(f"[Gemini Image] Model {selected_model} does not support image generation methods.")
            return None

        # Extract image bytes
        img_bytes = None
        if hasattr(result, "images") and result.images:
            img = result.images[0]
            if hasattr(img, "data") and isinstance(img.data, (bytes, bytearray)):
                img_bytes = bytes(img.data)
            elif hasattr(img, "base64"):
                try:
                    img_bytes = base64.b64decode(img.base64)
                except Exception:
                    img_bytes = None

        if img_bytes is None:
            try:
                for cand in getattr(result, "candidates", []) or []:
                    parts = getattr(cand, "content", {}).get("parts", []) or []
                    for part in parts:
                        if isinstance(part, dict) and part.get("inline_data"):
                            data_b64 = part["inline_data"].get("data")
                            if data_b64:
                                img_bytes = base64.b64decode(data_b64)
                                break
                    if img_bytes:
                        break
            except Exception:
                pass

        return img_bytes
    except Exception as e:
        print(f"[Gemini Image] Error: {e}")
        return None


async def generate_image_with_openrouter(prompt: str, size: str = "1024x1024", model: Optional[str] = None) -> Optional[bytes]:
    """Generate an image via OpenRouter using chat/completions endpoint with image generation models.

    Returns raw image bytes on success, else None.
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == "":
        return None
    if aiohttp is None:
        print("[OpenRouter Image] aiohttp not installed. Please add aiohttp to requirements.txt")
        return None

    # Use a model that supports image generation
    image_model = model or OPENROUTER_IMAGE_MODEL or "google/gemini-2.5-flash-image-preview"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_SITE_URL or "https://interactdevelopments.me",
        "X-Title": OPENROUTER_APP_NAME or "AI Discord Bot"
    }

    # For image generation, we need to use the chat/completions endpoint with image generation models
    # and include the modalities parameter
    body = {
        "model": image_model,
        "messages": [
            {
                "role": "user",
                "content": f"Generate an image: {prompt}"
            }
        ],
        "modalities": ["image", "text"],
        "max_tokens": 1000,
        "temperature": 0.7
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"[OpenRouter Image] HTTP {resp.status}: {text}")
                    return None
                
                data = await resp.json()
                
                # Check if response contains image data
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    if "message" in choice:
                        message = choice["message"]
                        
                        # Check for images array in message (OpenRouter format)
                        if "images" in message:
                            images = message["images"]
                            if images and len(images) > 0:
                                img_data = images[0]
                                # Check for direct base64 data
                                if "data" in img_data:
                                    try:
                                        import base64
                                        return base64.b64decode(img_data["data"])
                                    except Exception as e:
                                        print(f"[OpenRouter Image] Error decoding base64: {e}")
                                # Check for image URL
                                elif "image_url" in img_data and "url" in img_data["image_url"]:
                                    img_url = img_data["image_url"]["url"]
                                    async with session.get(img_url) as img_resp:
                                        if img_resp.status == 200:
                                            return await img_resp.read()
                        
                        # Check for image content in the message
                        if "content" in message:
                            content = message["content"]
                            
                            # If content is a string, it might contain image URLs or base64 data
                            if isinstance(content, str):
                                # Look for image URLs in the response
                                import re
                                url_pattern = r'https?://[^\s<>"]+\.(?:png|jpg|jpeg|gif|webp)'
                                urls = re.findall(url_pattern, content)
                                
                                if urls:
                                    # Download the first image URL
                                    async with session.get(urls[0]) as img_resp:
                                        if img_resp.status == 200:
                                            return await img_resp.read()
                                
                                # Look for base64 image data
                                b64_pattern = r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)'
                                b64_match = re.search(b64_pattern, content)
                                if b64_match:
                                    try:
                                        return base64.b64decode(b64_match.group(1))
                                    except Exception:
                                        pass
                
                print(f"[OpenRouter Image] No image data found in response")
                print(f"[OpenRouter Image] Response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                return None
                
    except Exception as e:
        print(f"[OpenRouter Image] Error: {e}")
        return None


async def generate_image_with_bentoml_local(prompt: str, size: str = "512x512") -> Optional[bytes]:
    """Generate an image using BentoML Stable Diffusion (local).
    
    Returns raw image bytes on success, else None.
    """
    if not BENTOML_AVAILABLE:
        print("[BentoML Image] BentoML not available. Install bentoml, diffusers, and torch.")
        return None
    
    try:
        return await generate_image_with_bentoml(prompt, size)
    except Exception as e:
        print(f"[BentoML Image] Error: {e}")
        return None


# Anthropic function removed - using OpenRouter for all models


async def get_openrouter_response(prompt: str, safe: bool, history: Optional[List[Dict[str, str]]] = None, system_override: Optional[str] = None, model: str = "meta-llama/llama-3.1-70b-instruct") -> Optional[str]:
    """Call OpenRouter API for various models.

    Returns a string on success, or None if not configured or on error.
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == "":
        return None
    if aiohttp is None:
        print("[OpenRouter] aiohttp not installed. Please add aiohttp to requirements.txt")
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
        
        # For models that don't support system messages, include system instruction in user message
        messages = []
        if history:
            messages.extend(history)
        
        # Combine system message with user prompt for models that don't support system role
        if system_msg and system_msg != "You are a helpful assistant. Keep responses safe for work.":
            user_content = f"System: {system_msg}\n\nUser: {prompt}"
        else:
            user_content = prompt
            
        messages.append({"role": "user", "content": user_content})
        
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"[OpenRouter] HTTP {resp.status}: {text}")
                    return None
                
                data = await resp.json()
                if data.get("choices") and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    # Handle Unicode characters properly
                    if isinstance(content, str):
                        return content
                return None
                
    except Exception as e:
        print(f"[OpenRouter] Error with model {model}: {e}")
        import traceback
        print(f"[OpenRouter] Traceback: {traceback.format_exc()}")
        return None


async def get_chat_response(prompt: str, is_nsfw: bool, history: Optional[List[Dict[str, str]]] = None, system_override: Optional[str] = None) -> str:
    """
    Gets a chat response from the appropriate API based on the mode.

    Args:
        prompt: The user's message.
        is_nsfw: A boolean indicating if 18+ mode is active.

    Returns:
        A string containing the AI's response.
    """
    # Try OpenRouter first (primary), then Gemini as fallback
    openrouter_text = await get_openrouter_response(prompt, safe=not is_nsfw, history=history, system_override=system_override, model="google/gemma-3n-e2b-it:free")
    if openrouter_text:
        return openrouter_text

    gemini_text = await get_gemini_response(prompt, safe=not is_nsfw, history=history, system_override=system_override)
    if gemini_text:
        return gemini_text

    # Fallback to placeholders
    if is_nsfw:
        return await get_nsfw_response(prompt)
    else:
        return await get_sfw_response(prompt)


async def generate_image_unified(prompt: str, size: str = "1024x1024", model: Optional[str] = None) -> Optional[bytes]:
    """
    Unified image generation function with BentoML as primary method:
    1. BentoML (PRIMARY) - local, free, private, high quality
    2. OpenRouter (fallback) - if API key available
    3. Gemini (fallback) - if API key available
    
    Returns raw image bytes on success, else None.
    """
    print(f"[Image Generation] 🎨 Generating image for prompt: '{prompt}'")
    print(f"[Image Generation] 📏 Size: {size}")
    
    # PRIMARY: Try BentoML first (local, free, private, high quality)
    if BENTOML_AVAILABLE:
        print("[Image Generation] 🚀 PRIMARY: Trying BentoML (local Stable Diffusion)...")
        try:
            bentoml_result = await generate_image_with_bentoml_local(prompt, size)
            if bentoml_result:
                print("[Image Generation] ✅ BentoML generation successful (PRIMARY METHOD)")
                return bentoml_result
            else:
                print("[Image Generation] ❌ BentoML generation failed")
        except Exception as e:
            print(f"[Image Generation] ❌ BentoML error: {e}")
    else:
        print("[Image Generation] ⚠️ BentoML not available - install with: python setup_bentoml.py")
    
    # FALLBACK 1: Try OpenRouter
    print("[Image Generation] 🔄 FALLBACK 1: Trying OpenRouter...")
    try:
        openrouter_result = await generate_image_with_openrouter(prompt, size, model)
        if openrouter_result:
            print("[Image Generation] ✅ OpenRouter generation successful (FALLBACK)")
            return openrouter_result
        else:
            print("[Image Generation] ❌ OpenRouter generation failed")
    except Exception as e:
        print(f"[Image Generation] ❌ OpenRouter error: {e}")
    
    # FALLBACK 2: Try Gemini
    print("[Image Generation] 🔄 FALLBACK 2: Trying Gemini...")
    try:
        gemini_result = await generate_image_with_gemini(prompt)
        if gemini_result:
            print("[Image Generation] ✅ Gemini generation successful (FALLBACK)")
            return gemini_result
        else:
            print("[Image Generation] ❌ Gemini generation failed")
    except Exception as e:
        print(f"[Image Generation] ❌ Gemini error: {e}")
    
    print("[Image Generation] ❌ All image generation methods failed")
    print("[Image Generation] 💡 Tip: Install BentoML for free local generation: python setup_bentoml.py")
    return None
