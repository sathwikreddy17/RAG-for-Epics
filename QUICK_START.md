# 🚀 Quick Start Guide

## Prerequisites

1. **Python 3.10+** installed
2. **LM Studio** installed and running
3. **16GB+ RAM** recommended (24GB for large documents)
4. **Apple Silicon Mac** (or adapt for other systems)

## Installation

### 1. Create Virtual Environment

```bash
cd /Users/sathwikreddy/Projects/Model\ Training/Codebase
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Setup Environment

```bash
cp .env.example .env
# Edit .env if you need custom settings
```

## Usage

### Step 1: Prepare Documents

```bash
# Create documents directory if it doesn't exist
mkdir -p documents

# Copy your PDF, DOCX, or TXT files to the documents/ folder
cp /path/to/your/document.pdf documents/
```

### Step 2: Extract Text (Phase 1)

```bash
# Extract text from all documents
python phase1_extract.py --all

# Or extract from a specific file
python phase1_extract.py --file documents/your_document.pdf

# Interactive mode (default)
python phase1_extract.py
```

This creates JSONL files in `documents/extracted_text/`

### Step 3: Create Embeddings (Phase 2)

```bash
# Process all extracted documents
python phase2_embed.py --all

# Or process a specific file
python phase2_embed.py --file documents/extracted_text/your_document_pages.jsonl

# Test mode (first 50 pages only)
python phase2_embed.py --test 50

# Interactive mode (default)
python phase2_embed.py
```

This creates the vector database in `data/index/`

### Step 4: Test the System

```bash
# Test retrieval
python test_retrieval.py
```

### Step 5: Start LM Studio

1. Open LM Studio application
2. Load a model (e.g., Qwen 2.5 Coder 14B, Llama, Mistral)
3. Start the local server (usually on port 1234)
4. Verify it's running: `curl http://localhost:1234/v1/models`

### Step 6: Start the RAG Server

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --port 8000 --workers 2
```

### Step 7: Access the UI

Open your browser and navigate to:
```
http://localhost:8000
```

## Quick Commands Reference

```bash
# Activate environment
source .venv/bin/activate

# Full processing pipeline
python phase1_extract.py --all && python phase2_embed.py --all

# Start server
uvicorn app.main:app --reload --port 8000

# Test everything
python test_retrieval.py

# Check health
curl http://localhost:8000/api/health
```

## Troubleshooting

### "No module named 'fitz'"
```bash
pip install PyMuPDF
```

### "LM Studio not reachable"
- Ensure LM Studio is running
- Check if a model is loaded
- Verify the URL in `.env` (default: http://localhost:1234/v1)

### "Table 'docs' not found"
- Run phase1_extract.py first
- Then run phase2_embed.py
- Check `data/index/` directory exists

### Memory issues during Phase 2
Edit `.env` and reduce:
```bash
EMBEDDING_BATCH_SIZE=2
MAX_MEMORY_CHUNKS=10
```

### Port 8000 already in use
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001

# Or find and kill the process
lsof -ti:8000 | xargs kill -9
```

## Example Workflow

```bash
# 1. Setup (one-time)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# 2. Add documents
cp ~/Documents/mybook.pdf documents/

# 3. Process documents
python phase1_extract.py --all
python phase2_embed.py --all

# 4. Start LM Studio (in separate terminal/app)
# Load your preferred model

# 5. Start RAG server
uvicorn app.main:app --reload --port 8000

# 6. Open browser to http://localhost:8000
```

## Next Steps

- Check `README.md` for detailed documentation
- See example queries in the UI
- Explore API endpoints at http://localhost:8000/docs
- Add more documents anytime by repeating steps 2-3

## Performance Tips

1. **First run:** Process a small test document first
2. **Large PDFs:** Use Phase 1 & 2 separately with checkpoints
3. **Multiple documents:** Process incrementally, one at a time
4. **Model selection:** Smaller models (7B) are faster, larger (14B+) are more accurate
5. **Batch sizes:** Reduce if you experience memory issues

## Common Questions

**Q: How long does processing take?**
A: Depends on document size. ~1-2 minutes per 100 pages on M4 Mac.

**Q: Can I add more documents later?**
A: Yes! Just run Phase 1 & 2 again. New documents are added to existing database.

**Q: Do I need internet?**
A: No! Everything runs locally once models are downloaded.

**Q: Can I use different LLMs?**
A: Yes! Any model in LM Studio works. Just load it and restart the RAG server.

**Q: How much disk space needed?**
A: ~2-5GB for models, ~100-500MB per large document processed.
