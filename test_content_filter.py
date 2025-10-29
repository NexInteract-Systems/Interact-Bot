"""
Test Script for Content Filter
Tests the content filtering system for Dolphin model NSFW vs drug content
"""

import asyncio
from content_filter import content_filter, ContentType

async def test_content_filtering():
    """Test the content filtering system"""
    print("Testing Content Filter System...")
    print("=" * 60)
    
    # Test cases for different content types
    test_cases = [
        # NSFW content (should be allowed for Dolphin in NSFW mode)
        {
            "text": "I want to talk about romantic relationships and intimacy",
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "is_nsfw": True,
            "expected_block": False,
            "description": "NSFW romantic content"
        },
        {
            "text": "Let's discuss adult topics and sexual health",
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "is_nsfw": True,
            "expected_block": False,
            "description": "NSFW adult content"
        },
        
        # Drug content (should be blocked for all models)
        {
            "text": "Tell me about cocaine and how to use it",
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "is_nsfw": True,
            "expected_block": True,
            "description": "Drug-related content"
        },
        {
            "text": "I want to know about marijuana and weed",
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "is_nsfw": True,
            "expected_block": True,
            "description": "Marijuana content"
        },
        {
            "text": "How do I get high on drugs?",
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "is_nsfw": True,
            "expected_block": True,
            "description": "Drug use content"
        },
        
        # Violence content (should be blocked)
        {
            "text": "I want to learn about weapons and violence",
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "is_nsfw": True,
            "expected_block": True,
            "description": "Violence content"
        },
        
        # SFW content (should be allowed)
        {
            "text": "Tell me about programming and software development",
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "is_nsfw": False,
            "expected_block": False,
            "description": "SFW programming content"
        },
        
        # NSFW content in SFW mode (should be blocked)
        {
            "text": "I want to talk about sex and relationships",
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "is_nsfw": False,
            "expected_block": True,
            "description": "NSFW content in SFW mode"
        },
        
        # Edge cases
        {
            "text": "I love cooking with herbs and spices",
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "is_nsfw": True,
            "expected_block": False,
            "description": "Cooking content (not drug-related)"
        },
        {
            "text": "Tell me about the drug war and politics",
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "is_nsfw": True,
            "expected_block": True,
            "description": "Political drug content"
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"   Text: '{test_case['text']}'")
        print(f"   Model: {test_case['model']}")
        print(f"   NSFW Mode: {test_case['is_nsfw']}")
        
        # Test content detection
        detected_types = content_filter.detect_content_type(test_case['text'])
        print(f"   Detected types: {[t.value for t in detected_types]}")
        
        # Test blocking decision
        should_block, reason = content_filter.should_block_content(
            test_case['text'], 
            test_case['model'], 
            test_case['is_nsfw']
        )
        
        print(f"   Should block: {should_block}")
        if reason:
            print(f"   Reason: {reason}")
        
        # Test response filtering
        filtered_response = content_filter.filter_response(
            f"Response to: {test_case['text']}", 
            test_case['model'], 
            test_case['is_nsfw']
        )
        print(f"   Filtered response: {filtered_response[:100].encode('ascii', 'replace').decode('ascii')}...")
        
        # Check if test passed
        if should_block == test_case['expected_block']:
            print("   PASS")
            passed_tests += 1
        else:
            print("   FAIL")
            print(f"   Expected: {test_case['expected_block']}, Got: {should_block}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("All content filtering tests passed!")
    else:
        print("Some tests failed. Check the output above for details.")
    
    return passed_tests == total_tests

async def test_model_guidelines():
    """Test model guidelines generation"""
    print("\nTesting Model Guidelines...")
    print("=" * 60)
    
    models_to_test = [
        "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "google/gemma-3n-e2b-it:free",
        "nvidia/nemotron-nano-9b-v2:free"
    ]
    
    for model_id in models_to_test:
        print(f"\nGuidelines for {model_id}:")
        guidelines = content_filter.get_model_guidelines(model_id)
        print(guidelines.encode('ascii', 'replace').decode('ascii'))

async def test_content_warnings():
    """Test content warning generation"""
    print("\nTesting Content Warnings...")
    print("=" * 60)
    
    test_texts = [
        "I want to talk about adult relationships",
        "Tell me about programming",
        "I need help with my homework"
    ]
    
    model_id = "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
    
    for text in test_texts:
        warning = content_filter.get_content_warning(text, model_id)
        print(f"Text: '{text}'")
        warning_text = warning or 'None'
        print(f"Warning: {warning_text.encode('ascii', 'replace').decode('ascii')}")
        print()

async def main():
    """Main test function"""
    print("Content Filter Test Suite")
    print("Testing Dolphin model NSFW vs drug content filtering")
    print("=" * 60)
    
    try:
        # Run all tests
        filter_tests_passed = await test_content_filtering()
        await test_model_guidelines()
        await test_content_warnings()
        
        print("\n" + "=" * 60)
        if filter_tests_passed:
            print("All tests completed successfully!")
            print("\nSummary:")
            print("• Dolphin model allows NSFW content in NSFW mode")
            print("• Dolphin model blocks drug-related content")
            print("• All models block violence and harassment")
            print("• Content filtering works as expected")
        else:
            print("Some tests failed. Please review the output above.")
        
        print("\nUsage Instructions:")
        print("• Use `/contentfilter` to see filtering information")
        print("• Use `/modelinfo dolphin` to see model guidelines")
        print("• Use `!togglemode` to enable NSFW mode (admin only)")
        print("• Use `/attest` to verify age for NSFW content")
        
    except Exception as e:
        print(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
