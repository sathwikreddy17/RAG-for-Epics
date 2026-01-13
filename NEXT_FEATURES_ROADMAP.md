# Next Features Roadmap (Implement One-by-One)

This document tracks **planned improvements** to the current local-first RAG system.

Goal: implement upgrades incrementally with stable checkpoints, and keep a copy/paste handoff block for starting a new chat.

---

## Guiding Principles
- Prefer **small, reversible** changes with toggles in `.env`.
- Add **observability first** (debug endpoints, stats) so we can measure improvements.
- Keep everything **local-friendly** (Apple Silicon + LM Studio + no cloud requirement).
- Every feature must include:
  - config knobs
  - a short doc update
  - a quick validation query (or test)

---

## Feature Queue (Priority Order)

### 0) Retrieval diagnostics + observability (recommended first)
**Why:** Makes every next feature easier to debug.

**Planned deliverables**
- Add `POST /api/debug/retrieval` endpoint returning candidate chunks with score breakdown.
- Expand `/api/stats` to include:
  - per-file chunk counts
  - top files by chunk count
  - BM25 + LanceDB row counts (already partially known)

**Config**
- `ENABLE_DEBUG_ENDPOINTS=true|false`
- `STATS_INCLUDE_PER_FILE=true|false` (default: true)
- `STATS_TOP_FILES_N=10` (default: 10)

**Validation**
- Call `/api/debug/retrieval` for an entity query (e.g., Sugreeva) and verify:
  - vector score, bm25 score, fused score, entity boost
  - file/page metadata for each result

**Usage**
- `POST /api/debug/retrieval` (requires `ENABLE_DEBUG_ENDPOINTS=true`)
  - Body: `{ "query": "Who is Sugreeva?", "k": 10, "file_filter": "all" }`

Status: IMPLEMENTED

---

### 1) Cross-encoder reranking (optional, high impact)
**Why:** Improves precision for entity-heavy corpora where multiple books overlap.

**Planned approach**
- Retrieve top `TOP_K_INITIAL` via hybrid.
- Rerank candidates using a cross-encoder.
- Return top `TOP_K_FINAL`.

**Local-friendly options**
- `sentence-transformers` cross-encoder (small model)
- (fallback) LLM-as-reranker via LM Studio (slower)

**Config**
- `USE_RERANKER=true|false`
- `RERANKER_MODEL=BAAI/bge-reranker-large` (default)
- `RERANK_TOP_N=40` (how many candidates to rerank before selecting top_k_final)

**Validation**
- Compare top sources before/after on:
  - entity queries (Sugreeva)
  - near-duplicate entities across books
- Use `POST /api/debug/retrieval` to inspect reranker scores in the `scores.reranker` field

**Usage**
- Enable in `.env`: `USE_RERANKER=true`
- Debug endpoint now shows reranker scores: `POST /api/debug/retrieval`
  - Response includes `reranker.enabled`, `reranker.model`, `scores.reranker` per candidate

Status: IMPLEMENTED

---

### 2) Source quality filtering / down-weighting
**Why:** OCR noise + dictionary/reference PDFs can steal top ranks.

**Planned approach**
- Compute per-chunk quality signals at retrieval time:
  - non-alphanumeric ratio (OCR noise indicator)
  - repetition ratio (garbled text indicator)
  - short-token density (fragmented OCR indicator)
- Apply per-file weight multipliers for manual control
- Apply quality penalty to scores at retrieval time

**Config**
- `USE_QUALITY_FILTERS=true|false` (default: true)
- `SOURCE_WEIGHTS_JSON={"dictallcheck.pdf": 0.5}` (per-file weights, 1.0=normal, <1=down-weighted)
- `QUALITY_PENALTY_WEIGHT=0.15` (penalty multiplier for low-quality chunks)

**Validation**
- Use `POST /api/debug/retrieval` to inspect quality scores per candidate
- Each candidate shows `quality.quality_score`, `quality.source_weight`, `quality.details`
- Dictionary/reference sources should appear lower when down-weighted

**Usage**
- Enable in `.env`: `USE_QUALITY_FILTERS=true`
- Set per-file weights: `SOURCE_WEIGHTS_JSON={"dictallcheck.pdf": 0.5, "reference.pdf": 0.3}`
- Debug endpoint shows quality info: `POST /api/debug/retrieval`

Status: IMPLEMENTED

---

### 3) Evidence sentence selection (quote-level grounding)
**Why:** Better faithfulness + clearer citations.

**Planned approach**
- From selected chunks, extract best sentences using semantic similarity to query
- Include extracted evidence as explicit quotes in the LLM prompt
- LLM instructed to cite the evidence when answering

**Config**
- `USE_EVIDENCE_EXTRACTION=true|false` (default: true)
- `EVIDENCE_MAX_SENTENCES=8` (max evidence sentences to extract)
- `EVIDENCE_SIMILARITY_THRESHOLD=0.3` (min similarity to include a sentence)

**Validation**
- Use `POST /api/debug/retrieval` to see extracted evidence in `evidence_extraction.result`
- Check `/api/ask` response `metadata.evidence_extracted` for count
- LLM responses should include more direct quotes from sources

**Usage**
- Enable in `.env`: `USE_EVIDENCE_EXTRACTION=true`
- Evidence is automatically added to LLM prompt with "Key Evidence:" section
- Debug endpoint shows extracted sentences with scores and source info

Status: IMPLEMENTED

---

### 4) Diversity selection (MMR / de-dup)
**Why:** Prevent many near-identical chunks from the same page.

**Implementation:**
- New module: `app/diversity_ranker.py`
- Uses Maximal Marginal Relevance (MMR) to balance relevance and diversity
- Also does page-level deduplication (limit chunks per file+page combination)

**Config knobs (.env):**
- `USE_DIVERSITY_RANKING=true|false`
- `MMR_LAMBDA=0.7` (0=max diversity, 1=max relevance)
- `MMR_SIMILARITY_THRESHOLD=0.85` (chunks more similar than this get penalized)
- `MAX_CHUNKS_PER_PAGE=2` (max chunks from same file+page combo)

**Usage:**
- Enable in `.env`: `USE_DIVERSITY_RANKING=true`
- System automatically applies page dedup + MMR after reranking
- Health endpoint shows `diversity_ranking_enabled: true` and stats

Status: IMPLEMENTED

---

### 5) Query Decomposition (multi-hop reasoning)
**Why:** Complex questions like "Compare Rama and Ravana" or "What happened when X met Y?" often need information from multiple places.

**Implementation:**
- Module: `app/query_decomposer.py`
- Breaks complex queries into simpler sub-queries
- Searches each sub-query independently
- Aggregates and re-ranks results by relevance to original query
- Supports both rule-based (fast) and LLM-based (more accurate) decomposition

**Config knobs (.env):**
- `USE_QUERY_DECOMPOSITION=true|false` (default: true)
- `DECOMPOSITION_USE_LLM=true|false` (default: true) — use LLM for smarter decomposition

**Triggers:**
- Automatically triggered when query router detects `multi_hop` query type
- Or when strategy suggests `decompose_query: true`

**Validation:**
- Use `POST /api/debug/decompose` to test decomposition:
  ```json
  {"query": "Compare Rama and Ravana", "use_llm": true}
  ```
- Check `/api/ask` response `metadata.decomposition_used` and `metadata.sub_queries`

**Usage:**
- Enable in `.env`: `USE_QUERY_DECOMPOSITION=true`
- Health endpoint shows `query_decomposition_enabled: true`
- Debug endpoint: `POST /api/debug/decompose`

Status: IMPLEMENTED

---

### 6) User Feedback Loop (retrieval quality tracking)
**Why:** Track answer quality over time, identify weak spots, collect training data.

**Implementation:**
- Module: `app/feedback_collector.py`
- Records user ratings (1-5 scale) with query, answer, and sources
- Tracks statistics: total feedback, satisfaction rate, by query type
- Identifies low-rated queries for review
- Exports high-quality pairs as potential training data

**Config knobs (.env):**
- `USE_FEEDBACK_COLLECTION=true|false` (default: true)
- `FEEDBACK_PATH=./data/feedback` — where to store feedback data

**Endpoints:**
- `POST /api/feedback` — submit feedback
  ```json
  {"query": "...", "answer": "...", "rating": 4, "comment": "..."}
  ```
- `GET /api/feedback/stats` — get feedback statistics
- `GET /api/feedback/low-rated` — queries with low ratings (debug endpoint)

**Validation:**
- Submit feedback, check stats endpoint updates
- Check `./data/feedback/feedback.jsonl` for recorded entries

Status: IMPLEMENTED

---

### 7) Response Cache (frequently asked questions)
**Why:** Avoid re-computing answers for repeated questions, faster responses.

**Implementation:**
- Module: `app/response_cache.py`
- LRU cache with configurable size and TTL
- Automatic cache hit/miss tracking
- Persists to disk for restart recovery
- Query normalization for fuzzy matching

**Config knobs (.env):**
- `USE_RESPONSE_CACHE=true|false` (default: true)
- `CACHE_PATH=./data/cache` — where to store cache
- `CACHE_MAX_SIZE=500` — max cached responses
- `CACHE_TTL_HOURS=24` — cache entry lifetime

**Endpoints:**
- `GET /api/cache/stats` — cache statistics (hit rate, size, etc.)
- `POST /api/cache/clear` — clear cache (debug endpoint)

**Validation:**
- Ask same question twice, second should be instant (`from_cache: true`)
- Check hit rate in `/api/cache/stats`

Status: IMPLEMENTED

---

## Copy/Paste Handoff Block (New Chat Starter)

Paste the following into a new chat to continue work:

---

**Context:** We have a working local-first RAG system in the repo. Key docs: `SYSTEM_CAPABILITIES.md` (current state/capabilities) and `NEXT_FEATURES_ROADMAP.md` (the plan). Backend: FastAPI in `app/main.py`, retrieval in `app/rag_backend.py`. Storage: LanceDB at `./data/index` table `docs`. BM25 index in `./data/bm25_index/`. LM Studio provides the LLM endpoint.

**Current capability:** Hybrid retrieval (BM25 + vector + fusion), query routing + context compression, entity synonym expansion + lexical boosting. **Cross-encoder reranking** (`USE_RERANKER=true`). **Source quality filtering** (`USE_QUALITY_FILTERS=true`). **Evidence extraction** (`USE_EVIDENCE_EXTRACTION=true`). **Diversity ranking/MMR** (`USE_DIVERSITY_RANKING=true`). **Query decomposition** for multi-hop (`USE_QUERY_DECOMPOSITION=true`). **Feedback collection** (`USE_FEEDBACK_COLLECTION=true`). **Response cache** (`USE_RESPONSE_CACHE=true`). OCR in `phase1_extract.py`; translation-at-ingestion in `phase2_embed.py`.

**Completed features:**
- Feature 0: Retrieval diagnostics + observability (`POST /api/debug/retrieval`)
- Feature 1: Cross-encoder reranking (`USE_RERANKER=true`)
- Feature 2: Source quality filtering (`USE_QUALITY_FILTERS=true`, `SOURCE_WEIGHTS_JSON`)
- Feature 3: Evidence sentence selection (`USE_EVIDENCE_EXTRACTION=true`)
- Feature 4: Diversity selection / MMR (`USE_DIVERSITY_RANKING=true`)
- Feature 5: Query decomposition / multi-hop (`USE_QUERY_DECOMPOSITION=true`)
- Feature 6: User feedback loop (`USE_FEEDBACK_COLLECTION=true`, `POST /api/feedback`)
- Feature 7: Response cache (`USE_RESPONSE_CACHE=true`, `GET /api/cache/stats`)

**All planned features + 3 additional improvements are now IMPLEMENTED!**

**Possible next improvements:**
- Evaluation harness for measuring retrieval quality (automated testing)
- Conversation memory (multi-turn context)
- Admin UI for monitoring and configuration
- Batch question processing

**Constraints:** Keep changes minimal and reversible. Update docs after implementing.

---

