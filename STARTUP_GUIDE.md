# 🚀 Smart Startup Guide

## Quick Start - Just One Command!

```bash
./start_everything.sh
```

That's it! This command automatically checks everything before starting:

## What Gets Checked Automatically ✅

The `start_everything.sh` script performs 7 critical checks:

### 1. **Python Virtual Environment**
- Verifies `.venv` exists
- Activates it automatically

### 2. **Required Python Packages**
- fastapi
- uvicorn
- lancedb
- sentence_transformers
- watchdog

### 3. **LM Studio Status** ⭐ KEY CHECK
- Verifies LM Studio is running on http://localhost:1234
- Confirms a model is loaded
- Shows which model is active
- **If this fails**: Open LM Studio → Load any model → Start Server

### 4. **Vector Database**
- Checks if `data/index/docs.lance` exists
- Verifies it contains data
- Shows approximate number of indexed chunks

### 5. **Port Availability**
- Checks if port 8000 is free
- Automatically stops conflicting processes
- Ensures clean startup

### 6. **Directory Structure**
- Verifies all required folders exist
- Creates missing directories automatically

### 7. **Required Files**
- Validates core application files are present
- Lists any missing files

---

## What Happens After Checks Pass ✅

1. **Stops** any existing server instances
2. **Starts** the FastAPI server in background
3. **Waits** for server to be ready (health check)
4. **Displays** access information:
   - Frontend URL: http://localhost:8000
   - Health API: http://localhost:8000/api/health
   - Log file: `server.log`

---

## If Checks Fail ❌

The script will:
- Show exactly what's wrong with ❌ markers
- Provide specific commands to fix each issue
- **NOT start the server** until all issues are resolved

### Common Issues & Fixes:

**LM Studio Not Running:**
```bash
# Open LM Studio application
# Go to "Local Server" tab
# Load a model (any model works)
# Click "Start Server"
# Wait for green "Server Running" indicator
# Then re-run: ./start_everything.sh
```

**Missing Packages:**
```bash
pip install -r requirements.txt
```

**No Database:**
```bash
./auto_pipeline.sh  # Process all documents
```

---

## Manual Controls

### Start Everything (Smart):
```bash
./start_everything.sh
```

### Stop Server:
```bash
pkill -f 'uvicorn app.main:app'
```

### Check Server Status:
```bash
curl http://localhost:8000/api/health | python3 -m json.tool
```

### View Logs:
```bash
tail -f server.log
```

### Process New Documents:
```bash
./auto_pipeline.sh
# OR enable auto-watching:
./watch_and_process.sh
```

---

## The Complete Workflow

### First Time Setup:
```bash
# 1. Ensure LM Studio is running with a model
# 2. Run smart startup
./start_everything.sh

# 3. Open browser
open http://localhost:8000
```

### Daily Usage:
```bash
# Just one command:
./start_everything.sh

# It checks EVERYTHING automatically!
```

### Adding New Documents:
```bash
# Option 1: Automatic (recommended)
./watch_and_process.sh  # Leave running
# Drop PDFs into documents/ folder
# They process automatically

# Option 2: Manual batch
cp your_new.pdf documents/
./auto_pipeline.sh
```

---

## Pre-flight Checks in Detail

### Why Each Check Matters:

| Check | Why It's Important | Fix If Failed |
|-------|-------------------|---------------|
| **Virtual Env** | Isolated dependencies | `python3 -m venv .venv` |
| **Packages** | Required libraries | `pip install -r requirements.txt` |
| **LM Studio** | 🔴 Critical for Q&A | Open app, load model, start server |
| **Database** | Source of knowledge | `./auto_pipeline.sh` |
| **Port 8000** | Server must listen | Script auto-fixes this |
| **Directories** | File organization | Script auto-creates |
| **Files** | Core application code | Check git status |

---

## Success Indicators

When everything is working, you'll see:

```
✅ All checks passed! Ready to start.
✅ Server starting (PID: XXXXX)
✅ Server is ready!

🎉 System Ready!

Frontend URL:  http://localhost:8000
```

---

## Troubleshooting

### "LM Studio not accessible"
**Cause**: LM Studio app not running or server not started  
**Fix**: Open LM Studio → Local Server → Start Server → Green indicator

### "Model loaded but server not responding"
**Cause**: LM Studio server starting up  
**Fix**: Wait 10 seconds, run `./start_everything.sh` again

### "Port 8000 already in use"
**Cause**: Old server still running  
**Fix**: Script automatically handles this! If not: `pkill -f uvicorn`

### "Database appears empty"
**Cause**: No documents processed yet  
**Fix**: `./auto_pipeline.sh` to process all PDFs

---

## Pro Tips 💡

1. **Always use `./start_everything.sh`** - Never start manually
2. **Check LM Studio first** - Most common issue
3. **Keep LM Studio running** - Don't close it while using the system
4. **Use any model** - System accepts all models (STRICT_CHECK disabled)
5. **Faster models recommended** - Qwen 2.5 Coder 7B/14B for speed

---

## Quick Commands Reference

```bash
# Start everything with checks
./start_everything.sh

# Stop server
pkill -f 'uvicorn app.main:app'

# Check health
curl http://localhost:8000/api/health | python3 -m json.tool

# View logs
tail -f server.log

# Process documents
./auto_pipeline.sh

# Enable auto-processing
./watch_and_process.sh
```

---

## File Organization

```
.
├── start_everything.sh      ⭐ NEW! Smart startup with checks
├── auto_pipeline.sh          📦 Batch process all PDFs
├── watch_and_process.sh      👁️  Auto-watch for new PDFs
├── server.log                📋 Server output logs
├── watcher.log               📋 File watcher logs
└── documents/                📁 Drop PDFs here
```

---

## System Architecture

```
┌─────────────────┐
│   LM Studio     │ ← Must be running with model loaded
│   :1234         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   RAG Server    │ ← Started by start_everything.sh
│   :8000         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Vector DB      │ ← Auto-reloads when documents change
│  (LanceDB)      │
└─────────────────┘
```

---

## Success Checklist

Before reporting issues, verify:
- [ ] LM Studio app is open
- [ ] A model is loaded in LM Studio
- [ ] LM Studio server is running (green indicator)
- [ ] `./start_everything.sh` shows all ✅ checks
- [ ] You can access http://localhost:8000
- [ ] Database has documents (shown in pre-flight)

---

## Current System Status

✅ **Server Running**: PID 51985  
✅ **Model Loaded**: openai/gpt-oss-20b  
✅ **Database**: ~9,199 chunks indexed  
✅ **Port**: 8000 available  
✅ **Frontend**: http://localhost:8000  

**You're ready to use the system!**
