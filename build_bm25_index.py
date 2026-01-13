#!/usr/bin/env python3
"""
Build BM25 Index for Hybrid Search
Run this after processing documents to create the BM25 keyword index.
"""

import sys
import logging
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.bm25_index import BM25Index

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Build BM25 index from existing LanceDB."""
    print("=" * 60)
    print("🔨 Building BM25 Index for Hybrid Search")
    print("=" * 60)
    print()
    
    # Check if LanceDB exists
    lancedb_path = Path("./data/index")
    if not lancedb_path.exists():
        print("❌ Error: LanceDB not found at ./data/index")
        print("   Please run Phase 1 and Phase 2 first to create the vector database.")
        print()
        print("   Steps:")
        print("   1. python phase1_extract.py --all")
        print("   2. python phase2_embed.py --all")
        print("   3. python build_bm25_index.py  (this script)")
        return 1
    
    try:
        # Initialize BM25 index
        print("📦 Initializing BM25 indexer...")
        bm25_index = BM25Index()
        
        # Build index from LanceDB
        print("🔄 Reading documents from LanceDB...")
        bm25_index.build_from_lancedb()
        
        # Show statistics
        stats = bm25_index.get_stats()
        print()
        print("=" * 60)
        print("✅ BM25 Index Built Successfully!")
        print("=" * 60)
        print(f"📊 Statistics:")
        print(f"   - Documents indexed: {stats['num_documents']}")
        print(f"   - Average document length: {stats['avg_doc_length']:.0f} tokens")
        print(f"   - Index location: {stats['index_path']}")
        print()
        print("🎉 Hybrid search is now ready!")
        print("   Your RAG system will now use BM25 + Vector search.")
        print()
        print("💡 Next steps:")
        print("   1. Restart your RAG server: ./run.sh")
        print("   2. Test hybrid search in the web interface")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error building BM25 index: {e}", exc_info=True)
        print()
        print("=" * 60)
        print("❌ Failed to build BM25 index")
        print(f"Error: {e}")
        print()
        print("Please check:")
        print("  - LanceDB is properly initialized")
        print("  - Documents have been processed (Phase 1 & 2)")
        print("  - You have write permissions to ./data/bm25_index/")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
