"""
Migration Script: Move existing data to database
Migrates conversation data, user preferences, and subscription data to the new database system
"""

import json
import os
import time
from pathlib import Path
from database_manager import db_manager, KnowledgeEntry
from context_manager import context_manager
from enhanced_model_manager import enhanced_model_manager

def migrate_user_preferences():
    """Migrate user preferences from JSON to database"""
    print("🔄 Migrating user preferences...")
    
    if not os.path.exists("user_preferences.json"):
        print("⚠️  No user_preferences.json found, skipping...")
        return
    
    try:
        with open("user_preferences.json", 'r') as f:
            user_prefs = json.load(f)
        
        migrated_count = 0
        for user_id, prefs_data in user_prefs.items():
            try:
                # Create user context
                user_context = {
                    'user_id': user_id,
                    'preferred_model': prefs_data.get('preferred_model', ''),
                    'conversation_style': 'friendly',  # Default style
                    'memory_duration_days': 7,  # Default duration
                    'rag_enabled': True,  # Enable RAG by default
                    'custom_knowledge': [],
                    'last_active': prefs_data.get('last_updated', time.time())
                }
                
                # Update user context
                context_manager.update_user_context(
                    user_id=user_id,
                    preferred_model=prefs_data.get('preferred_model'),
                    conversation_style='friendly',
                    memory_duration_days=7,
                    rag_enabled=True
                )
                
                migrated_count += 1
                
            except Exception as e:
                print(f"❌ Error migrating user {user_id}: {e}")
        
        print(f"✅ Migrated {migrated_count} user preferences")
        
    except Exception as e:
        print(f"❌ Error reading user_preferences.json: {e}")

def migrate_subscription_data():
    """Migrate subscription data (already in JSON, just ensure it's accessible)"""
    print("🔄 Checking subscription data...")
    
    if not os.path.exists("subscription_data.json"):
        print("⚠️  No subscription_data.json found, skipping...")
        return
    
    try:
        with open("subscription_data.json", 'r') as f:
            sub_data = json.load(f)
        
        print(f"✅ Found subscription data for {len(sub_data.get('subscriptions', {}))} users")
        print(f"✅ Found usage stats for {len(sub_data.get('usage_stats', {}))} entries")
        
    except Exception as e:
        print(f"❌ Error reading subscription_data.json: {e}")

def create_default_knowledge_base():
    """Create default knowledge base entries"""
    print("🔄 Creating default knowledge base...")
    
    default_knowledge = [
        {
            "title": "Discord Bot Commands",
            "content": "This bot supports various commands including !chat, !model, !models, !persona, !attest, and music commands. Use !help for a full list.",
            "category": "commands",
            "tags": ["discord", "bot", "commands", "help"]
        },
        {
            "title": "AI Model Information",
            "content": "The bot uses multiple AI models including Google Gemma, NVIDIA Nemotron, and Dolphin Mistral. Users can switch between models using !model command.",
            "category": "ai",
            "tags": ["ai", "models", "gemma", "nemotron", "dolphin"]
        },
        {
            "title": "Subscription Tiers",
            "content": "The bot has free and premium tiers. Free users have daily limits, while premium users get unlimited access and additional features.",
            "category": "subscription",
            "tags": ["subscription", "premium", "free", "limits"]
        },
        {
            "title": "NSFW Content Policy",
            "content": "NSFW content is available in channels marked as NSFW by Discord. Users must self-attest they are 18+ using the !attest command.",
            "category": "policy",
            "tags": ["nsfw", "policy", "age", "verification"]
        },
        {
            "title": "Music Features",
            "content": "The bot supports music playback with commands like !play, !pause, !skip, !queue. It uses Spotify integration and Lavalink for music streaming.",
            "category": "music",
            "tags": ["music", "spotify", "playback", "lavalink"]
        }
    ]
    
    migrated_count = 0
    for knowledge in default_knowledge:
        try:
            entry = KnowledgeEntry(
                title=knowledge["title"],
                content=knowledge["content"],
                category=knowledge["category"],
                tags=knowledge["tags"],
                created_at=time.time(),
                updated_at=time.time(),
                source="migration"
            )
            
            db_manager.save_knowledge_entry(entry)
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Error creating knowledge entry '{knowledge['title']}': {e}")
    
    print(f"✅ Created {migrated_count} default knowledge entries")

def backup_existing_files():
    """Create backup of existing data files"""
    print("🔄 Creating backups of existing data...")
    
    backup_dir = Path("backup")
    backup_dir.mkdir(exist_ok=True)
    
    files_to_backup = [
        "user_preferences.json",
        "subscription_data.json",
        "model_config.json",
        "subscription_config.py"
    ]
    
    backed_up = 0
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            try:
                import shutil
                shutil.copy2(file_path, backup_dir / file_path)
                backed_up += 1
            except Exception as e:
                print(f"❌ Error backing up {file_path}: {e}")
    
    print(f"✅ Backed up {backed_up} files to backup/ directory")

def test_database_functionality():
    """Test database functionality"""
    print("🧪 Testing database functionality...")
    
    try:
        # Test user context
        test_user_id = "test_migration_user"
        context_manager.update_user_context(
            user_id=test_user_id,
            preferred_model="google/gemma-3n-e2b-it:free",
            conversation_style="friendly",
            rag_enabled=True
        )
        
        user_context = context_manager.db.get_user_context(test_user_id)
        if user_context and user_context.user_id == test_user_id:
            print("✅ User context creation/retrieval works")
        else:
            print("❌ User context test failed")
        
        # Test knowledge search
        search_results = db_manager.search_knowledge("discord bot commands", limit=3)
        if search_results:
            print(f"✅ Knowledge search works - found {len(search_results)} results")
        else:
            print("⚠️  Knowledge search returned no results")
        
        # Test conversation saving
        from database_manager import ConversationTurn
        test_turn = ConversationTurn(
            context_id="test_context",
            role="user",
            content="Test message",
            timestamp=time.time(),
            model_used="test_model",
            user_id=test_user_id,
            channel_id="test_channel"
        )
        
        turn_id = db_manager.save_conversation_turn(test_turn)
        if turn_id:
            print("✅ Conversation saving works")
        else:
            print("❌ Conversation saving failed")
        
        # Clean up test data
        context_manager.db.cleanup_old_data(0)  # Clean up test data
        
    except Exception as e:
        print(f"❌ Database functionality test failed: {e}")

def main():
    """Main migration function"""
    print("=" * 70)
    print("🚀 AI Discord Bot - Database Migration")
    print("=" * 70)
    print()
    
    # Create backup
    backup_existing_files()
    
    # Migrate data
    migrate_user_preferences()
    migrate_subscription_data()
    create_default_knowledge_base()
    
    # Test functionality
    test_database_functionality()
    
    # Show database stats
    stats = db_manager.get_database_stats()
    print("\n📊 Database Statistics:")
    print(f"   Total conversations: {stats.get('total_conversations', 0)}")
    print(f"   Unique users: {stats.get('unique_users', 0)}")
    print(f"   Knowledge entries: {stats.get('knowledge_entries', 0)}")
    print(f"   Conversations last 24h: {stats.get('conversations_last_24h', 0)}")
    
    print("\n" + "=" * 70)
    print("✅ Migration completed!")
    print("=" * 70)
    print()
    print("📋 Next Steps:")
    print("1. Update main.py to use enhanced_model_manager")
    print("2. Test the bot with the new database system")
    print("3. Monitor database performance and adjust as needed")
    print("4. Consider setting up regular database cleanup")
    print()
    print("🆘 If you encounter issues:")
    print("   • Check backup/ directory for original files")
    print("   • Review database_manager.py for configuration")
    print("   • Test individual components using test_database_functionality()")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Migration interrupted by user")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Please check the error and try again.")
