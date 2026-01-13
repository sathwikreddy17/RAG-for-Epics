#!/bin/bash

# Local RAG System - Setup Script
# This script automates the initial setup process

set -e  # Exit on error

echo "======================================"
echo "  Local RAG System - Setup Script"
echo "======================================"
echo ""

# Check Python version
echo "🔍 Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "✅ Found Python $PYTHON_VERSION"
else
    echo "❌ Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet
echo "✅ pip upgraded"

# Install requirements
echo ""
echo "📚 Installing dependencies..."
echo "   (This may take a few minutes...)"

# Prefer the pinned, known-good runtime set if present to avoid dependency conflicts
if [ -f "requirements_fixed.txt" ]; then
    pip install -r requirements_fixed.txt --quiet
else
    pip install -r requirements.txt --quiet
fi

echo "✅ Dependencies installed"

# Create necessary directories
echo ""
echo "📁 Creating necessary directories..."
mkdir -p documents
mkdir -p documents/extracted_text
mkdir -p data/index
echo "✅ Directories created"

# Setup environment file
echo ""
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "======================================"
echo "  ✅ Setup Complete!"
echo "======================================"
echo ""
echo "📖 Next steps:"
echo ""
echo "1. Place your documents in the 'documents/' folder"
echo "   Example: cp /path/to/your/document.pdf documents/"
echo ""
echo "2. Extract text from documents:"
echo "   python phase1_extract.py --all"
echo ""
echo "3. Create embeddings:"
echo "   python phase2_embed.py --all"
echo ""
echo "4. Start LM Studio and load a model"
echo ""
echo "5. Start the RAG server:"
echo "   uvicorn app.main:app --reload --port 8000"
echo ""
echo "6. Open your browser:"
echo "   http://localhost:8000"
echo ""
echo "📚 For detailed instructions, see QUICK_START.md"
echo ""
