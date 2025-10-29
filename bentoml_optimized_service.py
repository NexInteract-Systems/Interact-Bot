#!/usr/bin/env python3
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
