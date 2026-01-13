# 🎯 START HERE - RAG 2026 Upgrade (Active)

This system is running **Best-in-Class RAG 2026** features.

---

## ✅ Current Runtime State (as configured)

The 2026 features are controlled via `.env` and are intended to be ON:

- `USE_HYBRID_SEARCH=true`
- `USE_QUERY_ROUTING=true`
- `USE_CONTEXT_COMPRESSION=true`

Also available:
- OCR extraction in `phase1_extract.py` (`--ocr`, `--ocr-lang`)
- Optional ingestion-time translation in `phase2_embed.py` (LM Studio)

---

## 🚀 What To Do Now (Typical Workflow)

### 1) Install dependencies
```bash
pip install -r requirements.txt
```

### 2) Ingest / update documents
```bash
python phase1_extract.py --all
python phase2_embed.py --all
```

**OCR example (Sanskrit):**
```bash
python phase1_extract.py --all --ocr --ocr-lang san
python phase2_embed.py --all
```

### 3) Build BM25 index (recommended after ingestion)
```bash
python build_bm25_index.py
```

### 4) Start server
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## ✅ Verify It Worked

Health:
```bash
curl -s http://localhost:8000/api/health | python -m json.tool
```

Stats:
```bash
curl -s http://localhost:8000/api/stats | python -m json.tool
```

Ask:
```bash
curl -s -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Who is Sugreeva?"}' | python -m json.tool
```

---

## 📌 Notes

- The older docs may mention `/status` or `/query`; the current API is under `/api/*` (e.g. `/api/health`, `/api/ask`).
- Rebuild BM25 whenever you add/translate new content.

---

## 📚 Where to Read More

- `README.md` - Complete overview + OCR/translation
- `IMPLEMENTATION_COMPLETE.md` - 2026 upgrade design details
- `ACTIVATION_CHECKLIST.md` - Step-by-step activation details (some endpoints may be legacy)
