"""
Query Router for Smart RAG Processing
Routes queries to optimal retrieval and response strategies.
"""

import logging
from typing import Dict, Any, List, Optional
from .query_classifier import QueryClassifier, QueryType

logger = logging.getLogger(__name__)

class QueryRouter:
    """
    Routes queries to optimal processing strategies based on classification.
    """
    
    def __init__(self, classifier: Optional[QueryClassifier] = None):
        """
        Initialize query router.
        
        Args:
            classifier: QueryClassifier instance, creates new if None
        """
        self.classifier = classifier or QueryClassifier()
        self.routing_stats = {
            "total_queries": 0,
            "by_type": {},
            "by_complexity": {"simple": 0, "complex": 0}
        }
    
    def route(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Route a query to optimal processing strategy.
        
        Args:
            query: User query
            context: Optional conversation context
            
        Returns:
            Routing decision with strategy and metadata
        """
        # Classify query
        classification = self.classifier.classify(query, context)
        
        # Get processing strategy
        strategy = self.classifier.get_processing_strategy(classification)
        
        # Update statistics
        self._update_stats(classification)
        
        routing_decision = {
            "query": query,
            "classification": classification,
            "strategy": strategy,
            "route": self._determine_route(classification)
        }
        
        logger.info(f"Routed query to: {routing_decision['route']} "
                   f"(type: {classification['type'].value})")
        
        return routing_decision
    
    def _determine_route(self, classification: Dict[str, Any]) -> str:
        """
        Determine which processing route to use.
        
        Args:
            classification: Query classification
            
        Returns:
            Route name
        """
        query_type = classification["type"]
        complexity = classification["complexity"]
        
        # Route mapping
        if query_type == QueryType.FACTUAL and complexity == "simple":
            return "fast_factual"
        
        elif query_type == QueryType.FACTUAL and complexity == "complex":
            return "detailed_factual"
        
        elif query_type == QueryType.COMPARATIVE:
            return "comparative_analysis"
        
        elif query_type == QueryType.ANALYTICAL:
            return "deep_analysis"
        
        elif query_type == QueryType.SUMMARIZATION:
            return "summarization"
        
        elif query_type == QueryType.MULTI_HOP:
            return "multi_hop_reasoning"
        
        elif query_type == QueryType.CONVERSATIONAL:
            return "conversational"
        
        else:
            return "standard"
    
    def _update_stats(self, classification: Dict[str, Any]):
        """Update routing statistics."""
        self.routing_stats["total_queries"] += 1
        
        query_type = classification["type"].value
        self.routing_stats["by_type"][query_type] = \
            self.routing_stats["by_type"].get(query_type, 0) + 1
        
        complexity = classification["complexity"]
        self.routing_stats["by_complexity"][complexity] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        return self.routing_stats.copy()
    
    def optimize_retrieval_params(self, strategy: Dict[str, Any], 
                                  available_docs: int) -> Dict[str, Any]:
        """
        Optimize retrieval parameters based on strategy and available documents.
        
        Args:
            strategy: Processing strategy from classification
            available_docs: Number of documents in index
            
        Returns:
            Optimized retrieval parameters
        """
        params = {
            "top_k": strategy["top_k"],
            "use_hybrid": strategy["use_hybrid_search"],
            "use_reranker": strategy["use_reranker"],
            "rerank_top_k": max(strategy["top_k"] * 2, 10)
        }
        
        # Adjust based on corpus size
        if available_docs < 100:
            # Small corpus - retrieve more
            params["top_k"] = min(params["top_k"] * 2, available_docs)
        
        elif available_docs > 10000:
            # Large corpus - be more selective
            params["rerank_top_k"] = min(params["rerank_top_k"], 50)
        
        return params
    
    def should_decompose(self, classification: Dict[str, Any]) -> bool:
        """
        Determine if query should be decomposed into sub-queries.
        
        Args:
            classification: Query classification
            
        Returns:
            True if decomposition recommended
        """
        strategy = self.classifier.get_processing_strategy(classification)
        return strategy["decompose_query"]
    
    def get_response_instructions(self, classification: Dict[str, Any]) -> str:
        """
        Get LLM instructions based on query classification.
        
        Args:
            classification: Query classification
            
        Returns:
            Instructions for LLM response generation
        """
        query_type = classification["type"]
        strategy = self.classifier.get_processing_strategy(classification)
        response_mode = strategy["response_mode"]
        
        instructions = {
            "direct": "Provide a direct, concise answer based on the context. Focus on facts.",
            
            "concise": "Answer the question concisely using the provided context.",
            
            "detailed": "Provide a detailed, comprehensive answer. Compare and contrast relevant points from the context.",
            
            "analytical": "Analyze the question deeply. Explain causes, effects, and reasoning. Use evidence from the context.",
            
            "summary": "Summarize the key points from the context. Be comprehensive but concise.",
            
            "narrative": "Provide a narrative answer that connects multiple pieces of information. Show the logical flow."
        }
        
        base_instruction = instructions.get(response_mode, instructions["concise"])
        
        # Add type-specific guidance
        if query_type == QueryType.COMPARATIVE:
            base_instruction += "\n\nStructure your answer to clearly show similarities and differences."
        
        elif query_type == QueryType.MULTI_HOP:
            base_instruction += "\n\nShow the logical connections between different pieces of information."
        
        elif query_type == QueryType.CONVERSATIONAL:
            base_instruction += "\n\nBe conversational and refer to previous context if relevant."
        
        return base_instruction
