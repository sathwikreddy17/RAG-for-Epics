"""
Feedback Collector for RAG System
Collects user feedback on answers to track retrieval quality.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """
    Collects and stores user feedback on RAG answers.
    Feedback can be used for:
    - Monitoring retrieval quality over time
    - Identifying queries that need improvement
    - Training data for future improvements
    """
    
    def __init__(self, feedback_path: Optional[str] = None):
        """
        Initialize feedback collector.
        
        Args:
            feedback_path: Path to store feedback data. Defaults to ./data/feedback/
        """
        self.feedback_path = Path(feedback_path or os.getenv("FEEDBACK_PATH", "./data/feedback"))
        self.feedback_path.mkdir(parents=True, exist_ok=True)
        
        self.feedback_file = self.feedback_path / "feedback.jsonl"
        self.stats_file = self.feedback_path / "stats.json"
        
        # In-memory stats
        self.stats = self._load_stats()
        
        logger.info(f"✅ Feedback collector initialized at {self.feedback_path}")
    
    def _load_stats(self) -> Dict[str, Any]:
        """Load feedback statistics from file."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading stats: {e}")
        
        return {
            "total_feedback": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "avg_rating": 0.0,
            "by_query_type": {},
            "low_rated_queries": [],  # Queries with rating <= 2
        }
    
    def _save_stats(self):
        """Save feedback statistics to file."""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving stats: {e}")
    
    def record_feedback(
        self,
        query: str,
        answer: str,
        rating: int,  # 1-5 scale
        sources: Optional[List[Dict[str, Any]]] = None,
        comment: Optional[str] = None,
        query_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record user feedback on an answer.
        
        Args:
            query: The original query
            answer: The generated answer
            rating: User rating 1-5 (1=very bad, 5=excellent)
            sources: Optional list of sources used
            comment: Optional user comment
            query_type: Optional query type classification
            metadata: Optional additional metadata
            
        Returns:
            Feedback record with ID
        """
        # Validate rating
        rating = max(1, min(5, int(rating)))
        
        # Create feedback record
        feedback_record = {
            "id": f"fb_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "answer": answer[:1000] if answer else None,  # Truncate long answers
            "rating": rating,
            "rating_label": self._rating_to_label(rating),
            "sources": [
                {"file_name": s.get("file_name"), "page": s.get("page")}
                for s in (sources or [])[:5]  # Keep top 5 sources
            ],
            "comment": comment[:500] if comment else None,  # Truncate long comments
            "query_type": query_type,
            "metadata": metadata,
        }
        
        # Append to feedback file (JSONL format)
        try:
            with open(self.feedback_file, 'a') as f:
                f.write(json.dumps(feedback_record) + '\n')
        except Exception as e:
            logger.error(f"Error writing feedback: {e}")
            return {"error": str(e)}
        
        # Update statistics
        self._update_stats(feedback_record)
        
        logger.info(f"Recorded feedback: rating={rating} for query='{query[:50]}...'")
        
        return feedback_record
    
    def _rating_to_label(self, rating: int) -> str:
        """Convert numeric rating to label."""
        labels = {
            1: "very_bad",
            2: "bad",
            3: "neutral",
            4: "good",
            5: "excellent"
        }
        return labels.get(rating, "unknown")
    
    def _update_stats(self, feedback: Dict[str, Any]):
        """Update feedback statistics."""
        rating = feedback["rating"]
        query_type = feedback.get("query_type", "unknown")
        
        # Update counts
        self.stats["total_feedback"] += 1
        
        if rating >= 4:
            self.stats["positive_count"] += 1
        elif rating <= 2:
            self.stats["negative_count"] += 1
            # Track low-rated queries for review
            self.stats["low_rated_queries"].append({
                "query": feedback["query"][:100],
                "rating": rating,
                "timestamp": feedback["timestamp"],
            })
            # Keep only last 50 low-rated queries
            self.stats["low_rated_queries"] = self.stats["low_rated_queries"][-50:]
        else:
            self.stats["neutral_count"] += 1
        
        # Update average rating
        total = self.stats["total_feedback"]
        old_avg = self.stats["avg_rating"]
        self.stats["avg_rating"] = round(((old_avg * (total - 1)) + rating) / total, 2)
        
        # Update by query type
        if query_type not in self.stats["by_query_type"]:
            self.stats["by_query_type"][query_type] = {
                "count": 0,
                "total_rating": 0,
                "avg_rating": 0.0,
            }
        
        type_stats = self.stats["by_query_type"][query_type]
        type_stats["count"] += 1
        type_stats["total_rating"] += rating
        type_stats["avg_rating"] = round(type_stats["total_rating"] / type_stats["count"], 2)
        
        # Save updated stats
        self._save_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        return {
            "total_feedback": self.stats["total_feedback"],
            "positive_count": self.stats["positive_count"],
            "negative_count": self.stats["negative_count"],
            "neutral_count": self.stats["neutral_count"],
            "avg_rating": self.stats["avg_rating"],
            "satisfaction_rate": round(
                (self.stats["positive_count"] / max(1, self.stats["total_feedback"])) * 100, 1
            ),
            "by_query_type": self.stats["by_query_type"],
            "low_rated_queries_count": len(self.stats["low_rated_queries"]),
        }
    
    def get_low_rated_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get queries with low ratings for review."""
        return self.stats["low_rated_queries"][-limit:]
    
    def get_recent_feedback(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent feedback entries."""
        if not self.feedback_file.exists():
            return []
        
        feedback_list = []
        try:
            with open(self.feedback_file, 'r') as f:
                for line in f:
                    if line.strip():
                        feedback_list.append(json.loads(line))
        except Exception as e:
            logger.error(f"Error reading feedback: {e}")
            return []
        
        # Return most recent entries
        return feedback_list[-limit:]
    
    def export_training_data(self, min_rating: int = 4) -> List[Dict[str, Any]]:
        """
        Export high-quality feedback as potential training data.
        
        Args:
            min_rating: Minimum rating to include (default: 4 = good/excellent)
            
        Returns:
            List of high-quality query-answer pairs
        """
        if not self.feedback_file.exists():
            return []
        
        training_data = []
        try:
            with open(self.feedback_file, 'r') as f:
                for line in f:
                    if line.strip():
                        feedback = json.loads(line)
                        if feedback.get("rating", 0) >= min_rating:
                            training_data.append({
                                "query": feedback["query"],
                                "answer": feedback["answer"],
                                "rating": feedback["rating"],
                                "sources": feedback.get("sources", []),
                            })
        except Exception as e:
            logger.error(f"Error exporting training data: {e}")
        
        return training_data
