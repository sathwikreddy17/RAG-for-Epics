"""
Citation Export Module

Generates academic citations for sources used in RAG responses.
Supports multiple citation formats:
- BibTeX (for LaTeX)
- Chicago Style (humanities)
- MLA (Modern Language Association)
- APA (American Psychological Association)

Also generates bibliography entries for entire documents.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import re
import hashlib

logger = logging.getLogger(__name__)


class CitationExporter:
    """
    Generates academic citations in various formats.
    """
    
    # Known document metadata (can be extended)
    DOCUMENT_METADATA = {
        "Ramayana.of.Valmiki.by.Hari.Prasad.Shastri": {
            "title": "The Ramayana of Valmiki",
            "author": "Valmiki",
            "translator": "Hari Prasad Shastri",
            "publisher": "Shanti Sadan",
            "year": "1952",
            "location": "London",
            "type": "book",
            "original_language": "Sanskrit",
        },
        "Mahabharata (Unabridged in English)": {
            "title": "The Mahabharata",
            "author": "Vyasa",
            "translator": "Kisari Mohan Ganguli",
            "publisher": "Bharata Press",
            "year": "1883-1896",
            "location": "Calcutta",
            "type": "book",
            "original_language": "Sanskrit",
            "volumes": "12",
        },
        "361952998-Srimad-Valmiki-Ramayana-Sanskrit": {
            "title": "Srimad Valmiki Ramayana",
            "author": "Valmiki",
            "language": "Sanskrit",
            "type": "manuscript",
            "year": "1933",
            "note": "Sanskrit original text",
        },
        "dictallcheck": {
            "title": "Sanskrit-English Dictionary",
            "type": "dictionary",
            "note": "Reference dictionary for Sanskrit terms",
        },
    }
    
    def __init__(self):
        """Initialize the citation exporter."""
        self.access_date = datetime.now().strftime("%B %d, %Y")
    
    def _get_document_metadata(self, file_name: str) -> Dict[str, str]:
        """Get metadata for a document, with fallbacks for unknown documents."""
        # Try exact match first
        if file_name in self.DOCUMENT_METADATA:
            return self.DOCUMENT_METADATA[file_name]
        
        # Try partial match
        for key, metadata in self.DOCUMENT_METADATA.items():
            if key.lower() in file_name.lower() or file_name.lower() in key.lower():
                return metadata
        
        # Default metadata for unknown documents
        return {
            "title": file_name.replace(".pdf", "").replace("_", " ").replace("-", " "),
            "type": "document",
            "note": "Source document from local knowledge base",
        }
    
    def _generate_cite_key(self, file_name: str, page: Any) -> str:
        """Generate a unique citation key."""
        base = file_name.split(".")[0].lower()
        base = re.sub(r'[^a-z0-9]', '', base)[:20]
        return f"{base}{page}"
    
    def format_bibtex(self, source: Dict[str, Any]) -> str:
        """
        Format a source as BibTeX entry.
        
        Args:
            source: Source dict with file_name, page, text, etc.
            
        Returns:
            BibTeX formatted string
        """
        file_name = source.get("file_name", "Unknown")
        page = source.get("page", "")
        metadata = self._get_document_metadata(file_name)
        
        cite_key = self._generate_cite_key(file_name, page)
        doc_type = metadata.get("type", "book")
        
        if doc_type == "book":
            bibtex = f"""@book{{{cite_key},
    title = {{{metadata.get('title', file_name)}}},
    author = {{{metadata.get('author', 'Unknown')}}},"""
            
            if metadata.get('translator'):
                bibtex += f"\n    translator = {{{metadata.get('translator')}}},"
            
            if metadata.get('publisher'):
                bibtex += f"\n    publisher = {{{metadata.get('publisher')}}},"
            
            if metadata.get('year'):
                bibtex += f"\n    year = {{{metadata.get('year')}}},"
            
            if metadata.get('location'):
                bibtex += f"\n    address = {{{metadata.get('location')}}},"
            
            if page:
                bibtex += f"\n    pages = {{{page}}},"
            
            bibtex += "\n}"
            
        elif doc_type == "dictionary":
            bibtex = f"""@misc{{{cite_key},
    title = {{{metadata.get('title', file_name)}}},
    howpublished = {{Local Knowledge Base}},
    note = {{{metadata.get('note', '')}}},
}}"""
        else:
            bibtex = f"""@misc{{{cite_key},
    title = {{{metadata.get('title', file_name)}}},
    note = {{Page {page}. {metadata.get('note', '')}}},
    howpublished = {{Local Knowledge Base}},
}}"""
        
        return bibtex
    
    def format_chicago(self, source: Dict[str, Any]) -> str:
        """
        Format a source in Chicago style (notes-bibliography).
        
        Args:
            source: Source dict
            
        Returns:
            Chicago style citation
        """
        file_name = source.get("file_name", "Unknown")
        page = source.get("page", "")
        metadata = self._get_document_metadata(file_name)
        
        author = metadata.get("author", "")
        title = metadata.get("title", file_name)
        translator = metadata.get("translator", "")
        publisher = metadata.get("publisher", "")
        location = metadata.get("location", "")
        year = metadata.get("year", "")
        
        # Chicago bibliography format
        parts = []
        
        if author:
            parts.append(f"{author}.")
        
        parts.append(f"*{title}*.")
        
        if translator:
            parts.append(f"Translated by {translator}.")
        
        if location and publisher:
            parts.append(f"{location}: {publisher},")
        elif publisher:
            parts.append(f"{publisher},")
        
        if year:
            parts.append(f"{year}.")
        
        if page:
            parts.append(f"Page {page}.")
        
        return " ".join(parts)
    
    def format_mla(self, source: Dict[str, Any]) -> str:
        """
        Format a source in MLA style (9th edition).
        
        Args:
            source: Source dict
            
        Returns:
            MLA style citation
        """
        file_name = source.get("file_name", "Unknown")
        page = source.get("page", "")
        metadata = self._get_document_metadata(file_name)
        
        author = metadata.get("author", "")
        title = metadata.get("title", file_name)
        translator = metadata.get("translator", "")
        publisher = metadata.get("publisher", "")
        year = metadata.get("year", "")
        
        # MLA works cited format
        parts = []
        
        if author:
            parts.append(f"{author}.")
        
        parts.append(f"*{title}*.")
        
        if translator:
            parts.append(f"Translated by {translator},")
        
        if publisher:
            parts.append(f"{publisher},")
        
        if year:
            parts.append(f"{year}.")
        
        if page:
            parts.append(f"p. {page}.")
        
        return " ".join(parts)
    
    def format_apa(self, source: Dict[str, Any]) -> str:
        """
        Format a source in APA style (7th edition).
        
        Args:
            source: Source dict
            
        Returns:
            APA style citation
        """
        file_name = source.get("file_name", "Unknown")
        page = source.get("page", "")
        metadata = self._get_document_metadata(file_name)
        
        author = metadata.get("author", "")
        title = metadata.get("title", file_name)
        translator = metadata.get("translator", "")
        publisher = metadata.get("publisher", "")
        year = metadata.get("year", "n.d.")
        
        # APA reference format
        parts = []
        
        if author:
            # APA uses Last, F. M. format
            parts.append(f"{author}")
        else:
            parts.append("Unknown")
        
        parts.append(f"({year}).")
        
        parts.append(f"*{title}*")
        
        if translator:
            parts.append(f"({translator}, Trans.).")
        else:
            parts.append(".")
        
        if publisher:
            parts.append(f"{publisher}.")
        
        if page:
            parts.append(f"(p. {page})")
        
        return " ".join(parts)
    
    def format_inline(self, source: Dict[str, Any], style: str = "chicago") -> str:
        """
        Format an inline/parenthetical citation.
        
        Args:
            source: Source dict
            style: Citation style
            
        Returns:
            Inline citation
        """
        file_name = source.get("file_name", "Unknown")
        page = source.get("page", "")
        metadata = self._get_document_metadata(file_name)
        
        author = metadata.get("author", "Unknown")
        year = metadata.get("year", "n.d.")
        
        # Get last name for author
        author_last = author.split()[-1] if author else "Unknown"
        
        if style.lower() == "apa":
            if page:
                return f"({author_last}, {year}, p. {page})"
            return f"({author_last}, {year})"
        
        elif style.lower() == "mla":
            if page:
                return f"({author_last} {page})"
            return f"({author_last})"
        
        else:  # chicago
            if page:
                return f"({author_last}, {page})"
            return f"({author_last})"
    
    def export_citations(self, sources: List[Dict[str, Any]], 
                        format: str = "bibtex") -> Dict[str, Any]:
        """
        Export all sources in the specified format.
        
        Args:
            sources: List of source dicts
            format: Citation format (bibtex, chicago, mla, apa)
            
        Returns:
            Dict with citations and metadata
        """
        format_lower = format.lower()
        
        if format_lower == "bibtex":
            formatter = self.format_bibtex
        elif format_lower == "chicago":
            formatter = self.format_chicago
        elif format_lower == "mla":
            formatter = self.format_mla
        elif format_lower == "apa":
            formatter = self.format_apa
        else:
            return {"error": f"Unknown format: {format}"}
        
        citations = []
        for i, source in enumerate(sources, 1):
            try:
                citation = formatter(source)
                citations.append({
                    "index": i,
                    "file_name": source.get("file_name"),
                    "page": source.get("page"),
                    "citation": citation,
                    "inline": self.format_inline(source, format_lower),
                })
            except Exception as e:
                logger.error(f"Error formatting citation: {e}")
                citations.append({
                    "index": i,
                    "error": str(e),
                })
        
        # Combine all citations into single text block
        if format_lower == "bibtex":
            combined = "\n\n".join(c["citation"] for c in citations if "citation" in c)
        else:
            combined = "\n\n".join(f"[{c['index']}] {c['citation']}" for c in citations if "citation" in c)
        
        return {
            "format": format,
            "count": len(citations),
            "citations": citations,
            "combined": combined,
            "generated_at": datetime.now().isoformat(),
        }
    
    def get_bibliography_entry(self, file_name: str, format: str = "chicago") -> str:
        """Get a bibliography entry for an entire document."""
        metadata = self._get_document_metadata(file_name)
        
        # Create a dummy source to use the formatters
        source = {"file_name": file_name}
        
        if format.lower() == "bibtex":
            return self.format_bibtex(source)
        elif format.lower() == "chicago":
            return self.format_chicago(source)
        elif format.lower() == "mla":
            return self.format_mla(source)
        elif format.lower() == "apa":
            return self.format_apa(source)
        else:
            return f"Unknown format: {format}"


# Singleton instance
_citation_exporter: Optional[CitationExporter] = None


def get_citation_exporter() -> CitationExporter:
    """Get or create the citation exporter singleton."""
    global _citation_exporter
    if _citation_exporter is None:
        _citation_exporter = CitationExporter()
    return _citation_exporter
