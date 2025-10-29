#!/usr/bin/env python3
"""
BentoML Image Generation Service
Provides open source image generation using Stable Diffusion via BentoML
"""

import bentoml
from bentoml.io import Image, JSON
import torch
from diffusers import StableDiffusionPipeline
import io
import base64
from typing import Dict, Any, Optional
import asyncio
import aiohttp

class BentoMLImageGenerator:
    """BentoML-based image generation service"""
    
    def __init__(self):
        self.service_url = "http://localhost:3000"  # Default BentoML service URL
        self.model_name = "sd2"  # Stable Diffusion 2.0 model
        self.is_initialized = False
        
    async def initialize_model(self):
        """Initialize the BentoML model if not already done"""
        try:
            # Check if model exists in BentoML store
            try:
                bentoml.diffusers.get(f"{self.model_name}:latest")
                print(f"[BentoML] Model {self.model_name} already exists")
            except Exception:
                print(f"[BentoML] Importing model {self.model_name}...")
                bentoml.diffusers.import_model(
                    self.model_name,
                    "stabilityai/stable-diffusion-2",
                )
                print(f"[BentoML] Model {self.model_name} imported successfully")
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            print(f"[BentoML] Error initializing model: {e}")
            return False
    
    async def generate_image(self, prompt: str, width: int = 512, height: int = 512, 
                           num_inference_steps: int = 20, guidance_scale: float = 7.5) -> Optional[bytes]:
        """
        Generate an image using BentoML service (PRIMARY IMAGE GENERATION METHOD)
        
        Args:
            prompt: Text prompt for image generation
            width: Image width (default: 512)
            height: Image height (default: 512)
            num_inference_steps: Number of denoising steps (default: 20)
            guidance_scale: Guidance scale for generation (default: 7.5)
            
        Returns:
            Image bytes if successful, None if failed
        """
        try:
            print(f"[BentoML] 🎨 Generating image: '{prompt[:50]}...'")
            print(f"[BentoML] 📏 Size: {width}x{height}")
            
            # Prepare request data
            request_data = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "num_images_per_prompt": 1
            }
            
            # Make request to BentoML service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.service_url}/txt2img",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=180)  # Increased timeout for generation
                ) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        print(f"[BentoML] ✅ Image generated successfully ({len(image_data)} bytes)")
                        return image_data
                    else:
                        error_text = await response.text()
                        print(f"[BentoML] ❌ HTTP {response.status}: {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            print(f"[BentoML] ❌ Timeout generating image (180s limit)")
            return None
        except Exception as e:
            print(f"[BentoML] ❌ Error generating image: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check if BentoML service is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.service_url}/healthz",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
        except Exception:
            return False

# Global BentoML image generator instance
bentoml_generator = BentoMLImageGenerator()

async def generate_image_with_bentoml(prompt: str, size: str = "512x512") -> Optional[bytes]:
    """
    Generate an image using BentoML Stable Diffusion
    
    Args:
        prompt: Text prompt for image generation
        size: Image size in format "WIDTHxHEIGHT" (default: "512x512")
        
    Returns:
        Image bytes if successful, None if failed
    """
    try:
        # Parse size
        width, height = map(int, size.split('x'))
        
        # Initialize model if needed
        if not bentoml_generator.is_initialized:
            if not await bentoml_generator.initialize_model():
                return None
        
        # Generate image
        image_data = await bentoml_generator.generate_image(
            prompt=prompt,
            width=width,
            height=height
        )
        
        return image_data
        
    except Exception as e:
        print(f"[BentoML Image] Error: {e}")
        return None

# BentoML Service Definition (for running the service)
def create_bentoml_service():
    """Create the BentoML service for image generation"""
    try:
        # Get the model
        bento_model = bentoml.diffusers.get("sd2:latest")
        stable_diffusion_runner = bento_model.to_runner()
        
        # Create service
        svc = bentoml.Service("stable_diffusion_v2", runners=[stable_diffusion_runner])
        
        @svc.api(input=JSON(), output=Image())
        def txt2img(input_data):
            """Text to image generation endpoint"""
            try:
                res = stable_diffusion_runner.text2img.run(**input_data)
                images = res[0]
                return images[0]
            except Exception as e:
                print(f"[BentoML Service] Error: {e}")
                return None
        
        return svc
        
    except Exception as e:
        print(f"[BentoML Service] Error creating service: {e}")
        return None

if __name__ == "__main__":
    # This can be used to run the BentoML service
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        svc = create_bentoml_service()
        if svc:
            print("Starting BentoML service...")
            # Note: In production, you would use: bentoml serve service:svc --production
            print("Use: bentoml serve bentoml_image_service:svc --production")
        else:
            print("Failed to create BentoML service")
    else:
        print("Usage: python bentoml_image_service.py serve")
