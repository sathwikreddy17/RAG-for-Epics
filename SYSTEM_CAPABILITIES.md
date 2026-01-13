# 🧠 System Capabilities: What This RAG System Specializes In

## Summary
This system is a **local-first, book-scale RAG** designed for:
- very large PDFs
- multi-document libraries
- entity-heavy domains (epics, historical texts, reference works)
- OCR and multilingual ingestion workflows

---

## Implementation Roadmap + New-Chat Handoff

If you are continuing work in a fresh chat (token limit), use:
- `NEXT_FEATURES_ROADMAP.md` — the one-by-one feature implementation queue
- the **Copy/Paste Handoff Block** at the bottom of that file — paste it into a new chat to resume with full context

---

## Current State (Hand-off Snapshot for Another LLM)

### What exists today (end-to-end)
This repo contains a working, local RAG system that can:
- ingest PDFs (including scanned/OCR-heavy books)
- chunk and embed text into a vector DB (LanceDB)
- build and use a BM25 keyword index
- answer questions through a FastAPI API using LM Studio as the local LLM
- return answers with citations (file + page)

### Core architecture
**Ingestion pipeline**
- `phase1_extract.py`: PDF ➜ extracted text (with optional OCR)
- `phase2_embed.py`: extracted text ➜ chunks ➜ embeddings ➜ LanceDB
- Store: `./data/index` (LanceDB), table `docs` (one row per chunk)

**Retrieval + answering**
- `app/main.py`: FastAPI endpoints
- `app/rag_backend.py` and/or `app/rag_backend_2026.py`: retrieval + prompt assembly + LLM call
- LLM: LM Studio in OpenAI-compatible mode (local HTTP endpoint)

### Retrieval capabilities (important)
- **Hybrid retrieval** (when enabled):
  - semantic vector search (meaning-based)
  - BM25 keyword search (term-based)
  - fusion ranking to combine both
- **2026 query-time upgrades** (when enabled):
  - query routing (choose strategy based on query type)
  - context compression (reduce tokens while keeping evidence)
- **Entity-heavy query hardening** (optional):
  - synonym expansion for transliteration variants (e.g., Sugreeva/Sugriva)
  - light lexical boosting for chunks containing entity variants

### Multilingual / OCR state
- OCR is supported for scanned PDFs via Tesseract.
- OCR language can be specified (e.g., Sanskrit via `--ocr-lang san`).
- Optional **translation-at-ingestion** exists to align non-English text into English embeddings (useful when the embedding model is English-optimized).

### Known “real corpus” evidence (Ramayana use-case)
- Corpus size observed: ~18.8k chunks in LanceDB.
- Entity name coverage diagnostic (example): `sugreeva/sugriva` found hundreds of times across multiple PDFs.
- After entity synonym expansion + lexical boost, “Who is Sugreeva?” reliably returns **Ramayana** sources instead of unrelated epics.

### Key runtime endpoints
- `POST /api/ask`: question ➜ answer + sources
- `GET /api/health`: health + feature availability
- `GET /api/stats`: current system status/flags (can be expanded)

### Key runtime configuration knobs (.env)
The system is controlled primarily via `.env` feature flags (names may vary slightly by branch/version, but the intent is):
- Retrieval toggles:
  - hybrid search enable/disable
  - query routing enable/disable
  - context compression enable/disable
  - top-k settings (initial and final)
- LM Studio:
  - base URL and API key (local)
- Multilingual:
  - `TRANSLATE_NON_ENGLISH` + `TRANSLATE_ONLY_FILES` + target language/model
- Entity-hardening:
  - `ENTITY_SYNONYMS_JSON`
  - `ENTITY_BOOST_WEIGHT`

### What this system is best suited for
- large book corpora where:
  - proper nouns matter (characters/places)
  - multiple books overlap in vocabulary
  - OCR noise exists
- offline/local deployments where cloud LLM calls are not desired

### Current limitations / gaps (explicit)
These are areas where a research-focused LLM can propose improvements:
- Observability:
  - `/api/stats` does not yet expose detailed per-document ingestion stats, per-file chunk counts, or retrieval diagnostics.
- Retrieval quality controls:
  - ✅ Cross-encoder reranker now available (enable with `USE_RERANKER=true`)
  - ✅ Source quality filtering available (enable with `USE_QUALITY_FILTERS=true`, configure `SOURCE_WEIGHTS_JSON`)
  - ✅ Evidence sentence selection available (enable with `USE_EVIDENCE_EXTRACTION=true`) — extracts best sentences for quote-level grounding
  - ✅ Diversity ranking / MMR available (enable with `USE_DIVERSITY_RANKING=true`) — prevents near-duplicate chunks
  - entity boost is global (one weight), not per-entity/per-source
- Multilingual strategy:
  - translation-at-ingestion is pragmatic but may introduce translation artifacts
  - multilingual embedding model option is not implemented/configured
- Evaluation:
  - evaluation scripts exist, but automated regression tests for retrieval quality (entity queries, citations) can be expanded.

### “Deep research” prompts to ask another LLM
If you hand this document to another LLM, useful research directions include:
- best-practice hybrid retrieval fusion methods (RRF variants, learned fusion)
- reranking strategies that work locally on Apple Silicon (fast cross-encoders)
- OCR cleanup and language-aware normalization for Sanskrit/IAST transliterations
- citation robustness (span selection, page mapping, deduping repeated chunks)
- per-source weighting / quality scoring and automatic “bad document” suppression
- better query understanding (entity detection, query decomposition for multi-hop)

---

## What It’s Best At

### 1) Book-scale ingestion
- Two-phase pipeline: extract ➜ embed
- Resumable processing
- Incremental additions without overwriting previous data

### 2) Robust retrieval
- Vector semantic search + BM25 keyword search
- Fusion ranking
- **Cross-encoder reranking** (optional, `USE_RERANKER=true`) — improves precision by scoring query-document relevance with a neural model
- **Source quality filtering** (optional, `USE_QUALITY_FILTERS=true`) — down-weights low-quality chunks (OCR noise) and allows per-file weight multipliers
- **Evidence sentence selection** (optional, `USE_EVIDENCE_EXTRACTION=true`) — extracts the best sentences from top chunks to include as quote-level grounding in the LLM prompt
- **Diversity ranking / MMR** (optional, `USE_DIVERSITY_RANKING=true`) — prevents near-duplicate chunks from dominating results using Maximal Marginal Relevance
- Optional entity synonym expansion + lexical boosting (for transliteration variants)

### 3) Practical query-time optimizations
- Query routing + context compression (2026 upgrade)
- Better latency and token usage without losing faithfulness

### 4) Multilingual support (optional)
- OCR extraction via Tesseract
- Optional translation-at-ingestion for aligning non-English text into English embeddings

---

## Plain-English: What We Did for the Sanskrit Book

Many Sanskrit PDFs are effectively **scanned images** (not selectable text). A normal PDF text extractor can’t reliably read them.

To make the Sanskrit Ramayana queryable, we used this pipeline:

### Phase 1: OCR text extraction
- We opened the PDF **page-by-page**.
- Where needed, we rendered each page to an image and ran **OCR** (Optical Character Recognition).
- For Sanskrit, OCR uses Tesseract configured with `--ocr-lang san`.

**Output:** a JSONL file in `documents/extracted_text/` with one record per page (`page_number` + extracted text).

### Phase 2: Chunking + embeddings
- The extracted text is split into overlapping “chunks” (small passages) so retrieval can target the right spot.
- Each chunk is converted into an **embedding** (a numeric vector) using `BAAI/bge-large-en-v1.5`.
- Each chunk is stored in **LanceDB** (`./data/index`, table `docs`) along with:
  - `file_name`, `page_number`, `chunk_index`, and the chunk `text`.

This is what turns a scanned Sanskrit PDF into something searchable.

---

## How the RAG Answers Questions Using the Sanskrit Book

When you ask a question:

1) **The question is prepared for retrieval**
- Query routing may classify it (factual/complex/etc.) to choose a strategy.
- Optional entity synonym expansion may add variant spellings (e.g., `Sugreeva` ↔ `Sugriva`).

2) **Retrieval selects the best chunks**
The system uses **hybrid search** when enabled:
- **Vector search**: finds semantically similar chunks (meaning-based)
- **BM25**: finds keyword matches (exact-term based)
- The rankings are fused (more robust than either alone)

3) **Entity-heavy queries get extra help (optional)**
- If enabled via `.env`, the system can:
  - expand entity spellings in the query
  - lightly boost chunks that contain any entity variant

This helps when the corpus has:
- transliteration variants
- noisy OCR
- multiple books with similar language

4) **The LLM answers using retrieved context**
- The backend constructs a prompt using the top retrieved chunks.
- The prompt is sent to LM Studio (OpenAI-compatible endpoint).
- The answer is returned along with source citations (file + page).

---

## Multilingual: Does This Work for Other Languages?

### OCR
Yes, as long as:
- the proper Tesseract language pack is installed, and
- `phase1_extract.py` is run with the correct `--ocr-lang`.

### Retrieval quality for English queries vs non-English documents
Important detail:
- Embeddings are language-sensitive.
- English queries may not reliably hit non-English OCR text unless we align languages.

We support two practical approaches:

1) **Translate at ingestion (recommended for English queries)**
- If enabled, `phase2_embed.py` translates non-English chunks to English **before embedding**.
- That way English queries retrieve them more reliably.

Controlled by `.env`:
- `TRANSLATE_NON_ENGLISH=true`
- `TRANSLATE_ONLY_FILES=...` (limit translation to specific file tokens)
- `TRANSLATION_TARGET_LANG=en`
- `TRANSLATION_MODEL=local-model`

2) **Use a multilingual embedding model (future option)**
- Not currently implemented, but can be done by swapping the embedding model to a multilingual one.

---

## What’s Happening in the Backend (High-Level)

### FastAPI API layer (`app/main.py`)
Key endpoints:
- `POST /api/ask` — question ➜ answer + sources
- `GET /api/health` — health + feature availability
- `GET /api/stats` — current status/feature flags (and can be expanded later)

### RAG core (`app/rag_backend.py` / `app/rag_backend_2026.py`)
On startup:
- loads embedding model (SentenceTransformers)
- connects to LanceDB table
- loads BM25 index (if present)
- initializes hybrid search + query routing + context compression (if enabled)

On each question:
1) normalize/route query
2) retrieve candidate chunks (hybrid: BM25 + vector)
3) optional context compression
4) call LM Studio to generate answer
5) return answer + sources

---

## How We’re Different From Typical RAG Demos
- Designed for large PDFs and long books (not just small clean docs)
- Handles OCR and noisy text realities
- Uses hybrid retrieval and entity-aware improvements for “proper noun” queries
- Runs fully locally (LM Studio + FastAPI + LanceDB)
