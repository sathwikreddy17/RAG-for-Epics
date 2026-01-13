"""
BM25 Index Manager for Hybrid Search
Manages BM25 keyword-based search index alongside vector embeddings.
"""

import os
import json
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
import lancedb

logger = logging.getLogger(__name__)

class BM25Index:
    """
    BM25 keyword search index for hybrid retrieval.
    """
    
    def __init__(self, index_path: str = "./data/bm25_index"):
        """
        Initialize BM25 index.
        
        Args:
            index_path: Directory to store BM25 index files
        """
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        self.bm25_path = self.index_path / "bm25_index.pkl"
        self.corpus_path = self.index_path / "corpus.json"
        
        self.bm25 = None
        self.corpus = []
        self.doc_ids = []
        
        # Try to load existing index
        self.load()
    
    def build_from_lancedb(self, lancedb_path: str = "./data/index", table_name: str = "docs"):
        """
        Build BM25 index from existing LanceDB.
        
        Args:
            lancedb_path: Path to LanceDB database
            table_name: Name of the table to index
        """
        logger.info("🔨 Building BM25 index from LanceDB...")
        
        try:
            # Connect to LanceDB
            db = lancedb.connect(lancedb_path)
            table = db.open_table(table_name)
            
            # Get all documents
            df = table.to_pandas()
            
            logger.info(f"📊 Found {len(df)} documents to index")
            
            # Prepare corpus
            self.corpus = []
            self.doc_ids = []
            
            for idx, row in df.iterrows():
                text = row['text']
                doc_id = row['id']
                
                # Tokenize for BM25 (simple whitespace split + lowercase)
                tokens = self._tokenize(text)
                
                self.corpus.append(tokens)
                self.doc_ids.append(doc_id)
            
            # Build BM25 index
            logger.info("🔧 Creating BM25 index...")
            self.bm25 = BM25Okapi(self.corpus)
            
            # Save index
            self.save()
            
            logger.info(f"✅ BM25 index built successfully: {len(self.corpus)} documents")
            
        except Exception as e:
            logger.error(f"❌ Error building BM25 index: {e}")
            raise
    
    def search(self, query: str, k: int = 20) -> List[Dict[str, Any]]:
        """
        Search using BM25.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of results with doc_id and score
        """
        if not self.bm25:
            logger.warning("⚠️  BM25 index not loaded")
            return []
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        
        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top k results
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include results with positive scores
                results.append({
                    "doc_id": self.doc_ids[idx],
                    "bm25_score": float(scores[idx]),
                    "rank": len(results) + 1
                })
        
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25.
        Simple whitespace tokenization + lowercasing.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Convert to lowercase and split on whitespace
        tokens = text.lower().split()
        
        # Remove very short tokens (< 2 chars)
        tokens = [t for t in tokens if len(t) >= 2]
        
        return tokens
    
    def save(self):
        """Save BM25 index to disk."""
        try:
            # Save BM25 index
            with open(self.bm25_path, 'wb') as f:
                pickle.dump({
                    'bm25': self.bm25,
                    'doc_ids': self.doc_ids,
                    'corpus_size': len(self.corpus)
                }, f)
            
            # Save corpus metadata
            with open(self.corpus_path, 'w') as f:
                json.dump({
                    'corpus_size': len(self.corpus),
                    'doc_ids': self.doc_ids
                }, f)
            
            logger.info(f"💾 BM25 index saved to {self.index_path}")
            
        except Exception as e:
            logger.error(f"❌ Error saving BM25 index: {e}")
    
    def load(self) -> bool:
        """
        Load BM25 index from disk.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not self.bm25_path.exists():
                logger.info("📝 No existing BM25 index found")
                return False
            
            # Load BM25 index
            with open(self.bm25_path, 'rb') as f:
                data = pickle.load(f)
                self.bm25 = data['bm25']
                self.doc_ids = data['doc_ids']
            
            # Load corpus metadata
            with open(self.corpus_path, 'r') as f:
                metadata = json.load(f)
            
            logger.info(f"✅ BM25 index loaded: {metadata['corpus_size']} documents")
            return True
            
        except Exception as e:
            logger.error(f"⚠️  Error loading BM25 index: {e}")
            return False
    
    def is_built(self) -> bool:
        """Check if BM25 index is built and loaded."""
        return self.bm25 is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self.bm25:
            return {"status": "not_built"}
        
        return {
            "status": "ready",
            "num_documents": len(self.doc_ids),
            "avg_doc_length": sum(len(doc) for doc in self.corpus) / len(self.corpus) if self.corpus else 0,
            "index_path": str(self.index_path)
        }
