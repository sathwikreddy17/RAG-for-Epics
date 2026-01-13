#!/bin/bash

# Watch and Process: Automatic document processing service
# Drop PDFs into documents/ and they auto-process

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      🔭 Document Watcher - Auto Processing Service          ║"
echo "╔══════════════════════════════════════════════════════════════╗"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "   Run ./setup.sh first to set up the environment"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Check if watchdog is installed
if ! python3 -c "import watchdog" 2>/dev/null; then
    echo "📦 Installing watchdog library..."
    pip install watchdog
    echo "✅ Watchdog installed"
    echo ""
fi

# Start the watcher
echo "🚀 Starting document watcher service..."
echo ""
python3 watch_documents.py
