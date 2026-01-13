#!/usr/bin/env python3
"""
Phase 2: Chunking & Embedding (Production Version)
Combines best practices for robust, resumable processing.

2026-01 update:
- Optional ingestion-time translation for non-English/Sanskrit OCR so English embeddings work well.
"""

import json
import gc
import os
from pathlib import Path
from datetime import datetime
import uuid
from typing import List, Dict, Any
import argparse

import lancedb
from sentence_transformers import SentenceTransformer
import tiktoken
from tqdm import tqdm

# Optional dependencies (translation feature)
try:
    from langdetect import detect as detect_lang
except Exception:
    detect_lang = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# --- CONFIGURATION ---
DB_PATH = "./data/index"
TABLE_NAME = "docs"
STATE_FILE = "phase2_state.json"

# Memory-safe batch sizes (conservative for stability)
CHUNK_BATCH_SIZE = 50  # Max chunks to accumulate before embedding
EMBED_BATCH_SIZE = 4   # Batch size for model.encode()
SAVE_EVERY_N_PAGES = 50  # Save state every N pages

# Chunking config
CHUNK_SIZE = 700  # tokens
CHUNK_OVERLAP = 150  # tokens
MIN_PAGE_LENGTH = 50  # Skip nearly-empty pages

# --- TRANSLATION CONFIG ---
TRANSLATE_NON_ENGLISH = os.getenv("TRANSLATE_NON_ENGLISH", "false").lower() == "true"
TRANSLATE_ONLY_FILES = [
    s.strip() for s in os.getenv("TRANSLATE_ONLY_FILES", "").split(",") if s.strip()
]
TRANSLATION_TARGET_LANG = os.getenv("TRANSLATION_TARGET_LANG", "en")
TRANSLATION_MODEL = os.getenv("TRANSLATION_MODEL", "local-model")

LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "not-needed-for-local")


def _should_translate(file_name: str) -> bool:
    if not TRANSLATE_NON_ENGLISH:
        return False
    if TRANSLATE_ONLY_FILES:
        return any(token in (file_name or "") for token in TRANSLATE_ONLY_FILES)
    return True


def _looks_like_devanagari(text: str) -> bool:
    if not text:
        return False
    # Devanagari block: U+0900..U+097F
    sample = text[:2000]
    return any("\u0900" <= ch <= "\u097F" for ch in sample)


def _is_non_english(text: str) -> bool:
    if not text:
        return False
    if _looks_like_devanagari(text):
        return True
    if detect_lang is None:
        return False
    try:
        # langdetect can be noisy; this is a best-effort heuristic
        return detect_lang(text[:1000]) != "en"
    except Exception:
        return False


def _translate_text_llm(client, text: str) -> str:
    """Translate text to English using LM Studio OpenAI-compatible endpoint."""
    if not text.strip():
        return text

    # Keep prompts short and deterministic
    prompt = (
        "Translate the following Sanskrit (or non-English) text into clear English. "
        "Preserve proper nouns (people/place names). If unsure, transliterate names. "
        "Return only the English translation.\n\n"
        f"TEXT:\n{text.strip()}"
    )

    resp = client.chat.completions.create(
        model=TRANSLATION_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise translation engine."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=800,
    )
    out = resp.choices[0].message.content or ""
    return out.strip() or text


# --- HELPER FUNCTIONS ---

def load_last_page(state_file: str) -> int:
    """Load resume point from state file."""
    if not os.path.exists(state_file):
        return 0
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
            return state.get("last_page", 0)
    except:
        return 0

def save_last_page(state_file: str, page_num: int):
    """Save resume point to state file."""
    with open(state_file, 'w') as f:
        json.dump({
            "last_page": page_num,
            "timestamp": datetime.now().isoformat()
        }, f)

def chunk_text(text: str, tokenizer, max_tokens: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Token-aware text chunking with overlap.
    
    Args:
        text: Input text to chunk
        tokenizer: tiktoken tokenizer
        max_tokens: Maximum tokens per chunk
        overlap: Token overlap between chunks
        
    Returns:
        List of text chunks
    """
    # Skip empty or tiny text
    if not text or len(text.strip()) < MIN_PAGE_LENGTH:
        return []
    
    # Tokenize
    tokens = tokenizer.encode(text)
    
    # If text is small enough, return as single chunk
    if len(tokens) <= max_tokens:
        return [text]
    
    # Sliding window with overlap
    chunks = []
    start = 0
    
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens)
        
        # Try to break at sentence boundaries (optional refinement)
        if end < len(tokens) and len(chunk_text) > 100:
            for break_point in ['. ', '.\n', '\n\n', '\n']:
                last_break = chunk_text.rfind(break_point)
                if last_break > len(chunk_text) * 0.7:  # At least 70% of chunk
                    chunk_text = chunk_text[:last_break + len(break_point)]
                    break
        
        chunks.append(chunk_text.strip())
        start += max_tokens - overlap
    
    return chunks

def process_batch(db, model, batch_texts: List[str], batch_metadata: List[Dict[str, Any]], table_name: str):
    """
    Embed a batch and save to LanceDB.
    Isolated function for clean memory cleanup.
    """
    if not batch_texts:
        return

    try:
        # Generate embeddings
        embeddings = model.encode(
            batch_texts,
            batch_size=EMBED_BATCH_SIZE,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        # Prepare records for LanceDB
        records = []
        for i, (text, metadata, embedding) in enumerate(zip(batch_texts, batch_metadata, embeddings)):
            record = {
                "id": metadata["id"],
                "text": text,
                "vector": embedding.tolist(),
                "file_name": metadata["file_name"],
                "page_number": metadata["page_number"],
                "chunk_index": metadata["chunk_index"],
                "created_at": metadata["created_at"],
            }

            records.append(record)

        # Save to database
        if table_name in db.table_names():
            table = db.open_table(table_name)
            table.add(records)
        else:
            # Create table on first batch
            table = db.create_table(table_name, records)

        # Explicit cleanup
        del embeddings, records
        gc.collect()

    except Exception as e:
        print(f"\n❌ Error processing batch: {e}")
        raise

# --- MAIN PROCESSING ---


def process_jsonl_file(jsonl_path: Path, db, model, tokenizer, state_file: str, test_pages: int = None):
    """Process a single JSONL file."""

    # Resume from last checkpoint
    last_processed_page = load_last_page(state_file)
    if last_processed_page > 0:
        print(f"\n♻️  Resuming from page {last_processed_page + 1}")

    # Count total pages for progress bar
    print("\n📊 Counting pages...")
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        total_pages = sum(1 for _ in f)
    print(f"✅ Found {total_pages} pages to process")

    if test_pages:
        total_pages = min(total_pages, test_pages)
        print(f"🧪 TEST MODE: Processing only first {test_pages} pages")

    # Process stream
    print("\n🔄 Processing pages...\n")

    batch_texts = []
    batch_metadata = []
    pages_processed = 0
    total_chunks = 0
    file_name = jsonl_path.stem.replace('_pages', '')

    # Translation client (optional)
    translate_this_file = _should_translate(file_name)
    translation_client = None
    if translate_this_file and OpenAI is not None:
        translation_client = OpenAI(base_url=LM_STUDIO_URL, api_key=LM_STUDIO_API_KEY)

    if translate_this_file:
        print(f"\n🌐 Translation enabled for: {file_name} (target={TRANSLATION_TARGET_LANG})")
        if translation_client is None:
            print("⚠️  Translation requested but OpenAI client not available; continuing without translation")

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        with tqdm(total=total_pages, desc="🧩 Processing pages", unit="page", colour='blue') as pbar:

            for line in f:
                # Parse page data
                try:
                    page_data = json.loads(line)
                except json.JSONDecodeError:
                    print("⚠️  JSON decode error, skipping line")
                    pbar.update(1)
                    continue

                page_num = page_data["page"]
                text = page_data.get("text", "").strip()

                # Skip if already processed (resume logic)
                if page_num <= last_processed_page:
                    pbar.update(1)
                    continue

                # Skip empty/tiny pages
                if not text or len(text) < MIN_PAGE_LENGTH:
                    pbar.update(1)
                    continue

                # Test mode limit
                if test_pages and page_num > test_pages:
                    break

                # Chunk this page
                page_chunks = chunk_text(text, tokenizer)

                if not page_chunks:
                    pbar.update(1)
                    continue

                # Add chunks to batch
                for chunk_idx, chunk_content in enumerate(page_chunks):
                    original_text = chunk_content
                    final_text = chunk_content

                    # Translate only when clearly non-English/Sanskrit and client is available
                    if translate_this_file and translation_client is not None:
                        if _is_non_english(original_text):
                            try:
                                translated_text = _translate_text_llm(translation_client, original_text)
                                # Store translation in the `text` field for embedding/search, while preserving source text inline.
                                final_text = (
                                    "[TRANSLATED_TO_ENGLISH]\n"
                                    f"{translated_text.strip()}\n\n"
                                    "[ORIGINAL_TEXT]\n"
                                    f"{original_text.strip()}"
                                )
                            except Exception:
                                final_text = original_text

                    batch_texts.append(final_text)
                    meta = {
                        "id": str(uuid.uuid4()),
                        "file_name": page_data.get("file", file_name),
                        "page_number": page_num,
                        "chunk_index": chunk_idx,
                        "created_at": datetime.now().isoformat(),
                    }
                    batch_metadata.append(meta)

                total_chunks += len(page_chunks)
                pages_processed += 1

                # Update progress
                pbar.update(1)
                pbar.set_postfix({
                    "chunks": total_chunks,
                    "batch": len(batch_texts)
                })

                # Process batch when full OR at save interval
                if len(batch_texts) >= CHUNK_BATCH_SIZE or pages_processed % SAVE_EVERY_N_PAGES == 0:
                    if batch_texts:
                        process_batch(db, model, batch_texts, batch_metadata, TABLE_NAME)

                        # Reset batch
                        batch_texts = []
                        batch_metadata = []
                        gc.collect()

                # Save checkpoint every N pages
                if pages_processed % SAVE_EVERY_N_PAGES == 0:
                    save_last_page(state_file, page_num)

            # Process final batch
            if batch_texts:
                print("\n💾 Processing final batch...")
                process_batch(db, model, batch_texts, batch_metadata, TABLE_NAME)

    # Save final state
    if pages_processed > 0:
        save_last_page(state_file, page_num if 'page_num' in locals() else 0)

    return pages_processed, total_chunks

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Chunk and embed documents for RAG")
    parser.add_argument("--test", type=int, help="Test mode: process only N pages")
    parser.add_argument("--file", type=str, help="Specific JSONL file to process")
    parser.add_argument("--all", action="store_true", help="Process all JSONL files")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 Phase 2: Chunking & Embedding")
    print("=" * 60)
    print(f"💾 Database: {DB_PATH}")
    print(f"📊 Batch sizes: chunks={CHUNK_BATCH_SIZE}, embed={EMBED_BATCH_SIZE}")
    if args.test:
        print(f"🧪 TEST MODE: Processing only first {args.test} pages")
    print("=" * 60)
    
    # 1. Initialize resources
    print("\n🔧 Loading tokenizer...")
    tokenizer = tiktoken.get_encoding("cl100k_base")
    
    print("🔧 Loading embedding model (BAAI/bge-large-en-v1.5)...")
    # Try MPS (Mac GPU) first, fall back to CPU
    try:
        model = SentenceTransformer('BAAI/bge-large-en-v1.5', device='mps')
        print("✅ Model loaded on Metal GPU (MPS)")
    except:
        model = SentenceTransformer('BAAI/bge-large-en-v1.5', device='cpu')
        print("✅ Model loaded on CPU")
    
    print("🔧 Connecting to LanceDB...")
    os.makedirs(DB_PATH, exist_ok=True)
    db = lancedb.connect(DB_PATH)
    print("✅ Database connected")
    
    # Find JSONL files
    extracted_dir = Path("documents/extracted_text")
    if not extracted_dir.exists():
        print(f"\n❌ Error: {extracted_dir} not found")
        print("   Run phase1_extract.py first to extract text from documents")
        return
    
    jsonl_files = list(extracted_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"\n❌ Error: No JSONL files found in {extracted_dir}")
        print("   Run phase1_extract.py first to extract text from documents")
        return
    
    # Process files
    if args.file:
        # Process specific file
        file_path = Path(args.file)
        if not file_path.exists():
            file_path = extracted_dir / args.file
        
        if not file_path.exists():
            print(f"\n❌ Error: File not found: {args.file}")
            return
        
        print(f"\n📄 Processing: {file_path.name}\n")
        state_file = f"phase2_state_{file_path.stem}.json"
        pages, chunks = process_jsonl_file(file_path, db, model, tokenizer, state_file, args.test)
        
        print(f"\n{'=' * 60}")
        print(f"✅ Completed: {file_path.name}")
        print(f"   Pages: {pages}, Chunks: {chunks}")
        
    elif args.all or len(jsonl_files) == 1:
        # Process all files
        total_pages_all = 0
        total_chunks_all = 0
        
        for jsonl_file in jsonl_files:
            print(f"\n📄 Processing: {jsonl_file.name}\n")
            state_file = f"phase2_state_{jsonl_file.stem}.json"
            
            try:
                pages, chunks = process_jsonl_file(jsonl_file, db, model, tokenizer, state_file, args.test)
                total_pages_all += pages
                total_chunks_all += chunks
                
                # Clean up state file if completed
                if not args.test and os.path.exists(state_file):
                    os.remove(state_file)
                
                print(f"\n✅ Completed: {jsonl_file.name}")
                print(f"   Pages: {pages}, Chunks: {chunks}\n")
                
            except Exception as e:
                print(f"\n❌ Error processing {jsonl_file.name}: {e}\n")
                continue
        
        print("\n" + "=" * 60)
        print("✅ Phase 2 Complete!")
        print("=" * 60)
        print(f"📊 Total Statistics:")
        print(f"   - Files processed: {len(jsonl_files)}")
        print(f"   - Total pages: {total_pages_all}")
        print(f"   - Total chunks: {total_chunks_all}")
        print(f"   - Database: {DB_PATH}/{TABLE_NAME}")
        print("=" * 60)
        
    else:
        # Interactive mode
        print(f"\nFound {len(jsonl_files)} JSONL files:")
        for i, f in enumerate(jsonl_files, 1):
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  {i}. {f.name} ({size_mb:.1f} MB)")
        
        choice = input(f"\nSelect file number (1-{len(jsonl_files)}) or 'all': ")
        
        if choice.lower() == 'all':
            total_pages_all = 0
            total_chunks_all = 0
            
            for jsonl_file in jsonl_files:
                print(f"\n📄 Processing: {jsonl_file.name}\n")
                state_file = f"phase2_state_{jsonl_file.stem}.json"
                
                try:
                    pages, chunks = process_jsonl_file(jsonl_file, db, model, tokenizer, state_file, args.test)
                    total_pages_all += pages
                    total_chunks_all += chunks
                    
                    # Clean up state file if completed
                    if not args.test and os.path.exists(state_file):
                        os.remove(state_file)
                    
                    print(f"\n✅ Completed: {jsonl_file.name}")
                    print(f"   Pages: {pages}, Chunks: {chunks}\n")
                    
                except Exception as e:
                    print(f"\n❌ Error processing {jsonl_file.name}: {e}\n")
                    continue
            
            print("\n" + "=" * 60)
            print("✅ Phase 2 Complete!")
            print("=" * 60)
            print(f"📊 Total Statistics:")
            print(f"   - Files processed: {len(jsonl_files)}")
            print(f"   - Total pages: {total_pages_all}")
            print(f"   - Total chunks: {total_chunks_all}")
            print(f"   - Database: {DB_PATH}/{TABLE_NAME}")
            print("=" * 60)
        else:
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(jsonl_files):
                    print("❌ Invalid selection")
                    return
                
                jsonl_file = jsonl_files[idx]
                print(f"\n📄 Processing: {jsonl_file.name}\n")
                state_file = f"phase2_state_{jsonl_file.stem}.json"
                pages, chunks = process_jsonl_file(jsonl_file, db, model, tokenizer, state_file, args.test)
                
                # Clean up state file if completed
                if not args.test and os.path.exists(state_file):
                    os.remove(state_file)
                
                print(f"\n{'=' * 60}")
                print(f"✅ Completed: {jsonl_file.name}")
                print(f"   Pages: {pages}, Chunks: {chunks}")
                
            except ValueError:
                print("❌ Invalid selection")
                return
    
    print("\n🎉 Ready for RAG queries!")
    print("   Next: uvicorn app.main:app --reload --port 8000")

if __name__ == "__main__":
    main()
