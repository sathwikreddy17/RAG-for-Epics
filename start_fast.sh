#!/bin/bash

# Fast RAG - Disable reranker for speed, keep 2026 retrieval upgrades enabled

echo "🚀 Starting FAST RAG System (No Reranker)"
echo ""

# Kill existing
pkill -9 -f "uvicorn app.main:app"
sleep 2

cd "/Users/sathwikreddy/Projects/Model Training/Codebase"
source .venv/bin/activate

# Export settings
export STRICT_MODEL_CHECK=false
export USE_RERANKER=false

# 2026 features ON (fast mode still benefits from these)
export USE_HYBRID_SEARCH=true
export USE_QUERY_ROUTING=true
export USE_CONTEXT_COMPRESSION=true

# Retrieval defaults for fast mode
export TOP_K_INITIAL=10
export TOP_K_FINAL=5

echo "Settings:"
echo "- Model Check: DISABLED (use any model)"
echo "- Reranker: DISABLED (fast mode)"
echo "- Hybrid Search: ENABLED"
echo "- Query Routing: ENABLED"
echo "- Context Compression: ENABLED"
echo "- Retrieval: 10 chunks total"
echo ""

# Start server
python3 -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

