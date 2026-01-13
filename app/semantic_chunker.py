"""
Semantic Chunking for Better Document Boundaries
Creates chunks based on semantic coherence rather than fixed token counts.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer, util
import re

logger = logging.getLogger(__name__)

class SemanticChunker:
    """
    Chunks documents based on semantic similarity rather than fixed sizes.
    Creates more coherent chunks that respect topic boundaries.
    """
    
    def __init__(self, embedding_model: SentenceTransformer, 
                 similarity_threshold: float = 0.5,
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 1000):
        """
        Initialize semantic chunker.
        
        Args:
            embedding_model: Pre-loaded sentence transformer
            similarity_threshold: Threshold for grouping sentences (0-1)
            min_chunk_size: Minimum chunk size in characters
            max_chunk_size: Maximum chunk size in characters
        """
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        
        self.stats = {
            "total_documents": 0,
            "total_chunks": 0,
            "avg_chunk_size": 0,
            "avg_coherence_score": 0.0
        }
    
    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Chunk text semantically.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries
        """
        if not text or len(text) < self.min_chunk_size:
            return [{
                "text": text,
                "chunk_index": 0,
                "coherence_score": 1.0,
                **(metadata or {})
            }]
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        if len(sentences) <= 1:
            return [{
                "text": text,
                "chunk_index": 0,
                "coherence_score": 1.0,
                **(metadata or {})
            }]
        
        # Encode sentences
        embeddings = self.embedding_model.encode(sentences)
        
        # Find semantic boundaries
        boundaries = self._find_boundaries(sentences, embeddings)
        
        # Create chunks from boundaries
        chunks = self._create_chunks(sentences, boundaries, metadata)
        
        # Update statistics
        self._update_stats(chunks)
        
        logger.debug(f"Created {len(chunks)} semantic chunks from {len(sentences)} sentences")
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences with better handling than simple regex.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Handle common abbreviations
        text = text.replace("Mr.", "Mr<prd>")
        text = text.replace("Mrs.", "Mrs<prd>")
        text = text.replace("Dr.", "Dr<prd>")
        text = text.replace("Sr.", "Sr<prd>")
        text = text.replace("Jr.", "Jr<prd>")
        text = text.replace("St.", "St<prd>")
        text = text.replace("vs.", "vs<prd>")
        text = text.replace("i.e.", "i<prd>e<prd>")
        text = text.replace("e.g.", "e<prd>g<prd>")
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        
        # Restore abbreviations
        sentences = [s.replace("<prd>", ".") for s in sentences]
        
        # Filter very short sentences
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        return sentences
    
    def _find_boundaries(self, sentences: List[str], embeddings: np.ndarray) -> List[int]:
        """
        Find semantic boundaries where topic changes.
        
        Args:
            sentences: List of sentences
            embeddings: Sentence embeddings
            
        Returns:
            List of boundary indices
        """
        if len(sentences) <= 1:
            return [0]
        
        # Calculate similarity between consecutive sentences
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = util.cos_sim(embeddings[i], embeddings[i + 1])[0][0].item()
            similarities.append(sim)
        
        # Find local minima (topic boundaries)
        boundaries = [0]  # Always start with first sentence
        
        for i in range(1, len(similarities) - 1):
            # Check if this is a local minimum and below threshold
            if similarities[i] < similarities[i-1] and similarities[i] < similarities[i+1]:
                if similarities[i] < self.similarity_threshold:
                    boundaries.append(i + 1)
        
        # Always end with last sentence
        boundaries.append(len(sentences))
        
        return boundaries
    
    def _create_chunks(self, sentences: List[str], boundaries: List[int], 
                      metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Create chunks from sentences and boundaries.
        
        Args:
            sentences: List of sentences
            boundaries: List of boundary indices
            metadata: Optional metadata
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1]
            
            chunk_sentences = sentences[start_idx:end_idx]
            chunk_text = " ".join(chunk_sentences)
            
            # Skip chunks that are too small
            if len(chunk_text) < self.min_chunk_size:
                # Try to merge with previous chunk if exists
                if chunks and len(chunks[-1]["text"]) + len(chunk_text) < self.max_chunk_size:
                    chunks[-1]["text"] += " " + chunk_text
                    chunks[-1]["sentence_count"] += len(chunk_sentences)
                    continue
            
            # Split chunks that are too large
            if len(chunk_text) > self.max_chunk_size:
                sub_chunks = self._split_large_chunk(chunk_sentences, metadata, len(chunks))
                chunks.extend(sub_chunks)
            else:
                # Calculate coherence score
                coherence = self._calculate_coherence(chunk_sentences)
                
                chunk = {
                    "text": chunk_text,
                    "chunk_index": len(chunks),
                    "sentence_count": len(chunk_sentences),
                    "char_count": len(chunk_text),
                    "coherence_score": round(coherence, 3),
                    **(metadata or {})
                }
                chunks.append(chunk)
        
        return chunks
    
    def _split_large_chunk(self, sentences: List[str], metadata: Optional[Dict], 
                          start_index: int) -> List[Dict[str, Any]]:
        """
        Split a chunk that exceeds max_chunk_size.
        
        Args:
            sentences: Sentences in the large chunk
            metadata: Metadata to attach
            start_index: Starting chunk index
            
        Returns:
            List of smaller chunks
        """
        sub_chunks = []
        current_sentences = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.max_chunk_size and current_sentences:
                # Create chunk from accumulated sentences
                chunk_text = " ".join(current_sentences)
                coherence = self._calculate_coherence(current_sentences)
                
                sub_chunks.append({
                    "text": chunk_text,
                    "chunk_index": start_index + len(sub_chunks),
                    "sentence_count": len(current_sentences),
                    "char_count": len(chunk_text),
                    "coherence_score": round(coherence, 3),
                    **(metadata or {})
                })
                
                current_sentences = [sentence]
                current_size = sentence_size
            else:
                current_sentences.append(sentence)
                current_size += sentence_size
        
        # Add remaining sentences
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            coherence = self._calculate_coherence(current_sentences)
            
            sub_chunks.append({
                "text": chunk_text,
                "chunk_index": start_index + len(sub_chunks),
                "sentence_count": len(current_sentences),
                "char_count": len(chunk_text),
                "coherence_score": round(coherence, 3),
                **(metadata or {})
            })
        
        return sub_chunks
    
    def _calculate_coherence(self, sentences: List[str]) -> float:
        """
        Calculate coherence score for a chunk.
        
        Args:
            sentences: Sentences in chunk
            
        Returns:
            Coherence score (0-1, higher is better)
        """
        if len(sentences) <= 1:
            return 1.0
        
        # Encode sentences
        embeddings = self.embedding_model.encode(sentences)
        
        # Calculate average pairwise similarity
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = util.cos_sim(embeddings[i], embeddings[j])[0][0].item()
                similarities.append(sim)
        
        return float(np.mean(similarities)) if similarities else 1.0
    
    def _update_stats(self, chunks: List[Dict[str, Any]]):
        """Update statistics."""
        self.stats["total_documents"] += 1
        self.stats["total_chunks"] += len(chunks)
        
        # Update average chunk size
        total_chars = sum(chunk["char_count"] for chunk in chunks)
        avg_size = total_chars / len(chunks) if chunks else 0
        
        n = self.stats["total_documents"]
        old_avg = self.stats["avg_chunk_size"]
        self.stats["avg_chunk_size"] = (old_avg * (n - 1) + avg_size) / n
        
        # Update average coherence
        avg_coherence = np.mean([chunk["coherence_score"] for chunk in chunks]) if chunks else 0
        old_coherence = self.stats["avg_coherence_score"]
        self.stats["avg_coherence_score"] = (old_coherence * (n - 1) + avg_coherence) / n
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chunking statistics."""
        stats = self.stats.copy()
        stats["avg_chunk_size"] = round(stats["avg_chunk_size"], 1)
        stats["avg_coherence_score"] = round(stats["avg_coherence_score"], 3)
        
        if stats["total_documents"] > 0:
            stats["avg_chunks_per_doc"] = round(stats["total_chunks"] / stats["total_documents"], 2)
        else:
            stats["avg_chunks_per_doc"] = 0
        
        return stats
    
    def compare_with_fixed_chunking(self, text: str, fixed_chunk_size: int = 700) -> Dict[str, Any]:
        """
        Compare semantic chunking with fixed-size chunking.
        
        Args:
            text: Input text
            fixed_chunk_size: Fixed chunk size for comparison
            
        Returns:
            Comparison statistics
        """
        # Semantic chunking
        semantic_chunks = self.chunk_text(text)
        
        # Fixed-size chunking
        fixed_chunks = []
        for i in range(0, len(text), fixed_chunk_size):
            fixed_chunks.append(text[i:i+fixed_chunk_size])
        
        return {
            "semantic_chunks": len(semantic_chunks),
            "fixed_chunks": len(fixed_chunks),
            "semantic_avg_coherence": round(np.mean([c["coherence_score"] for c in semantic_chunks]), 3),
            "semantic_avg_size": round(np.mean([c["char_count"] for c in semantic_chunks]), 1),
            "fixed_avg_size": fixed_chunk_size,
            "improvement": f"{len(semantic_chunks) / len(fixed_chunks) * 100:.1f}% chunks needed"
        }
