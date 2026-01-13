"""
Query Decomposer for Multi-Hop Reasoning
Breaks down complex queries into simpler sub-queries.
"""

import logging
import re
from typing import List, Dict, Any, Optional
import openai

logger = logging.getLogger(__name__)

class QueryDecomposer:
    """
    Decomposes complex queries into simpler sub-queries for better retrieval.
    """
    
    def __init__(self, llm_client: Optional[openai.OpenAI] = None):
        """
        Initialize query decomposer.
        
        Args:
            llm_client: Optional OpenAI client for LLM-based decomposition
        """
        self.llm_client = llm_client
        self.stats = {
            "total_decompositions": 0,
            "avg_subqueries": 0.0
        }
    
    def decompose(self, query: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        Decompose a complex query into sub-queries.
        
        Args:
            query: Complex user query
            use_llm: Whether to use LLM for decomposition
            
        Returns:
            Decomposition result with sub-queries
        """
        # Try rule-based decomposition first
        sub_queries = self._rule_based_decompose(query)
        
        # If LLM available and complex query, use LLM
        if use_llm and self.llm_client and self._is_complex(query):
            try:
                llm_sub_queries = self._llm_decompose(query)
                if llm_sub_queries:
                    sub_queries = llm_sub_queries
            except Exception as e:
                logger.warning(f"LLM decomposition failed: {e}, using rule-based")
        
        # Update stats
        self._update_stats(len(sub_queries))
        
        result = {
            "original_query": query,
            "sub_queries": sub_queries,
            "num_sub_queries": len(sub_queries),
            "strategy": "llm" if use_llm and self.llm_client else "rule_based"
        }
        
        logger.debug(f"Decomposed query into {len(sub_queries)} sub-queries")
        
        return result
    
    def _rule_based_decompose(self, query: str) -> List[str]:
        """
        Rule-based query decomposition.
        
        Args:
            query: User query
            
        Returns:
            List of sub-queries
        """
        sub_queries = []
        
        # Pattern 1: "Compare X and Y" → ["What is X?", "What is Y?"]
        compare_match = re.search(r'compare\s+(.+?)\s+and\s+(.+)', query, re.IGNORECASE)
        if compare_match:
            x, y = compare_match.groups()
            sub_queries.append(f"What is {x.strip()}?")
            sub_queries.append(f"What is {y.strip()}?")
            return sub_queries
        
        # Pattern 2: "Difference between X and Y"
        diff_match = re.search(r'difference\s+between\s+(.+?)\s+and\s+(.+)', query, re.IGNORECASE)
        if diff_match:
            x, y = diff_match.groups()
            sub_queries.append(f"Describe {x.strip()}")
            sub_queries.append(f"Describe {y.strip()}")
            return sub_queries
        
        # Pattern 3: "X did Y, what happened?" → ["Who is X?", "What did X do?", "What was the result?"]
        cause_effect_match = re.search(r'(.+?)\s+(did|caused|resulted in)\s+(.+?)[\?,]', query, re.IGNORECASE)
        if cause_effect_match:
            subject, action, result = cause_effect_match.groups()
            sub_queries.append(f"Who or what is {subject.strip()}?")
            sub_queries.append(f"What {action} {result.strip()}?")
            sub_queries.append(f"What was the consequence of {subject.strip()} {action} {result.strip()}?")
            return sub_queries
        
        # Pattern 4: Questions with "and" connecting multiple sub-questions
        if " and " in query.lower() and "?" in query:
            parts = re.split(r'\s+and\s+', query, flags=re.IGNORECASE)
            for part in parts:
                cleaned = part.strip().rstrip('?') + '?'
                sub_queries.append(cleaned)
            if len(sub_queries) > 1:
                return sub_queries
        
        # Pattern 5: Multi-part questions with commas
        if query.count(',') >= 2 or query.count('?') >= 2:
            # Split on question marks
            parts = query.split('?')
            for part in parts:
                if part.strip():
                    sub_queries.append(part.strip() + '?')
            if len(sub_queries) > 1:
                return sub_queries
        
        # Default: Return original query
        return [query]
    
    def _llm_decompose(self, query: str) -> List[str]:
        """
        Use LLM to decompose complex queries.
        
        Args:
            query: User query
            
        Returns:
            List of sub-queries
        """
        decomposition_prompt = f"""Break down this complex question into simpler sub-questions that can be answered independently.
Each sub-question should focus on one aspect of the original question.

Original Question: {query}

Provide 2-4 sub-questions, one per line, without numbering or bullet points.
If the question is already simple, just return it as is.

Sub-questions:"""

        try:
            response = self.llm_client.chat.completions.create(
                model="local-model",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that breaks down complex questions."},
                    {"role": "user", "content": decomposition_prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse sub-queries (one per line)
            sub_queries = [
                q.strip().lstrip('1234567890.-•*) ').strip()
                for q in result.split('\n')
                if q.strip() and len(q.strip()) > 10
            ]
            
            # Ensure questions end with ?
            sub_queries = [
                q if q.endswith('?') else q + '?'
                for q in sub_queries
            ]
            
            return sub_queries if sub_queries else [query]
            
        except Exception as e:
            logger.error(f"LLM decomposition error: {e}")
            return [query]
    
    def _is_complex(self, query: str) -> bool:
        """
        Determine if query is complex enough to warrant decomposition.
        
        Args:
            query: User query
            
        Returns:
            True if complex
        """
        complexity_indicators = [
            "compare", "contrast", "difference between",
            "relationship between", "how does", "why did",
            "what happened when", "what was the result",
            "and", "or", "but also", "as well as"
        ]
        
        query_lower = query.lower()
        
        # Check for complexity indicators
        for indicator in complexity_indicators:
            if indicator in query_lower:
                return True
        
        # Check length and structure
        word_count = len(query.split())
        if word_count > 15:
            return True
        
        if query.count(',') >= 2 or query.count('?') >= 2:
            return True
        
        return False
    
    def _update_stats(self, num_subqueries: int):
        """Update statistics."""
        n = self.stats["total_decompositions"]
        old_avg = self.stats["avg_subqueries"]
        
        self.stats["total_decompositions"] += 1
        self.stats["avg_subqueries"] = (old_avg * n + num_subqueries) / (n + 1)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get decomposition statistics."""
        return self.stats.copy()
    
    async def decompose_and_search(self, query: str, search_func, k: int = 5) -> Dict[str, Any]:
        """
        Decompose query and search for each sub-query.
        
        Args:
            query: Original query
            search_func: Async search function
            k: Results per sub-query
            
        Returns:
            Aggregated search results
        """
        # Decompose
        decomposition = self.decompose(query)
        sub_queries = decomposition["sub_queries"]
        
        # Search for each sub-query
        all_results = []
        sub_query_results = {}
        
        for sub_q in sub_queries:
            try:
                results = await search_func(sub_q, k=k)
                all_results.extend(results)
                sub_query_results[sub_q] = len(results)
            except Exception as e:
                logger.error(f"Search error for sub-query '{sub_q}': {e}")
        
        # Deduplicate results (by text content)
        seen_texts = set()
        unique_results = []
        for result in all_results:
            text = result.get("text", "")
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique_results.append(result)
        
        return {
            "original_query": query,
            "sub_queries": sub_queries,
            "results": unique_results[:k * 2],  # Return up to 2x requested results
            "sub_query_counts": sub_query_results,
            "total_results": len(unique_results)
        }
