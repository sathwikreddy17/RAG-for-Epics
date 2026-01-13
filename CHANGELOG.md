# 📋 Changelog

All notable changes to this RAG system are documented here.

---

## [2.2.0] - January 11, 2026

### ✨ New Features

#### Query History
- **New File:** `app/query_history.py` (260+ lines)
- **Capabilities:**
  - Stores recent queries with answer previews
  - Persistent storage (survives server restarts)
  - Search through past queries
  - Click to re-run any previous query
  - Delete individual entries or clear all
  - Maximum 100 entries (configurable)
  - Automatic duplicate prevention
- **New API Endpoints:**
  - `GET /api/history` - Get recent query history
  - `GET /api/history?search=term` - Search history
  - `GET /api/history/{id}` - Get specific entry
  - `DELETE /api/history/{id}` - Delete entry
  - `DELETE /api/history` - Clear all history

### 🎨 UI Improvements
- Added history sidebar panel (toggle with 📜 History button)
- Search bar in history sidebar
- Click history item to re-run query
- Individual delete buttons on history items
- "Clear All" button in history footer
- Query count display

---

## [2.1.0] - January 11, 2026

### ✨ New Features

#### Streaming Responses (SSE)
- **Files Changed:** `app/rag_backend.py`, `app/main.py`, `app/templates/index.html`
- **Capabilities:**
  - Real-time LLM output using Server-Sent Events
  - Sources displayed immediately before answer starts streaming
  - Toggle between streaming and non-streaming modes in UI
  - Visual streaming indicator while generating
- **New API Endpoint:**
  - `POST /api/ask/stream` - Returns SSE stream with events:
    - `sources` - Retrieved documents
    - `token` - Individual LLM tokens
    - `done` - Final metadata
    - `error` - Error messages

#### Source Text Highlighting
- **New File:** `app/text_highlighter.py` (180+ lines)
- **Capabilities:**
  - Highlights query keywords in source passages
  - Intelligent stopword filtering
  - Proper noun detection
  - Configurable highlight limits
  - Toggle highlighting in UI
- **New API Endpoint:**
  - `POST /api/highlight` - Highlight terms in any text

#### Export Results
- **New File:** `app/result_exporter.py` (280+ lines)
- **Capabilities:**
  - Export answers and sources to multiple formats:
    - **Markdown** - Clean, portable documentation
    - **HTML** - Standalone styled webpage (printable)
    - **JSON** - Machine-readable format
  - Download buttons in UI after each query
  - Automatic timestamp and metadata inclusion
- **New API Endpoint:**
  - `POST /api/export` - Export results to file download

### 🎨 UI Improvements
- Added streaming toggle checkbox
- Added highlighting toggle checkbox
- Added export control buttons
- Streaming indicator animation
- Highlighted text styling with gradient background

---

## [2.0.0] - January 11, 2026

### 🐛 Bug Fixes

#### Context Length Overflow
- **Problem:** Complex queries caused LLM context overflow
- **Solution:** 
  - Added `MAX_CONTEXT_CHARS=6000` configuration
  - Implemented smart truncation at sentence boundaries
  - Limited query decomposition to 3 sub-queries, 3 docs each
- **Files Changed:** `app/rag_backend.py`, `.env`

#### LLM Hallucination (Factual Errors)
- **Problem:** LLM incorrectly stated "Kaikeyi was daughter of Dasaratha's second wife"
- **Solution:**
  - Updated system prompt with strict factual guidelines
  - Added rule: "NEVER infer or assume relationships not directly stated"
  - Reduced temperature from 0.1 to 0.05
- **Files Changed:** `app/rag_backend.py`

### ✨ New Features

#### Spelling Suggestions System
- **New File:** `app/spelling_suggester.py` (400+ lines)
- **Capabilities:**
  - Extracts entities from indexed documents (11,864 entities)
  - Three matching methods:
    1. Simplified key (handles transliterations like meganath→Meghanada)
    2. Phonetic matching (similar sounds)
    3. Fuzzy matching (edit distance)
  - Autocomplete suggestions while typing
  - "Did you mean?" suggestions for poor results
- **New API Endpoints:**
  - `GET /api/autocomplete?q=<prefix>&limit=10`
  - `GET /api/spelling/suggest?query=<text>`
  - `GET /api/spelling/stats`
  - `POST /api/spelling/rebuild`

#### Expandable Source Cards
- **File Changed:** `app/templates/index.html`
- **Features:**
  - Click any source card to expand
  - View full passage text (scrollable, max 400px)
  - "Copy Text" button
  - "Collapse" button
  - Smooth animations
  - Visual expand indicator (▶ rotates when expanded)

#### Frontend Enhancements
- **File Changed:** `app/templates/index.html`
- **New UI Components:**
  - Autocomplete dropdown with keyboard navigation
  - "Did you mean?" clickable banner
  - Source expansion with full text view
  - Copy to clipboard functionality

### 📝 Documentation

- Created `FULL_SYSTEM_DOCUMENTATION.md` - Complete A-Z documentation
- Updated `README.md` - Concise overview with links
- Created `CHANGELOG.md` - This file

---

## [1.0.0] - January 2026 (Initial Release)

### Features
- ✅ Hybrid Search (BM25 + Vector + RRF)
- ✅ Query Routing
- ✅ Context Compression
- ✅ Cross-encoder Reranking
- ✅ Quality Filtering
- ✅ Evidence Extraction
- ✅ Diversity/MMR Ranking
- ✅ Query Decomposition
- ✅ Feedback Collection
- ✅ Response Cache
- ✅ Two-phase ingestion (extract → embed)
- ✅ OCR support for scanned PDFs
- ✅ Modern glassmorphism UI

---

## Configuration Changes

### New in .env

```bash
# Added in 2.0.0
MAX_CONTEXT_CHARS=6000
MAX_SUB_QUERIES=3
MAX_DOCS_PER_SUBQUERY=3

# Changed in 2.0.0
LLM_TEMPERATURE=0.05  # Was 0.1
```

---

## API Changes

### New Endpoints (2.0.0)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/autocomplete` | GET | Autocomplete suggestions |
| `/api/spelling/suggest` | GET | Spelling corrections |
| `/api/spelling/stats` | GET | Index statistics |
| `/api/spelling/rebuild` | POST | Rebuild spelling index |

### Modified Responses (2.0.0)

`POST /api/ask` now includes:
```json
{
  "metadata": {
    "context_truncated": true,  // NEW
    "did_you_mean": "Meghanada"  // NEW
  }
}
```

---

## File Changes Summary

### New Files
- `app/spelling_suggester.py`
- `data/spelling/entities.json`
- `FULL_SYSTEM_DOCUMENTATION.md`
- `CHANGELOG.md`

### Modified Files
- `app/main.py` - Added spelling endpoints, autocomplete
- `app/rag_backend.py` - Context limits, better prompts
- `app/templates/index.html` - Autocomplete, expandable sources
- `.env` - New configuration options
- `README.md` - Updated documentation

---

*Maintained by: RAG System Team*
