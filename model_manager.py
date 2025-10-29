"""
Multi-Model LLM Manager for Discord Bot
Handles multiple LLM providers with user preferences and failover
"""

import asyncio
import json
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os

# Import existing API handlers
from api_handler import (
    get_gemini_response, 
    get_openrouter_response,
    generate_image_with_openrouter
)
from content_filter import content_filter

# Import subscription manager
from subscription_manager import subscription_manager

class ModelProvider(Enum):
    """Available LLM providers"""
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"

class ModelStatus(Enum):
    """Model availability status"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

@dataclass
class ModelInfo:
    """Information about a specific model"""
    id: str
    name: str
    provider: ModelProvider
    description: str
    max_tokens: int
    cost_per_1k_tokens: float
    supports_images: bool = False
    supports_functions: bool = False
    status: ModelStatus = ModelStatus.UNKNOWN
    last_used: Optional[float] = None
    usage_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0

@dataclass
class UserPreferences:
    """User's model preferences"""
    user_id: str
    preferred_model: str
    fallback_models: List[str]
    custom_settings: Dict[str, Any]
    last_updated: float

class ModelManager:
    """Centralized manager for all LLM models"""
    
    def __init__(self, config_file: str = "model_config.json", user_prefs_file: str = "user_preferences.json"):
        self.config_file = config_file
        self.user_prefs_file = user_prefs_file
        self.models: Dict[str, ModelInfo] = {}
        self.user_preferences: Dict[str, UserPreferences] = {}
        self.model_stats: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default models
        self._initialize_default_models()
        self._load_config()
        self._load_user_preferences()
    
    def _initialize_default_models(self):
        """Initialize default model configurations"""
        default_models = [
            ModelInfo(
                id="google/gemma-3n-e2b-it:free",
                name="Google Gemma 3n 2B (free)",
                provider=ModelProvider.OPENROUTER,
                description="Google's efficient 2B parameter Gemma model - fast, free, and capable",
                max_tokens=8192,
                cost_per_1k_tokens=0.0,  # Free model
                supports_functions=True
            ),
            ModelInfo(
                id="nvidia/nemotron-nano-9b-v2:free",
                name="NVIDIA Nemotron Nano 9B V2",
                provider=ModelProvider.OPENROUTER,
                description="NVIDIA's free 9B parameter model - excellent fallback option when other APIs are down",
                max_tokens=4096,
                cost_per_1k_tokens=0.0,  # Free model
                supports_functions=False
            ),
            ModelInfo(
                id="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
                name="Dolphin Mistral 24B Venice Edition",
                provider=ModelProvider.OPENROUTER,
                description="Advanced 24B parameter Mistral model - excellent for complex reasoning, creative tasks, and adult conversations (NSFW mode). Blocks drug-related content while allowing appropriate adult topics.",
                max_tokens=8192,
                cost_per_1k_tokens=0.0,  # Free model
                supports_functions=True
            )
        ]
        
        for model in default_models:
            self.models[model.id] = model
    
    def _load_config(self):
        """Load model configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    # Update model configurations
                    for model_id, model_data in data.get('models', {}).items():
                        if model_id in self.models:
                            for key, value in model_data.items():
                                if hasattr(self.models[model_id], key):
                                    # Convert string values back to enums if needed
                                    if key == 'status' and isinstance(value, str):
                                        try:
                                            value = ModelStatus(value)
                                        except ValueError:
                                            value = ModelStatus.UNKNOWN
                                    elif key == 'provider' and isinstance(value, str):
                                        try:
                                            value = ModelProvider(value)
                                        except ValueError:
                                            continue  # Skip invalid provider
                                    setattr(self.models[model_id], key, value)
            except Exception as e:
                print(f"Error loading model config: {e}")
    
    def _save_config(self):
        """Save model configuration to file"""
        try:
            data = {
                'models': {
                    model_id: {
                        'status': model.status.value,
                        'last_used': model.last_used,
                        'usage_count': model.usage_count,
                        'error_count': model.error_count,
                        'avg_response_time': model.avg_response_time
                    }
                    for model_id, model in self.models.items()
                }
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving model config: {e}")
    
    def _load_user_preferences(self):
        """Load user preferences from file"""
        if os.path.exists(self.user_prefs_file):
            try:
                with open(self.user_prefs_file, 'r') as f:
                    data = json.load(f)
                    for user_id, prefs_data in data.items():
                        self.user_preferences[user_id] = UserPreferences(**prefs_data)
            except Exception as e:
                print(f"Error loading user preferences: {e}")
    
    def _save_user_preferences(self):
        """Save user preferences to file"""
        try:
            data = {
                user_id: asdict(prefs)
                for user_id, prefs in self.user_preferences.items()
            }
            with open(self.user_prefs_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving user preferences: {e}")
    
    def get_user_preference(self, user_id: str) -> Optional[str]:
        """Get user's preferred model"""
        prefs = self.user_preferences.get(user_id)
        if prefs and prefs.preferred_model in self.models:
            return prefs.preferred_model
        return self.get_default_model()
    
    def find_model_by_name(self, model_name: str) -> Optional[str]:
        """Find model ID by name (case-insensitive, handles spaces and special chars)"""
        # First try exact match
        if model_name in self.models:
            return model_name
        
        # Try case-insensitive match
        for model_id in self.models.keys():
            if model_id.lower() == model_name.lower():
                return model_id
        
        # Try matching by display name
        for model_id, model in self.models.items():
            if model.name.lower() == model_name.lower():
                return model_id
        
        # Try matching transformed name (spaces to dashes, lowercase)
        transformed_name = model_name.lower().replace(' ', '-')
        for model_id in self.models.keys():
            if model_id.lower() == transformed_name:
                return model_id
        
        # Try partial matching for complex model IDs
        for model_id, model in self.models.items():
            # Check if the model name contains the search term
            if model_name.lower() in model.name.lower() or model_name.lower() in model_id.lower():
                return model_id
        
        return None

    def set_user_preference(self, user_id: str, model_id: str) -> bool:
        """Set user's preferred model"""
        # Try to find the model by name first
        actual_model_id = self.find_model_by_name(model_id)
        if not actual_model_id:
            return False
        
        model_id = actual_model_id
        
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreferences(
                user_id=user_id,
                preferred_model=model_id,
                fallback_models=[],
                custom_settings={},
                last_updated=time.time()
            )
        else:
            self.user_preferences[user_id].preferred_model = model_id
            self.user_preferences[user_id].last_updated = time.time()
        
        self._save_user_preferences()
        return True
    
    def get_default_model(self) -> str:
        """Get the default model (first available model)"""
        for model_id, model in self.models.items():
            if model.status == ModelStatus.ONLINE:
                return model_id
        return "google/gemma-3n-e2b-it:free"  # Fallback to Google Gemma
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get list of available models"""
        return [model for model in self.models.values() if model.status == ModelStatus.ONLINE]
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        return self.models.get(model_id)
    
    def update_model_status(self, model_id: str, status: ModelStatus):
        """Update model status"""
        if model_id in self.models:
            self.models[model_id].status = status
            self._save_config()
    
    async def get_chat_response(
        self, 
        prompt: str, 
        user_id: str, 
        is_nsfw: bool = False,
        history: Optional[List[Dict[str, str]]] = None,
        system_override: Optional[str] = None,
        preferred_model: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Get chat response using user's preferred model or specified model
        
        Returns:
            Tuple of (response_text, model_used)
        """
        # For NSFW mode, use Google Gemma as the primary model
        if is_nsfw:
            model_id = "google/gemma-3n-e2b-it:free"
        else:
            # Determine which model to use for SFW mode
            model_id = preferred_model or self.get_user_preference(user_id)
        
        # Check if user can use the requested model
        is_premium_model = model_id in subscription_manager.get_premium_models()
        is_ultra_premium_model = model_id in subscription_manager.get_ultra_premium_models()
        
        if not subscription_manager.can_use_premium_model(user_id, model_id):
            # Check if user needs ultra-premium for this model
            if is_ultra_premium_model:
                return "❌ You need an Ultra-Premium subscription ($99.90 per 3 months) to use Grok AI models. Use `/subscribe` to upgrade!", "error"
            # User can't use premium model, try to find a free alternative
            free_models = [m for m in self.models.keys() if m not in subscription_manager.get_premium_models() and m not in subscription_manager.get_ultra_premium_models()]
            if free_models:
                model_id = free_models[0]  # Use first available free model
            else:
                return "❌ You need a premium subscription to use this model. Use `/subscribe` to upgrade!", "error"
        
        # Check if user can send a message (including NSFW limits)
        if not subscription_manager.can_send_message(user_id, is_premium_model or is_ultra_premium_model, is_nsfw):
            usage = subscription_manager.get_daily_usage(user_id)
            if is_ultra_premium_model:
                return "❌ You need an Ultra-Premium subscription ($99.90 per 3 months) to use this uncensored model. Use `/subscribe` to upgrade!", "error"
            elif is_premium_model:
                return "❌ You need a premium subscription to use premium models. Use `/subscribe` to upgrade!", "error"
            elif is_nsfw:
                remaining = subscription_manager.NSFW_DAILY_LIMIT - usage.nsfw_messages_used
                return f"❌ You've reached your daily NSFW limit of {subscription_manager.NSFW_DAILY_LIMIT} messages. You have {remaining} NSFW messages remaining. Upgrade to ultra-premium for truly uncensored access!", "error"
            else:
                remaining = subscription_manager.FREE_DAILY_LIMIT - usage.messages_used
                return f"❌ You've reached your daily limit of {subscription_manager.FREE_DAILY_LIMIT} messages. You have {remaining} messages remaining. Upgrade to premium for unlimited access!", "error"
        
        # Check if prompt should be blocked before processing
        should_block, block_reason = content_filter.should_block_content(prompt, model_id, is_nsfw)
        if should_block:
            return f"❌ {block_reason}", "blocked"
        
        # Try the preferred model first
        print(f"[ModelManager] Trying preferred model: {model_id}")
        response = await self._try_model(model_id, prompt, is_nsfw, history, system_override)
        if response:
            print(f"[ModelManager] Success with {model_id}: {len(response)} chars")
            # Apply content filtering to the response
            filtered_response = content_filter.filter_response(response, model_id, is_nsfw)
            
            self._update_model_stats(model_id, True, time.time())
            # Record usage
            subscription_manager.record_message_usage(user_id, is_premium_model or is_ultra_premium_model, is_nsfw)
            return filtered_response, model_id
        else:
            print(f"[ModelManager] Failed with {model_id}, trying fallbacks...")
        
        # Try fallback models
        fallback_models = self._get_fallback_models(model_id)
        print(f"[ModelManager] Fallback models: {fallback_models}")
        for fallback_id in fallback_models:
            print(f"[ModelManager] Trying fallback: {fallback_id}")
            # Check if fallback model is premium or ultra-premium
            fallback_is_premium = fallback_id in subscription_manager.get_premium_models()
            fallback_is_ultra_premium = fallback_id in subscription_manager.get_ultra_premium_models()
            if not subscription_manager.can_use_premium_model(user_id, fallback_id):
                print(f"[ModelManager] Skipping {fallback_id} - premium model, user not authorized")
                continue
                
            response = await self._try_model(fallback_id, prompt, is_nsfw, history, system_override)
            if response:
                print(f"[ModelManager] Success with fallback {fallback_id}: {len(response)} chars")
                # Apply content filtering to the response
                filtered_response = content_filter.filter_response(response, fallback_id, is_nsfw)
                
                self._update_model_stats(fallback_id, True, time.time())
                # Record usage
                subscription_manager.record_message_usage(user_id, fallback_is_premium or fallback_is_ultra_premium, is_nsfw)
                return filtered_response, fallback_id
            else:
                print(f"[ModelManager] Failed with fallback {fallback_id}")
        
        # Final fallback to placeholder
        return await self._get_fallback_response(prompt, is_nsfw), "fallback"
    
    async def _try_model(
        self, 
        model_id: str, 
        prompt: str, 
        is_nsfw: bool,
        history: Optional[List[Dict[str, str]]] = None,
        system_override: Optional[str] = None
    ) -> Optional[str]:
        """Try to get response from a specific model"""
        if model_id not in self.models:
            print(f"[ModelManager] Model {model_id} not found in models")
            return None
        
        model = self.models[model_id]
        start_time = time.time()
        print(f"[ModelManager] Calling {model.provider} API for {model_id}")
        
        try:
            # Route to appropriate API handler based on provider
            if model.provider == ModelProvider.GEMINI:
                response = await get_gemini_response(prompt, safe=not is_nsfw, history=history, system_override=system_override)
            elif model.provider == ModelProvider.OPENROUTER:
                response = await get_openrouter_response(prompt, safe=not is_nsfw, history=history, system_override=system_override, model=model_id)
            else:
                print(f"[ModelManager] Unknown provider {model.provider} for {model_id}")
                return None
            
            if response:
                response_time = time.time() - start_time
                print(f"[ModelManager] {model_id} returned {len(response)} chars in {response_time:.2f}s")
                self._update_model_stats(model_id, True, response_time)
                return response
            else:
                print(f"[ModelManager] {model_id} returned None/empty response")
                self._update_model_stats(model_id, False, time.time() - start_time)
                return None
                
        except Exception as e:
            print(f"[ModelManager] Exception with model {model_id}: {e}")
            import traceback
            print(f"[ModelManager] Traceback: {traceback.format_exc()}")
            self._update_model_stats(model_id, False, time.time() - start_time)
            return None
    
    
    async def _get_fallback_response(self, prompt: str, is_nsfw: bool) -> str:
        """Get fallback response when all models fail"""
        if is_nsfw:
            return f"I'm having trouble connecting to my AI models right now. Your message was: '{prompt}'. Please try again later!"
        else:
            return f"I'm experiencing some technical difficulties. I received your message about '{prompt}' but couldn't process it right now. Please try again in a moment!"
    
    def _get_fallback_models(self, preferred_model: str) -> List[str]:
        """Get list of fallback models in order of preference"""
        # Fallback order prioritizing truly free models and reliability
        fallback_order = [
            "google/gemma-3n-e2b-it:free",  # Primary Google Gemma model
            "nvidia/nemotron-nano-9b-v2:free",  # Free NVIDIA model as primary fallback
            "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",  # Free Dolphin Mistral as secondary fallback
        ]
        
        # Remove the preferred model from fallbacks
        fallbacks = [m for m in fallback_order if m != preferred_model and m in self.models]
        return fallbacks
    
    def _update_model_stats(self, model_id: str, success: bool, response_time: float):
        """Update model usage statistics"""
        if model_id not in self.models:
            return
        
        model = self.models[model_id]
        model.last_used = time.time()
        model.usage_count += 1
        
        if success:
            # Update average response time
            if model.avg_response_time == 0:
                model.avg_response_time = response_time
            else:
                model.avg_response_time = (model.avg_response_time + response_time) / 2
        else:
            model.error_count += 1
        
        # Update status based on error rate
        error_rate = model.error_count / model.usage_count if model.usage_count > 0 else 0
        if error_rate > 0.5:
            model.status = ModelStatus.DEGRADED
        elif error_rate > 0.8:
            model.status = ModelStatus.OFFLINE
        else:
            model.status = ModelStatus.ONLINE
        
        self._save_config()
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get comprehensive model statistics"""
        stats = {
            'total_models': len(self.models),
            'online_models': len([m for m in self.models.values() if m.status == ModelStatus.ONLINE]),
            'offline_models': len([m for m in self.models.values() if m.status == ModelStatus.OFFLINE]),
            'degraded_models': len([m for m in self.models.values() if m.status == ModelStatus.DEGRADED]),
            'models': {}
        }
        
        for model_id, model in self.models.items():
            stats['models'][model_id] = {
                'name': model.name,
                'provider': model.provider.value,
                'status': model.status.value,
                'usage_count': model.usage_count,
                'error_count': model.error_count,
                'error_rate': model.error_count / model.usage_count if model.usage_count > 0 else 0,
                'avg_response_time': model.avg_response_time,
                'last_used': model.last_used
            }
        
        return stats
    
    async def health_check(self):
        """Perform health check on all models"""
        print("Performing model health check...")
        
        test_prompt = "Hello, this is a health check. Please respond with 'OK'."
        
        for model_id, model in self.models.items():
            try:
                response = await self._try_model(model_id, test_prompt, False, None, None)
                if response:
                    print(f"✅ {model.name} ({model_id}) - Online")
                    self.update_model_status(model_id, ModelStatus.ONLINE)
                else:
                    print(f"❌ {model.name} ({model_id}) - Offline")
                    self.update_model_status(model_id, ModelStatus.OFFLINE)
            except Exception as e:
                print(f"❌ {model.name} ({model_id}) - Error: {e}")
                self.update_model_status(model_id, ModelStatus.OFFLINE)
            
            # Small delay between checks
            await asyncio.sleep(0.5)

# Global model manager instance
model_manager = ModelManager()
