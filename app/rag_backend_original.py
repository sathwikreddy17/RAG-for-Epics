"""
RAG Backend for Local RAG system.
Handles document retrieval and LLM interaction.
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import time

import lancedb
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class RAGBackend:
    """
    Backend for RAG operations including embedding, retrieval, and LLM interaction.
    """
    
    def __init__(self):
        """Initialize the RAG backend."""
        # Configuration
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
        self.reranker_model_name = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-large")
        self.use_reranker = os.getenv("USE_RERANKER", "true").lower() == "true"
        self.lancedb_path = os.getenv("LANCEDB_PATH", "./data/index")
        self.table_name = os.getenv("TABLE_NAME", "docs")
        self.top_k_initial = int(os.getenv("TOP_K_INITIAL", "20"))
        self.top_k_final = int(os.getenv("TOP_K_FINAL", "5"))
        
        # LM Studio configuration
        self.lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        self.lm_studio_api_key = os.getenv("LM_STUDIO_API_KEY", "not-needed-for-local")
        
        # Initialize models and database
        self._initialize_models()
        self._initialize_database()
        
    def _initialize_models(self):
        """Initialize embedding and reranking models."""
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        if self.use_reranker:
            logger.info(f"Loading reranker model: {self.reranker_model_name}")
            self.reranker = CrossEncoder(self.reranker_model_name)
        else:
            self.reranker = None
            
        # Initialize OpenAI client for LM Studio
        self.llm_client = openai.OpenAI(
            base_url=self.lm_studio_url,
            api_key=self.lm_studio_api_key
        )
        
        logger.info("Models initialized successfully")
        
    def _initialize_database(self):
        """Initialize LanceDB connection."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.lancedb_path, exist_ok=True)
            
            # Connect to LanceDB
            self.db = lancedb.connect(self.lancedb_path)
            
            # Check if table exists
            table_names = self.db.table_names()
            if self.table_name not in table_names:
                logger.warning(f"Table '{self.table_name}' not found. Please run ingest.py first.")
                self.table = None
            else:
                self.table = self.db.open_table(self.table_name)
                logger.info(f"Connected to LanceDB table: {self.table_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.table = None
            
    async def search(self, query: str, k: Optional[int] = None, file_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant documents.
        
        Args:
            query: Search query
            k: Number of results to return (defaults to top_k_final)
            file_filter: Optional filename to filter results by
            
        Returns:
            List of relevant document chunks with metadata
        """
        if not self.table:
            raise Exception("Vector store not initialized. Please run ingest.py first.")
            
        k = k or self.top_k_final
        
        # Embed the query
        query_embedding = self.embedding_model.encode(query)
        
        # Initial vector search with optional file filter
        search_query = self.table.search(query_embedding).limit(self.top_k_initial)
        
        # Apply file filter if specified
        if file_filter and file_filter != "all":
            search_query = search_query.where(f"file_name LIKE '%{file_filter}%'")
        
        initial_results = search_query.to_list()
        
        if not initial_results:
            return []
            
        # Optional reranking
        if self.use_reranker and self.reranker and len(initial_results) > k:
            # Prepare query-document pairs for reranking
            query_doc_pairs = [(query, doc["text"]) for doc in initial_results]
            
            # Get reranking scores
            rerank_scores = self.reranker.predict(query_doc_pairs)
            
            # Sort by reranking scores and take top k
            scored_results = list(zip(initial_results, rerank_scores))
            scored_results.sort(key=lambda x: x[1], reverse=True)
            final_results = [doc for doc, score in scored_results[:k]]
        else:
            final_results = initial_results[:k]
            
        return final_results
        
    async def answer(self, query: str, include_sources: bool = True, file_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate an answer to a query using retrieved documents.
        
        Args:
            query: User question
            include_sources: Whether to include source documents in response
            file_filter: Optional filename to filter results by
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Track performance timings
        timings = {}
        start_time = time.time()
        
        # Retrieve relevant documents
        search_start = time.time()
        retrieved_docs = await self.search(query, file_filter=file_filter)
        timings['search'] = round(time.time() - search_start, 3)
        
        if not retrieved_docs:
            return {
                "answer": "I couldn't find any relevant information in the knowledge base to answer your question.",
                "sources": [],
                "metadata": {"num_sources": 0, "query": query}
            }
            
        # Prepare context from retrieved documents
        context_parts = []
        sources = []
        
        for i, doc in enumerate(retrieved_docs, 1):
            context_parts.append(f"[Source {i}]\n{doc['text']}")
            
            if include_sources:
                # Calculate relevance score (convert distance to similarity percentage)
                # LanceDB returns L2 distance, smaller is better
                distance = doc.get("_distance", 1.0)
                # Convert to similarity score (0-1 range, higher is better)
                similarity_score = max(0, 1 - (distance / 2))  # Normalize distance
                
                sources.append({
                    "index": i,
                    "file_name": doc.get("file_name", "Unknown"),
                    "page": doc.get("page_number", "N/A"),
                    "chunk_index": doc.get("chunk_index"),
                    "text": doc["text"],
                    "score": similarity_score
                })
                
        context = "\n\n".join(context_parts)
        
        # Prepare prompt for LLM
        prompt = self._create_prompt(query, context)
        
        # Get answer from LLM
        llm_start = time.time()
        try:
            response = self.llm_client.chat.completions.create(
                model="local-model",  # LM Studio doesn't require specific model name
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context. Always cite your sources and be precise."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            timings['llm'] = round(time.time() - llm_start, 3)
            
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            answer = f"Error generating answer: {str(e)}. Please check if LM Studio is running and accessible."
            timings['llm'] = round(time.time() - llm_start, 3)
        
        # Total time
        timings['total'] = round(time.time() - start_time, 3)
            
        return {
            "answer": answer,
            "sources": sources if include_sources else [],
            "metadata": {
                "num_sources": len(retrieved_docs),
                "query": query,
                "context_length": len(context),
                "reranker_used": self.use_reranker and self.reranker is not None
            },
            "timings": timings
        }
        
    def _create_prompt(self, query: str, context: str) -> str:
        """
        Create a prompt for the LLM.
        
        Args:
            query: User question
            context: Retrieved context
            
        Returns:
            Formatted prompt
        """
        return f"""Based on the provided context, please answer the following question. Be precise and cite the sources when possible.

Context:
{context}

Question: {query}

Answer:"""

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            "embedding_model": self.embedding_model_name,
            "reranker_enabled": self.use_reranker,
            "database_connected": self.table is not None,
            "lm_studio_url": self.lm_studio_url
        }
        
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        if not self.table:
            return {"error": "Database not connected"}
            
        try:
            # Get table statistics
            count = self.table.count_rows()
            schema = self.table.schema
            
            return {
                "document_count": count,
                "table_name": self.table_name,
                "schema": str(schema),
                "embedding_dimension": len(self.embedding_model.encode("test")),
                "models": {
                    "embedding": self.embedding_model_name,
                    "reranker": self.reranker_model_name if self.use_reranker else None
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_available_documents(self) -> List[str]:
        """Get list of unique document names in the database."""
        if not self.table:
            return []
        
        try:
            # Query unique file names
            results = self.table.to_pandas()
            unique_files = results['file_name'].unique().tolist()
            return sorted(unique_files)
        except Exception as e:
            logger.error(f"Error getting document list: {e}")
            return []
    
    def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about each document."""
        if not self.table:
            return {}
        
        try:
            df = self.table.to_pandas()
            stats = {}
            
            for file_name in df['file_name'].unique():
                file_df = df[df['file_name'] == file_name]
                stats[file_name] = {
                    "chunk_count": len(file_df),
                    "pages": file_df['page_number'].nunique() if 'page_number' in file_df.columns else 0,
                    "avg_chunk_length": int(file_df['text'].str.len().mean()) if 'text' in file_df.columns else 0
                }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting document stats: {e}")
            return {}
