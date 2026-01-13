"""
Evidence Extractor for quote-level grounding.

Extracts the most relevant sentences from retrieved chunks to use as
explicit evidence/quotes in the LLM prompt, improving faithfulness.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)


class EvidenceExtractor:
    """
    Extracts the most relevant sentences from chunks for quote-level grounding.
    
    This helps the LLM by:
    1. Highlighting the most relevant evidence
    2. Providing explicit quotes to cite
    3. Reducing noise from less relevant parts of chunks
    """
    
    def __init__(
        self, 
        embedding_model: SentenceTransformer,
        min_sentence_length: int = 20,
        max_sentence_length: int = 500,
        similarity_threshold: float = 0.3,
    ):
        """
        Initialize the evidence extractor.
        
        Args:
            embedding_model: SentenceTransformer model for computing similarity
            min_sentence_length: Minimum character length for a valid sentence
            max_sentence_length: Maximum character length for a sentence
            similarity_threshold: Minimum similarity score to include a sentence
        """
        self.embedding_model = embedding_model
        self.min_sentence_length = min_sentence_length
        self.max_sentence_length = max_sentence_length
        self.similarity_threshold = similarity_threshold
        
        # Stats tracking
        self._stats = {
            "total_extractions": 0,
            "total_sentences_processed": 0,
            "total_sentences_selected": 0,
        }
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex-based splitting.
        
        Handles common sentence boundaries while preserving abbreviations.
        """
        if not text:
            return []
        
        # Clean up the text
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        # Split on sentence boundaries
        # This pattern looks for: period/exclamation/question followed by space and capital
        # But avoids splitting on common abbreviations
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        
        # First pass: split on clear sentence boundaries
        raw_sentences = re.split(sentence_pattern, text)
        
        # Second pass: clean and filter
        sentences = []
        for s in raw_sentences:
            s = s.strip()
            if len(s) >= self.min_sentence_length:
                # Truncate very long sentences
                if len(s) > self.max_sentence_length:
                    s = s[:self.max_sentence_length] + "..."
                sentences.append(s)
        
        return sentences
    
    def _compute_sentence_scores(
        self, 
        query: str, 
        sentences: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Compute relevance scores for sentences against the query.
        
        Returns list of (sentence, score) tuples sorted by score descending.
        """
        if not sentences:
            return []
        
        # Encode query and sentences
        query_embedding = self.embedding_model.encode(query, convert_to_numpy=True)
        sentence_embeddings = self.embedding_model.encode(sentences, convert_to_numpy=True)
        
        # Compute cosine similarities
        # Normalize embeddings
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-9)
        sentence_norms = sentence_embeddings / (np.linalg.norm(sentence_embeddings, axis=1, keepdims=True) + 1e-9)
        
        # Compute similarities
        similarities = np.dot(sentence_norms, query_norm)
        
        # Create scored list
        scored = [(sentences[i], float(similarities[i])) for i in range(len(sentences))]
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored
    
    def extract_evidence(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        max_sentences_per_chunk: int = 3,
        max_total_sentences: int = 10,
    ) -> Dict[str, Any]:
        """
        Extract the most relevant evidence sentences from chunks.
        
        Args:
            query: The user's query
            chunks: List of retrieved chunk dictionaries (must have 'text' key)
            max_sentences_per_chunk: Maximum sentences to extract per chunk
            max_total_sentences: Maximum total sentences to return
            
        Returns:
            Dictionary with:
                - evidence: List of evidence items with sentence, score, source info
                - summary: Summary statistics
        """
        self._stats["total_extractions"] += 1
        
        all_evidence = []
        
        for chunk_idx, chunk in enumerate(chunks):
            text = chunk.get("text", "")
            if not text:
                continue
            
            # Split into sentences
            sentences = self._split_into_sentences(text)
            self._stats["total_sentences_processed"] += len(sentences)
            
            if not sentences:
                continue
            
            # Score sentences against query
            scored_sentences = self._compute_sentence_scores(query, sentences)
            
            # Take top sentences that meet threshold
            selected = []
            for sentence, score in scored_sentences:
                if score >= self.similarity_threshold and len(selected) < max_sentences_per_chunk:
                    selected.append({
                        "sentence": sentence,
                        "score": round(score, 4),
                        "chunk_index": chunk_idx,
                        "file_name": chunk.get("file_name", "Unknown"),
                        "page": chunk.get("page_number", "N/A"),
                    })
            
            all_evidence.extend(selected)
        
        # Sort all evidence by score and take top
        all_evidence.sort(key=lambda x: x["score"], reverse=True)
        final_evidence = all_evidence[:max_total_sentences]
        
        self._stats["total_sentences_selected"] += len(final_evidence)
        
        return {
            "evidence": final_evidence,
            "summary": {
                "chunks_processed": len(chunks),
                "sentences_extracted": len(final_evidence),
                "top_score": final_evidence[0]["score"] if final_evidence else 0.0,
                "avg_score": round(sum(e["score"] for e in final_evidence) / len(final_evidence), 4) if final_evidence else 0.0,
            }
        }
    
    def format_evidence_for_prompt(
        self,
        evidence_result: Dict[str, Any],
        include_scores: bool = False,
    ) -> str:
        """
        Format extracted evidence as a string for inclusion in the LLM prompt.
        
        Args:
            evidence_result: Result from extract_evidence()
            include_scores: Whether to include relevance scores
            
        Returns:
            Formatted string with numbered evidence quotes
        """
        evidence = evidence_result.get("evidence", [])
        if not evidence:
            return ""
        
        lines = ["Key Evidence:"]
        for i, e in enumerate(evidence, 1):
            source_info = f"[{e['file_name']}, p.{e['page']}]"
            score_info = f" (relevance: {e['score']:.2f})" if include_scores else ""
            lines.append(f"  {i}. \"{e['sentence']}\" {source_info}{score_info}")
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        return {
            **self._stats,
            "avg_sentences_per_extraction": round(
                self._stats["total_sentences_selected"] / max(1, self._stats["total_extractions"]), 2
            ),
        }
