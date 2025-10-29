"""
Test Script for Database and RAG Functionality
Comprehensive testing of the new database and RAG system
"""

import asyncio
import time
import json
from database_manager import db_manager, KnowledgeEntry, ConversationTurn
from context_manager import context_manager
from enhanced_model_manager import enhanced_model_manager

async def test_database_operations():
    """Test basic database operations"""
    print("🧪 Testing Database Operations...")
    
    # Test 1: User Context Management
    print("\n1. Testing User Context Management...")
    test_user_id = "test_user_123"
    
    # Create user context
    await context_manager.update_user_context(
        user_id=test_user_id,
        preferred_model="google/gemma-3n-e2b-it:free",
        conversation_style="friendly",
        memory_duration_days=7,
        rag_enabled=True,
        custom_knowledge=["Test knowledge entry"]
    )
    
    # Retrieve user context
    user_context = context_manager.db.get_user_context(test_user_id)
    assert user_context is not None, "Failed to retrieve user context"
    assert user_context.user_id == test_user_id, "User ID mismatch"
    assert user_context.conversation_style == "friendly", "Conversation style mismatch"
    print("✅ User context management works")
    
    # Test 2: Conversation Storage
    print("\n2. Testing Conversation Storage...")
    test_context_id = "test_context_123"
    
    # Save conversation turns
    await context_manager.save_conversation_turn(
        context_id=test_context_id,
        user_id=test_user_id,
        role="user",
        content="Hello, how are you?",
        model_used="",
        is_nsfw=False,
        guild_id="test_guild",
        channel_id="test_channel"
    )
    
    await context_manager.save_conversation_turn(
        context_id=test_context_id,
        user_id=test_user_id,
        role="assistant",
        content="I'm doing well, thank you for asking!",
        model_used="google/gemma-3n-e2b-it:free",
        is_nsfw=False,
        guild_id="test_guild",
        channel_id="test_channel"
    )
    
    # Retrieve conversation history
    history = context_manager.db.get_conversation_history(test_context_id, 10)
    assert len(history) == 2, f"Expected 2 conversation turns, got {len(history)}"
    assert history[0].role == "user", "First turn should be user"
    assert history[1].role == "assistant", "Second turn should be assistant"
    print("✅ Conversation storage works")
    
    # Test 3: Knowledge Base Operations
    print("\n3. Testing Knowledge Base Operations...")
    
    # Add knowledge entries
    knowledge_entries = [
        {
            "title": "Test Knowledge 1",
            "content": "This is a test knowledge entry about Discord bots and their capabilities.",
            "category": "testing",
            "tags": ["discord", "bot", "test"]
        },
        {
            "title": "Test Knowledge 2", 
            "content": "Another test entry about AI models and machine learning concepts.",
            "category": "testing",
            "tags": ["ai", "ml", "models"]
        }
    ]
    
    entry_ids = []
    for entry_data in knowledge_entries:
        entry_id = await context_manager.add_knowledge_entry(
            title=entry_data["title"],
            content=entry_data["content"],
            category=entry_data["category"],
            tags=entry_data["tags"],
            user_id=test_user_id,
            source="test"
        )
        entry_ids.append(entry_id)
        assert entry_id is not None, "Failed to create knowledge entry"
    
    print("✅ Knowledge base operations work")
    
    # Test 4: RAG Search
    print("\n4. Testing RAG Search...")
    
    # Search for relevant knowledge
    search_results = context_manager.db.search_knowledge(
        query="Discord bot capabilities",
        user_id=test_user_id,
        limit=5
    )
    
    assert len(search_results) > 0, "RAG search should return results"
    print(f"✅ RAG search works - found {len(search_results)} results")
    
    # Test 5: Context Summaries
    print("\n5. Testing Context Summaries...")
    
    # Create context summary
    conversation_history = [
        {"role": "user", "content": "What is a Discord bot?"},
        {"role": "assistant", "content": "A Discord bot is an automated user that can interact with Discord servers."},
        {"role": "user", "content": "How do I create one?"},
        {"role": "assistant", "content": "You can create a Discord bot using the Discord API and a programming language like Python."}
    ]
    
    await context_manager.create_context_summary(
        context_id=test_context_id,
        user_id=test_user_id,
        conversation_history=conversation_history
    )
    
    # Retrieve context summaries
    summaries = context_manager.db.get_context_summaries(test_user_id)
    assert len(summaries) > 0, "Should have context summaries"
    print("✅ Context summaries work")
    
    print("\n✅ All database operations passed!")

async def test_rag_integration():
    """Test RAG integration with model manager"""
    print("\n🧪 Testing RAG Integration...")
    
    test_user_id = "test_rag_user"
    test_context_id = "test_rag_context"
    
    # Set up user context
    await context_manager.update_user_context(
        user_id=test_user_id,
        preferred_model="google/gemma-3n-e2b-it:free",
        conversation_style="friendly",
        rag_enabled=True
    )
    
    # Add some knowledge
    await context_manager.add_knowledge_entry(
        title="Python Programming",
        content="Python is a high-level programming language known for its simplicity and readability. It's widely used for web development, data science, and automation.",
        category="programming",
        tags=["python", "programming", "language"],
        user_id=test_user_id
    )
    
    # Test RAG context retrieval
    rag_context = await context_manager.get_rag_context(
        context_id=test_context_id,
        user_id=test_user_id,
        current_message="Tell me about Python programming",
        is_nsfw=False
    )
    
    assert rag_context is not None, "RAG context should not be None"
    assert rag_context.user_context is not None, "User context should be present"
    assert len(rag_context.relevant_knowledge) > 0, "Should have relevant knowledge"
    
    print("✅ RAG integration works")
    
    # Test enhanced prompt building
    enhanced_prompt = enhanced_model_manager._build_enhanced_prompt(
        "Tell me about Python programming",
        rag_context,
        None
    )
    
    assert "Python" in enhanced_prompt, "Enhanced prompt should contain relevant knowledge"
    assert "programming" in enhanced_prompt, "Enhanced prompt should contain relevant terms"
    
    print("✅ Enhanced prompt building works")

async def test_model_manager_integration():
    """Test model manager integration with database"""
    print("\n🧪 Testing Model Manager Integration...")
    
    test_user_id = "test_model_user"
    test_context_id = "test_model_context"
    
    # Test user preference management
    success = enhanced_model_manager.set_user_preference(
        test_user_id, 
        "google/gemma-3n-e2b-it:free"
    )
    assert success, "Should be able to set user preference"
    
    # Test user stats
    stats = enhanced_model_manager.get_user_stats(test_user_id)
    assert 'user_stats' in stats, "Stats should contain user_stats"
    assert 'model_stats' in stats, "Stats should contain model_stats"
    assert 'database_stats' in stats, "Stats should contain database_stats"
    
    print("✅ Model manager integration works")

async def test_performance():
    """Test performance with multiple operations"""
    print("\n🧪 Testing Performance...")
    
    start_time = time.time()
    
    # Create multiple users and contexts
    for i in range(10):
        user_id = f"perf_test_user_{i}"
        context_id = f"perf_test_context_{i}"
        
        # Set up user
        await context_manager.update_user_context(
            user_id=user_id,
            preferred_model="google/gemma-3n-e2b-it:free",
            rag_enabled=True
        )
        
        # Add some conversations
        for j in range(5):
            await context_manager.save_conversation_turn(
                context_id=context_id,
                user_id=user_id,
                role="user" if j % 2 == 0 else "assistant",
                content=f"Test message {j}",
                model_used="test_model",
                is_nsfw=False,
                channel_id=f"channel_{i}"
            )
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"✅ Performance test completed in {duration:.2f} seconds")
    
    # Test database stats
    stats = context_manager.db.get_database_stats()
    print(f"📊 Database stats: {stats}")

async def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    
    # Clean up old data (everything older than 0 days = everything)
    await context_manager.cleanup_old_data(0)
    
    print("✅ Test data cleaned up")

async def main():
    """Main test function"""
    print("=" * 70)
    print("🧪 AI Discord Bot - Database and RAG Test Suite")
    print("=" * 70)
    
    try:
        # Run all tests
        await test_database_operations()
        await test_rag_integration()
        await test_model_manager_integration()
        await test_performance()
        
        print("\n" + "=" * 70)
        print("✅ All tests passed successfully!")
        print("=" * 70)
        
        # Show final stats
        stats = context_manager.db.get_database_stats()
        print(f"\n📊 Final Database Statistics:")
        print(f"   Total conversations: {stats.get('total_conversations', 0)}")
        print(f"   Unique users: {stats.get('unique_users', 0)}")
        print(f"   Knowledge entries: {stats.get('knowledge_entries', 0)}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test data
        await cleanup_test_data()

if __name__ == "__main__":
    asyncio.run(main())
