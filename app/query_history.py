"""
Query History Module for RAG System.
Stores and manages recent query history.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import deque
import hashlib

logger = logging.getLogger(__name__)


class QueryHistory:
    """Manages query history with persistence."""
    
    def __init__(
        self,
        history_file: str = "data/query_history.json",
        max_entries: int = 100
    ):
        """
        Initialize query history manager.
        
        Args:
            history_file: Path to the history JSON file
            max_entries: Maximum number of entries to keep
        """
        self.history_file = Path(history_file)
        self.max_entries = max_entries
        self.history: deque = deque(maxlen=max_entries)
        
        # Create directory if needed
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing history
        self._load_history()
        
        logger.info(f"Query history initialized with {len(self.history)} entries")
    
    def _load_history(self):
        """Load history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    entries = data.get("entries", [])
                    # Load into deque (most recent last)
                    self.history = deque(entries[-self.max_entries:], maxlen=self.max_entries)
                    logger.info(f"Loaded {len(self.history)} history entries")
            except Exception as e:
                logger.error(f"Error loading history: {e}")
                self.history = deque(maxlen=self.max_entries)
        else:
            self.history = deque(maxlen=self.max_entries)
    
    def _save_history(self):
        """Save history to file."""
        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "entries": list(self.history)
            }
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    def _generate_id(self, query: str) -> str:
        """Generate a unique ID for a query."""
        timestamp = datetime.now().isoformat()
        content = f"{query}:{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def add_entry(
        self,
        query: str,
        answer: str,
        sources: List[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        num_sources: int = 0,
        query_type: Optional[str] = None,
        response_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Add a query to history.
        
        Args:
            query: The query text
            answer: The generated answer (truncated for storage)
            sources: Source documents used (for counting)
            metadata: Additional metadata
            num_sources: Number of sources used (deprecated, use sources list)
            query_type: Type of query (factual, analytical, etc.)
            response_time: Time taken to generate response
            
        Returns:
            The created history entry
        """
        # Truncate answer for storage (keep first 200 chars)
        answer_preview = answer[:200] + "..." if len(answer) > 200 else answer
        
        # Calculate source count from sources list or use num_sources
        source_count = len(sources) if sources else num_sources
        
        # Get response time from metadata if available
        if metadata and not response_time:
            timings = metadata.get("timings", {})
            response_time = timings.get("total")
        
        # Get query type from metadata if available
        if metadata and not query_type:
            query_type = metadata.get("query_type")
        
        entry = {
            "id": self._generate_id(query),
            "query": query,
            "answer_preview": answer_preview,
            "source_count": source_count,
            "query_type": query_type,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat(),
            "date_display": datetime.now().strftime("%b %d, %H:%M")
        }
        
        # Check if this exact query already exists (avoid duplicates)
        # Remove older duplicate if exists
        self.history = deque(
            [e for e in self.history if e["query"].lower() != query.lower()],
            maxlen=self.max_entries
        )
        
        # Add new entry
        self.history.append(entry)
        
        # Save to file
        self._save_history()
        
        logger.debug(f"Added history entry: {entry['id']}")
        return entry
    
    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent history entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of history entries (most recent first)
        """
        # Return reversed (most recent first)
        entries = list(self.history)
        entries.reverse()
        return entries[:limit]
    
    def get_history(self, limit: int = 50, search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get history entries with optional search.
        
        Args:
            limit: Maximum number of entries to return
            search_term: Optional term to filter by
            
        Returns:
            List of history entries (most recent first)
        """
        if search_term:
            return self.search_history(search_term, limit)
        return self.get_recent(limit)
    
    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific history entry by ID.
        
        Args:
            entry_id: The entry ID
            
        Returns:
            The entry or None if not found
        """
        for entry in self.history:
            if entry["id"] == entry_id:
                return entry
        return None
    
    def delete_entry(self, entry_id: str) -> bool:
        """
        Delete a history entry.
        
        Args:
            entry_id: The entry ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        original_len = len(self.history)
        self.history = deque(
            [e for e in self.history if e["id"] != entry_id],
            maxlen=self.max_entries
        )
        
        if len(self.history) < original_len:
            self._save_history()
            return True
        return False
    
    def clear_history(self) -> int:
        """
        Clear all history entries.
        
        Returns:
            Number of entries cleared
        """
        count = len(self.history)
        self.history.clear()
        self._save_history()
        logger.info(f"Cleared {count} history entries")
        return count
    
    def search_history(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search history entries.
        
        Args:
            search_term: Term to search for in queries
            limit: Maximum results
            
        Returns:
            Matching entries (most recent first)
        """
        search_lower = search_term.lower()
        matches = [
            e for e in self.history
            if search_lower in e["query"].lower()
        ]
        matches.reverse()  # Most recent first
        return matches[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get history statistics."""
        if not self.history:
            return {
                "total_entries": 0,
                "oldest_entry": None,
                "newest_entry": None,
                "query_types": {}
            }
        
        # Count query types
        query_types = {}
        for entry in self.history:
            qt = entry.get("query_type", "unknown") or "unknown"
            query_types[qt] = query_types.get(qt, 0) + 1
        
        entries = list(self.history)
        return {
            "total_entries": len(entries),
            "oldest_entry": entries[0]["timestamp"] if entries else None,
            "newest_entry": entries[-1]["timestamp"] if entries else None,
            "query_types": query_types,
            "max_entries": self.max_entries
        }


# Singleton instance
_query_history = None


def get_query_history() -> QueryHistory:
    """Get the singleton query history instance."""
    global _query_history
    if _query_history is None:
        _query_history = QueryHistory()
    return _query_history
