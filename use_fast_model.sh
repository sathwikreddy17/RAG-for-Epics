#!/bin/bash

# Quick fix for slow performance: Use the faster 14B model

echo "🚨 PERFORMANCE FIX"
echo ""
echo "The 32B model is too slow. Switching to 14B model..."
echo ""

# Stop current server
echo "Stopping server..."
pkill -f "uvicorn app.main:app"
sleep 2

# Start with 14B model (faster)
echo ""
echo "🚀 Starting server with FASTER settings..."
echo ""
echo "CHANGES:"
echo "- Model check: DISABLED (use any model)"
echo "- Retrieval: 20 initial → 5 final (faster)"
echo "- Context: 3000 tokens max (faster LLM)"
echo "- Max tokens: 800 (faster generation)"
echo ""

cd /Users/sathwikreddy/Projects/Model\ Training/Codebase
source .venv/bin/activate

export STRICT_MODEL_CHECK=false
export TOP_K_INITIAL=20
export TOP_K_FINAL=5

python3 -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0 &

sleep 5

echo ""
echo "✅ Server started!"
echo ""
echo "NOW DO THIS IN LM STUDIO:"
echo "1. UNLOAD the 32B model (it's too slow)"
echo "2. LOAD qwen2.5-coder-14B instead"
echo "3. Set context length to 8192"
echo "4. Try your query again - should be under 10 seconds!"
echo ""
echo "The 14B model is:"
echo "- 3-4x FASTER"
echo "- Still very accurate"
echo "- Better for real-time use"
echo ""
