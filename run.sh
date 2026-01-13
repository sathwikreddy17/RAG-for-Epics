#!/bin/bash

# Local RAG System - Run Script
# Quick script to start the RAG server

set -e

echo "======================================"
echo "  Starting Local RAG System"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run: ./setup.sh"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Check if data directory exists
if [ ! -d "data/index" ] || [ -z "$(ls -A data/index 2>/dev/null)" ]; then
    echo ""
    echo "⚠️  Warning: Vector database not found!"
    echo "   Please run document processing first:"
    echo "   1. python phase1_extract.py --all"
    echo "   2. python phase2_embed.py --all"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if LM Studio is running
echo ""
echo "🔍 Checking LM Studio connection..."
if curl -s -f -o /dev/null http://localhost:1234/v1/models; then
    echo "✅ LM Studio is running"
else
    echo "⚠️  Warning: Cannot connect to LM Studio"
    echo "   Make sure LM Studio is running and a model is loaded"
    echo "   Default URL: http://localhost:1234"
    echo ""
fi

# Start the server
echo ""
echo "🚀 Starting RAG server on http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""
echo "======================================"
echo ""

uvicorn app.main:app --reload --port 8000
