#!/bin/bash

# Complete Setup Script with Automation
# Sets up the RAG system with automatic document processing

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🚀 RAG System Setup - With Automation                   ║"
echo "╔══════════════════════════════════════════════════════════════╗"
echo ""

# Check Python version
echo "📋 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo "❌ Error: Python 3.10+ required, found $PYTHON_VERSION"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION detected"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "⚠️  Virtual environment already exists"
    read -p "Recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .venv
        python3 -m venv .venv
        echo "✅ Virtual environment recreated"
    else
        echo "⏭️  Using existing virtual environment"
    fi
else
    python3 -m venv .venv
    echo "✅ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate
echo "✅ Activated"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet
echo "✅ pip upgraded"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
echo "   This may take a few minutes..."
pip install -r requirements.txt --quiet

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    echo "   Try: pip install -r requirements.txt"
    exit 1
fi
echo "✅ Dependencies installed"
echo ""

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p documents
mkdir -p documents/extracted_text
mkdir -p data/index
echo "✅ Directories created"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env configuration..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ .env created from template"
    else
        echo "⚠️  .env.example not found, skipping"
    fi
else
    echo "✅ .env already exists"
fi
echo ""

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x run.sh
chmod +x auto_pipeline.sh
chmod +x watch_and_process.sh
chmod +x setup.sh
echo "✅ Scripts are executable"
echo ""

# Verify setup
echo "✅ Verifying setup..."
python3 -c "import lancedb, sentence_transformers, fastapi" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Core libraries verified"
else
    echo "⚠️  Warning: Some libraries may not be properly installed"
fi
echo ""

# Summary
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         ✅ Setup Complete!                                   ║"
echo "╔══════════════════════════════════════════════════════════════╗"
echo ""
echo "📚 What's installed:"
echo "   ✅ Python virtual environment (.venv)"
echo "   ✅ All dependencies (RAG, ML, automation)"
echo "   ✅ Directory structure"
echo "   ✅ Configuration files"
echo "   ✅ Automation scripts"
echo ""
echo "🎯 Next steps:"
echo ""
echo "   Option A: AUTOMATED (Recommended)"
echo "   ════════════════════════════════════"
echo "   1. Terminal 1: ./watch_and_process.sh"
echo "   2. Terminal 2: ./run.sh"
echo "   3. Drop PDFs into documents/ folder"
echo "   4. Open: http://localhost:8000"
echo ""
echo "   Option B: MANUAL"
echo "   ════════════════════════════════════"
echo "   1. Place documents in documents/ folder"
echo "   2. ./auto_pipeline.sh"
echo "   3. ./run.sh"
echo "   4. Open: http://localhost:8000"
echo ""
echo "📖 Documentation:"
echo "   • AUTOMATION_GUIDE.md - Full automation guide"
echo "   • README.md - Complete documentation"
echo "   • QUICK_START.md - Step-by-step tutorial"
echo ""
echo "💡 Pro tip: Start the watcher once and it runs forever!"
echo "   Just drop PDFs and they auto-process. No manual work!"
echo ""
