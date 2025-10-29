# BentoML Image Generation Integration

This document explains how to set up and use BentoML for open source image generation in your Discord bot.

## 🎯 Overview

BentoML integration provides:
- **Local image generation** using Stable Diffusion 2.0
- **No API costs** - completely free to run
- **Privacy** - images generated locally, not sent to external services
- **High quality** - professional-grade image generation
- **Fallback system** - works alongside existing image generation methods

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Setup Script
```bash
python setup_bentoml.py
```

This will:
- Install BentoML and required dependencies
- Download Stable Diffusion 2.0 model
- Create startup scripts
- Test the integration

### 3. Start BentoML Service

**Linux/Mac:**
```bash
./start_bentoml_service.sh
```

**Windows:**
```cmd
start_bentoml_service.bat
```

**Manual:**
```bash
bentoml serve bentoml_image_service:svc --production --port 3000
```

## 🔧 Configuration

### Service Configuration
The BentoML service runs on `http://localhost:3000` by default. You can change this in `bentoml_image_service.py`:

```python
self.service_url = "http://localhost:3000"  # Change this if needed
```

### Model Configuration
The service uses Stable Diffusion 2.0 by default. You can change the model in `bentoml_image_service.py`:

```python
self.model_name = "sd2"  # Change to use different model
```

## 🎨 Usage

### In Discord Bot
The bot automatically uses BentoML for image generation when available. Users can generate images with:

```
!image a beautiful sunset over mountains
```

### Programmatic Usage
```python
from api_handler import generate_image_unified

# Generate an image
image_data = await generate_image_unified(
    prompt="a cute robot painting",
    size="512x512"
)

# Save the image
with open("generated_image.png", "wb") as f:
    f.write(image_data)
```

## 🔄 Primary Image Generation System

BentoML is now the **PRIMARY** image generation method. The system tries methods in this order:

1. **🚀 BentoML (PRIMARY)** - Local, free, private, high quality
2. **🔄 OpenRouter (Fallback)** - If API key available
3. **🔄 Gemini (Fallback)** - If API key available

BentoML is prioritized because it's:
- ✅ **Free** - No API costs
- ✅ **Private** - Images generated locally
- ✅ **High Quality** - Professional Stable Diffusion results
- ✅ **Reliable** - No external service dependencies

## 📊 Performance

### System Requirements
- **RAM**: 8GB+ recommended (4GB minimum)
- **GPU**: CUDA-compatible GPU recommended (CPU fallback available)
- **Storage**: ~5GB for model files
- **Network**: Only for initial model download

### Generation Times
- **GPU**: 10-30 seconds per image
- **CPU**: 2-5 minutes per image
- **Quality**: 512x512 to 1024x1024 pixels

## 🛠️ Troubleshooting

### Common Issues

**1. "BentoML not available" error**
```bash
pip install bentoml diffusers torch transformers pillow
```

**2. "Model not found" error**
```bash
python setup_bentoml.py
```

**3. "Service not running" error**
```bash
bentoml serve bentoml_image_service:svc --production --port 3000
```

**4. Out of memory error**
- Reduce image size: use "256x256" instead of "512x512"
- Close other applications
- Use CPU mode if GPU memory is insufficient

### Testing
Run the test script to verify everything is working:

```bash
python test_bentoml_integration.py
```

## 🔒 Privacy & Security

### Benefits
- **No data sent to external services** - everything runs locally
- **No API keys required** - completely self-contained
- **No usage tracking** - your prompts stay private
- **No costs** - completely free to use

### Considerations
- **Local storage** - model files stored on your system
- **Resource usage** - uses CPU/GPU resources
- **Internet required** - only for initial model download

## 📈 Advanced Configuration

### Custom Models
You can use different Stable Diffusion models:

```python
# In bentoml_image_service.py
bentoml.diffusers.import_model(
    "custom-model",
    "runwayml/stable-diffusion-v1-5",  # Different model
)
```

### Performance Tuning
Adjust generation parameters:

```python
# In bentoml_image_service.py
image_data = await bentoml_generator.generate_image(
    prompt=prompt,
    width=512,
    height=512,
    num_inference_steps=20,  # More steps = better quality, slower
    guidance_scale=7.5      # Higher = more prompt adherence
)
```

## 🆘 Support

If you encounter issues:

1. **Check logs** - Look for error messages in the console
2. **Verify dependencies** - Run `python setup_bentoml.py`
3. **Test service** - Run `python test_bentoml_integration.py`
4. **Check resources** - Ensure sufficient RAM/GPU memory

## 🎉 Benefits of BentoML as Primary Method

- ✅ **PRIMARY METHOD** - BentoML is now the first choice for image generation
- ✅ **Free** - No API costs or usage limits
- ✅ **Private** - Images generated locally, never sent to external services
- ✅ **High Quality** - Professional-grade Stable Diffusion results
- ✅ **Reliable** - No external service dependencies or API rate limits
- ✅ **Customizable** - Full control over generation parameters
- ✅ **Scalable** - Can handle multiple concurrent requests
- ✅ **Fast** - Local generation with GPU acceleration
- ✅ **Unlimited** - No daily limits or subscription requirements

Your Discord bot now has **BentoML as the primary image generation method** - powerful, free, and completely private! 🚀
