"""
Conversation Memory for Context-Aware Responses
Maintains conversation history for follow-up questions.
"""

import logging
from typing import List, Dict, Any, Optional
from collections import deque
import time

logger = logging.getLogger(__name__)

class ConversationMemory:
    """
    Manages conversation history for context-aware responses.
    """
    
    def __init__(self, max_history: int = 10, max_age_seconds: int = 3600):
        """
        Initialize conversation memory.
        
        Args:
            max_history: Maximum number of turns to remember
            max_age_seconds: Maximum age of memories in seconds
        """
        self.max_history = max_history
        self.max_age_seconds = max_age_seconds
        self.conversations = {}  # session_id -> conversation history
        
        self.stats = {
            "total_sessions": 0,
            "total_turns": 0,
            "active_sessions": 0
        }
    
    def add_turn(self, session_id: str, query: str, answer: str, 
                 sources: Optional[List[Dict]] = None, metadata: Optional[Dict] = None):
        """
        Add a conversation turn.
        
        Args:
            session_id: Unique session identifier
            query: User query
            answer: System answer
            sources: Optional retrieved sources
            metadata: Optional turn metadata
        """
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                "turns": deque(maxlen=self.max_history),
                "created_at": time.time(),
                "last_updated": time.time()
            }
            self.stats["total_sessions"] += 1
        
        turn = {
            "timestamp": time.time(),
            "query": query,
            "answer": answer,
            "sources": sources or [],
            "metadata": metadata or {}
        }
        
        self.conversations[session_id]["turns"].append(turn)
        self.conversations[session_id]["last_updated"] = time.time()
        self.stats["total_turns"] += 1
        
        # Clean up old sessions
        self._cleanup_old_sessions()
        
        logger.debug(f"Added turn to session {session_id} ({len(self.conversations[session_id]['turns'])} turns)")
    
    def get_history(self, session_id: str, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            last_n: Optional limit to last N turns
            
        Returns:
            List of conversation turns
        """
        if session_id not in self.conversations:
            return []
        
        turns = list(self.conversations[session_id]["turns"])
        
        if last_n:
            turns = turns[-last_n:]
        
        return turns
    
    def get_context_for_query(self, session_id: str, current_query: str, 
                             last_n: int = 3) -> Dict[str, Any]:
        """
        Get relevant context for current query from history.
        
        Args:
            session_id: Session identifier
            current_query: Current user query
            last_n: Number of recent turns to include
            
        Returns:
            Context dictionary with previous queries and answers
        """
        history = self.get_history(session_id, last_n)
        
        if not history:
            return {
                "has_history": False,
                "previous_queries": [],
                "previous_answers": [],
                "previous_topics": []
            }
        
        # Extract previous queries and answers
        previous_queries = [turn["query"] for turn in history]
        previous_answers = [turn["answer"] for turn in history]
        
        # Extract topics (simple keyword extraction)
        previous_topics = self._extract_topics(previous_queries + previous_answers)
        
        # Detect if current query is a follow-up
        is_followup = self._is_followup_query(current_query, previous_queries)
        
        return {
            "has_history": True,
            "previous_queries": previous_queries,
            "previous_answers": previous_answers,
            "previous_topics": previous_topics,
            "is_followup": is_followup,
            "history_length": len(history)
        }
    
    def build_conversation_prompt(self, session_id: str, current_query: str, 
                                 context: str, last_n: int = 2) -> str:
        """
        Build a prompt that includes conversation history.
        
        Args:
            session_id: Session identifier
            current_query: Current query
            context: Retrieved context
            last_n: Number of previous turns to include
            
        Returns:
            Enhanced prompt with conversation history
        """
        history = self.get_history(session_id, last_n)
        
        if not history:
            # No history, return basic prompt
            return f"""Context:
{context}

Question: {current_query}

Answer:"""
        
        # Build prompt with history
        history_str = ""
        for i, turn in enumerate(history, 1):
            history_str += f"\nPrevious Question {i}: {turn['query']}"
            history_str += f"\nPrevious Answer {i}: {turn['answer']}\n"
        
        prompt = f"""You are having a conversation with a user. Here is the conversation history:

{history_str}

Now the user asks a follow-up question. Use the conversation history and the provided context to answer.

Context:
{context}

Current Question: {current_query}

Answer (considering the conversation history):"""
        
        return prompt
    
    def _is_followup_query(self, current_query: str, previous_queries: List[str]) -> bool:
        """
        Detect if current query is a follow-up to previous queries.
        
        Args:
            current_query: Current query
            previous_queries: List of previous queries
            
        Returns:
            True if likely a follow-up
        """
        if not previous_queries:
            return False
        
        query_lower = current_query.lower()
        
        # Follow-up indicators
        followup_indicators = [
            "what about", "how about", "tell me more",
            "also", "additionally", "furthermore",
            "what happened", "and then", "after that",
            "why", "how", "when", "where",
            "he", "she", "they", "it", "that", "this", "those"
        ]
        
        # Short queries with pronouns are likely follow-ups
        if len(current_query.split()) <= 6:
            for indicator in followup_indicators:
                if query_lower.startswith(indicator):
                    return True
        
        # Check for pronoun references
        pronouns = ["he", "she", "they", "it", "that", "this", "those", "them", "him", "her"]
        for pronoun in pronouns:
            if f" {pronoun} " in f" {query_lower} ":
                return True
        
        return False
    
    def _extract_topics(self, texts: List[str]) -> List[str]:
        """
        Extract key topics from text (simple keyword extraction).
        
        Args:
            texts: List of texts
            
        Returns:
            List of extracted topics
        """
        # Simple approach: extract capitalized words (proper nouns)
        topics = set()
        
        for text in texts:
            words = text.split()
            for word in words:
                # Capitalize words that aren't at start of sentence
                if word and word[0].isupper() and len(word) > 2:
                    # Clean punctuation
                    clean_word = word.strip('.,!?;:')
                    if clean_word and clean_word not in ["The", "A", "An", "I", "This", "That"]:
                        topics.add(clean_word)
        
        return sorted(list(topics))[:10]  # Top 10 topics
    
    def _cleanup_old_sessions(self):
        """Remove sessions older than max_age_seconds."""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, data in self.conversations.items():
            if current_time - data["last_updated"] > self.max_age_seconds:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.conversations[session_id]
            logger.debug(f"Cleaned up expired session: {session_id}")
        
        self.stats["active_sessions"] = len(self.conversations)
    
    def clear_session(self, session_id: str):
        """Clear a specific session."""
        if session_id in self.conversations:
            del self.conversations[session_id]
            logger.info(f"Cleared session: {session_id}")
    
    def clear_all(self):
        """Clear all conversations."""
        self.conversations = {}
        logger.info("Cleared all conversation memory")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get conversation memory statistics."""
        self.stats["active_sessions"] = len(self.conversations)
        
        if self.conversations:
            avg_turns = sum(len(conv["turns"]) for conv in self.conversations.values()) / len(self.conversations)
        else:
            avg_turns = 0
        
        return {
            **self.stats,
            "avg_turns_per_session": round(avg_turns, 2)
        }
