"""
Response Cache for RAG System
Caches answers to frequently asked questions for faster responses.
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from collections import OrderedDict

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    LRU cache for RAG responses.
    Caches query-answer pairs to speed up repeated queries.
    """
    
    def __init__(
        self,
        cache_path: Optional[str] = None,
        max_size: int = 500,
        ttl_hours: int = 24,
    ):
        """
        Initialize response cache.
        
        Args:
            cache_path: Path to persist cache (optional)
            max_size: Maximum number of cached responses
            ttl_hours: Time-to-live for cache entries in hours
        """
        self.cache_path = Path(cache_path) if cache_path else Path(os.getenv("CACHE_PATH", "./data/cache"))
        self.max_size = int(os.getenv("CACHE_MAX_SIZE", str(max_size)))
        self.ttl_hours = int(os.getenv("CACHE_TTL_HOURS", str(ttl_hours)))
        
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_path / "response_cache.json"
        
        # LRU cache (OrderedDict for LRU behavior)
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }
        
        # Load persisted cache
        self._load_cache()
        
        logger.info(f"✅ Response cache initialized (max_size={self.max_size}, ttl={self.ttl_hours}h)")
    
    def _make_cache_key(self, query: str, file_filter: Optional[str] = None) -> str:
        """Generate cache key from query and filter."""
        normalized_query = query.strip().lower()
        key_input = f"{normalized_query}|{file_filter or 'all'}"
        return hashlib.sha256(key_input.encode()).hexdigest()[:16]
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry has expired."""
        created_at = datetime.fromisoformat(entry.get("created_at", "1970-01-01T00:00:00"))
        expiry = created_at + timedelta(hours=self.ttl_hours)
        return datetime.utcnow() > expiry
    
    def get(self, query: str, file_filter: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response for query.
        
        Args:
            query: User query
            file_filter: Optional file filter
            
        Returns:
            Cached response or None
        """
        cache_key = self._make_cache_key(query, file_filter)
        
        if cache_key not in self._cache:
            self.stats["misses"] += 1
            return None
        
        entry = self._cache[cache_key]
        
        # Check expiration
        if self._is_expired(entry):
            del self._cache[cache_key]
            self.stats["expirations"] += 1
            self.stats["misses"] += 1
            return None
        
        # Move to end for LRU behavior
        self._cache.move_to_end(cache_key)
        self.stats["hits"] += 1
        
        logger.debug(f"Cache hit for query: '{query[:50]}...'")
        
        return entry["response"]
    
    def set(
        self,
        query: str,
        response: Dict[str, Any],
        file_filter: Optional[str] = None,
        query_type: Optional[str] = None,
    ):
        """
        Cache a response.
        
        Args:
            query: User query
            response: RAG response to cache
            file_filter: Optional file filter
            query_type: Optional query type classification
        """
        cache_key = self._make_cache_key(query, file_filter)
        
        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self.stats["evictions"] += 1
        
        self._cache[cache_key] = {
            "query": query,
            "file_filter": file_filter,
            "query_type": query_type,
            "response": response,
            "created_at": datetime.utcnow().isoformat(),
            "hit_count": 0,
        }
        
        logger.debug(f"Cached response for query: '{query[:50]}...'")
        
        # Periodically persist cache
        if len(self._cache) % 10 == 0:
            self._save_cache()
    
    def invalidate(self, query: Optional[str] = None, file_filter: Optional[str] = None):
        """
        Invalidate cache entries.
        
        Args:
            query: Specific query to invalidate (None = clear all)
            file_filter: Specific filter to invalidate
        """
        if query is None:
            # Clear all
            self._cache.clear()
            logger.info("Cache cleared")
        else:
            cache_key = self._make_cache_key(query, file_filter)
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug(f"Invalidated cache for query: '{query[:50]}...'")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": round(hit_rate, 1),
            "evictions": self.stats["evictions"],
            "expirations": self.stats["expirations"],
            "ttl_hours": self.ttl_hours,
        }
    
    def _load_cache(self):
        """Load cache from disk."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                
            # Load entries, filtering expired ones
            for key, entry in data.get("entries", {}).items():
                if not self._is_expired(entry):
                    self._cache[key] = entry
                else:
                    self.stats["expirations"] += 1
            
            logger.info(f"Loaded {len(self._cache)} cached responses from disk")
        except Exception as e:
            logger.warning(f"Error loading cache: {e}")
    
    def _save_cache(self):
        """Persist cache to disk."""
        try:
            data = {
                "version": 1,
                "saved_at": datetime.utcnow().isoformat(),
                "entries": dict(self._cache),
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.debug(f"Persisted {len(self._cache)} cached responses to disk")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def get_frequent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently accessed cached queries."""
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].get("hit_count", 0),
            reverse=True
        )
        
        return [
            {
                "query": entry["query"],
                "hit_count": entry.get("hit_count", 0),
                "created_at": entry["created_at"],
            }
            for _, entry in sorted_entries[:limit]
        ]
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns number removed."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if self._is_expired(entry)
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        self.stats["expirations"] += len(expired_keys)
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            self._save_cache()
        
        return len(expired_keys)
    
    def shutdown(self):
        """Save cache before shutdown."""
        self._save_cache()
        logger.info("Cache saved on shutdown")
