# 🚀 Start BentoML Image Generation Service

## Quick Start

To fix the "Failed to generate image" error, you need to start the BentoML service:

### Windows:
```cmd
start_optimized_bentoml.bat
```

### Linux/Mac:
```bash
./start_optimized_bentoml.sh
```

## What This Does

1. **Checks if the model exists** - If not, automatically downloads Stable Diffusion 2.1
2. **Starts the BentoML service** on port 3000
3. **Enables local image generation** - No API keys needed!
4. **Makes BentoML the PRIMARY method** for image generation

## Expected Output

When you run the startup script, you should see:
```
Starting Optimized BentoML Service...
This service has better error handling and performance

Model not found. Importing...
[Download progress...]
Starting service on port 3000...
```

## After Starting the Service

1. **Keep the terminal window open** - The service needs to stay running
2. **Test image generation** in Discord with: `/image a cute robot`
3. **The bot will now use BentoML** as the primary image generation method

## Troubleshooting

### If you get "Model not found" error:
- The script will automatically download the model (this takes a few minutes)
- Make sure you have at least 10GB free disk space

### If you get "Port 3000 already in use" error:
- Close any other services using port 3000
- Or change the port in the startup script

### If image generation still fails:
- Check that the BentoML service is running
- Look for error messages in the terminal
- Try restarting the service

## Benefits of BentoML

✅ **Free** - No API costs  
✅ **Private** - Images generated locally  
✅ **Fast** - GPU acceleration  
✅ **Unlimited** - No daily limits  
✅ **High Quality** - Professional Stable Diffusion results  

Your Discord bot now has powerful, free, and private image generation! 🎨










