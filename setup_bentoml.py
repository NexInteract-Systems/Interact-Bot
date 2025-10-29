#!/usr/bin/env python3
"""
BentoML Setup Script for Image Generation
Helps users set up BentoML for local image generation
"""

import subprocess
import sys
import os
import asyncio
import aiohttp

def install_dependencies():
    """Install required dependencies for BentoML"""
    print("Installing BentoML dependencies...")
    
    dependencies = [
        "bentoml>=1.1.0",
        "diffusers>=0.21.0", 
        "torch>=2.0.0",
        "transformers>=4.30.0",
        "pillow>=9.5.0"
    ]
    
    for dep in dependencies:
        try:
            print(f"Installing {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✅ {dep} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {dep}: {e}")
            return False
    
    return True

def import_stable_diffusion_model():
    """Import Stable Diffusion model into BentoML"""
    print("Importing Stable Diffusion model into BentoML...")
    
    try:
        import bentoml
        
        # Check if model already exists
        try:
            bentoml.diffusers.get("sd2:latest")
            print("✅ Stable Diffusion model already exists in BentoML")
            return True
        except Exception:
            pass
        
        # Import the model
        print("Downloading and importing Stable Diffusion 2.0...")
        bentoml.diffusers.import_model(
            "sd2",
            "stabilityai/stable-diffusion-2",
        )
        print("✅ Stable Diffusion model imported successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to import model: {e}")
        return False

async def test_bentoml_service():
    """Test if BentoML service is working"""
    print("Testing BentoML service...")
    
    try:
        # Try to import and test the service
        from bentoml_image_service import bentoml_generator
        
        # Test health check
        is_healthy = await bentoml_generator.health_check()
        if is_healthy:
            print("✅ BentoML service is running")
        else:
            print("⚠️ BentoML service is not running. You may need to start it manually.")
            print("Run: bentoml serve bentoml_image_service:svc --production")
        
        return is_healthy
        
    except Exception as e:
        print(f"❌ BentoML service test failed: {e}")
        return False

def create_startup_script():
    """Create a startup script for the BentoML service"""
    startup_script = """#!/bin/bash
# BentoML Image Generation Service Startup Script

echo "Starting BentoML Image Generation Service..."
echo "This will start the Stable Diffusion service on port 3000"
echo "Press Ctrl+C to stop the service"
echo ""

# Start the BentoML service
bentoml serve bentoml_image_service:svc --production --port 3000
"""
    
    try:
        with open("start_bentoml_service.sh", "w") as f:
            f.write(startup_script)
        os.chmod("start_bentoml_service.sh", 0o755)
        print("✅ Created startup script: start_bentoml_service.sh")
        return True
    except Exception as e:
        print(f"❌ Failed to create startup script: {e}")
        return False

def create_windows_batch():
    """Create a Windows batch file for starting the service"""
    batch_content = """@echo off
echo Starting BentoML Image Generation Service...
echo This will start the Stable Diffusion service on port 3000
echo Press Ctrl+C to stop the service
echo.

bentoml serve bentoml_image_service:svc --production --port 3000
pause
"""
    
    try:
        with open("start_bentoml_service.bat", "w") as f:
            f.write(batch_content)
        print("✅ Created Windows batch file: start_bentoml_service.bat")
        return True
    except Exception as e:
        print(f"❌ Failed to create Windows batch file: {e}")
        return False

async def main():
    """Main setup function"""
    print("🚀 BentoML Image Generation Setup")
    print("=" * 50)
    
    # Step 1: Install dependencies
    print("\n📦 Step 1: Installing dependencies...")
    if not install_dependencies():
        print("❌ Failed to install dependencies. Please install manually.")
        return False
    
    # Step 2: Import model
    print("\n🤖 Step 2: Importing Stable Diffusion model...")
    if not import_stable_diffusion_model():
        print("❌ Failed to import model. Please check your internet connection.")
        return False
    
    # Step 3: Create startup scripts
    print("\n📝 Step 3: Creating startup scripts...")
    create_startup_script()
    create_windows_batch()
    
    # Step 4: Test service
    print("\n🧪 Step 4: Testing BentoML service...")
    service_working = await test_bentoml_service()
    
    print("\n" + "=" * 50)
    if service_working:
        print("✅ BentoML setup completed successfully!")
        print("\nTo start the image generation service:")
        print("  Linux/Mac: ./start_bentoml_service.sh")
        print("  Windows: start_bentoml_service.bat")
        print("  Manual: bentoml serve bentoml_image_service:svc --production --port 3000")
    else:
        print("⚠️ BentoML setup completed with warnings!")
        print("\nThe model has been imported, but the service needs to be started manually.")
        print("Run: bentoml serve bentoml_image_service:svc --production --port 3000")
    
    print("\n🎨 Your Discord bot can now generate images locally using Stable Diffusion!")
    return True

if __name__ == "__main__":
    asyncio.run(main())


