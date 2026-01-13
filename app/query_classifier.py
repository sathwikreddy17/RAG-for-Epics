"""
Query Classifier for Smart Routing
Classifies user queries into different types for optimal processing.
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Types of queries the system can handle."""
    FACTUAL = "factual"  # "Who is X?", "What is Y?"
    COMPARATIVE = "comparative"  # "Compare A and B"
    ANALYTICAL = "analytical"  # "Why did X happen?"
    SUMMARIZATION = "summarization"  # "Summarize X"
    MULTI_HOP = "multi_hop"  # "X did Y, what was the result?"
    CONVERSATIONAL = "conversational"  # "Tell me more", "What about..."
    SIMPLE = "simple"  # Simple lookups
    COMPLEX = "complex"  # Complex reasoning needed

class QueryClassifier:
    """
    Classifies queries to determine optimal processing strategy.
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize query classifier.
        
        Args:
            llm_client: Optional LLM client for advanced classification
        """
        self.llm_client = llm_client
        
        # Keyword patterns for rule-based classification
        self.patterns = {
            QueryType.FACTUAL: [
                "who is", "who was", "who were", "what is", "what was",
                "what are", "when did", "when was", "where is", "where was"
            ],
            QueryType.COMPARATIVE: [
                "compare", "difference between", "similarities between",
                "versus", "vs", "contrast", "which is better"
            ],
            QueryType.ANALYTICAL: [
                "why did", "why is", "why was", "how did", "explain why",
                "what caused", "reason for", "because"
            ],
            QueryType.SUMMARIZATION: [
                "summarize", "summary of", "overview of", "main points",
                "key takeaways", "brief", "in short"
            ],
            QueryType.MULTI_HOP: [
                "and then", "after that", "what happened next",
                "as a result", "consequently", "therefore"
            ],
            QueryType.CONVERSATIONAL: [
                "tell me more", "what about", "and what", "also",
                "additionally", "furthermore"
            ]
        }
    
    def classify(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classify a query.
        
        Args:
            query: User query
            context: Optional conversation context
            
        Returns:
            Classification result with type, confidence, and metadata
        """
        query_lower = query.lower().strip()
        
        # Rule-based classification
        classification = self._rule_based_classify(query_lower)
        
        # Check if conversational (depends on context)
        if context and context.get("previous_queries"):
            if self._is_conversational(query_lower):
                classification["type"] = QueryType.CONVERSATIONAL
                classification["confidence"] = 0.9
        
        # Determine complexity
        classification["complexity"] = self._assess_complexity(query_lower)
        
        logger.debug(f"Query classified as: {classification['type'].value} "
                    f"(confidence: {classification['confidence']:.2f})")
        
        return classification
    
    def _rule_based_classify(self, query: str) -> Dict[str, Any]:
        """
        Rule-based classification using keyword patterns.
        
        Args:
            query: Lowercase query string
            
        Returns:
            Classification dictionary
        """
        scores = {}
        
        # Score each query type
        for query_type, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in query:
                    score += 1
            scores[query_type] = score
        
        # Get type with highest score
        if max(scores.values()) > 0:
            best_type = max(scores, key=scores.get)
            confidence = min(scores[best_type] * 0.3, 0.95)
        else:
            # Default to factual for simple queries
            best_type = QueryType.FACTUAL
            confidence = 0.5
        
        return {
            "type": best_type,
            "confidence": confidence,
            "all_scores": scores
        }
    
    def _is_conversational(self, query: str) -> bool:
        """Check if query is conversational (follow-up)."""
        conversational_indicators = [
            "what about", "tell me more", "also", "and", "additionally",
            "furthermore", "that", "it", "they", "them"
        ]
        
        # Short queries starting with pronouns or connectors are likely conversational
        if len(query.split()) <= 5:
            for indicator in conversational_indicators:
                if query.startswith(indicator):
                    return True
        
        return False
    
    def _assess_complexity(self, query: str) -> str:
        """
        Assess query complexity.
        
        Args:
            query: Lowercase query string
            
        Returns:
            "simple" or "complex"
        """
        complexity_indicators = {
            "complex": [
                "compare", "contrast", "analyze", "evaluate",
                "why", "how", "explain", "relationship between",
                "impact of", "consequence", "multiple", "several",
                "and", "or", "both"
            ],
            "simple": [
                "who", "what", "when", "where", "which",
                "list", "name", "is", "was", "are"
            ]
        }
        
        complex_score = sum(1 for word in complexity_indicators["complex"] if word in query)
        simple_score = sum(1 for word in complexity_indicators["simple"] if word in query)
        
        # Multiple clauses or long queries are complex
        word_count = len(query.split())
        if word_count > 15 or query.count(",") > 1:
            return "complex"
        
        if complex_score > simple_score:
            return "complex"
        else:
            return "simple"
    
    async def classify_with_llm(self, query: str) -> Dict[str, Any]:
        """
        Use LLM for more accurate classification.
        
        Args:
            query: User query
            
        Returns:
            Classification result
        """
        if not self.llm_client:
            return self.classify(query)
        
        # Fallback to rule-based for now
        # LLM classification can be added later
        return self.classify(query)
    
    def get_processing_strategy(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine processing strategy based on classification.
        
        Args:
            classification: Query classification
            
        Returns:
            Processing strategy recommendations
        """
        query_type = classification["type"]
        complexity = classification["complexity"]
        
        strategy = {
            "use_hybrid_search": True,
            "use_reranker": True,
            "top_k": 5,
            "decompose_query": False,
            "use_conversation_context": False,
            "response_mode": "concise"
        }
        
        # Adjust based on query type
        if query_type == QueryType.FACTUAL:
            strategy["top_k"] = 5  # Increased from 3 to get more context for character queries
            strategy["response_mode"] = "direct"
            
        elif query_type == QueryType.COMPARATIVE:
            strategy["top_k"] = 10
            strategy["decompose_query"] = True
            strategy["response_mode"] = "detailed"
            
        elif query_type == QueryType.ANALYTICAL:
            strategy["top_k"] = 8
            strategy["decompose_query"] = True
            strategy["response_mode"] = "analytical"
            
        elif query_type == QueryType.SUMMARIZATION:
            strategy["top_k"] = 15
            strategy["response_mode"] = "summary"
            
        elif query_type == QueryType.MULTI_HOP:
            strategy["top_k"] = 10
            strategy["decompose_query"] = True
            strategy["response_mode"] = "narrative"
            
        elif query_type == QueryType.CONVERSATIONAL:
            strategy["use_conversation_context"] = True
            strategy["top_k"] = 5
        
        # Adjust based on complexity
        if complexity == "complex":
            strategy["top_k"] = min(strategy["top_k"] * 2, 20)
            strategy["decompose_query"] = True
            strategy["use_reranker"] = True
        
        return strategy
