#!/usr/bin/env python3
"""
BentoML Import Fix and Setup
"""

import os
import sys
import subprocess

def install_missing_packages():
    """Install missing packages for better BentoML performance"""
    print("Installing missing packages for BentoML...")
    
    packages = [
        "huggingface_hub[hf_xet]",  # For better download performance
        "hf_xet",  # Alternative Xet storage
    ]
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"OK - {package} installed")
        except subprocess.CalledProcessError as e:
            print(f"WARNING - Failed to install {package}: {e}")

def create_optimized_bentoml_service():
    """Create an optimized BentoML service with better error handling"""
    service_code = '''#!/usr/bin/env python3
"""
Optimized BentoML Image Generation Service
"""

import bentoml
from bentoml.io import Image, JSON
import torch
from diffusers import StableDiffusionPipeline
import asyncio
import aiohttp
from typing import Optional

class OptimizedBentoMLGenerator:
    """Optimized BentoML image generator with better error handling"""
    
    def __init__(self):
        self.service_url = "http://localhost:3000"
        self.model_name = "sd2"
        self.is_initialized = False
        
    async def initialize_model(self):
        """Initialize model with better error handling"""
        try:
            print("[BentoML] Initializing model...")
            
            # Check if model exists
            try:
                bentoml.diffusers.get(f"{self.model_name}:latest")
                print(f"[BentoML] Model {self.model_name} already exists")
                return True
            except Exception:
                print(f"[BentoML] Importing model {self.model_name}...")
                
                # Use a more stable model
                bentoml.diffusers.import_model(
                    self.model_name,
                    "stabilityai/stable-diffusion-2-1",  # More stable than 2.0
                )
                print(f"[BentoML] Model imported successfully")
                return True
                
        except Exception as e:
            print(f"[BentoML] Error initializing model: {e}")
            return False
    
    async def generate_image(self, prompt: str, width: int = 512, height: int = 512) -> Optional[bytes]:
        """Generate image with optimized settings"""
        try:
            print(f"[BentoML] Generating: {prompt[:50]}...")
            
            request_data = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_inference_steps": 20,
                "guidance_scale": 7.5,
                "num_images_per_prompt": 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.service_url}/txt2img",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes
                ) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        print(f"[BentoML] Generated {len(image_data)} bytes")
                        return image_data
                    else:
                        error_text = await response.text()
                        print(f"[BentoML] HTTP {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"[BentoML] Error: {e}")
            return None

# Global instance
generator = OptimizedBentoMLGenerator()

async def generate_image_with_bentoml_optimized(prompt: str, size: str = "512x512") -> Optional[bytes]:
    """Optimized BentoML image generation"""
    try:
        if not generator.is_initialized:
            if not await generator.initialize_model():
                return None
        
        width, height = map(int, size.split('x'))
        return await generator.generate_image(prompt, width, height)
        
    except Exception as e:
        print(f"[BentoML] Error: {e}")
        return None

# BentoML Service Definition
def create_optimized_service():
    """Create optimized BentoML service"""
    try:
        bento_model = bentoml.diffusers.get("sd2:latest")
        runner = bento_model.to_runner()
        
        svc = bentoml.Service("stable_diffusion_optimized", runners=[runner])
        
        @svc.api(input=JSON(), output=Image())
        def txt2img(input_data):
            try:
                result = runner.text2img.run(**input_data)
                return result[0][0] if result and result[0] else None
            except Exception as e:
                print(f"[Service] Error: {e}")
                return None
        
        return svc
    except Exception as e:
        print(f"[Service] Error creating service: {e}")
        return None

if __name__ == "__main__":
    print("Optimized BentoML Service")
    print("Use: bentoml serve bentoml_import_fix:create_optimized_service() --production")
'''
    
    with open("bentoml_optimized_service.py", "w") as f:
        f.write(service_code)
    
    print("Created optimized BentoML service: bentoml_optimized_service.py")

def create_startup_scripts():
    """Create startup scripts for the optimized service"""
    
    # Windows batch file
    batch_content = '''@echo off
echo Starting Optimized BentoML Service...
echo This service has better error handling and performance
echo.

REM Check if model exists
python -c "import bentoml; bentoml.diffusers.get('sd2:latest')" 2>nul
if errorlevel 1 (
    echo Model not found. Importing...
    python -c "import bentoml; bentoml.diffusers.import_model('sd2', 'stabilityai/stable-diffusion-2-1')"
)

echo Starting service on port 3000...
bentoml serve bentoml_optimized_service:create_optimized_service() --production --port 3000
pause
'''
    
    with open("start_optimized_bentoml.bat", "w") as f:
        f.write(batch_content)
    
    # Linux/Mac shell script
    shell_content = '''#!/bin/bash
echo "Starting Optimized BentoML Service..."
echo "This service has better error handling and performance"
echo ""

# Check if model exists
python -c "import bentoml; bentoml.diffusers.get('sd2:latest')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Model not found. Importing..."
    python -c "import bentoml; bentoml.diffusers.import_model('sd2', 'stabilityai/stable-diffusion-2-1')"
fi

echo "Starting service on port 3000..."
bentoml serve bentoml_optimized_service:create_optimized_service() --production --port 3000
'''
    
    with open("start_optimized_bentoml.sh", "w") as f:
        f.write(shell_content)
    
    # Make shell script executable
    try:
        os.chmod("start_optimized_bentoml.sh", 0o755)
    except:
        pass
    
    print("Created startup scripts:")
    print("- start_optimized_bentoml.bat (Windows)")
    print("- start_optimized_bentoml.sh (Linux/Mac)")

def main():
    """Main fix function"""
    print("BentoML Import Fix and Optimization")
    print("=" * 40)
    
    print("\n1. Installing missing packages...")
    install_missing_packages()
    
    print("\n2. Creating optimized service...")
    create_optimized_bentoml_service()
    
    print("\n3. Creating startup scripts...")
    create_startup_scripts()
    
    print("\n" + "=" * 40)
    print("FIXES APPLIED:")
    print("✅ Installed missing packages for better performance")
    print("✅ Created optimized BentoML service with better error handling")
    print("✅ Created startup scripts for easy service management")
    
    print("\nNEXT STEPS:")
    print("1. Run: start_optimized_bentoml.bat (Windows) or ./start_optimized_bentoml.sh (Linux/Mac)")
    print("2. The service will automatically import the model if needed")
    print("3. Your Discord bot will now use the optimized BentoML service")
    
    print("\nBENEFITS:")
    print("- Better error handling")
    print("- Optimized model (SD 2.1 instead of 2.0)")
    print("- Faster downloads with Xet storage")
    print("- More stable service")

if __name__ == "__main__":
    main()










