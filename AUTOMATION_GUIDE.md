# 🤖 Automated RAG Pipeline

## Overview

This RAG system now supports **fully automated document processing**. Just drop a PDF into the `documents/` folder and it will automatically:
1. Extract text
2. Generate embeddings
3. Make it queryable in the chatbot

## 🚀 Three Ways to Process Documents

### Method 1: Automatic File Watching (Recommended)

**Best for:** Continuous operation, processing multiple documents over time

```bash
# Terminal 1: Start the document watcher
./watch_and_process.sh

# Terminal 2: Start the RAG server
./run.sh

# Now just drop PDFs into documents/ folder!
cp ~/Downloads/new_book.pdf documents/
```

The watcher will:
- ✅ Detect new files automatically
- ✅ Process them through Phase 1 & 2
- ✅ Notify when complete
- ✅ Auto-reload the chatbot (new docs immediately queryable)

---

### Method 2: One-Command Pipeline

**Best for:** Processing specific files on-demand

```bash
# Process a specific file
./auto_pipeline.sh documents/my_book.pdf

# Or process all files at once
./auto_pipeline.sh
```

This runs both phases automatically and prepares everything for querying.

---

### Method 3: Manual Processing (Original)

**Best for:** Fine control, debugging, or step-by-step processing

```bash
# Step 1: Extract text
python phase1_extract.py --file documents/my_book.pdf

# Step 2: Create embeddings
python phase2_embed.py --file documents/extracted_text/my_book_pages.jsonl

# Start server
./run.sh
```

---

## 📋 Complete Workflow Examples

### Example 1: Start Fresh with Automatic Processing

```bash
# 1. Start the watcher (keeps running)
./watch_and_process.sh
```

In another terminal:
```bash
# 2. Start the RAG server
./run.sh
```

Now you're ready! Just drop PDFs into `documents/` and they'll auto-process.

---

### Example 2: Process Existing Documents

If you already have PDFs in `documents/` folder:

```bash
# Process all existing documents
./auto_pipeline.sh

# Then start the server
./run.sh
```

---

### Example 3: Add New Document to Running System

With both watcher and server running:

```bash
# Just copy the file - it auto-processes!
cp ~/Downloads/new_document.pdf documents/

# Watch the terminal - you'll see:
# 📄 New document detected: new_document.pdf
# 🚀 Starting pipeline...
# ✅ Phase 1 complete
# ✅ Phase 2 complete
# 🎉 SUCCESS! Ready for querying
# 🔄 Triggered backend reload
```

No need to restart anything - the chatbot immediately knows about the new document!

---

## 🎯 How It Works

### File Watcher (`watch_documents.py`)

Monitors the `documents/` folder for new files and:

1. **Detects** new PDFs/TXT/DOCX files
2. **Checks** if already processed (`.processed` marker)
3. **Runs Phase 1** (text extraction)
4. **Runs Phase 2** (embedding generation)
5. **Marks complete** (creates `.processed` file)
6. **Triggers reload** (chatbot auto-updates)

### Hot Reload System

The RAG backend checks for new documents before each query:
- Looks for `.reload_trigger` file
- Reloads database connection if found
- New documents immediately searchable

### Processing Markers

- `.processing` - Document is currently being processed
- `.processed` - Document has been successfully processed
- `.reload_trigger` - Signals backend to reload database

---

## 📊 Processing Status

### Check What's Been Processed

```bash
# List all documents
ls -la documents/

# Check for processed markers
ls documents/*.processed

# View watcher logs
tail -f watcher.log
```

### Reprocess a Document

```bash
# Remove the processed marker
rm documents/my_book.pdf.processed

# The watcher will auto-detect and reprocess
# Or manually process:
./auto_pipeline.sh documents/my_book.pdf
```

---

## ⚡ Performance Tips

### Large Documents (100+ MB)

The watcher processes in the background, so you can:
- Drop multiple files (they queue automatically)
- Continue using the chatbot while processing
- Check `watcher.log` for progress

### Multiple Documents

Processing times (on M4 Mac):
- Small PDF (1-10 MB): 1-2 minutes
- Medium PDF (10-50 MB): 3-8 minutes  
- Large PDF (50-100 MB): 10-20 minutes
- Very Large PDF (100+ MB): 20-40 minutes

### Timeouts

Built-in timeouts prevent hanging:
- Phase 1: 10 minutes max
- Phase 2: 30 minutes max

If timeout occurs, check `watcher.log` for errors.

---

## 🔧 Configuration

### Supported File Types

Currently supports:
- `.pdf` - PDF documents
- `.txt` - Plain text files
- `.docx` - Word documents

### Change Watch Directory

Edit `watch_documents.py`:
```python
DOCUMENTS_DIR = Path("documents")  # Change this
```

### Disable Hot Reload

If you want to manually control when new documents are loaded:

Edit `.env`:
```bash
AUTO_RELOAD=false
```

---

## 🐛 Troubleshooting

### Watcher Not Detecting Files

1. Check watcher is running: `ps aux | grep watch_documents`
2. Check file permissions: `ls -la documents/`
3. Check watcher logs: `tail -f watcher.log`

### Processing Failed

Check logs:
```bash
# Watcher logs
tail -50 watcher.log

# Server logs
tail -50 server.log
```

Common issues:
- Corrupted PDF → Try re-downloading
- Memory issues → Close other apps
- Permission errors → Check file ownership

### Backend Not Reloading

1. Check `.reload_trigger` file exists: `ls data/.reload_trigger`
2. Restart server: `pkill -f uvicorn && ./run.sh`
3. Check server logs for reload messages

### Document Shows as Processed But Not Queryable

Force reload:
```bash
# Trigger manual reload
touch data/.reload_trigger

# Or restart server
pkill -f uvicorn
./run.sh
```

---

## 🎓 Advanced Usage

### Custom Processing Pipeline

You can modify `watch_documents.py` to add:
- Custom preprocessing
- Quality checks
- Metadata extraction
- Format conversions

### Batch Processing

Process multiple files efficiently:
```bash
# Copy all files at once
cp ~/Documents/books/*.pdf documents/

# Watcher processes them in order
# Check progress: tail -f watcher.log
```

### Integration with Other Tools

The watcher can be modified to:
- Send notifications (email, Slack, etc.)
- Upload to cloud storage
- Generate reports
- Trigger webhooks

---

## 📈 Monitoring

### Real-time Monitoring

```bash
# Watch logs in real-time
tail -f watcher.log

# In another terminal, watch for new embeddings
watch -n 5 'ls -lh data/index/docs.lance/'
```

### Processing Statistics

The watcher logs include:
- Total pages processed
- Total chunks created
- Processing time
- Success/failure status

---

## 🎉 Benefits

### Compared to Manual Processing

| Feature | Manual | Automated |
|---------|--------|-----------|
| Detect new files | ❌ Manual | ✅ Automatic |
| Run pipeline | ❌ 2 commands | ✅ Automatic |
| Reload backend | ❌ Restart | ✅ Hot reload |
| Monitor progress | ❌ Manual | ✅ Logs |
| Error handling | ❌ Manual | ✅ Automatic retry |
| Time saved | 0 | ~5 min per document |

### Production Ready

- ✅ Handles errors gracefully
- ✅ Prevents duplicate processing
- ✅ Supports concurrent operations
- ✅ Logs all activities
- ✅ Zero downtime document addition

---

## 🚦 Quick Start Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Start watcher: `./watch_and_process.sh`
- [ ] Start server: `./run.sh` (in new terminal)
- [ ] Drop PDF into `documents/`
- [ ] Wait for "SUCCESS!" message
- [ ] Query in chatbot at `http://localhost:8000`

**That's it!** Your RAG system is now fully automated. 🎉
