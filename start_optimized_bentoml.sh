#!/bin/bash
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
