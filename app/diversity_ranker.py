"""
Diversity Ranker - Maximal Marginal Relevance (MMR) for result diversification.

Prevents near-identical chunks from dominating results by balancing:
- Relevance: How well a chunk matches the query
- Diversity: How different a chunk is from already-selected chunks

Configure via .env:
    USE_DIVERSITY_RANKING=true|false
    MMR_LAMBDA=0.7  (0=max diversity, 1=max relevance)
    MMR_SIMILARITY_THRESHOLD=0.85  (chunks more similar than this to selected ones get penalized)
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class DiversityRanker:
    """
    Implements Maximal Marginal Relevance (MMR) for diversifying search results.
    
    MMR balances relevance and diversity:
    MMR = λ * Relevance(doc, query) - (1-λ) * max(Similarity(doc, selected_docs))
    
    Higher λ = more emphasis on relevance
    Lower λ = more emphasis on diversity
    """
    
    def __init__(
        self,
        embedding_model,
        lambda_param: float = 0.7,
        similarity_threshold: float = 0.85,
    ):
        """
        Initialize the diversity ranker.
        
        Args:
            embedding_model: SentenceTransformer model for computing embeddings
            lambda_param: Balance between relevance (1.0) and diversity (0.0). Default 0.7.
            similarity_threshold: Chunks with similarity > this to selected chunks get penalized more
        """
        self.embedding_model = embedding_model
        self.lambda_param = lambda_param
        self.similarity_threshold = similarity_threshold
        
        # Statistics tracking
        self._stats = {
            "total_diversifications": 0,
            "total_candidates_processed": 0,
            "total_duplicates_suppressed": 0,
            "avg_diversity_gain": 0.0,
        }
    
    def _compute_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))
    
    def _compute_text_similarity(self, text1: str, text2: str) -> float:
        """Compute approximate text similarity using token overlap (fast heuristic)."""
        if not text1 or not text2:
            return 0.0
        
        # Tokenize (simple whitespace split)
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0
    
    def _is_near_duplicate(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Check if two texts are near-duplicates based on token overlap."""
        return self._compute_text_similarity(text1, text2) > threshold
    
    def rerank_mmr(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        relevance_scores: List[float],
        k: int,
        use_embeddings: bool = True,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Apply MMR to select diverse results.
        
        Args:
            query: The search query
            candidates: List of candidate documents (must have 'text' field)
            relevance_scores: Relevance score for each candidate (higher = more relevant)
            k: Number of results to return
            use_embeddings: If True, use embedding similarity; else use text overlap
            
        Returns:
            Tuple of (selected_documents, mmr_info_dict)
        """
        if not candidates or k <= 0:
            return [], {"selected": 0, "method": "empty"}
        
        n = len(candidates)
        if n <= k:
            # Not enough candidates to diversify
            return candidates, {"selected": n, "method": "passthrough", "reason": "fewer candidates than k"}
        
        # Normalize relevance scores to [0, 1]
        max_score = max(relevance_scores) if relevance_scores else 1.0
        min_score = min(relevance_scores) if relevance_scores else 0.0
        score_range = max_score - min_score
        if score_range > 0:
            norm_scores = [(s - min_score) / score_range for s in relevance_scores]
        else:
            norm_scores = [1.0] * n
        
        # Compute embeddings if needed
        embeddings = None
        if use_embeddings:
            try:
                texts = [c.get("text", "") for c in candidates]
                embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
            except Exception as e:
                logger.warning(f"Failed to compute embeddings for MMR, falling back to text similarity: {e}")
                use_embeddings = False
        
        # MMR selection
        selected_indices = []
        selected_texts = []
        remaining = set(range(n))
        duplicates_suppressed = 0
        
        # Track original ranks for diversity gain calculation
        original_order = sorted(range(n), key=lambda i: relevance_scores[i], reverse=True)
        
        while len(selected_indices) < k and remaining:
            best_idx = None
            best_mmr = float('-inf')
            
            for idx in remaining:
                # Relevance component
                relevance = norm_scores[idx]
                
                # Diversity component (max similarity to already selected)
                max_sim = 0.0
                if selected_indices:
                    if use_embeddings and embeddings is not None:
                        for sel_idx in selected_indices:
                            sim = self._compute_similarity(embeddings[idx], embeddings[sel_idx])
                            max_sim = max(max_sim, sim)
                    else:
                        # Text-based similarity
                        cand_text = candidates[idx].get("text", "")
                        for sel_text in selected_texts:
                            sim = self._compute_text_similarity(cand_text, sel_text)
                            max_sim = max(max_sim, sim)
                
                # Check for near-duplicate suppression
                if max_sim > self.similarity_threshold:
                    duplicates_suppressed += 1
                
                # MMR score
                mmr_score = self.lambda_param * relevance - (1 - self.lambda_param) * max_sim
                
                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected_indices.append(best_idx)
                selected_texts.append(candidates[best_idx].get("text", ""))
                remaining.remove(best_idx)
            else:
                break
        
        # Build result
        selected = [candidates[i] for i in selected_indices]
        
        # Calculate diversity gain (how much reordering happened)
        original_top_k = set(original_order[:k])
        selected_set = set(selected_indices)
        diversity_gain = len(selected_set - original_top_k) / k if k > 0 else 0.0
        
        # Update stats
        self._stats["total_diversifications"] += 1
        self._stats["total_candidates_processed"] += n
        self._stats["total_duplicates_suppressed"] += duplicates_suppressed
        # Running average of diversity gain
        prev_avg = self._stats["avg_diversity_gain"]
        count = self._stats["total_diversifications"]
        self._stats["avg_diversity_gain"] = prev_avg + (diversity_gain - prev_avg) / count
        
        mmr_info = {
            "method": "mmr",
            "lambda": self.lambda_param,
            "candidates_considered": n,
            "selected": len(selected),
            "duplicates_suppressed": duplicates_suppressed,
            "diversity_gain": round(diversity_gain, 3),
            "used_embeddings": use_embeddings,
            "selected_indices": selected_indices,
        }
        
        return selected, mmr_info
    
    def deduplicate_by_page(
        self,
        candidates: List[Dict[str, Any]],
        max_per_page: int = 2,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Simple deduplication: limit chunks per (file, page) combination.
        
        Useful as a fast pre-filter before MMR.
        
        Args:
            candidates: List of candidate documents
            max_per_page: Maximum chunks to keep per (file, page) combination
            
        Returns:
            Tuple of (filtered_candidates, dedup_info)
        """
        if not candidates:
            return [], {"method": "page_dedup", "removed": 0}
        
        page_counts: Dict[Tuple[str, Any], int] = {}
        filtered = []
        removed = 0
        
        for c in candidates:
            file_name = c.get("file_name", "")
            page = c.get("page_number", c.get("page", ""))
            key = (file_name, page)
            
            count = page_counts.get(key, 0)
            if count < max_per_page:
                filtered.append(c)
                page_counts[key] = count + 1
            else:
                removed += 1
        
        return filtered, {
            "method": "page_dedup",
            "max_per_page": max_per_page,
            "original_count": len(candidates),
            "filtered_count": len(filtered),
            "removed": removed,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get diversity ranking statistics."""
        return {
            "total_diversifications": self._stats["total_diversifications"],
            "total_candidates_processed": self._stats["total_candidates_processed"],
            "total_duplicates_suppressed": self._stats["total_duplicates_suppressed"],
            "avg_diversity_gain": round(self._stats["avg_diversity_gain"], 3),
        }
