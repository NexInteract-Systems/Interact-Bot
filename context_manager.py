"""
Context Manager for AI Discord Bot
Handles conversation contexts with RAG (Retrieval-Augmented Generation) capabilities
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from database_manager import db_manager, ConversationTurn, KnowledgeEntry, UserContext
import json

@dataclass
class RAGContext:
    """Context with RAG-enhanced information"""
    conversation_history: List[Dict[str, str]]
    relevant_knowledge: List[Dict[str, Any]]
    user_context: Optional[UserContext]
    context_summary: Optional[str] = None
    key_points: List[str] = None

class ContextManager:
    """Manages conversation contexts with RAG capabilities"""
    
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.db = db_manager
    
    def _context_id_from_interaction(self, interaction) -> str:
        """Generate context ID from Discord interaction"""
        if interaction.guild:
            return f"guild_{interaction.guild.id}_channel_{interaction.channel.id}"
        else:
            return f"dm_{interaction.user.id}"
    
    def _context_id_from_message(self, message) -> str:
        """Generate context ID from Discord message"""
        if message.guild:
            return f"guild_{message.guild.id}_channel_{message.channel.id}"
        else:
            return f"dm_{message.author.id}"
    
    async def get_rag_context(
        self, 
        context_id: str, 
        user_id: str, 
        current_message: str,
        is_nsfw: bool = False
    ) -> RAGContext:
        """Get RAG-enhanced context for a conversation"""
        
        # Get conversation history from database
        conversation_turns = self.db.get_conversation_history(context_id, self.max_turns)
        conversation_history = [
            {"role": turn.role, "content": turn.content} 
            for turn in conversation_turns
        ]
        
        # Get user context
        user_context = self.db.get_user_context(user_id)
        if not user_context:
            # Create default user context
            user_context = UserContext(
                user_id=user_id,
                preferred_model="",
                conversation_style="friendly",
                memory_duration_days=7,
                rag_enabled=True,
                last_active=time.time()
            )
            self.db.save_user_context(user_context)
        
        # Update last active time
        user_context.last_active = time.time()
        self.db.save_user_context(user_context)
        
        # Get relevant knowledge using RAG
        relevant_knowledge = []
        if user_context.rag_enabled:
            # Search for relevant knowledge
            search_query = self._build_search_query(conversation_history, current_message)
            relevant_knowledge = self.db.search_knowledge(
                query=search_query,
                user_id=user_id,
                limit=3
            )
            
            # Add user-specific custom knowledge
            if user_context.custom_knowledge:
                for custom_knowledge in user_context.custom_knowledge:
                    if any(keyword.lower() in current_message.lower() 
                          for keyword in custom_knowledge.split()):
                        relevant_knowledge.append({
                            'content': custom_knowledge,
                            'similarity': 0.8,  # High similarity for custom knowledge
                            'title': 'Custom Knowledge',
                            'id': 'custom'
                        })
        
        # Get context summaries for long-term memory
        context_summaries = self.db.get_context_summaries(user_id)
        context_summary = None
        key_points = []
        
        if context_summaries:
            # Combine recent summaries
            recent_summaries = context_summaries[:3]  # Last 3 summaries
            context_summary = " ".join([s['summary'] for s in recent_summaries])
            key_points = []
            for summary in recent_summaries:
                key_points.extend(summary['key_points'])
        
        return RAGContext(
            conversation_history=conversation_history,
            relevant_knowledge=relevant_knowledge,
            user_context=user_context,
            context_summary=context_summary,
            key_points=key_points
        )
    
    def _build_search_query(self, conversation_history: List[Dict[str, str]], current_message: str) -> str:
        """Build search query from conversation history and current message"""
        # Extract key terms from recent conversation
        recent_messages = conversation_history[-6:]  # Last 6 messages
        query_terms = [current_message]
        
        for msg in recent_messages:
            if msg['role'] == 'user':
                # Extract important words from user messages
                words = msg['content'].split()
                # Take first few words as they're usually most important
                query_terms.extend(words[:5])
        
        return " ".join(query_terms)
    
    async def save_conversation_turn(
        self,
        context_id: str,
        user_id: str,
        role: str,
        content: str,
        model_used: str,
        is_nsfw: bool = False,
        guild_id: Optional[str] = None,
        channel_id: str = ""
    ):
        """Save a conversation turn to the database"""
        turn = ConversationTurn(
            context_id=context_id,
            role=role,
            content=content,
            timestamp=time.time(),
            model_used=model_used,
            is_nsfw=is_nsfw,
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id
        )
        
        self.db.save_conversation_turn(turn)
    
    async def create_context_summary(self, context_id: str, user_id: str, conversation_history: List[Dict[str, str]]):
        """Create a summary of the conversation for long-term memory"""
        if len(conversation_history) < 4:  # Don't summarize short conversations
            return
        
        # Simple summarization - in a real implementation, you'd use an LLM
        user_messages = [msg['content'] for msg in conversation_history if msg['role'] == 'user']
        assistant_messages = [msg['content'] for msg in conversation_history if msg['role'] == 'assistant']
        
        # Extract key topics
        key_points = []
        for msg in user_messages[-3:]:  # Last 3 user messages
            words = msg.split()
            if len(words) > 3:
                key_points.append(" ".join(words[:3]))
        
        # Create summary
        summary = f"User discussed: {', '.join(key_points[:3])}. "
        if assistant_messages:
            summary += f"Assistant provided responses about: {', '.join(assistant_messages[-1].split()[:5])}"
        
        self.db.create_context_summary(context_id, user_id, summary, key_points)
    
    async def add_knowledge_entry(
        self,
        title: str,
        content: str,
        category: str = "general",
        tags: List[str] = None,
        user_id: Optional[str] = None,
        source: str = "manual"
    ) -> int:
        """Add a knowledge entry to the RAG system"""
        if tags is None:
            tags = []
        
        entry = KnowledgeEntry(
            title=title,
            content=content,
            category=category,
            tags=tags,
            created_at=time.time(),
            updated_at=time.time(),
            source=source,
            user_id=user_id
        )
        
        entry_id = self.db.save_knowledge_entry(entry)
        
        # Reload embeddings
        self.db._load_knowledge_embeddings()
        
        return entry_id
    
    async def update_user_context(
        self,
        user_id: str,
        preferred_model: Optional[str] = None,
        conversation_style: Optional[str] = None,
        memory_duration_days: Optional[int] = None,
        rag_enabled: Optional[bool] = None,
        custom_knowledge: Optional[List[str]] = None
    ):
        """Update user context settings"""
        user_context = self.db.get_user_context(user_id)
        if not user_context:
            user_context = UserContext(user_id=user_id, last_active=time.time())
        
        if preferred_model is not None:
            user_context.preferred_model = preferred_model
        if conversation_style is not None:
            user_context.conversation_style = conversation_style
        if memory_duration_days is not None:
            user_context.memory_duration_days = memory_duration_days
        if rag_enabled is not None:
            user_context.rag_enabled = rag_enabled
        if custom_knowledge is not None:
            user_context.custom_knowledge = custom_knowledge
        
        user_context.last_active = time.time()
        self.db.save_user_context(user_context)
    
    def get_user_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get conversation statistics for a user"""
        conversations = self.db.get_user_conversations(user_id, limit=100)
        
        stats = {
            'total_messages': len(conversations),
            'user_messages': len([c for c in conversations if c.role == 'user']),
            'assistant_messages': len([c for c in conversations if c.role == 'assistant']),
            'unique_contexts': len(set(c.context_id for c in conversations)),
            'nsfw_messages': len([c for c in conversations if c.is_nsfw]),
            'models_used': list(set(c.model_used for c in conversations if c.model_used))
        }
        
        return stats
    
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old conversation data"""
        self.db.cleanup_old_data(days)
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return self.db.get_database_stats()

# Global context manager instance
context_manager = ContextManager()
