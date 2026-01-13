# 📚 Complete RAG System Documentation

> **Last Updated:** January 11, 2026  
> **Version:** 2.1 (with Streaming, Highlighting & Export)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [All Features (15 Total)](#3-all-features-15-total)
4. [Installation & Setup](#4-installation--setup)
5. [Configuration Reference](#5-configuration-reference)
6. [API Reference](#6-api-reference)
7. [Frontend Features](#7-frontend-features)
8. [File Structure](#8-file-structure)
9. [Troubleshooting](#9-troubleshooting)
10. [Recent Changes & Bug Fixes](#10-recent-changes--bug-fixes)
11. [Performance Tuning](#11-performance-tuning)
12. [Future Roadmap](#12-future-roadmap)

---

## 1. System Overview

### What Is This?

A **fully local, offline RAG (Retrieval-Augmented Generation) system** designed for:
- Large document corpora (epics, religious texts, historical documents)
- Indian language transliterations and name variations
- Privacy-first operation (everything runs locally)
- Production-quality answers with source citations

### Key Highlights

| Aspect | Details |
|--------|---------|
| **LLM** | LM Studio (local, any model) |
| **Vector DB** | LanceDB (embedded, fast) |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **Reranker** | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| **Search** | Hybrid (BM25 + Vector + RRF fusion) |
| **Frontend** | Modern glassmorphism UI |
| **Backend** | FastAPI with async support |
| **Streaming** | Real-time SSE responses ✨ NEW |

### Current Stats (Your Index)

- **Total Chunks:** 18,791
- **Indexed Entities:** 11,864+
- **Features:** 15 (all working ✅)
- **Documents:** Ramayana texts (Valmiki, Hari Prasad Shastri translations)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  • Autocomplete Dropdown (as-you-type suggestions)      │   │
│   │  • "Did You Mean?" Banner (spelling corrections)        │   │
│   │  • Expandable Source Cards (click to see full text)     │   │
│   │  • Feedback Buttons (👍/👎)                              │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI BACKEND                          │
│   Endpoints: /api/ask, /api/autocomplete, /api/health, etc.    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RAG PIPELINE                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Query   │→ │  Query   │→ │  Hybrid  │→ │ Reranker │        │
│  │ Classify │  │Decompose │  │  Search  │  │(CrossEnc)│        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│       │              │             │              │              │
│       ▼              ▼             ▼              ▼              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Context  │← │ Evidence │← │ Diversity│← │ Quality  │        │
│  │Compress  │  │ Extract  │  │  (MMR)   │  │ Filter   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               LLM (LM Studio @ localhost:1234)            │  │
│  │   • Strict factual prompts • Temperature: 0.05            │  │
│  │   • Context limit: 6000 chars • No hallucinations         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  LanceDB    │  │  BM25 Index │  │   Spelling Index        │ │
│  │ (./data/    │  │ (./data/    │  │ (./data/spelling/       │ │
│  │   index)    │  │  bm25_index)│  │   entities.json)        │ │
│  │ 18,791 docs │  │             │  │ 11,864 entities         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. All Features (15 Total)

### Feature Summary Table

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 1 | Hybrid Search | ✅ Active | BM25 + Vector + RRF fusion |
| 2 | Query Routing | ✅ Active | Routes to factual/analytical/comparison handlers |
| 3 | Context Compression | ✅ Active | Reduces context to fit LLM limits |
| 4 | Reranking | ✅ Active | Cross-encoder for precision |
| 5 | Quality Filtering | ✅ Active | Filters low-score results |
| 6 | Evidence Extraction | ✅ Active | Extracts relevant sentences |
| 7 | Diversity (MMR) | ✅ Active | Reduces redundant results |
| 8 | Query Decomposition | ✅ Active | Breaks complex queries into sub-queries |
| 9 | Feedback Collection | ✅ Active | Thumbs up/down on answers |
| 10 | Response Cache | ✅ Active | Caches repeated queries |
| 11 | Spelling Suggestions | ✅ Active | Autocomplete + "Did you mean?" |
| 12 | Expandable Sources | ✅ Active | Click to expand source passages |
| 13 | Text Highlighting | ✅ **NEW** | Query terms highlighted in sources |
| 14 | Export Results | ✅ **NEW** | Download as Markdown/HTML/JSON |
| 15 | Streaming Responses | ✅ **NEW** | Real-time LLM output via SSE |

---

### Feature Details

#### Feature 1: Hybrid Search
**File:** `app/hybrid_search.py`, `app/bm25_index.py`

Combines three retrieval methods:
- **Vector Search:** Semantic similarity using embeddings
- **BM25:** Keyword/exact term matching
- **RRF Fusion:** Reciprocal Rank Fusion combines both

```python
# Configuration in .env
HYBRID_SEARCH_ENABLED=true
HYBRID_ALPHA=0.7  # 70% vector, 30% BM25
```

#### Feature 2: Query Routing
**File:** `app/query_router.py`

Classifies queries into types and routes accordingly:
- `factual`: Direct fact lookup
- `analytical`: Deep analysis needed
- `comparison`: Compare entities
- `exploratory`: Open-ended questions

#### Feature 3: Context Compression
**File:** `app/context_compressor.py`

Reduces retrieved context to fit within LLM limits while preserving important information.

#### Feature 4: Reranking
**File:** `app/rag_backend.py`

Uses cross-encoder model to rerank initial results:
```python
self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
```

#### Feature 5: Quality Filtering
**File:** `app/rag_backend.py`

Filters results below quality threshold:
```python
self.quality_threshold = 0.3  # Minimum reranker score
```

#### Feature 6: Evidence Extraction
**File:** `app/evidence_extractor.py`

Extracts the most relevant sentences from retrieved chunks to include in context.

#### Feature 7: Diversity/MMR
**File:** `app/diversity_ranker.py`

Maximal Marginal Relevance ensures diverse results, not just duplicates.

#### Feature 8: Query Decomposition
**File:** `app/query_decomposer.py`

Breaks complex queries into sub-queries:
```
"Compare Rama and Ravana" →
  - "Who is Rama?"
  - "Who is Ravana?"
  - "Differences between Rama and Ravana"
```

**Limits:**
- Max 3 sub-queries per complex query
- Max 3 docs retrieved per sub-query

#### Feature 9: Feedback Collection
**File:** `app/main.py`

Collects user feedback (👍/👎) on answers for future improvements.

#### Feature 10: Response Cache
**File:** `app/rag_backend.py`

LRU cache for repeated queries:
```python
self.response_cache = {}  # query_hash -> response
self.cache_max_size = 100
```

#### Feature 11: Spelling Suggestions ⭐ NEW
**File:** `app/spelling_suggester.py`

Handles name/entity variations common in Indian texts:

**Three Matching Methods:**
1. **Simplified Key Matching:** Handles transliterations
   - `meganath` → `megn` (simplified)
   - `Meghanada` → `megn` (simplified)
   - Both match!

2. **Phonetic Matching:** Similar sounds
   - Removes aspirated consonants (th→t, dh→d)
   - Normalizes vowels

3. **Fuzzy Matching:** Edit distance
   - SequenceMatcher with 60% threshold

**Features:**
- **Autocomplete:** As-you-type suggestions (prefix + contains matching)
- **"Did You Mean?":** Shows when results are poor
- **11,864 indexed entities** extracted from your documents

**API Endpoints:**
```
GET  /api/autocomplete?q=meg&limit=10
GET  /api/spelling/suggest?query=meganath
GET  /api/spelling/stats
POST /api/spelling/rebuild
```

#### Feature 12: Expandable Sources
**File:** `app/templates/index.html`

**Before:** Sources showed 300 chars, truncated, no interaction.

**After:**
- Click any source card to expand
- See full passage text (scrollable, max 400px)
- "Copy Text" button to copy source
- "Collapse" button to close
- Smooth animations
- Visual indicator (▶ rotates to ▼ when expanded)

#### Feature 13: Text Highlighting ⭐ NEW
**File:** `app/text_highlighter.py`

Highlights query keywords in source passages:

**How It Works:**
1. Extracts keywords from query (ignoring stopwords)
2. Highlights matches in source text with colored spans
3. Preserves proper nouns even if short

**Features:**
- Toggle in UI: "Highlight terms" checkbox
- Max 50 highlights per source (prevents over-highlighting)
- Case-insensitive matching
- Longest-match-first for overlapping terms

**API Endpoint:**
```
POST /api/highlight
Body: {"text": "...", "query": "...", "max_highlights": 50}
```

#### Feature 14: Export Results ⭐ NEW
**File:** `app/result_exporter.py`

Export Q&A results to files:

**Supported Formats:**
| Format | Description |
|--------|-------------|
| **Markdown** | Clean documentation format |
| **HTML** | Standalone styled webpage (printable) |
| **JSON** | Machine-readable format |

**Features:**
- Download buttons appear after each query
- Includes: query, answer, all sources, metadata
- Automatic timestamped filenames
- Beautiful HTML export with print styling

**API Endpoint:**
```
POST /api/export
Body: {"query": "...", "answer": "...", "sources": [...], "format": "markdown"}
```

#### Feature 15: Streaming Responses ⭐ NEW
**Files:** `app/rag_backend.py`, `app/main.py`

Real-time LLM output using Server-Sent Events (SSE):

**How It Works:**
1. Sources are retrieved and sent immediately
2. LLM generates answer token-by-token
3. Each token is streamed to the browser as it's generated
4. User sees answer "typing out" in real-time

**Benefits:**
- Feels much faster (immediate feedback)
- Sources visible while answer generates
- Similar experience to ChatGPT

**UI Toggle:** "Stream response" checkbox

**API Endpoint:**
```
POST /api/ask/stream
Returns SSE stream with events:
  - {"type": "sources", "data": [...]}
  - {"type": "token", "data": "word"}
  - {"type": "done", "data": {...}}
  - {"type": "error", "data": "..."}
```

---

## 4. Installation & Setup

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.9+ | Runtime |
| LM Studio | Latest | Local LLM inference |
| Tesseract | Optional | OCR for scanned PDFs |

### Step-by-Step Installation

```bash
# 1. Navigate to project
cd "/Users/sathwikreddy/Projects/Model Training/Codebase"

# 2. Create and activate virtual environment
python3 -m venv venv_rag_2026
source venv_rag_2026/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file (if not exists)
cp .env.example .env
# Edit .env with your settings

# 5. Place documents in documents/ folder

# 6. Run Phase 1: Extract text from PDFs
python phase1_extract.py --all
# For OCR: python phase1_extract.py --all --ocr --ocr-lang san

# 7. Run Phase 2: Create embeddings and index
python phase2_embed.py --all

# 8. Build BM25 index
python build_bm25_index.py

# 9. Start LM Studio and load a model, then start server

# 10. Start the RAG server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 11. Open browser to http://localhost:8000
```

---

## 5. Configuration Reference

### Environment Variables (.env)

```bash
# === LLM Configuration ===
LM_STUDIO_URL=http://localhost:1234/v1
LLM_TEMPERATURE=0.05          # Low for factual accuracy
LLM_MAX_TOKENS=1000

# === Context Limits ===
MAX_CONTEXT_CHARS=6000        # Max chars sent to LLM
MAX_SUB_QUERIES=3             # For query decomposition
MAX_DOCS_PER_SUBQUERY=3       # Docs per sub-query

# === Hybrid Search ===
HYBRID_SEARCH_ENABLED=true
HYBRID_ALPHA=0.7              # Vector weight (0-1)

# === Quality Thresholds ===
QUALITY_THRESHOLD=0.3         # Min reranker score
RELEVANCE_THRESHOLD=0.5       # Min similarity score

# === Entity Configuration (Optional) ===
ENTITY_SYNONYMS_JSON={"rama":["rama","ram"],"krishna":["krishna","krsna"]}
ENTITY_BOOST_WEIGHT=0.08

# === Translation (Optional) ===
TRANSLATE_NON_ENGLISH=false
TRANSLATE_ONLY_FILES=
```

---

## 6. API Reference

### Main Endpoints

#### `POST /api/ask`
Ask a question and get an answer with sources.

**Request:**
```json
{
  "question": "Who is Meghanada?",
  "instructions": "Be concise"  // optional
}
```

**Response:**
```json
{
  "answer": "Meghanada, also known as Indrajit, was the son of Ravana...",
  "sources": [
    {
      "text": "Full passage text...",
      "page": 245,
      "file_name": "Ramayana.pdf",
      "score": 0.89
    }
  ],
  "metadata": {
    "retrieval_time": 0.234,
    "llm_time": 1.456,
    "total_time": 1.69,
    "sources_count": 5,
    "query_type": "factual",
    "context_truncated": false,
    "did_you_mean": null  // or "Meghanada" if spelling was wrong
  }
}
```

#### `GET /api/autocomplete`
Get autocomplete suggestions while typing.

**Request:** `GET /api/autocomplete?q=meg&limit=10`

**Response:**
```json
{
  "suggestions": [
    {"entity": "Meghanada", "frequency": 45, "match_type": "prefix"},
    {"entity": "Meghnath", "frequency": 12, "match_type": "prefix"}
  ]
}
```

#### `GET /api/spelling/suggest`
Get spelling suggestions for a query.

**Request:** `GET /api/spelling/suggest?query=meganath`

**Response:**
```json
{
  "suggestions": [
    {
      "original": "meganath",
      "suggestion": "Meghanada",
      "score": 0.93,
      "match_type": "transliteration",
      "frequency": 45
    }
  ]
}
```

#### `GET /api/spelling/stats`
Get statistics about the spelling index.

**Response:**
```json
{
  "total_entities": 11864,
  "total_variants": 15234,
  "phonetic_groups": 8456,
  "top_entities": [
    ["Rama", 1523],
    ["Sita", 987],
    ["Ravana", 756]
  ]
}
```

#### `POST /api/spelling/rebuild`
Rebuild the spelling index from LanceDB.

#### `GET /api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "lancedb": "connected",
  "chunks_count": 18791,
  "bm25_loaded": true,
  "spelling_entities": 11864
}
```

#### `POST /api/feedback`
Submit feedback on an answer.

**Request:**
```json
{
  "question": "Who is Rama?",
  "answer": "...",
  "feedback": "positive",  // or "negative"
  "comment": "Great answer!"  // optional
}
```

#### `POST /api/ask/stream` ⭐ NEW
Stream an answer in real-time using Server-Sent Events.

**Request:**
```json
{
  "question": "Who is Meghanada?",
  "include_sources": true
}
```

**Response:** SSE stream with events:
```
data: {"type": "sources", "data": [{"text": "...", "page": 245, ...}]}

data: {"type": "token", "data": "Meghanada"}

data: {"type": "token", "data": " was"}

data: {"type": "token", "data": " the"}

...

data: {"type": "done", "data": {"answer": "...", "timings": {...}}}
```

#### `POST /api/highlight` ⭐ NEW
Highlight query terms in text.

**Request:**
```json
{
  "text": "Rama was the prince of Ayodhya and son of Dasharatha.",
  "query": "Who is Rama?",
  "max_highlights": 50
}
```

**Response:**
```json
{
  "highlighted_text": "<span class=\"highlight\">Rama</span> was the prince of Ayodhya...",
  "keywords": ["rama"],
  "highlight_count": 1
}
```

#### `POST /api/export` ⭐ NEW
Export Q&A results to a file.

**Request:**
```json
{
  "query": "Who is Meghanada?",
  "answer": "Meghanada was the son of Ravana...",
  "sources": [...],
  "format": "markdown"  // or "html", "json"
}
```

**Response:** File download with appropriate Content-Type and filename.

---

## 7. Frontend Features

### User Interface Components

#### 1. Search Input with Autocomplete
- Large textarea for questions
- Autocomplete dropdown appears after 2 characters
- Keyboard navigation (↑↓ arrows, Enter to select, Escape to close)
- Debounced API calls (300ms)

#### 2. Control Checkboxes
- **Show sources:** Include source documents in response
- **Stream response:** Real-time token-by-token output ⭐ NEW
- **Highlight terms:** Highlight query keywords in sources ⭐ NEW

#### 3. "Did You Mean?" Banner
- Appears when spelling correction is suggested
- Clickable to re-run query with correction
- Auto-hides when query succeeds

#### 4. Answer Display
- Clean, formatted answer text
- Streaming indicator while generating ("Generating..." with pulse animation) ⭐ NEW
- Metadata badges (query type, retrieval time, etc.)

#### 5. Export Buttons ⭐ NEW
- **Export Markdown:** Clean documentation format
- **Export HTML:** Styled standalone webpage
- **Export JSON:** Machine-readable format
- Appear after each successful query

#### 6. Expandable Source Cards
- **Collapsed State:**
  - Shows page number and file name
  - Match score percentage
  - 2-line preview of text
  - ▶ expand indicator

- **Expanded State:**
  - Full passage text (scrollable)
  - Query keywords highlighted with gradient background ⭐ NEW
  - "Copy Text" button
  - "Collapse" button
  - ▼ rotated indicator

#### 7. Feedback Buttons
- 👍 Thumbs up
- 👎 Thumbs down
- Saves to backend for analysis

### UI Design
- **Theme:** Dark glassmorphism
- **Colors:** Purple gradient (#667eea to #764ba2)
- **Highlight Color:** Purple/pink gradient for query terms ⭐ NEW
- **Font:** System fonts (Apple system, Segoe UI)
- **Animations:** Smooth transitions (0.3s ease)

---

## 8. File Structure

```
Codebase/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application (+ streaming endpoints)
│   ├── rag_backend.py          # Core RAG logic (+ streaming method)
│   ├── hybrid_search.py        # Hybrid search implementation
│   ├── bm25_index.py           # BM25 keyword search
│   ├── query_router.py         # Query classification
│   ├── query_decomposer.py     # Complex query breakdown
│   ├── context_compressor.py   # Context reduction
│   ├── evidence_extractor.py   # Relevant sentence extraction
│   ├── diversity_ranker.py     # MMR diversity ranking
│   ├── conversation_memory.py  # Chat history (optional)
│   ├── spelling_suggester.py   # Spelling suggestions
│   ├── text_highlighter.py     # ⭐ NEW: Query term highlighting
│   ├── result_exporter.py      # ⭐ NEW: Export to MD/HTML/JSON
│   ├── semantic_chunker.py     # Advanced chunking
│   └── templates/
│       └── index.html          # Frontend UI (streaming + export + highlighting)
│
├── data/
│   ├── index/                  # LanceDB vector store
│   ├── bm25_index/             # BM25 index files
│   ├── spelling/               # Spelling index
│   │   └── entities.json       # 11,864 extracted entities
│   └── exports/                # ⭐ NEW: Exported result files
│
├── documents/                  # Source PDFs
│
├── phase1_extract.py           # PDF text extraction
├── phase2_embed.py             # Embedding generation
├── build_bm25_index.py         # BM25 index builder
│
├── requirements.txt            # Python dependencies
├── .env                        # Configuration
│
└── [Documentation files]
    ├── README.md
    ├── FULL_SYSTEM_DOCUMENTATION.md  # ⭐ This file
    ├── CHANGELOG.md                  # Version history
    ├── HANDOFF_INSTRUCTIONS.md       # For continuing development
    ├── QUICK_START.md
    └── ...
```

---

## 9. Troubleshooting

### Common Issues

#### Issue: "Context length exceeded" error
**Cause:** Query decomposition retrieving too many chunks.
**Solution:** 
- Set `MAX_CONTEXT_CHARS=6000` in `.env`
- Restart server

#### Issue: LLM gives wrong facts (hallucinations)
**Cause:** Generic system prompt allowed inference.
**Solution:**
- System prompt now includes "NEVER infer or assume relationships"
- Temperature reduced to 0.05
- Already fixed in current version

#### Issue: Spelling suggestions not appearing
**Cause:** Spelling index not built.
**Solution:**
```bash
curl -X POST http://localhost:8000/api/spelling/rebuild
```

#### Issue: "meganath" doesn't find "Meghanada"
**Cause:** Need simplified key matching.
**Solution:** Already implemented! Both normalize to `megn`.

#### Issue: Sources show truncated text
**Cause:** Old UI behavior.
**Solution:** Click on source card to expand (already implemented).

#### Issue: BM25 seems outdated
**Solution:**
```bash
python build_bm25_index.py
```

#### Issue: Server won't start
**Check:**
1. LM Studio running at `localhost:1234`?
2. Virtual environment activated?
3. All dependencies installed?

---

## 10. Recent Changes & Bug Fixes

### January 11, 2026 - Session Summary

#### Bug Fix 1: Context Length Error
**Problem:** Query "what do you know about kaikeyi" caused LLM context overflow.

**Root Cause:** Query decomposition was retrieving unlimited chunks.

**Solution:**
```python
# Added to rag_backend.py
self.max_context_chars = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))

# Truncation logic before LLM call
if len(context_str) > self.max_context_chars:
    # Smart truncation at sentence boundary
    truncated = context_str[:self.max_context_chars]
    last_period = truncated.rfind('.')
    if last_period > self.max_context_chars * 0.7:
        context_str = truncated[:last_period + 1]
```

**Also:**
- Limited sub-queries to 3 max
- Limited docs per sub-query to 3

#### Bug Fix 2: LLM Hallucination (Kaikeyi)
**Problem:** LLM said "Kaikeyi was the daughter of Dasaratha's second wife" (wrong - she IS the second wife).

**Root Cause:** Generic system prompt allowed inference.

**Solution:**
```python
# Updated system prompt in rag_backend.py
system_prompt = """You are a precise, factual assistant...
IMPORTANT RULES:
1. ONLY state facts that are EXPLICITLY mentioned in the sources
2. NEVER infer or assume relationships not directly stated
3. If the sources don't clearly state something, say "The sources don't explicitly mention..."
4. For relationships (wife, son, daughter, etc.), only state what is directly written
5. When uncertain, acknowledge the uncertainty"""

# Reduced temperature
self.temperature = 0.05  # Was 0.1
```

#### New Feature: Spelling Suggestions
**Files Created:**
- `app/spelling_suggester.py` (400+ lines)

**Features:**
- Entity extraction from indexed documents
- Three matching methods (simplified, phonetic, fuzzy)
- Autocomplete API
- "Did you mean?" integration

**Key Algorithm - Simplified Key:**
```python
def get_simplified_key(word: str) -> str:
    # meganath → megn
    # Meghanada → megn
    # Both match!
    
    # 1. Remove double letters
    word = re.sub(r'(.)\1+', r'\1', word)
    
    # 2. Normalize aspirated consonants
    # th→t, dh→d, bh→b, etc.
    
    # 3. Remove common endings
    # -nada, -nath, -nad → n
    
    # 4. Remove trailing vowels
```

#### New Feature: Expandable Sources
**File Modified:** `app/templates/index.html`

**CSS Added:**
- `.source-item` clickable with hover effects
- `.source-preview` (2-line truncated)
- `.source-full-text` (hidden by default, scrollable)
- `.source-actions` (copy/collapse buttons)
- Smooth expand animation

**JavaScript Added:**
```javascript
function toggleSource(element) {
    element.classList.toggle('expanded');
}

function copySourceText(event, button) {
    // Copy to clipboard with visual feedback
}
```

---

## 11. Performance Tuning

### Recommended Settings for Your Setup

| Setting | Value | Reason |
|---------|-------|--------|
| `MAX_CONTEXT_CHARS` | 6000 | Fits most LLM context windows |
| `HYBRID_ALPHA` | 0.7 | Good balance for named entities |
| `LLM_TEMPERATURE` | 0.05 | Factual accuracy over creativity |
| `QUALITY_THRESHOLD` | 0.3 | Filter low-quality results |

### Hardware Optimization (Apple Silicon)

The system automatically uses MPS (Metal Performance Shaders) for:
- Embedding generation
- Reranker inference

```python
# Automatic detection in rag_backend.py
device = "mps" if torch.backends.mps.is_available() else "cpu"
```

### Query Performance Tips

1. **Simple queries:** ~1-2 seconds
2. **Complex queries (decomposition):** ~3-5 seconds
3. **First query after startup:** Slower (model loading)

---

## 12. Future Roadmap

### ✅ Completed Features (v2.1)

| Feature | Status | Description |
|---------|--------|-------------|
| ~~Source Highlighting~~ | ✅ DONE | Query terms highlighted in source text |
| ~~Export Results~~ | ✅ DONE | Download as Markdown/HTML/JSON |
| ~~Streaming Responses~~ | ✅ DONE | Real-time SSE token streaming |

### Potential Next Features

| Priority | Feature | Description |
|----------|---------|-------------|
| High | Chapter Navigation | Browse by book/chapter/verse |
| High | Multi-document Comparison | Compare across multiple texts |
| Medium | Query History | Recent queries sidebar |
| Medium | Bookmarks | Save interesting passages |
| Low | Voice Input | Speak your questions |
| Low | Mobile Responsive | Better mobile UI |
| Low | Dark/Light Theme Toggle | User preference |

### Technical Improvements

- [ ] Better chunk boundary handling
- [ ] Multi-language embedding support
- [ ] Query intent confidence scoring
- [ ] Batch query processing
- [ ] Citation generation

---

## Quick Commands Reference

```bash
# Start everything
cd "/Users/sathwikreddy/Projects/Model Training/Codebase"
source venv_rag_2026/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Rebuild indexes
python build_bm25_index.py
curl -X POST http://localhost:8000/api/spelling/rebuild

# Check health
curl http://localhost:8000/api/health

# Test spelling
curl "http://localhost:8000/api/spelling/suggest?query=meganath"

# Test autocomplete
curl "http://localhost:8000/api/autocomplete?q=Ram&limit=5"

# Test streaming (NEW)
curl -X POST "http://localhost:8000/api/ask/stream" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who is Rama?"}'

# Test export (NEW)
curl -X POST "http://localhost:8000/api/export" \
  -H "Content-Type: application/json" \
  -d '{"query": "Who is Rama?", "answer": "...", "sources": [], "format": "markdown"}'
```

---

## Support

For issues or questions, check:
1. This documentation
2. `TROUBLESHOOTING` section above
3. Server logs: `server.log`
4. `CHANGELOG.md` for version history

---

*Documentation generated: January 11, 2026*
