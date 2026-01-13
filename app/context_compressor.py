"""
Context Compressor for Token Optimization
Removes irrelevant sentences from retrieved context to reduce LLM input size.
"""

import logging
import re
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer, util
import numpy as np

logger = logging.getLogger(__name__)

class ContextCompressor:
    """
    Compresses retrieved context by removing irrelevant sentences.
    Uses semantic similarity to keep only the most relevant parts.
    """
    
    def __init__(self, embedding_model: SentenceTransformer, relevance_threshold: float = 0.3):
        """
        Initialize context compressor.
        
        Args:
            embedding_model: Pre-loaded sentence transformer model
            relevance_threshold: Minimum similarity score to keep sentence (0-1)
        """
        self.embedding_model = embedding_model
        self.relevance_threshold = relevance_threshold
        
        self.stats = {
            "total_compressions": 0,
            "total_sentences_input": 0,
            "total_sentences_output": 0,
            "total_chars_saved": 0,
            "avg_compression_ratio": 0.0
        }
    
    def compress(self, query: str, contexts: List[str], 
                 max_sentences: int = None) -> Tuple[List[str], Dict[str, Any]]:
        """
        Compress retrieved contexts by removing irrelevant sentences.
        
        Args:
            query: User query
            contexts: List of retrieved context strings
            max_sentences: Maximum sentences to keep (None = no limit)
            
        Returns:
            Tuple of (compressed_contexts, compression_stats)
        """
        if not contexts:
            return [], {"compression_ratio": 0.0, "sentences_kept": 0, "sentences_removed": 0}
        
        # Combine all contexts
        all_sentences = []
        sentence_sources = []  # Track which context each sentence came from
        
        for ctx_idx, context in enumerate(contexts):
            sentences = self._split_into_sentences(context)
            all_sentences.extend(sentences)
            sentence_sources.extend([ctx_idx] * len(sentences))
        
        if not all_sentences:
            return contexts, {"compression_ratio": 1.0, "sentences_kept": 0, "sentences_removed": 0}
        
        original_count = len(all_sentences)
        original_length = sum(len(s) for s in all_sentences)
        
        # Score each sentence
        scored_sentences = self._score_sentences(query, all_sentences)
        
        # Filter by relevance threshold
        relevant_sentences = [
            (sent, score, src) 
            for (sent, score), src in zip(scored_sentences, sentence_sources)
            if score >= self.relevance_threshold
        ]
        
        # Sort by score (descending)
        relevant_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Apply max_sentences limit if specified
        if max_sentences and len(relevant_sentences) > max_sentences:
            relevant_sentences = relevant_sentences[:max_sentences]
        
        # Reconstruct contexts preserving original grouping
        compressed_contexts = self._reconstruct_contexts(
            relevant_sentences, len(contexts)
        )
        
        # Calculate stats
        kept_count = len(relevant_sentences)
        removed_count = original_count - kept_count
        compressed_length = sum(len(s[0]) for s in relevant_sentences)
        compression_ratio = kept_count / original_count if original_count > 0 else 1.0
        chars_saved = original_length - compressed_length
        
        # Update global stats
        self._update_stats(original_count, kept_count, chars_saved, compression_ratio)
        
        stats = {
            "compression_ratio": round(compression_ratio, 3),
            "sentences_kept": kept_count,
            "sentences_removed": removed_count,
            "chars_original": original_length,
            "chars_compressed": compressed_length,
            "chars_saved": chars_saved,
            "avg_relevance_score": round(np.mean([s[1] for s in relevant_sentences]), 3) if relevant_sentences else 0.0
        }
        
        logger.debug(f"Compressed context: {kept_count}/{original_count} sentences kept "
                    f"({compression_ratio:.1%}), {chars_saved} chars saved")
        
        return compressed_contexts, stats
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with nltk/spacy)
        # Split on . ! ? followed by space and capital letter or end
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        
        # Filter out very short "sentences" (likely formatting artifacts)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        return sentences
    
    def _score_sentences(self, query: str, sentences: List[str]) -> List[Tuple[str, float]]:
        """
        Score sentences by relevance to query.
        
        Args:
            query: User query
            sentences: List of sentences
            
        Returns:
            List of (sentence, score) tuples
        """
        if not sentences:
            return []
        
        # Encode query and sentences
        query_embedding = self.embedding_model.encode(query, convert_to_tensor=True)
        sentence_embeddings = self.embedding_model.encode(sentences, convert_to_tensor=True)
        
        # Calculate cosine similarity
        similarities = util.cos_sim(query_embedding, sentence_embeddings)[0]
        
        # Convert to list of (sentence, score) tuples
        scored = [(sent, float(sim)) for sent, sim in zip(sentences, similarities)]
        
        return scored
    
    def _reconstruct_contexts(self, relevant_sentences: List[Tuple[str, float, int]], 
                             num_contexts: int) -> List[str]:
        """
        Reconstruct contexts from filtered sentences, preserving original grouping.
        
        Args:
            relevant_sentences: List of (sentence, score, source_index) tuples
            num_contexts: Number of original contexts
            
        Returns:
            List of compressed context strings
        """
        # Group sentences by source
        context_sentences = {i: [] for i in range(num_contexts)}
        
        for sentence, score, source_idx in relevant_sentences:
            context_sentences[source_idx].append(sentence)
        
        # Reconstruct context strings
        compressed = []
        for idx in range(num_contexts):
            if context_sentences[idx]:
                compressed.append(" ".join(context_sentences[idx]))
        
        return compressed
    
    def _update_stats(self, input_count: int, output_count: int, 
                     chars_saved: int, compression_ratio: float):
        """Update global statistics."""
        self.stats["total_compressions"] += 1
        self.stats["total_sentences_input"] += input_count
        self.stats["total_sentences_output"] += output_count
        self.stats["total_chars_saved"] += chars_saved
        
        # Update running average
        n = self.stats["total_compressions"]
        old_avg = self.stats["avg_compression_ratio"]
        self.stats["avg_compression_ratio"] = (old_avg * (n - 1) + compression_ratio) / n
    
    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        stats = self.stats.copy()
        
        if stats["total_sentences_input"] > 0:
            stats["overall_compression_ratio"] = \
                stats["total_sentences_output"] / stats["total_sentences_input"]
        else:
            stats["overall_compression_ratio"] = 1.0
        
        return stats
    
    def compress_single_context(self, query: str, context: str, 
                               max_length: int = None) -> Tuple[str, Dict[str, Any]]:
        """
        Compress a single context string.
        
        Args:
            query: User query
            context: Single context string
            max_length: Maximum character length (None = no limit)
            
        Returns:
            Tuple of (compressed_context, stats)
        """
        compressed_list, stats = self.compress(query, [context])
        
        if not compressed_list:
            return "", stats
        
        compressed = compressed_list[0]
        
        # Apply character limit if specified
        if max_length and len(compressed) > max_length:
            compressed = compressed[:max_length] + "..."
            stats["truncated"] = True
            stats["chars_compressed"] = max_length
        
        return compressed, stats
