"""
Database Manager for AI Discord Bot
Handles conversation contexts, user data, and RAG knowledge base storage
"""

import sqlite3
import json
import asyncio
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import os
import numpy as np
from pathlib import Path

# For vector embeddings (we'll use a simple TF-IDF approach initially)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation"""
    id: Optional[int] = None
    context_id: str = ""
    role: str = ""  # 'user' or 'assistant'
    content: str = ""
    timestamp: float = 0.0
    model_used: str = ""
    is_nsfw: bool = False
    user_id: str = ""
    guild_id: Optional[str] = None
    channel_id: str = ""

@dataclass
class KnowledgeEntry:
    """Represents a knowledge base entry for RAG"""
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    category: str = ""
    tags: List[str] = None
    embedding: Optional[List[float]] = None
    created_at: float = 0.0
    updated_at: float = 0.0
    source: str = ""
    user_id: Optional[str] = None  # If user-specific knowledge

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.embedding is None:
            self.embedding = []

@dataclass
class UserContext:
    """User-specific context and preferences"""
    user_id: str = ""
    preferred_model: str = ""
    conversation_style: str = "friendly"  # friendly, professional, casual, etc.
    memory_duration_days: int = 7
    rag_enabled: bool = True
    custom_knowledge: List[str] = None
    last_active: float = 0.0

    def __post_init__(self):
        if self.custom_knowledge is None:
            self.custom_knowledge = []

class DatabaseManager:
    """Manages all database operations for the Discord bot"""
    
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.knowledge_embeddings = None
        self.knowledge_texts = []
        self.knowledge_entries = []
        
        # Initialize database
        self._init_database()
        self._load_knowledge_embeddings()
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    model_used TEXT,
                    is_nsfw BOOLEAN DEFAULT FALSE,
                    user_id TEXT NOT NULL,
                    guild_id TEXT,
                    channel_id TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Knowledge base table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    tags TEXT,  -- JSON array of tags
                    embedding BLOB,  -- Pickled embedding vector
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    source TEXT DEFAULT 'manual',
                    user_id TEXT
                )
            ''')
            
            # User contexts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_contexts (
                    user_id TEXT PRIMARY KEY,
                    preferred_model TEXT,
                    conversation_style TEXT DEFAULT 'friendly',
                    memory_duration_days INTEGER DEFAULT 7,
                    rag_enabled BOOLEAN DEFAULT TRUE,
                    custom_knowledge TEXT,  -- JSON array
                    last_active REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Context summaries table (for long-term memory)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS context_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    key_points TEXT,  -- JSON array of key points
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_context_id ON conversations(context_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_base(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_user_id ON knowledge_base(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_context_summaries_context_id ON context_summaries(context_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_context_summaries_expires_at ON context_summaries(expires_at)')
            
            conn.commit()
    
    def _load_knowledge_embeddings(self):
        """Load knowledge base embeddings for RAG"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, content, embedding FROM knowledge_base WHERE embedding IS NOT NULL')
                rows = cursor.fetchall()
                
                if rows:
                    self.knowledge_texts = []
                    self.knowledge_entries = []
                    
                    for row in rows:
                        entry_id, content, embedding_blob = row
                        self.knowledge_texts.append(content)
                        embedding = pickle.loads(embedding_blob) if embedding_blob else []
                        self.knowledge_entries.append({
                            'id': entry_id,
                            'content': content,
                            'embedding': embedding
                        })
                    
                    # Fit vectorizer and create embeddings
                    if self.knowledge_texts:
                        self.knowledge_embeddings = self.vectorizer.fit_transform(self.knowledge_texts)
        except Exception as e:
            print(f"Error loading knowledge embeddings: {e}")
            self.knowledge_embeddings = None
    
    def save_conversation_turn(self, turn: ConversationTurn) -> int:
        """Save a conversation turn to the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversations 
                (context_id, role, content, timestamp, model_used, is_nsfw, user_id, guild_id, channel_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                turn.context_id, turn.role, turn.content, turn.timestamp,
                turn.model_used, turn.is_nsfw, turn.user_id, turn.guild_id, turn.channel_id
            ))
            return cursor.lastrowid
    
    def get_conversation_history(self, context_id: str, limit: int = 20) -> List[ConversationTurn]:
        """Get conversation history for a context"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, context_id, role, content, timestamp, model_used, is_nsfw, user_id, guild_id, channel_id
                FROM conversations 
                WHERE context_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (context_id, limit))
            
            rows = cursor.fetchall()
            return [ConversationTurn(
                id=row[0], context_id=row[1], role=row[2], content=row[3],
                timestamp=row[4], model_used=row[5], is_nsfw=bool(row[6]),
                user_id=row[7], guild_id=row[8], channel_id=row[9]
            ) for row in reversed(rows)]
    
    def get_user_conversations(self, user_id: str, limit: int = 50) -> List[ConversationTurn]:
        """Get recent conversations for a user across all contexts"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, context_id, role, content, timestamp, model_used, is_nsfw, user_id, guild_id, channel_id
                FROM conversations 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            rows = cursor.fetchall()
            return [ConversationTurn(
                id=row[0], context_id=row[1], role=row[2], content=row[3],
                timestamp=row[4], model_used=row[5], is_nsfw=bool(row[6]),
                user_id=row[7], guild_id=row[8], channel_id=row[9]
            ) for row in rows]
    
    def save_knowledge_entry(self, entry: KnowledgeEntry) -> int:
        """Save a knowledge base entry"""
        # Generate embedding
        if entry.content:
            embedding = self._generate_embedding(entry.content)
            entry.embedding = embedding.tolist()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO knowledge_base 
                (title, content, category, tags, embedding, created_at, updated_at, source, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.title, entry.content, entry.category,
                json.dumps(entry.tags), pickle.dumps(entry.embedding) if entry.embedding else None,
                entry.created_at, entry.updated_at, entry.source, entry.user_id
            ))
            return cursor.lastrowid
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate TF-IDF embedding for text"""
        if not hasattr(self, '_temp_vectorizer'):
            self._temp_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            # Fit on existing knowledge if available
            if self.knowledge_texts:
                self._temp_vectorizer.fit(self.knowledge_texts)
        
        try:
            embedding = self._temp_vectorizer.transform([text]).toarray()[0]
            return embedding
        except:
            # Fallback to simple word count if TF-IDF fails
            return np.zeros(1000)
    
    def search_knowledge(self, query: str, user_id: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search knowledge base using RAG"""
        if not self.knowledge_embeddings is not None or not self.knowledge_texts:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            # Calculate similarities
            similarities = cosine_similarity([query_embedding], self.knowledge_embeddings)[0]
            
            # Get top results
            top_indices = np.argsort(similarities)[::-1][:limit]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    entry = self.knowledge_entries[idx]
                    results.append({
                        'id': entry['id'],
                        'content': entry['content'],
                        'similarity': float(similarities[idx]),
                        'title': self._get_knowledge_title(entry['id'])
                    })
            
            return results
        except Exception as e:
            print(f"Error in knowledge search: {e}")
            return []
    
    def _get_knowledge_title(self, entry_id: int) -> str:
        """Get title for a knowledge entry"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT title FROM knowledge_base WHERE id = ?', (entry_id,))
            row = cursor.fetchone()
            return row[0] if row else "Untitled"
    
    def save_user_context(self, context: UserContext):
        """Save or update user context"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_contexts 
                (user_id, preferred_model, conversation_style, memory_duration_days, 
                 rag_enabled, custom_knowledge, last_active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                context.user_id, context.preferred_model, context.conversation_style,
                context.memory_duration_days, context.rag_enabled,
                json.dumps(context.custom_knowledge), context.last_active,
                datetime.now().timestamp()
            ))
    
    def get_user_context(self, user_id: str) -> Optional[UserContext]:
        """Get user context"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, preferred_model, conversation_style, memory_duration_days,
                       rag_enabled, custom_knowledge, last_active
                FROM user_contexts WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            if row:
                return UserContext(
                    user_id=row[0],
                    preferred_model=row[1] or "",
                    conversation_style=row[2] or "friendly",
                    memory_duration_days=row[3] or 7,
                    rag_enabled=bool(row[4]),
                    custom_knowledge=json.loads(row[5]) if row[5] else [],
                    last_active=row[6] or 0.0
                )
            return None
    
    def create_context_summary(self, context_id: str, user_id: str, summary: str, key_points: List[str]):
        """Create a context summary for long-term memory"""
        expires_at = datetime.now().timestamp() + (7 * 24 * 3600)  # 7 days
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO context_summaries 
                (context_id, user_id, summary, key_points, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                context_id, user_id, summary, json.dumps(key_points),
                datetime.now().timestamp(), expires_at
            ))
    
    def get_context_summaries(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active context summaries for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT context_id, summary, key_points, created_at
                FROM context_summaries 
                WHERE user_id = ? AND expires_at > ?
                ORDER BY created_at DESC
            ''', (user_id, datetime.now().timestamp()))
            
            rows = cursor.fetchall()
            return [{
                'context_id': row[0],
                'summary': row[1],
                'key_points': json.loads(row[2]) if row[2] else [],
                'created_at': row[3]
            } for row in rows]
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old conversation data and expired summaries"""
        cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete old conversations
            cursor.execute('DELETE FROM conversations WHERE timestamp < ?', (cutoff_time,))
            
            # Delete expired summaries
            cursor.execute('DELETE FROM context_summaries WHERE expires_at < ?', (datetime.now().timestamp(),))
            
            conn.commit()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Conversation stats
            cursor.execute('SELECT COUNT(*) FROM conversations')
            stats['total_conversations'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM conversations')
            stats['unique_users'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT context_id) FROM conversations')
            stats['unique_contexts'] = cursor.fetchone()[0]
            
            # Knowledge base stats
            cursor.execute('SELECT COUNT(*) FROM knowledge_base')
            stats['knowledge_entries'] = cursor.fetchone()[0]
            
            # Recent activity
            cursor.execute('SELECT COUNT(*) FROM conversations WHERE timestamp > ?', 
                         ((datetime.now() - timedelta(days=1)).timestamp(),))
            stats['conversations_last_24h'] = cursor.fetchone()[0]
            
            return stats

# Global database manager instance
db_manager = DatabaseManager()
