# Epic Literature RAG System - Complete Documentation

**Last Updated**: January 12, 2026  
**Version**: 2.0 (2026 Upgrade)

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Core Features](#core-features)
4. [API Reference](#api-reference)
5. [Frontend Features](#frontend-features)
6. [Configuration](#configuration)
7. [Data Sources](#data-sources)

---

## 🎯 System Overview

This is an AI-powered Retrieval-Augmented Generation (RAG) system specialized for exploring ancient Indian epic literature - the **Ramayana** and **Mahabharata**. The system combines vector search, BM25 keyword search, and local LLMs to provide accurate, source-grounded answers.

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **Hybrid Search** | Combines semantic (vector) and keyword (BM25) search |
| **Smart Query Routing** | Classifies queries and optimizes retrieval strategy |
| **Context Compression** | Extracts most relevant sentences to maximize context quality |
| **Evidence Extraction** | Quote-level grounding for verifiable answers |
| **Diversity Ranking** | MMR-based result diversification to avoid redundancy |
| **Multi-hop Reasoning** | Decomposes complex queries into sub-questions |
| **Streaming Responses** | Real-time token streaming via SSE |
| **Response Caching** | Caches frequent queries for fast responses |
| **Feedback Collection** | Tracks user satisfaction for continuous improvement |

---

## 🏗️ Architecture

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend Framework** | FastAPI (Python) |
| **Vector Database** | LanceDB |
| **Embedding Model** | BAAI/bge-large-en-v1.5 |
| **Reranker Model** | BAAI/bge-reranker-large |
| **Keyword Search** | BM25 (custom implementation) |
| **LLM Backend** | LM Studio (local, localhost:1234) |
| **Frontend** | Vanilla HTML/CSS/JavaScript |

### Directory Structure

```
app/
├── main.py                 # FastAPI application, all endpoints
├── rag_backend.py          # Core RAG logic (search, answer, streaming)
├── bm25_index.py           # BM25 keyword search index
├── hybrid_search.py        # Combines BM25 + vector search
├── query_classifier.py     # Query type classification
├── query_router.py         # Routes queries to optimal strategies
├── query_decomposer.py     # Multi-hop query decomposition
├── context_compressor.py   # Sentence-level compression
├── evidence_extractor.py   # Quote extraction for grounding
├── diversity_ranker.py     # MMR-based diversification
├── response_cache.py       # Response caching layer
├── feedback_collector.py   # User feedback tracking
├── related_questions.py    # Follow-up question suggestions
├── character_graph.py      # Character knowledge graph
├── timeline.py             # Event timeline management
├── citation_exporter.py    # Academic citation generation
├── spelling_suggester.py   # "Did you mean?" suggestions
├── text_highlighter.py     # Answer-source highlighting
├── result_exporter.py      # Export to PDF/Markdown/JSON
├── query_history.py        # Query history management
├── conversation_memory.py  # Conversation context
└── templates/
    └── index.html          # Frontend UI
```

---

## ⚙️ Core Features

### 1. Hybrid Search (BM25 + Vector)

Combines two search methods using Reciprocal Rank Fusion:
- **Vector Search**: Semantic similarity using BGE embeddings
- **BM25 Search**: Keyword matching with TF-IDF weighting

```
Final Score = α × Vector_Score + (1-α) × BM25_Score
```

### 2. Smart Query Routing

Classifies queries into types and adjusts retrieval strategy:

| Query Type | top_k | Strategy |
|------------|-------|----------|
| `factual` | 5 | Quick retrieval, direct answer |
| `analytical` | 7 | More context, synthesis needed |
| `comparative` | 8 | Multiple topics, diversity focus |
| `exploratory` | 6 | Broad context |
| `multi_hop` | 8 | Query decomposition enabled |

### 3. Context Compression

Extracts the most relevant sentences from retrieved chunks:
- Computes sentence-level relevance scores
- Keeps sentences above relevance threshold
- Reduces context size by ~60% while maintaining quality

### 4. Evidence Extraction

For quote-level grounding:
- Extracts key evidence sentences from each chunk
- Scores sentences by query relevance
- Provides "KEY EVIDENCE" section in prompts

### 5. Diversity Ranking (MMR)

Maximal Marginal Relevance to balance:
- **Relevance**: How well results match the query
- **Diversity**: How different results are from each other
- **Page Deduplication**: Limits chunks per (file, page) combination

### 6. Query Decomposition

For complex multi-hop questions:
```
"How did Rama's exile lead to the war with Ravana?"
→ Sub-queries:
  1. "Why was Rama exiled?"
  2. "What happened during Rama's exile?"
  3. "How did Ravana kidnap Sita?"
  4. "How did the war with Ravana begin?"
```

### 7. Quality Filtering

Filters out low-quality chunks:
- Minimum character length
- Non-alphanumeric ratio check
- Repetition detection (OCR artifacts)
- Corrupted translation markers

---

## 📡 API Reference

### Core Endpoints

#### `POST /api/ask`
Main question-answering endpoint.

**Request:**
```json
{
  "question": "Who is Rama?",
  "include_sources": true,
  "file_filter": "Ramayana"
}
```

**Response:**
```json
{
  "answer": "Rama is the hero of the Ramayana...",
  "sources": [
    {
      "index": 1,
      "file_name": "Ramayana.of.Valmiki.by.Hari.Prasad.Shastri.pdf",
      "page": 42,
      "text": "...",
      "score": 0.89
    }
  ],
  "metadata": {
    "num_sources": 5,
    "query": "Who is Rama?",
    "context_length": 4500,
    "reranker_used": true,
    "related_questions": [...]
  },
  "timings": {
    "search": 0.234,
    "llm": 1.567,
    "total": 1.823
  }
}
```

#### `POST /api/ask/stream`
Streaming version with Server-Sent Events.

**Events:**
- `{"type": "sources", "data": [...]}` - Sources sent first
- `{"type": "token", "data": "..."}` - Each LLM token
- `{"type": "done", "data": {...}}` - Final metadata

---

### Character Knowledge Graph

#### `GET /api/characters`
List all characters.
```
GET /api/characters?epic=Ramayana
```

#### `GET /api/characters/{name}`
Get character profile with relationships.

#### `GET /api/characters/{name}/relationships`
Get all relationships for a character.

#### `GET /api/characters/{name}/family`
Get family tree (parents, children, siblings, spouses).

#### `GET /api/characters/path/{source}/{target}`
Find relationship path between two characters.
```
GET /api/characters/path/Arjuna/Krishna
→ ["Arjuna", "ally", "Krishna"]
```

#### `GET /api/characters/search?q={query}`
Search characters by name/title/description.

#### `GET /api/characters-graph/stats`
```json
{
  "total_characters": 25,
  "ramayana_characters": 13,
  "mahabharata_characters": 12,
  "total_relationships": 42,
  "relationship_types": ["parent", "child", "spouse", "sibling", "ally", "enemy", ...]
}
```

---

### Timeline & Events

#### `GET /api/timeline`
Get events with filters.
```
GET /api/timeline?epic=Ramayana&character=Hanuman&book=Sundara%20Kanda
```

#### `GET /api/timeline/event/{event_id}`
Get specific event details.

#### `GET /api/timeline/character/{name}`
Get all events for a character across epics.

#### `GET /api/timeline/books`
List all books/kandas/parvas with event counts.

#### `GET /api/timeline/search?q={query}`
Search events by keyword.

#### `GET /api/timeline/tag/{tag}`
Get events by tag (death, marriage, battle, etc.).

#### `GET /api/timeline/stats`
```json
{
  "total_events": 68,
  "ramayana_events": 30,
  "mahabharata_events": 38,
  "unique_characters": 74,
  "unique_tags": 127
}
```

---

### Citation Export

#### `POST /api/citations/export`
Export citations in academic formats.

**Request:**
```json
{
  "sources": [
    {"file_name": "Ramayana.of.Valmiki.pdf", "page": 524}
  ],
  "format": "bibtex"
}
```

**Response:**
```json
{
  "citations": [
    {
      "citation": "@book{ramayana524, ...}",
      "inline": "(Valmiki, 524)"
    }
  ],
  "combined": "..."
}
```

#### `GET /api/citations/formats`
List available formats: BibTeX, Chicago, MLA, APA.

#### `GET /api/citations/document/{file_name}`
Get bibliography entry for a document.

---

### Related Questions

#### `POST /api/related-questions`
Get follow-up question suggestions.

**Request:**
```json
{
  "query": "Who is Rama?",
  "answer": "Rama is...",
  "max_questions": 5
}
```

---

### Search & Autocomplete

#### `GET /api/autocomplete?q={query}&limit=10`
Entity autocomplete suggestions.

#### `GET /api/spelling/suggest?q={query}`
"Did you mean?" spelling corrections.

---

### Feedback & Analytics

#### `POST /api/feedback`
Submit answer feedback.
```json
{
  "query": "Who is Rama?",
  "answer": "...",
  "rating": 5,
  "comment": "Very helpful!"
}
```

#### `GET /api/feedback/stats`
Get feedback statistics.

#### `GET /api/feedback/low-rated`
Get queries with low ratings for review.

---

### Cache Management

#### `GET /api/cache/stats`
Cache hit/miss statistics.

#### `POST /api/cache/clear`
Clear cache entries.

---

### Query History

#### `GET /api/history?limit=50`
Get recent query history.

#### `GET /api/history/{entry_id}`
Get specific history entry.

#### `DELETE /api/history/{entry_id}`
Delete history entry.

#### `DELETE /api/history`
Clear all history.

---

### Export & Utilities

#### `POST /api/export`
Export Q&A session.
```json
{
  "format": "markdown",
  "question": "...",
  "answer": "...",
  "sources": [...]
}
```
Formats: `markdown`, `json`, `pdf`

#### `POST /api/highlight`
Highlight answer text with source references.

---

### Debug & Health

#### `GET /api/health`
Basic health check.

#### `GET /api/health/detailed`
Detailed system status with all component states.

#### `GET /api/stats`
Database and model statistics.

#### `POST /api/debug/retrieval`
Debug retrieval with score breakdown:
- Vector scores
- BM25 scores
- Fused scores
- Reranker scores
- Quality adjustments
- Evidence extraction results

#### `POST /api/debug/decompose`
Debug query decomposition.

---

## 🎨 Frontend Features

### Current UI (`app/templates/index.html`)

| Feature | Status |
|---------|--------|
| Question input with autocomplete | ✅ |
| Streaming answer display | ✅ |
| Source cards with page numbers | ✅ |
| "Did you mean?" suggestions | ✅ |
| Document filter dropdown | ✅ |
| Copy answer button | ✅ |
| Export to Markdown/JSON | ✅ |
| Feedback rating (1-5 stars) | ✅ |
| Query history sidebar | ✅ |
| Related questions display | ✅ |
| Dark theme | ✅ |

### Not Yet in Frontend

These backend features exist but aren't exposed in the UI:
- Character Knowledge Graph visualization
- Timeline/Event browser
- Citation export UI
- Advanced search with filters
- Feedback analytics dashboard

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# Models
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
RERANKER_MODEL=BAAI/bge-reranker-large
USE_RERANKER=true

# LM Studio
LM_STUDIO_URL=http://localhost:1234/v1

# Database
LANCEDB_PATH=./data/index
TABLE_NAME=docs

# Retrieval
TOP_K_INITIAL=50
TOP_K_FINAL=5
RERANK_TOP_N=50

# Features
USE_HYBRID_SEARCH=true
USE_QUERY_ROUTING=true
USE_CONTEXT_COMPRESSION=true
USE_EVIDENCE_EXTRACTION=true
USE_DIVERSITY_RANKING=true
USE_QUERY_DECOMPOSITION=true
USE_FEEDBACK_COLLECTION=true
USE_RESPONSE_CACHE=true
USE_QUALITY_FILTERS=true

# Quality Filters
ENTITY_BOOST_WEIGHT=0.15
QUALITY_PENALTY_WEIGHT=0.15
MIN_CHUNK_LENGTH=50

# Diversity (MMR)
MMR_LAMBDA=0.7
MMR_SIMILARITY_THRESHOLD=0.85
MAX_CHUNKS_PER_PAGE=2

# Context
MAX_CONTEXT_CHARS=6000
EVIDENCE_MAX_SENTENCES=8
```

---

## 📚 Data Sources

### Indexed Documents

| Document | Author/Translator | Year | Chunks |
|----------|-------------------|------|--------|
| The Ramayana of Valmiki | Hari Prasad Shastri | 1952 | ~12,000 |
| The Mahabharata | Kisari Mohan Ganguli | 1883-1896 | ~5,000 |
| Srimad Valmiki Ramayana (Sanskrit) | - | 1933 | ~1,500 |

**Total Indexed Chunks**: ~18,791

### Characters in Knowledge Graph

**Ramayana (13)**: Rama, Sita, Lakshmana, Bharata, Hanuman, Ravana, Dasaratha, Kaikeyi, Kausalya, Sugriva, Vali, Vibhishana, Jatayu

**Mahabharata (12)**: Krishna, Arjuna, Yudhishthira, Bhima, Draupadi, Duryodhana, Karna, Bhishma, Drona, Dhritarashtra, Kunti, Gandhari

### Timeline Events

| Epic | Events | Books/Kandas |
|------|--------|--------------|
| Ramayana | 30 | 7 Kandas |
| Mahabharata | 38 | 18 Parvas |

---

## 🚀 Quick Start

```bash
# 1. Start LM Studio and load a model

# 2. Activate environment
source venv_rag_2026/bin/activate

# 3. Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Open browser
open http://localhost:8000
```

---

## 📝 Changelog Summary

### January 12, 2026
- ✅ Timeline & Event Ordering (68 events)
- ✅ Citation Export (BibTeX/Chicago/MLA/APA)
- ✅ Related Questions Suggestion
- ✅ Character Knowledge Graph (25 characters, 42 relationships)
- ✅ Search fix for character queries
- ✅ Enhanced entity synonyms and query expansion

### Previous (2026 Upgrade)
- ✅ Hybrid Search (BM25 + Vector)
- ✅ Smart Query Routing
- ✅ Context Compression
- ✅ Evidence Extraction
- ✅ Diversity Ranking (MMR)
- ✅ Multi-hop Query Decomposition
- ✅ Response Caching
- ✅ Feedback Collection
- ✅ Spelling Suggestions
- ✅ Text Highlighting
- ✅ Export (Markdown/JSON/PDF)
- ✅ Query History

---

## 🎯 Frontend Redesign Targets

The current frontend is functional but basic. Planned improvements:

1. **Modern Design System** - Professional, immersive UI
2. **Character Explorer** - Visual knowledge graph
3. **Timeline Browser** - Interactive event timeline
4. **Citation Manager** - Easy citation export
5. **Advanced Search** - Filters, facets, saved searches
6. **Analytics Dashboard** - Usage and feedback visualization
7. **Mobile Responsive** - Works on all devices

---

*Documentation generated on January 12, 2026*
