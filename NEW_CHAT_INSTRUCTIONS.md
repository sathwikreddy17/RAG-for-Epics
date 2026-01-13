# New Chat Instructions (Copy/Paste)

Use this when the current chat is near token limit.

---

## Copy/Paste Block

**Context:** We have a working local-first RAG system in this repo. Read `SYSTEM_CAPABILITIES.md` for the current capabilities and state. Read `NEXT_FEATURES_ROADMAP.md` for the planned improvements.

**Architecture:**
- FastAPI API: `app/main.py` with endpoints `/api/ask`, `/api/health`, `/api/stats`.
- Retrieval core: `app/rag_backend.py` and/or `app/rag_backend_2026.py`.
- Vector DB: LanceDB at `./data/index`, table `docs`.
- BM25 index: `./data/bm25_index/`.
- LLM: LM Studio (OpenAI-compatible HTTP endpoint configured via `.env`).

**Existing features:**
- Hybrid retrieval (BM25 + vector + fusion) and feature flags in `.env`.
- Optional 2026 upgrades: query routing + context compression.
- Optional entity synonym expansion + lexical boosting configured by:
  - `ENTITY_SYNONYMS_JSON`
  - `ENTITY_BOOST_WEIGHT`
- OCR ingestion: `phase1_extract.py` (supports `--ocr` / `--ocr-lang`), used for Sanskrit scans.
- Optional translation-at-ingestion in `phase2_embed.py` for selected files.

**Next task (do FIRST): Implement observability (Feature 0 in `NEXT_FEATURES_ROADMAP.md`).**
1) Add `POST /api/debug/retrieval` endpoint (guarded by `ENABLE_DEBUG_ENDPOINTS=true`) that:
   - runs retrieval for a query
   - returns top candidates with per-scorer breakdown (vector, bm25, fused, entity boost)
   - includes metadata (file name, page, chunk id)
2) Expand `/api/stats` to include per-file chunk counts and totals.

**Constraints:**
- Keep changes small/reversible.
- Add `.env` flags for any new behavior.
- Update docs after implementing.
- Validate using an entity query like “Who is Sugreeva?” and confirm Ramayana sources win.

---
