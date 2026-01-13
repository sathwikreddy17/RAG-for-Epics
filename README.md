# � Epic Literature RAG System

> **Version 2.0** | January 12, 2026 | AI-Powered Search for Ramayana & Mahabharata

A production-ready **Retrieval-Augmented Generation (RAG)** system specialized for exploring ancient Indian epic literature. Features semantic search, character knowledge graphs, event timelines, and citation export.

---

## ✨ Features at a Glance

### Core RAG Features
| Feature | Description |
|---------|-------------|
| 🔍 **Hybrid Search** | BM25 + Vector search with RRF fusion |
| 🧠 **Smart Query Routing** | Classifies queries for optimal retrieval |
| 📊 **Cross-Encoder Reranking** | BGE reranker for precision |
| ✂️ **Context Compression** | Extracts most relevant sentences |
| 🎯 **Evidence Extraction** | Quote-level grounding |
| 🔄 **Diversity Ranking (MMR)** | Avoids duplicate results |
| ⚡ **Streaming Responses** | Real-time LLM output via SSE |
| 💾 **Response Caching** | Fast repeated queries |

### Knowledge Features
| Feature | Description |
|---------|-------------|
| � **Character Knowledge Graph** | 25 characters, 42 relationships |
| 📅 **Event Timeline** | 68 events across both epics |
| ❓ **Related Questions** | Smart follow-up suggestions |
| 📚 **Citation Export** | BibTeX, Chicago, MLA, APA formats |

### User Experience
| Feature | Description |
|---------|-------------|
| � **Autocomplete** | Entity suggestions while typing |
| ✏️ **Spelling Suggestions** | Handles transliteration variants |
| 🖍️ **Text Highlighting** | Query terms in sources |
| 📄 **Export Results** | Markdown, JSON, PDF |
| 👍 **Feedback Collection** | Rate answers 1-5 stars |
| 📜 **Query History** | Browse past searches |

---

## 🏃 Quick Start

```bash
# 1. Setup
cd "/Users/sathwikreddy/Projects/Model Training/Codebase"
source venv_rag_2026/bin/activate

# 2. Start LM Studio (load any chat model, start server)

# 3. Run the RAG server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. Open http://localhost:8000
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [**COMPLETE_SYSTEM_DOCUMENTATION.md**](COMPLETE_SYSTEM_DOCUMENTATION.md) | Full API reference & feature guide |
| [SEARCH_FIX_SUMMARY.md](SEARCH_FIX_SUMMARY.md) | Recent fixes & feature additions |
| [QUICK_START.md](QUICK_START.md) | Getting started guide |

---

## 📡 Key API Endpoints

### Core Q&A
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ask` | POST | Ask a question |
| `/api/ask/stream` | POST | Streaming Q&A (SSE) |
| `/api/related-questions` | POST | Get follow-up suggestions |

### Knowledge Graph
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/characters` | GET | List all characters |
| `/api/characters/{name}` | GET | Character profile |
| `/api/characters/path/{a}/{b}` | GET | Relationship path |
| `/api/timeline` | GET | Event timeline |
| `/api/timeline/character/{name}` | GET | Character's events |

### Citations & Export
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/citations/export` | POST | Export citations |
| `/api/citations/formats` | GET | Available formats |
| `/api/export` | POST | Export to MD/JSON/PDF |

### Utilities
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/autocomplete` | GET | Entity suggestions |
| `/api/spelling/suggest` | GET | Spelling corrections |
| `/api/feedback` | POST | Submit rating |
| `/api/health` | GET | Health check |

---

## 📊 Current Stats

| Metric | Value |
|--------|-------|
| **Indexed Chunks** | 18,791 |
| **Characters** | 25 (13 Ramayana, 12 Mahabharata) |
| **Relationships** | 42 |
| **Timeline Events** | 68 (30 Ramayana, 38 Mahabharata) |
| **Citation Formats** | 4 (BibTeX, Chicago, MLA, APA) |

---

## 📁 Project Structure

```
app/
├── main.py              # FastAPI server (40+ endpoints)
├── rag_backend.py       # Core RAG logic
├── character_graph.py   # Knowledge graph
├── timeline.py          # Event timeline
├── citation_exporter.py # Citation generation
├── related_questions.py # Follow-up suggestions
├── hybrid_search.py     # BM25 + Vector search
├── query_router.py      # Smart query routing
├── context_compressor.py
├── evidence_extractor.py
├── diversity_ranker.py
└── templates/
    └── index.html       # Frontend UI
```

---

## 🎯 What's Next: Frontend Redesign

The backend is feature-complete. Next phase focuses on building a modern, beautiful frontend to expose all capabilities:

- 🎨 **Modern Design** - Immersive, professional UI
- �️ **Character Explorer** - Visual knowledge graph
- 📅 **Timeline Browser** - Interactive event navigation  
- 📚 **Citation Manager** - Easy academic exports
- 📱 **Mobile Support** - Responsive design

---

## 📜 License

MIT License - See [LICENSE](LICENSE)

## 🛠️ Tech Stack

- **Backend:** FastAPI, Python 3.9
- **Vector DB:** LanceDB
- **Embeddings:** sentence-transformers
- **Reranker:** cross-encoder/ms-marco-MiniLM
- **LLM:** LM Studio (local)
- **Frontend:** HTML/CSS/JS (glassmorphism)

---

*Last updated: January 11, 2026*
