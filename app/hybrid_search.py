"""
Hybrid Search combining BM25 (keyword) and Vector (semantic) search.
Uses Reciprocal Rank Fusion (RRF) to combine results.
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

class HybridSearcher:
    """
    Combines BM25 keyword search with vector semantic search.
    """
    
    def __init__(self, bm25_index, vector_table, embedding_model):
        """
        Initialize hybrid searcher.
        
        Args:
            bm25_index: BM25Index instance
            vector_table: LanceDB table
            embedding_model: SentenceTransformer model
        """
        self.bm25_index = bm25_index
        self.vector_table = vector_table
        self.embedding_model = embedding_model
    
    def search(
        self, 
        query: str, 
        k: int = 5,
        alpha: float = 0.5,
        use_rrf: bool = True,
        file_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search.
        
        Args:
            query: Search query
            k: Number of final results to return
            alpha: Weight for combining scores (0=BM25 only, 1=vector only, 0.5=balanced)
            use_rrf: Use Reciprocal Rank Fusion instead of score fusion
            file_filter: Optional filename to filter results
            
        Returns:
            List of search results with combined scores
        """
        # Get more results from each method for better fusion
        k_retrieval = k * 4  # Retrieve 4x more for fusion
        
        # 1. BM25 keyword search
        bm25_results = []
        if self.bm25_index and self.bm25_index.is_built():
            bm25_results = self.bm25_index.search(query, k=k_retrieval)
        else:
            logger.warning("⚠️  BM25 index not available, using vector search only")
        
        # 2. Vector semantic search
        query_embedding = self.embedding_model.encode(query)
        search_query = self.vector_table.search(query_embedding).limit(k_retrieval)
        
        # Apply file filter if specified
        if file_filter and file_filter != "all":
            search_query = search_query.where(f"file_name LIKE '%{file_filter}%'")
        
        vector_results = search_query.to_list()
        
        # 3. Combine results
        if not bm25_results:
            # Fallback to vector only
            return vector_results[:k]
        
        if use_rrf:
            combined = self._reciprocal_rank_fusion(bm25_results, vector_results, k=k)
        else:
            combined = self._score_fusion(bm25_results, vector_results, alpha=alpha, k=k)
        
        return combined
    
    def _reciprocal_rank_fusion(
        self, 
        bm25_results: List[Dict[str, Any]], 
        vector_results: List[Dict[str, Any]], 
        k: int = 5,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine results using Reciprocal Rank Fusion.
        
        RRF formula: score = sum(1 / (k + rank_i)) for each ranker i
        
        Args:
            bm25_results: Results from BM25 search
            vector_results: Results from vector search
            k: Number of final results
            rrf_k: RRF constant (typically 60)
            
        Returns:
            Fused and ranked results
        """
        # Build BM25 rank map
        bm25_ranks = {result['doc_id']: idx + 1 for idx, result in enumerate(bm25_results)}
        
        # Build vector rank map
        vector_ranks = {result['id']: idx + 1 for idx, result in enumerate(vector_results)}
        
        # Get all unique doc IDs
        all_doc_ids = set(bm25_ranks.keys()) | set(vector_ranks.keys())
        
        # Calculate RRF scores
        rrf_scores = {}
        for doc_id in all_doc_ids:
            score = 0.0
            
            # Add BM25 contribution
            if doc_id in bm25_ranks:
                score += 1.0 / (rrf_k + bm25_ranks[doc_id])
            
            # Add vector contribution
            if doc_id in vector_ranks:
                score += 1.0 / (rrf_k + vector_ranks[doc_id])
            
            rrf_scores[doc_id] = score
        
        # Sort by RRF score
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        # Build result list with full document data
        # Include both vector results AND BM25-only results
        doc_map = {r['id']: r for r in vector_results}
        
        # For BM25-only results, fetch full document from LanceDB
        bm25_only_ids = set(bm25_ranks.keys()) - set(vector_ranks.keys())
        if bm25_only_ids and self.vector_table is not None:
            try:
                # Fetch documents that were found by BM25 but not vector search
                for doc_id in bm25_only_ids:
                    if doc_id not in doc_map:
                        # Query LanceDB for this specific document
                        result_df = self.vector_table.search().where(f"id = '{doc_id}'").limit(1).to_list()
                        if result_df:
                            doc_map[doc_id] = result_df[0]
            except Exception as e:
                logger.warning(f"Failed to fetch BM25-only results: {e}")
        
        final_results = []
        for doc_id in sorted_doc_ids[:k]:
            if doc_id in doc_map:
                result = doc_map[doc_id].copy()
                result['hybrid_score'] = rrf_scores[doc_id]
                result['fusion_method'] = 'rrf'
                
                # Add component ranks for debugging
                result['bm25_rank'] = bm25_ranks.get(doc_id, None)
                result['vector_rank'] = vector_ranks.get(doc_id, None)
                
                final_results.append(result)
        
        return final_results
    
    def _score_fusion(
        self, 
        bm25_results: List[Dict[str, Any]], 
        vector_results: List[Dict[str, Any]], 
        alpha: float = 0.5,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Combine results using weighted score fusion.
        
        Combined score = alpha * vector_score + (1 - alpha) * bm25_score
        
        Args:
            bm25_results: Results from BM25 search
            vector_results: Results from vector search
            alpha: Weight (0=BM25 only, 1=vector only, 0.5=balanced)
            k: Number of final results
            
        Returns:
            Fused and ranked results
        """
        # Normalize BM25 scores
        bm25_scores = [r['bm25_score'] for r in bm25_results]
        if bm25_scores:
            max_bm25 = max(bm25_scores)
            bm25_normalized = {
                r['doc_id']: r['bm25_score'] / max_bm25 if max_bm25 > 0 else 0
                for r in bm25_results
            }
        else:
            bm25_normalized = {}
        
        # Normalize vector distances (convert to similarity)
        vector_scores = {}
        for r in vector_results:
            # LanceDB returns L2 distance, convert to similarity score
            distance = r.get('_distance', 1.0)
            similarity = max(0, 1 - (distance / 2))  # Normalize
            vector_scores[r['id']] = similarity
        
        if vector_scores:
            max_vector = max(vector_scores.values())
            if max_vector > 0:
                vector_normalized = {
                    doc_id: score / max_vector 
                    for doc_id, score in vector_scores.items()
                }
            else:
                vector_normalized = vector_scores
        else:
            vector_normalized = {}
        
        # Combine scores
        all_doc_ids = set(bm25_normalized.keys()) | set(vector_normalized.keys())
        
        combined_scores = {}
        for doc_id in all_doc_ids:
            bm25_score = bm25_normalized.get(doc_id, 0)
            vector_score = vector_normalized.get(doc_id, 0)
            
            # Weighted combination
            combined_scores[doc_id] = alpha * vector_score + (1 - alpha) * bm25_score
        
        # Sort by combined score
        sorted_doc_ids = sorted(
            combined_scores.keys(), 
            key=lambda x: combined_scores[x], 
            reverse=True
        )
        
        # Build result list
        doc_map = {r['id']: r for r in vector_results}
        
        final_results = []
        for doc_id in sorted_doc_ids[:k]:
            if doc_id in doc_map:
                result = doc_map[doc_id].copy()
                result['hybrid_score'] = combined_scores[doc_id]
                result['fusion_method'] = 'score'
                result['alpha'] = alpha
                
                final_results.append(result)
        
        return final_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get hybrid search statistics."""
        return {
            "bm25_available": self.bm25_index.is_built() if self.bm25_index else False,
            "vector_available": self.vector_table is not None,
            "bm25_stats": self.bm25_index.get_stats() if self.bm25_index else {}
        }
