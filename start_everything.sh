#!/bin/bash

# Smart Startup Script - Checks everything before starting
# This ensures all prerequisites are met before launching the RAG system

set -e  # Exit on any error

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                          ║"
echo "║              🚀 Smart RAG System Startup                                ║"
echo "║              Running Pre-flight Checks...                               ║"
echo "║                                                                          ║"
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CHECKS_PASSED=true

# ============================================================================
# CHECK 1: Python Virtual Environment
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 1: Python Virtual Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d ".venv" ]; then
    echo -e "${GREEN}✅ Virtual environment found${NC}"
    source .venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "   Run: python3 -m venv .venv"
    CHECKS_PASSED=false
fi
echo ""

# ============================================================================
# CHECK 2: Required Python Packages
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 2: Required Python Packages"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REQUIRED_PACKAGES=("fastapi" "uvicorn" "lancedb" "sentence_transformers" "watchdog")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python -c "import $package" 2>/dev/null; then
        echo -e "${GREEN}✅ $package installed${NC}"
    else
        echo -e "${RED}❌ $package missing${NC}"
        MISSING_PACKAGES+=("$package")
        CHECKS_PASSED=false
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}💡 Install missing packages:${NC}"
    echo "   pip install ${MISSING_PACKAGES[@]}"
fi
echo ""

# ============================================================================
# CHECK 3: LM Studio Running
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 3: LM Studio Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if curl -s --max-time 2 http://localhost:1234/v1/models >/dev/null 2>&1; then
    echo -e "${GREEN}✅ LM Studio is running (http://localhost:1234)${NC}"
    
    # Check if a model is loaded
    MODEL_CHECK=$(curl -s --max-time 2 http://localhost:1234/v1/models)
    if echo "$MODEL_CHECK" | grep -q "id"; then
        echo -e "${GREEN}✅ Model loaded in LM Studio${NC}"
        MODEL_NAME=$(echo "$MODEL_CHECK" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', [{}])[0].get('id', 'Unknown'))" 2>/dev/null || echo "Unknown")
        echo -e "   Model: ${YELLOW}$MODEL_NAME${NC}"
    else
        echo -e "${YELLOW}⚠️  LM Studio running but no model loaded${NC}"
        echo "   Open LM Studio and load a model, then start the server"
        CHECKS_PASSED=false
    fi
else
    echo -e "${RED}❌ LM Studio not accessible${NC}"
    echo "   1. Open LM Studio application"
    echo "   2. Go to 'Local Server' tab"
    echo "   3. Load a model (any model works)"
    echo "   4. Click 'Start Server'"
    echo "   5. Wait for 'Server Running' message"
    CHECKS_PASSED=false
fi
echo ""

# ============================================================================
# CHECK 4: Database Availability
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 4: Vector Database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d "data/index/docs.lance" ]; then
    echo -e "${GREEN}✅ Vector database found${NC}"
    
    # Count approximate chunks
    FILE_COUNT=$(find data/index/docs.lance/data -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "$FILE_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ Database contains data${NC}"
        echo "   Files: ~$FILE_COUNT data files"
    else
        echo -e "${YELLOW}⚠️  Database exists but appears empty${NC}"
        echo "   Process documents: ./auto_pipeline.sh"
    fi
else
    echo -e "${YELLOW}⚠️  No vector database found${NC}"
    echo "   This is OK if you're starting fresh"
    echo "   Process documents: ./auto_pipeline.sh"
fi
echo ""

# ============================================================================
# CHECK 5: Port Availability
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 5: Port Availability"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use${NC}"
    PID=$(lsof -Pi :8000 -sTCP:LISTEN -t)
    echo "   Process PID: $PID"
    echo -e "${YELLOW}   Stopping existing server...${NC}"
    kill -9 $PID 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✅ Port 8000 is now free${NC}"
else
    echo -e "${GREEN}✅ Port 8000 is available${NC}"
fi
echo ""

# ============================================================================
# CHECK 6: Directory Structure
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 6: Directory Structure"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DIRS=("documents" "documents/extracted_text" "data" "data/index" "app" "app/templates")
for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ $dir${NC}"
    else
        echo -e "${YELLOW}⚠️  Creating $dir${NC}"
        mkdir -p "$dir"
    fi
done
echo ""

# ============================================================================
# CHECK 7: Required Files
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 7: Required Files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REQUIRED_FILES=("app/main.py" "app/rag_backend.py" "app/templates/index.html" "phase1_extract.py" "phase2_embed.py")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ Missing: $file${NC}"
        CHECKS_PASSED=false
    fi
done
echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                      Pre-flight Check Summary                           ║"
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo ""

if [ "$CHECKS_PASSED" = true ]; then
    echo -e "${GREEN}✅ All checks passed! Ready to start.${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Starting RAG Server..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Stop any existing server
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    sleep 2
    
    # Start server in background
    nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
    SERVER_PID=$!
    
    echo -e "${GREEN}✅ Server starting (PID: $SERVER_PID)${NC}"
    echo ""
    
    # Wait for server to be ready
    echo "Waiting for server to be ready..."
    for i in {1..10}; do
        if curl -s --max-time 1 http://localhost:8000/api/health >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Server is ready!${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    echo ""
    echo ""
    
    # Display access information
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║                      🎉 System Ready!                                   ║"
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo ""
    echo -e "${GREEN}Frontend URL:${NC}  http://localhost:8000"
    echo -e "${GREEN}Health Check:${NC} http://localhost:8000/api/health"
    echo -e "${GREEN}Server Logs:${NC}  tail -f server.log"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 Next Steps:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "1. Open: http://localhost:8000"
    echo "2. Ask questions about your documents"
    echo "3. Monitor: tail -f server.log"
    echo ""
    echo "To stop server: pkill -f 'uvicorn app.main:app'"
    echo ""
    
else
    echo -e "${RED}❌ Some checks failed. Please fix the issues above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  • Install packages: pip install -r requirements.txt"
    echo "  • Start LM Studio: Open app → Load model → Start server"
    echo "  • Process documents: ./auto_pipeline.sh"
    echo ""
    exit 1
fi
