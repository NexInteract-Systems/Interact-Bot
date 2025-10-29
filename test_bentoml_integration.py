#!/usr/bin/env python3
"""
Test script for BentoML image generation integration
"""

import asyncio
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_handler import generate_image_unified, BENTOML_AVAILABLE

async def test_bentoml_integration():
    """Test BentoML image generation integration"""
    print("Testing BentoML image generation integration...")
    
    # Test 1: Check BentoML availability
    print(f"\n=== Test 1: BentoML Availability ===")
    if BENTOML_AVAILABLE:
        print("[SUCCESS] BentoML is available")
    else:
        print("[WARNING] BentoML is not available. Install bentoml, diffusers, and torch.")
        print("Run: python setup_bentoml.py")
        return
    
    # Test 2: Test unified image generation (PRIMARY METHOD)
    print(f"\n=== Test 2: Unified Image Generation (BentoML Primary) ===")
    test_prompt = "a cute robot painting a picture"
    
    try:
        print(f"Generating image with prompt: '{test_prompt}'")
        print("This should use BentoML as the PRIMARY method...")
        image_data = await generate_image_unified(test_prompt, "512x512")
        
        if image_data:
            print(f"[SUCCESS] Image generated successfully!")
            print(f"Image size: {len(image_data)} bytes")
            
            # Save test image
            try:
                with open("test_bentoml_primary.png", "wb") as f:
                    f.write(image_data)
                print(f"[SUCCESS] Test image saved as 'test_bentoml_primary.png'")
            except Exception as e:
                print(f"[WARNING] Could not save test image: {e}")
        else:
            print("[FAILED] Image generation failed")
            print("Note: BentoML is the PRIMARY method - install it for best results")
            
    except Exception as e:
        print(f"[ERROR] Image generation test failed: {e}")
    
    # Test 3: Test different sizes
    print(f"\n=== Test 3: Different Image Sizes ===")
    sizes = ["256x256", "512x512", "768x768"]
    
    for size in sizes:
        try:
            print(f"Testing size: {size}")
            image_data = await generate_image_unified("a simple flower", size)
            if image_data:
                print(f"[SUCCESS] {size} generation successful")
            else:
                print(f"[FAILED] {size} generation failed")
        except Exception as e:
            print(f"[ERROR] {size} test failed: {e}")
    
    # Test 4: Test service health
    print(f"\n=== Test 4: Service Health Check ===")
    try:
        from bentoml_image_service import bentoml_generator
        is_healthy = await bentoml_generator.health_check()
        if is_healthy:
            print("[SUCCESS] BentoML service is running and healthy")
        else:
            print("[WARNING] BentoML service is not running")
            print("Start the service with: bentoml serve bentoml_image_service:svc --production --port 3000")
    except Exception as e:
        print(f"[ERROR] Health check failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_bentoml_integration())
