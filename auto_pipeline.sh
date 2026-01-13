#!/bin/bash

# Auto-Pipeline: One-command document processing
# Usage: ./auto_pipeline.sh [file.pdf]

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         🤖 Automated RAG Pipeline                           ║"
echo "╔══════════════════════════════════════════════════════════════╗"
echo ""

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Error: .venv not found. Run ./setup.sh first"
    exit 1
fi

# Check if specific file provided
if [ -n "$1" ]; then
    FILE="$1"
    
    if [ ! -f "$FILE" ]; then
        echo "❌ Error: File not found: $FILE"
        exit 1
    fi
    
    echo "📄 Processing single file: $(basename "$FILE")"
    echo ""
    
    # Phase 1: Extract
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 Phase 1: Extracting text..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    python3 phase1_extract.py --file "$FILE"
    
    if [ $? -ne 0 ]; then
        echo "❌ Phase 1 failed"
        exit 1
    fi
    
    echo ""
    echo "✅ Phase 1 complete"
    echo ""
    
    # Find the generated JSONL
    BASENAME=$(basename "$FILE" | sed 's/\.[^.]*$//')
    JSONL="documents/extracted_text/${BASENAME}_pages.jsonl"
    
    if [ ! -f "$JSONL" ]; then
        echo "❌ Error: JSONL not found: $JSONL"
        exit 1
    fi
    
    # Phase 2: Embed
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧩 Phase 2: Creating embeddings..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    python3 phase2_embed.py --file "$JSONL"
    
    if [ $? -ne 0 ]; then
        echo "❌ Phase 2 failed"
        exit 1
    fi
    
    echo ""
    echo "✅ Phase 2 complete"
    echo ""
    
else
    # Process all unprocessed files
    echo "📚 Processing all documents in documents/ folder"
    echo ""
    
    # Phase 1: Extract all
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 Phase 1: Extracting text from all documents..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    python3 phase1_extract.py --all
    
    if [ $? -ne 0 ]; then
        echo "❌ Phase 1 failed"
        exit 1
    fi
    
    echo ""
    echo "✅ Phase 1 complete"
    echo ""
    
    # Phase 2: Embed all
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧩 Phase 2: Creating embeddings for all documents..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    python3 phase2_embed.py --all
    
    if [ $? -ne 0 ]; then
        echo "❌ Phase 2 failed"
        exit 1
    fi
    
    echo ""
    echo "✅ Phase 2 complete"
    echo ""
fi

# Mark completion
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         🎉 Pipeline Complete!                               ║"
echo "╔══════════════════════════════════════════════════════════════╗"
echo ""
echo "✅ All documents processed and ready for querying"
echo ""
echo "🚀 Next steps:"
echo "   1. Make sure LM Studio is running with a model loaded"
echo "   2. Start the RAG server: ./run.sh"
echo "   3. Open browser: http://localhost:8000"
echo "   4. Ask questions about your documents!"
echo ""
