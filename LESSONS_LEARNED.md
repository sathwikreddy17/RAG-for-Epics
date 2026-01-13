# 📚 Lessons Learned (Local RAG System)

This document captures practical lessons learned while building and hardening this RAG system for **large, real-world PDFs** and **entity-heavy corpora**.

## 1) Hybrid retrieval beats vector-only on real corpora
Vector embeddings are great for meaning, but they often underperform on:
- exact names (Sugreeva/Sugriva)
- transliteration variants
- citations/verse-like references
- short queries that are mostly proper nouns

**Fix:** Hybrid retrieval (BM25 + vector) + lightweight canonicalization.

## 2) OCR ingestion changes the game
OCR introduces:
- misspellings
- broken line wraps
- random artifacts

Even if embeddings work, output can become noisy.

**Fixes used here:**
- OCR fallback for scanned PDFs
- optional translation at ingestion to align into English embedding space

## 3) Translation is best done at ingestion (optional)
For multilingual corpora, embedding raw Sanskrit won’t reliably serve English queries.

**Preferred approach:** Translate chunks to English before embedding (when a model is available locally).

## 4) Eval dependencies should be isolated
Some evaluation stacks pull in heavy dependencies that can destabilize runtime.

**Approach:** keep evaluation requirements separate from runtime requirements when possible.

## 5) Validate with sources, not just answers
A fluent answer can be wrong if sources are wrong.

**Rule:** Always check top sources for key queries after changes.
