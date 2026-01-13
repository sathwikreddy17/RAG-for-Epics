# 🎯 AUTOMATION QUICK START

Drop a PDF → Auto-processes → Chatbot ready!

## 30-Second Setup

```bash
# 1. Setup (one time)
./setup_with_automation.sh

# 2. Start watcher (Terminal 1)
./watch_and_process.sh

# 3. Start server (Terminal 2)
./run.sh

# 4. Drop PDF
cp ~/Downloads/book.pdf documents/

# 5. Wait 2-5 minutes
# 6. Ask questions at http://localhost:8000
```

Done! 🎉

---

## What Happens Automatically

```
You drop PDF
    ↓
📄 Watcher detects it
    ↓
📝 Phase 1: Extract text (30 sec)
    ↓
🧩 Phase 2: Create embeddings (1-5 min)
    ↓
🔄 Backend auto-reloads
    ↓
✅ Document ready to query!
```

**No manual commands needed!**

---

## Workflows

### Workflow 1: Continuous Operation (Best)

Start once, runs forever:
```bash
# Terminal 1
./watch_and_process.sh

# Terminal 2  
./run.sh

# Now just drop PDFs anytime - they auto-process!
```

### Workflow 2: Process Existing Files

```bash
./auto_pipeline.sh    # Process all in documents/
./run.sh             # Start server
```

### Workflow 3: Process Single File

```bash
./auto_pipeline.sh documents/mybook.pdf
./run.sh
```

---

## Status Checks

```bash
# Is watcher running?
ps aux | grep watch_documents

# Watch processing live
tail -f watcher.log

# Check what's processed
ls documents/*.processed

# Check database size
du -h data/index/
```

---

## Troubleshooting

**Watcher not working?**
```bash
# Check if installed
pip install watchdog

# Restart watcher
pkill -f watch_documents
./watch_and_process.sh
```

**Document not showing up?**
```bash
# Force reload
touch data/.reload_trigger

# Or restart server
pkill -f uvicorn
./run.sh
```

**Reprocess a document?**
```bash
rm documents/mybook.pdf.processed
# Watcher will auto-detect and reprocess
```

---

## File Markers

- `mybook.pdf` - Your original document
- `mybook.pdf.processing` - Currently processing (temporary)
- `mybook.pdf.processed` - Successfully processed (permanent)
- `.reload_trigger` - Signals backend to reload (temporary)

---

## Benefits

| Before | After (Automated) |
|--------|-------------------|
| 1. Run phase1_extract.py | ✅ Automatic |
| 2. Wait | ✅ Automatic |
| 3. Run phase2_embed.py | ✅ Automatic |
| 4. Wait | ✅ Automatic |
| 5. Restart server | ✅ Hot reload |
| 6. Test in UI | Same! |
| **~5 minutes manual work** | **~0 minutes** |

---

## Advanced

### Add Custom Processing
Edit `watch_documents.py`:
```python
def process_document(self, file_path: Path):
    # Add your custom steps here
    # e.g., format conversion, quality checks
```

### Notification on Complete
Add to `watch_documents.py`:
```python
# After processing
os.system('say "Document ready"')  # Mac
# or send email, Slack message, etc.
```

### Batch Upload
```bash
cp ~/Documents/*.pdf documents/
# All auto-process in order
```

---

## Production Tips

1. **Run watcher as service** (systemd/launchd)
2. **Monitor logs** with log aggregation
3. **Set up alerts** for failures
4. **Backup** `.processed` markers
5. **Use SSD** for faster processing

---

## Full Documentation

See `AUTOMATION_GUIDE.md` for complete details.

---

**That's it! Your RAG is now fully automated.** 🚀
