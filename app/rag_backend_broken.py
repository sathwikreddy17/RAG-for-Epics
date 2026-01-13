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
        
        # Required model (strict checking)
        self.required_model = os.getenv("REQUIRED_MODEL_NAME", "qwen2.5-coder-32b").lower()
        self.strict_model_check = os.getenv("STRICT_MODEL_CHECK", "true").lower() == "true"
        
        # Initialize models and database
        self._initialize_models()
        self._initialize_database()
        self._verify_llm_model()
        
    def _initialize_models(self):
        """Initialize embedding and reranking models."""
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        try:
            # Try MPS (Metal) for Mac, fallback to CPU
            self.embedding_model = SentenceTransformer(self.embedding_model_name, device='mps')
            logger.info("✅ Embedding model loaded on Metal GPU")
        except:
            self.embedding_model = SentenceTransformer(self.embedding_model_name, device='cpu')
            logger.info("✅ Embedding model loaded on CPU")
        
        if self.use_reranker:
            try:
                logger.info(f"Loading reranker model: {self.reranker_model_name}")
                self.reranker = CrossEncoder(self.reranker_model_name)
                logger.info("✅ Reranker model loaded")
            except Exception as e:
                logger.warning(f"Could not load reranker: {e}. Continuing without reranker.")
                self.reranker = None
        else:
            self.reranker = None
            
        # Initialize OpenAI client for LM Studio with timeout
        self.llm_client = openai.OpenAI(
            base_url=self.lm_studio_url,
            api_key=self.lm_studio_api_key,
            timeout=60.0  # 60 second timeout
        )
        
        logger.info("Models initialized successfully")
        
    def _initialize_database(self):
        """Initialize LanceDB connection."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.lancedb_path, exist_ok=True)
            
            # Connect to LanceDB
            self.db = lancedb.connect(self.lancedb_path)
            
            # Check if table exists (try both methods for compatibility)
            try:
                table_names = self.db.table_names()
            except:
                # Fallback to list_tables() for newer versions
                table_names = [t.name for t in self.db.list_tables()]
            
            if self.table_name not in table_names:
                logger.warning(f"Table '{self.table_name}' not found. Please run phase1_extract.py and phase2_embed.py first.")
                self.table = None
            else:
                self.table = self.db.open_table(self.table_name)
                count = self.table.count_rows()
                logger.info(f"Connected to LanceDB table: {self.table_name} ({count:,} chunks)")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.table = None
            
    def _verify_llm_model(self):
        """Verify that the required LLM model is loaded in LM Studio."""
        if not self.strict_model_check:
            logger.info("Strict model checking disabled")
            return
        
        try:
            import requests
            response = requests.get(f"{self.lm_studio_url.replace('/v1', '')}/v1/models", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                models = data.get('data', [])
                
                if not models:
                    logger.error("❌ No models loaded in LM Studio")
                    self.model_verified = False
                    return
                
                # Check if required model is loaded
                loaded_model = models[0].get('id', '').lower()
                
                # Flexible matching for model name (handles variations)
                if self.required_model in loaded_model or loaded_model in self.required_model:
                    logger.info(f"✅ Required model verified: {loaded_model}")
                    self.model_verified = True
                    self.loaded_model_name = loaded_model
                else:
                    logger.error(f"❌ Wrong model loaded!")
                    logger.error(f"   Required: {self.required_model}")
                    logger.error(f"   Loaded: {loaded_model}")
                    self.model_verified = False
                    self.loaded_model_name = loaded_model
            else:
                logger.error(f"❌ Cannot connect to LM Studio (status {response.status_code})")
                self.model_verified = False
                
        except Exception as e:
            logger.error(f"❌ Cannot verify LM Studio model: {e}")
            self.model_verified = False
    
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
            raise Exception("Vector store not initialized. Please run phase1_extract.py and phase2_embed.py first.")
            
        k = k or self.top_k_final
        
        # Embed the query
        query_embedding = self.embedding_model.encode(query, normalize_embeddings=True)
        
        # Initial vector search
        search_query = self.table.search(query_embedding).limit(self.top_k_initial)
        
        # Apply file filter if specified
        if file_filter and file_filter != "all":
            search_query = search_query.where(f"file_name LIKE '%{file_filter}%'")
        
        initial_results = search_query.to_list()
        
        if not initial_results:
            return []
            
        # Optional reranking
        if self.use_reranker and self.reranker and len(initial_results) > k:
            try:
                # Prepare query-document pairs for reranking
                query_doc_pairs = [(query, doc["text"]) for doc in initial_results]
                
                # Get reranking scores
                rerank_scores = self.reranker.predict(query_doc_pairs)
                
                # Sort by reranking scores and take top k
                scored_results = list(zip(initial_results, rerank_scores))
                scored_results.sort(key=lambda x: x[1], reverse=True)
                final_results = [doc for doc, score in scored_results[:k]]
            except Exception as e:
                logger.warning(f"Reranking failed: {e}. Using vector search results.")
                final_results = initial_results[:k]
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
        # Check if correct model is loaded (strict mode)
        if self.strict_model_check and not getattr(self, 'model_verified', False):
            loaded = getattr(self, 'loaded_model_name', 'unknown')
            raise Exception(
                f"Required model not loaded in LM Studio!\n\n"
                f"Expected: {self.required_model}\n"
                f"Loaded: {loaded}\n\n"
                f"Please load the Qwen 2.5 Coder 32B model in LM Studio."
            )
        
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
                "metadata": {
                    "num_sources": 0, 
                    "query": query,
                    "timings": timings
                }
            }
            
        # Prepare context from retrieved documents with token limit
        context_parts = []
        sources = []
        max_context_tokens = 3000  # Reduced for faster LLM processing
        current_tokens = 0
        
        for i, doc in enumerate(retrieved_docs, 1):
            doc_text = doc['text']
            # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
            doc_tokens = len(doc_text) // 4
            
            # Check if adding this chunk would exceed limit
            if current_tokens + doc_tokens > max_context_tokens and i > 3:
                # Always include at least 3 sources, then stop if exceeding
                logger.info(f"Context limit reached at {i-1} sources ({current_tokens} tokens)")
                break
            
            context_parts.append(f"[Source {i}]\n{doc_text}")
            current_tokens += doc_tokens
            
            if include_sources:
                # Calculate relevance score (convert distance to similarity percentage)
                # LanceDB returns L2 distance, smaller is better
                distance = doc.get("_distance", 1.0)
                # Convert to similarity score (0-100 range, higher is better)
                similarity_score = max(0, 100 * (1 - (distance / 2)))
                
                sources.append({
                    "index": i,
                    "file_name": doc.get("file_name", "Unknown"),
                    "page": doc.get("page_number", "N/A"),
                    "chunk_index": doc.get("chunk_index", 0),
                    "text": doc_text,
                    "score": round(similarity_score, 1)
                })
                
        context = "\n\n".join(context_parts)
        logger.info(f"Final context: {len(sources)} sources, ~{current_tokens} tokens")
        
        # Prepare prompt for LLM
        prompt = self._create_prompt(query, context)
        
        # Get answer from LLM
        llm_start = time.time()
        try:
            logger.info(f"Sending {len(prompt)} chars to LLM (estimated {len(prompt)//4} tokens)...")
            response = self.llm_client.chat.completions.create(
                model="local-model",  # LM Studio doesn't require specific model name
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert on ancient Indian epics (Mahabharata, Ramayana) and Sanskrit texts. Answer questions accurately using only the provided context. Cite sources as [Source X]."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=800,  # Reduced for faster generation
                stream=False
            )
            
            answer = response.choices[0].message.content
            timings['llm'] = round(time.time() - llm_start, 3)
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            answer = f"Error communicating with LLM: {str(e)}. Please ensure LM Studio is running and a model is loaded."
            timings['llm'] = 0
        
        timings['total'] = round(time.time() - start_time, 3)
        
        return {
            "answer": answer,
            "sources": sources,
            "metadata": {
                "num_sources": len(retrieved_docs),
                "query": query,
                "timings": timings
            }
        }
    
    def _create_prompt(self, query: str, context: str) -> str:
        """Create a concise prompt for the LLM."""
        return f"""Context:
{context}

Question: {query}

Instructions: Answer using only the context above. Cite sources as [Source X]. If the answer is not in the context, say so clearly.

Answer:"""
    
    def get_status(self) -> Dict[str, Any]:
        """Get backend status information."""
        status = {
            "database_connected": self.table is not None,
            "embedding_model": self.embedding_model_name,
            "reranker_enabled": self.use_reranker,
            "llm_url": self.lm_studio_url
        }
        
        if self.table:
            try:
                status["total_chunks"] = self.table.count_rows()
                # Get list of unique files
                sample = self.table.to_pandas()
                if 'file_name' in sample.columns:
                    status["indexed_files"] = sample['file_name'].unique().tolist()
                else:
                    status["indexed_files"] = []
            except Exception as e:
                status["error"] = str(e)
        
        return status
