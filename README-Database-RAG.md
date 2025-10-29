# AI Discord Bot - Database and RAG System

This document describes the enhanced AI Discord Bot with database-backed conversation contexts and Retrieval-Augmented Generation (RAG) capabilities.

## 🚀 Features

### Database Integration
- **SQLite Database**: Persistent storage for all conversation data
- **User Contexts**: Personalized settings and preferences per user
- **Conversation History**: Long-term memory with configurable retention
- **Knowledge Base**: Searchable knowledge entries for RAG
- **Context Summaries**: Automatic summarization of long conversations

### RAG (Retrieval-Augmented Generation)
- **Vector Embeddings**: TF-IDF based similarity search
- **Knowledge Retrieval**: Automatic retrieval of relevant information
- **Enhanced Prompts**: Context-aware prompt generation
- **User-Specific Knowledge**: Custom knowledge per user
- **Category-Based Organization**: Organized knowledge by categories

## 📁 File Structure

```
ai-discord-bot/
├── database_manager.py          # Core database operations
├── context_manager.py           # Context and RAG management
├── enhanced_model_manager.py    # Enhanced model manager with RAG
├── main_enhanced.py            # Enhanced main bot file
├── migrate_to_database.py      # Migration script
├── test_database_rag.py        # Test suite
├── bot_database.db             # SQLite database (created automatically)
└── README-Database-RAG.md      # This file
```

## 🗄️ Database Schema

### Tables

#### `conversations`
Stores individual conversation turns
- `id`: Primary key
- `context_id`: Unique context identifier
- `role`: 'user' or 'assistant'
- `content`: Message content
- `timestamp`: Unix timestamp
- `model_used`: AI model used for response
- `is_nsfw`: NSFW flag
- `user_id`: Discord user ID
- `guild_id`: Discord guild ID (optional)
- `channel_id`: Discord channel ID

#### `knowledge_base`
Stores knowledge entries for RAG
- `id`: Primary key
- `title`: Knowledge entry title
- `content`: Knowledge content
- `category`: Knowledge category
- `tags`: JSON array of tags
- `embedding`: Pickled vector embedding
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `source`: Source of knowledge
- `user_id`: User-specific knowledge (optional)

#### `user_contexts`
Stores user preferences and settings
- `user_id`: Discord user ID (primary key)
- `preferred_model`: Preferred AI model
- `conversation_style`: Conversation style preference
- `memory_duration_days`: Memory retention period
- `rag_enabled`: RAG feature enabled flag
- `custom_knowledge`: JSON array of custom knowledge
- `last_active`: Last activity timestamp

#### `context_summaries`
Stores conversation summaries for long-term memory
- `id`: Primary key
- `context_id`: Context identifier
- `user_id`: User ID
- `summary`: Conversation summary
- `key_points`: JSON array of key points
- `created_at`: Creation timestamp
- `expires_at`: Expiration timestamp

## 🔧 Setup and Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Migration

```bash
python migrate_to_database.py
```

This will:
- Create the SQLite database
- Migrate existing user preferences
- Create default knowledge base entries
- Test database functionality

### 3. Test the System

```bash
python test_database_rag.py
```

### 4. Start the Enhanced Bot

```bash
python main_enhanced.py
```

## 🎯 Usage

### Slash Commands

#### `/chat <message>`
Chat with the AI bot using RAG-enhanced responses
- Automatically retrieves relevant knowledge
- Maintains conversation context
- Uses user's preferred model and style

#### `/model [model_name]`
Set or view your preferred AI model
- Lists available models if no name provided
- Switches to specified model if name provided

#### `/persona [style]`
Set your conversation style
- Options: friendly, professional, casual, technical, creative
- Affects how the AI responds to you

#### `/rag <title> <content> [category]`
Add knowledge to the bot's memory
- Creates searchable knowledge entries
- Available in future conversations
- Category helps organize knowledge

#### `/stats`
View your conversation statistics
- Total messages sent/received
- Models used
- Context information

### Regular Commands

#### `!chat <message>`
Legacy chat command for backward compatibility

## 🔍 RAG System Details

### How RAG Works

1. **Query Processing**: User message is processed to extract key terms
2. **Knowledge Retrieval**: Relevant knowledge is retrieved using vector similarity
3. **Context Building**: Retrieved knowledge is combined with conversation history
4. **Enhanced Prompt**: AI model receives context-aware prompt
5. **Response Generation**: AI generates response with relevant information

### Knowledge Categories

- `general`: General knowledge
- `commands`: Bot commands and usage
- `ai`: AI and machine learning topics
- `programming`: Programming and development
- `music`: Music and audio features
- `subscription`: Subscription and billing
- `policy`: Terms of service and policies

### Vector Embeddings

- Uses TF-IDF (Term Frequency-Inverse Document Frequency)
- 1000-dimensional feature vectors
- Cosine similarity for retrieval
- Minimum similarity threshold: 0.1

## ⚙️ Configuration

### User Context Settings

```python
# Example user context
{
    "user_id": "123456789",
    "preferred_model": "google/gemma-3n-e2b-it:free",
    "conversation_style": "friendly",
    "memory_duration_days": 7,
    "rag_enabled": True,
    "custom_knowledge": ["My favorite color is blue"],
    "last_active": 1640995200.0
}
```

### Database Configuration

```python
# Database settings in database_manager.py
DB_PATH = "bot_database.db"
MAX_CONVERSATION_HISTORY = 20
KNOWLEDGE_SEARCH_LIMIT = 5
CONTEXT_SUMMARY_THRESHOLD = 10
```

## 📊 Monitoring and Maintenance

### Database Statistics

```python
# Get database stats
stats = enhanced_model_manager.get_user_stats(user_id)
print(f"Total conversations: {stats['database_stats']['total_conversations']}")
print(f"Knowledge entries: {stats['database_stats']['knowledge_entries']}")
```

### Cleanup Operations

```python
# Clean up old data (30 days)
await enhanced_model_manager.cleanup_old_data(30)
```

### Performance Monitoring

- Monitor database size and growth
- Track query performance
- Monitor memory usage
- Check embedding quality

## 🚨 Troubleshooting

### Common Issues

#### Database Locked
```bash
# Check for running processes
ps aux | grep python
# Kill stuck processes
kill -9 <process_id>
```

#### Memory Issues
```python
# Reduce conversation history
MAX_TURNS = 10  # Instead of 20
```

#### RAG Not Working
```python
# Check knowledge base
stats = db_manager.get_database_stats()
print(f"Knowledge entries: {stats['knowledge_entries']}")

# Rebuild embeddings
db_manager._load_knowledge_embeddings()
```

### Performance Optimization

1. **Regular Cleanup**: Run cleanup operations regularly
2. **Index Optimization**: Monitor database indexes
3. **Embedding Quality**: Ensure knowledge entries are well-written
4. **Context Limits**: Adjust conversation history limits

## 🔒 Security Considerations

### Data Privacy
- User data is stored locally in SQLite
- No external data sharing
- Configurable data retention periods

### Access Control
- Admin-only commands for database operations
- User-specific knowledge isolation
- NSFW content restrictions

### Backup Strategy
- Regular database backups
- JSON file backups maintained
- Migration scripts for data portability

## 🚀 Future Enhancements

### Planned Features
- **Advanced Embeddings**: Switch to transformer-based embeddings
- **Multi-Modal RAG**: Support for images and documents
- **Real-Time Learning**: Learn from user interactions
- **Advanced Summarization**: LLM-based conversation summarization
- **Analytics Dashboard**: Web interface for monitoring

### Performance Improvements
- **Caching Layer**: Redis for frequently accessed data
- **Async Operations**: Full async/await implementation
- **Batch Processing**: Bulk operations for efficiency
- **Query Optimization**: Advanced SQL query optimization

## 📝 API Reference

### DatabaseManager

```python
# Core database operations
db_manager = DatabaseManager()

# Save conversation turn
db_manager.save_conversation_turn(turn)

# Get conversation history
history = db_manager.get_conversation_history(context_id, limit)

# Search knowledge
results = db_manager.search_knowledge(query, user_id, limit)

# Save knowledge entry
db_manager.save_knowledge_entry(entry)
```

### ContextManager

```python
# Context management
context_manager = ContextManager()

# Get RAG context
rag_context = await context_manager.get_rag_context(context_id, user_id, message)

# Update user context
await context_manager.update_user_context(user_id, **settings)

# Add knowledge
await context_manager.add_knowledge_entry(title, content, category)
```

### EnhancedModelManager

```python
# Enhanced model management
enhanced_model_manager = EnhancedModelManager()

# Get RAG-enhanced response
response, model, context = await enhanced_model_manager.get_chat_response_with_rag(
    prompt, user_id, context_id, is_nsfw, guild_id, channel_id
)

# Update user preferences
await enhanced_model_manager.update_user_preferences(user_id, **preferences)

# Get user statistics
stats = enhanced_model_manager.get_user_stats(user_id)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the troubleshooting section
- Run the test suite
- Review the API reference
- Open an issue on GitHub
