"""
Enhanced Model Manager with RAG Integration
Extends the existing model manager with database-backed contexts and RAG capabilities
"""

import asyncio
import time
from typing import Optional, List, Dict, Any, Tuple
from model_manager import ModelManager, ModelProvider, ModelStatus, ModelInfo
from context_manager import context_manager, RAGContext
from database_manager import db_manager
import json

class EnhancedModelManager(ModelManager):
    """Enhanced model manager with RAG and database integration"""
    
    def __init__(self, config_file: str = "model_config.json", user_prefs_file: str = "user_preferences.json"):
        super().__init__(config_file, user_prefs_file)
        self.context_manager = context_manager
        self.db = db_manager
    
    async def get_chat_response_with_rag(
        self, 
        prompt: str, 
        user_id: str, 
        context_id: str,
        is_nsfw: bool = False,
        guild_id: Optional[str] = None,
        channel_id: str = "",
        preferred_model: Optional[str] = None,
        system_override: Optional[str] = None
    ) -> Tuple[str, str, RAGContext]:
        """
        Get chat response with RAG-enhanced context
        
        Returns:
            Tuple of (response_text, model_used, rag_context)
        """
        # Get RAG-enhanced context
        rag_context = await self.context_manager.get_rag_context(
            context_id=context_id,
            user_id=user_id,
            current_message=prompt,
            is_nsfw=is_nsfw
        )
        
        # Build enhanced prompt with RAG context
        enhanced_prompt = self._build_enhanced_prompt(prompt, rag_context, system_override)
        
        # Get model preference
        model_id = preferred_model or rag_context.user_context.preferred_model or self.get_user_preference(user_id)
        
        # Check subscription limits
        is_premium_model = model_id in self.subscription_manager.get_premium_models()
        is_ultra_premium_model = model_id in self.subscription_manager.get_ultra_premium_models()
        
        if not self.subscription_manager.can_use_premium_model(user_id, model_id):
            # Check if user needs ultra-premium for this model
            if is_ultra_premium_model:
                return "❌ You need an Ultra-Premium subscription ($99.90 per 3 months) to use Grok AI models. Use `/subscribe` to upgrade!", "error", rag_context
            # Check if user needs regular premium
            free_models = [m for m in self.models.keys() if m not in self.subscription_manager.get_premium_models() and m not in self.subscription_manager.get_ultra_premium_models()]
            if free_models:
                model_id = free_models[0]
            else:
                return "❌ You need a premium subscription to use this model. Use `/subscribe` to upgrade!", "error", rag_context
        
        if not self.subscription_manager.can_send_message(user_id, is_premium_model or is_ultra_premium_model, is_nsfw):
            usage = self.subscription_manager.get_daily_usage(user_id)
            if is_ultra_premium_model:
                return "❌ You need an Ultra-Premium subscription ($99.90 per 3 months) to use this uncensored model. Use `/subscribe` to upgrade!", "error", rag_context
            elif is_premium_model:
                return "❌ You need a premium subscription to use premium models. Use `/subscribe` to upgrade!", "error", rag_context
            elif is_nsfw:
                remaining = self.subscription_manager.NSFW_DAILY_LIMIT - usage.nsfw_messages_used
                return f"❌ You've reached your daily NSFW limit of {self.subscription_manager.NSFW_DAILY_LIMIT} messages. You have {remaining} NSFW messages remaining. Upgrade to ultra-premium for truly uncensored access!", "error", rag_context
            else:
                remaining = self.subscription_manager.FREE_DAILY_LIMIT - usage.messages_used
                return f"❌ You've reached your daily limit of {self.subscription_manager.FREE_DAILY_LIMIT} messages. You have {remaining} messages remaining. Upgrade to premium for unlimited access!", "error", rag_context
        
        # Try the preferred model first
        response = await self._try_model_with_rag(
            model_id, enhanced_prompt, is_nsfw, rag_context.conversation_history, system_override
        )
        
        if response:
            self._update_model_stats(model_id, True, time.time())
            self.subscription_manager.record_message_usage(user_id, is_premium_model or is_ultra_premium_model, is_nsfw)
            
            # Save conversation turn
            await self.context_manager.save_conversation_turn(
                context_id=context_id,
                user_id=user_id,
                role="user",
                content=prompt,
                model_used="",
                is_nsfw=is_nsfw,
                guild_id=guild_id,
                channel_id=channel_id
            )
            
            await self.context_manager.save_conversation_turn(
                context_id=context_id,
                user_id=user_id,
                role="assistant",
                content=response,
                model_used=model_id,
                is_nsfw=is_nsfw,
                guild_id=guild_id,
                channel_id=channel_id
            )
            
            return response, model_id, rag_context
        
        # Try fallback models
        fallback_models = self._get_fallback_models(model_id)
        for fallback_id in fallback_models:
            fallback_is_premium = fallback_id in self.subscription_manager.get_premium_models()
            fallback_is_ultra_premium = fallback_id in self.subscription_manager.get_ultra_premium_models()
            if not self.subscription_manager.can_use_premium_model(user_id, fallback_id):
                continue
                
            response = await self._try_model_with_rag(
                fallback_id, enhanced_prompt, is_nsfw, rag_context.conversation_history, system_override
            )
            if response:
                self._update_model_stats(fallback_id, True, time.time())
                self.subscription_manager.record_message_usage(user_id, fallback_is_premium or fallback_is_ultra_premium, is_nsfw)
                
                # Save conversation turn
                await self.context_manager.save_conversation_turn(
                    context_id=context_id,
                    user_id=user_id,
                    role="user",
                    content=prompt,
                    model_used="",
                    is_nsfw=is_nsfw,
                    guild_id=guild_id,
                    channel_id=channel_id
                )
                
                await self.context_manager.save_conversation_turn(
                    context_id=context_id,
                    user_id=user_id,
                    role="assistant",
                    content=response,
                    model_used=fallback_id,
                    is_nsfw=is_nsfw,
                    guild_id=guild_id,
                    channel_id=channel_id
                )
                
                return response, fallback_id, rag_context
        
        # Final fallback
        fallback_response = await self._get_fallback_response(enhanced_prompt, is_nsfw)
        return fallback_response, "fallback", rag_context
    
    def _build_enhanced_prompt(self, prompt: str, rag_context: RAGContext, system_override: Optional[str] = None) -> str:
        """Build enhanced prompt with RAG context"""
        enhanced_parts = []
        
        # Add system context
        if system_override:
            enhanced_parts.append(f"System: {system_override}")
        elif rag_context.user_context:
            style_context = self._get_style_context(rag_context.user_context.conversation_style)
            enhanced_parts.append(f"System: {style_context}")
        
        # Add long-term memory context
        if rag_context.context_summary:
            enhanced_parts.append(f"Previous conversation context: {rag_context.context_summary}")
        
        # Add relevant knowledge
        if rag_context.relevant_knowledge:
            knowledge_text = "Relevant information:\n"
            for knowledge in rag_context.relevant_knowledge[:3]:  # Top 3 most relevant
                knowledge_text += f"- {knowledge['content']}\n"
            enhanced_parts.append(knowledge_text)
        
        # Add conversation history
        if rag_context.conversation_history:
            history_text = "Conversation history:\n"
            for msg in rag_context.conversation_history[-6:]:  # Last 6 messages
                role = "User" if msg['role'] == 'user' else "Assistant"
                history_text += f"{role}: {msg['content']}\n"
            enhanced_parts.append(history_text)
        
        # Add current prompt
        enhanced_parts.append(f"User: {prompt}")
        
        return "\n\n".join(enhanced_parts)
    
    def _get_style_context(self, conversation_style: str) -> str:
        """Get system context based on conversation style"""
        styles = {
            "friendly": "You are a friendly and helpful AI assistant. Be warm, engaging, and conversational.",
            "professional": "You are a professional AI assistant. Be formal, precise, and business-like.",
            "casual": "You are a casual AI assistant. Be relaxed, informal, and easy-going.",
            "technical": "You are a technical AI assistant. Be precise, detailed, and focus on accuracy.",
            "creative": "You are a creative AI assistant. Be imaginative, artistic, and think outside the box."
        }
        return styles.get(conversation_style, styles["friendly"])
    
    async def _try_model_with_rag(
        self, 
        model_id: str, 
        enhanced_prompt: str, 
        is_nsfw: bool,
        history: Optional[List[Dict[str, str]]] = None,
        system_override: Optional[str] = None
    ) -> Optional[str]:
        """Try to get response from a specific model with enhanced prompt"""
        if model_id not in self.models:
            return None
        
        model = self.models[model_id]
        start_time = time.time()
        
        try:
            # For RAG-enhanced prompts, we don't use history as it's already included
            if model.provider == ModelProvider.GEMINI:
                response = await self._get_gemini_response(enhanced_prompt, safe=not is_nsfw)
            elif model.provider == ModelProvider.OPENROUTER:
                response = await self._get_openrouter_response(enhanced_prompt, safe=not is_nsfw, model=model_id)
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
    
    async def _get_gemini_response(self, prompt: str, safe: bool = True) -> Optional[str]:
        """Get response from Gemini API"""
        try:
            from api_handler import get_gemini_response
            return await get_gemini_response(prompt, safe=safe)
        except Exception as e:
            print(f"Gemini API error: {e}")
            return None
    
    async def _get_openrouter_response(self, prompt: str, safe: bool = True, model: str = "google/gemma-3n-e2b-it:free") -> Optional[str]:
        """Get response from OpenRouter API"""
        try:
            from api_handler import get_openrouter_response
            return await get_openrouter_response(prompt, safe=safe, model=model)
        except Exception as e:
            print(f"OpenRouter API error: {e}")
            return None
    
    async def add_knowledge_entry(
        self,
        title: str,
        content: str,
        category: str = "general",
        tags: List[str] = None,
        user_id: Optional[str] = None,
        source: str = "manual"
    ) -> int:
        """Add knowledge entry to RAG system"""
        return await self.context_manager.add_knowledge_entry(
            title, content, category, tags, user_id, source
        )
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferred_model: Optional[str] = None,
        conversation_style: Optional[str] = None,
        memory_duration_days: Optional[int] = None,
        rag_enabled: Optional[bool] = None,
        custom_knowledge: Optional[List[str]] = None
    ):
        """Update user preferences and context"""
        # Update in context manager
        await self.context_manager.update_user_context(
            user_id, preferred_model, conversation_style, 
            memory_duration_days, rag_enabled, custom_knowledge
        )
        
        # Update in model manager
        if preferred_model:
            self.set_user_preference(user_id, preferred_model)
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        model_stats = self.get_model_stats()
        context_stats = self.context_manager.get_user_conversation_stats(user_id)
        db_stats = self.db.get_database_stats()
        
        return {
            'user_stats': context_stats,
            'model_stats': model_stats,
            'database_stats': db_stats
        }
    
    async def create_context_summary(self, context_id: str, user_id: str):
        """Create a summary of the current conversation context"""
        conversations = self.db.get_conversation_history(context_id, 50)
        conversation_history = [
            {"role": turn.role, "content": turn.content} 
            for turn in conversations
        ]
        
        await self.context_manager.create_context_summary(
            context_id, user_id, conversation_history
        )
    
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old data"""
        await self.context_manager.cleanup_old_data(days)

# Global enhanced model manager instance
enhanced_model_manager = EnhancedModelManager()
