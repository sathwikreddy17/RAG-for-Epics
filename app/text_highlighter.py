"""
Text Highlighter Module for RAG System.
Highlights query-relevant terms in source passages.
"""

import re
import logging
from typing import List, Dict, Any, Set, Tuple
from html import escape

logger = logging.getLogger(__name__)


class TextHighlighter:
    """Highlights query terms in source text passages."""
    
    # Common English stopwords to exclude from highlighting
    STOPWORDS = {
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
        'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some',
        'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
        'very', 's', 't', 'just', 'don', 'now', 'about', 'there', 'here', 'i',
        'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'it', 'they', 'them',
        'his', 'her', 'its', 'their', 'him', 'tell', 'said', 'know', 'did'
    }
    
    # Minimum word length to highlight
    MIN_WORD_LENGTH = 3
    
    def __init__(self, highlight_class: str = "highlight"):
        """
        Initialize the text highlighter.
        
        Args:
            highlight_class: CSS class name for highlighted spans
        """
        self.highlight_class = highlight_class
    
    def extract_keywords(self, query: str) -> Set[str]:
        """
        Extract meaningful keywords from a query.
        
        Args:
            query: The search query
            
        Returns:
            Set of keywords to highlight
        """
        # Tokenize and normalize
        words = re.findall(r'\b[a-zA-Z]+\b', query.lower())
        
        # Filter out stopwords and short words
        keywords = {
            word for word in words
            if word not in self.STOPWORDS and len(word) >= self.MIN_WORD_LENGTH
        }
        
        # Also keep proper nouns (capitalized words in original query)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', query)
        for noun in proper_nouns:
            if len(noun) >= 2:  # Keep shorter proper nouns
                keywords.add(noun.lower())
        
        return keywords
    
    def highlight_text(
        self,
        text: str,
        query: str,
        max_highlights: int = 50,
        escape_html: bool = True
    ) -> Dict[str, Any]:
        """
        Highlight query terms in text.
        
        Args:
            text: The source text to highlight
            query: The search query containing terms to highlight
            max_highlights: Maximum number of highlights (to prevent over-highlighting)
            escape_html: Whether to escape HTML characters
            
        Returns:
            Dictionary with:
                - highlighted_text: Text with HTML highlight spans
                - keywords: Keywords that were highlighted
                - highlight_count: Number of highlights applied
        """
        if not text or not query:
            return {
                "highlighted_text": escape(text) if escape_html else text,
                "keywords": [],
                "highlight_count": 0
            }
        
        keywords = self.extract_keywords(query)
        
        if not keywords:
            return {
                "highlighted_text": escape(text) if escape_html else text,
                "keywords": [],
                "highlight_count": 0
            }
        
        # Escape HTML first if needed
        if escape_html:
            text = escape(text)
        
        # Build regex pattern for all keywords (case-insensitive word boundaries)
        # Sort by length (longest first) to handle overlapping matches correctly
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        pattern = r'\b(' + '|'.join(re.escape(kw) for kw in sorted_keywords) + r')\b'
        
        highlight_count = 0
        highlighted_keywords = set()
        
        def replace_match(match):
            nonlocal highlight_count
            if highlight_count >= max_highlights:
                return match.group(0)
            highlight_count += 1
            matched_word = match.group(0)
            highlighted_keywords.add(matched_word.lower())
            return f'<span class="{self.highlight_class}">{matched_word}</span>'
        
        highlighted_text = re.sub(pattern, replace_match, text, flags=re.IGNORECASE)
        
        return {
            "highlighted_text": highlighted_text,
            "keywords": list(highlighted_keywords),
            "highlight_count": highlight_count
        }
    
    def highlight_sources(
        self,
        sources: List[Dict[str, Any]],
        query: str,
        text_field: str = "text",
        max_highlights_per_source: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Add highlighting to a list of source documents.
        
        Args:
            sources: List of source documents
            query: The search query
            text_field: Field name containing the text to highlight
            max_highlights_per_source: Maximum highlights per source
            
        Returns:
            Sources with added 'highlighted_text' field
        """
        keywords = self.extract_keywords(query)
        
        for source in sources:
            text = source.get(text_field, "")
            if text:
                result = self.highlight_text(
                    text,
                    query,
                    max_highlights=max_highlights_per_source
                )
                source["highlighted_text"] = result["highlighted_text"]
                source["highlight_keywords"] = result["keywords"]
                source["highlight_count"] = result["highlight_count"]
            else:
                source["highlighted_text"] = ""
                source["highlight_keywords"] = []
                source["highlight_count"] = 0
        
        return sources


# Singleton instance
_highlighter = None


def get_text_highlighter() -> TextHighlighter:
    """Get the singleton text highlighter instance."""
    global _highlighter
    if _highlighter is None:
        _highlighter = TextHighlighter()
    return _highlighter
