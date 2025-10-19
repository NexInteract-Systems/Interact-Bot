import asyncio
from typing import Optional, List, Dict
import io
import base64
from config import OPENAI_API_KEY, GEMINI_API_KEY
from config import OPENROUTER_API_KEY, OPENROUTER_SITE_URL, OPENROUTER_APP_NAME, OPENROUTER_IMAGE_MODEL
import json

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None  # type: ignore

try:
    import google.generativeai as genai
except Exception:
    genai = None  # type: ignore

try:
    import aiohttp
except Exception:
    aiohttp = None  # type: ignore

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


async def get_openai_response(prompt: str, safe: bool, history: Optional[List[Dict[str, str]]] = None, system_override: Optional[str] = None) -> Optional[str]:
    """Call OpenAI Chat Completions API if configured.

    Returns a string on success, or None if not configured or on error.
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY.strip() == "":
        return None
    if AsyncOpenAI is None:
        return None

    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        system_msg = (
            "You are a helpful, friendly assistant. Keep responses safe for work."
            if safe
            else "You are a helpful assistant that can be more direct, but never unsafe or illegal."
        )
        if system_override:
            system_msg = system_override
        # Order should be: system, prior turns, latest user
        prior = history[:] if history else []
        messages = [{"role": "system", "content": system_msg}] + prior + [
            {"role": "user", "content": prompt},
        ]
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=300,
        )
        content = response.choices[0].message.content if response.choices else None
        return content or None
    except Exception as e:
        print(f"[OpenAI] Error: {e}")
        return None


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


async def generate_image_with_openrouter(prompt: str, size: str = "1024x1024") -> Optional[bytes]:
    """Generate an image via OpenRouter Images API using Gemini 2.5 Flash Image.

    Returns raw image bytes on success, else None.
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == "":
        return None
    if aiohttp is None:
        print("[OpenRouter Image] aiohttp not installed. Please add aiohttp to requirements.txt")
        return None

    url = "https://openrouter.ai/api/v1/images"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    if OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = OPENROUTER_SITE_URL
    if OPENROUTER_APP_NAME:
        headers["X-Title"] = OPENROUTER_APP_NAME

    body = {
        "model": OPENROUTER_IMAGE_MODEL or "google/gemini-2.5-flash-image-preview",
        "prompt": prompt,
        "size": size,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=json.dumps(body), timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"[OpenRouter Image] HTTP {resp.status}: {text}")
                    return None
                data = await resp.json()
                images = data.get("data") or []
                if not images:
                    return None
                first = images[0]
                if "b64_json" in first and first["b64_json"]:
                    try:
                        return base64.b64decode(first["b64_json"])
                    except Exception:
                        return None
                img_url = first.get("url")
                if img_url:
                    async with session.get(img_url) as img_resp:
                        if img_resp.status == 200:
                            return await img_resp.read()
                        else:
                            print(f"[OpenRouter Image] URL fetch failed {img_resp.status}")
                            return None
                return None
    except Exception as e:
        print(f"[OpenRouter Image] Error: {e}")
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
    # Try Gemini first if configured, then OpenAI
    gemini_text = await get_gemini_response(prompt, safe=not is_nsfw, history=history, system_override=system_override)
    if gemini_text:
        return gemini_text

    openai_text = await get_openai_response(prompt, safe=not is_nsfw, history=history, system_override=system_override)
    if openai_text:
        return openai_text

    # Fallback to placeholders
    if is_nsfw:
        return await get_nsfw_response(prompt)
    else:
        return await get_sfw_response(prompt)
