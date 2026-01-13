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

# --- Query normalization / entity handling (configurable) ---
_DEFAULT_ENTITY_SYNONYMS = {
    "sugreeva": ["sugreeva", "sugriva"],
    "sugriva": ["sugreeva", "sugriva"],
}


def _load_entity_synonyms() -> Dict[str, List[str]]:
    raw = os.getenv("ENTITY_SYNONYMS_JSON", "").strip()
    if not raw:
        return _DEFAULT_ENTITY_SYNONYMS
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return _DEFAULT_ENTITY_SYNONYMS
        cleaned: Dict[str, List[str]] = {}
        for k, v in data.items():
            if not isinstance(k, str):
                continue
            if isinstance(v, list):
                variants = [str(x).strip().lower() for x in v if str(x).strip()]
            else:
                variants = [str(v).strip().lower()] if str(v).strip() else []
            if variants:
                cleaned[k.strip().lower()] = list(dict.fromkeys(variants))
        return cleaned or _DEFAULT_ENTITY_SYNONYMS
    except Exception:
        return _DEFAULT_ENTITY_SYNONYMS


_ENTITY_SYNONYMS = _load_entity_synonyms()
_ENTITY_BOOST_WEIGHT = float(os.getenv("ENTITY_BOOST_WEIGHT", "0.08") or 0.08)


def _normalize_query_for_retrieval(query: str) -> str:
    q = " ".join(query.strip().split())
    q_lower = q.lower()
    for key, variants in _ENTITY_SYNONYMS.items():
        if not key or key not in q_lower:
            continue
        extra = " ".join(v for v in variants if v and v not in q_lower)
        if extra:
            return f"{q} {extra}"
    return q


def _lexical_entity_boost(query: str, text: str) -> float:
    q = query.lower()
    t = (text or "").lower()
    boost = 0.0
    for key, variants in _ENTITY_SYNONYMS.items():
        if key and key in q:
            if any(v and v in t for v in variants):
                boost += _ENTITY_BOOST_WEIGHT
    return boost

# 2026 Upgrade: Hybrid Search
try:
    from app.bm25_index import BM25Index
    from app.hybrid_search import HybridSearcher
    HYBRID_SEARCH_AVAILABLE = True
except ImportError:
    HYBRID_SEARCH_AVAILABLE = False
    logger.warning("⚠️  Hybrid search modules not available")

# 2026 Upgrade: Smart Query Routing
try:
    from app.query_classifier import QueryClassifier
    from app.query_router import QueryRouter
    QUERY_ROUTING_AVAILABLE = True
except ImportError:
    QUERY_ROUTING_AVAILABLE = False
    logger.warning("⚠️  Query routing modules not available")

# 2026 Upgrade: Context Compression
try:
    from app.context_compressor import ContextCompressor
    CONTEXT_COMPRESSION_AVAILABLE = True
except ImportError:
    CONTEXT_COMPRESSION_AVAILABLE = False
    logger.warning("⚠️  Context compression not available")

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
        self.use_hybrid_search = os.getenv("USE_HYBRID_SEARCH", "true").lower() == "true"
        self.use_query_routing = os.getenv("USE_QUERY_ROUTING", "true").lower() == "true"
        self.use_context_compression = os.getenv("USE_CONTEXT_COMPRESSION", "true").lower() == "true"
        self.lancedb_path = os.getenv("LANCEDB_PATH", "./data/index")
        self.table_name = os.getenv("TABLE_NAME", "docs")
        self.top_k_initial = int(os.getenv("TOP_K_INITIAL", "20"))
        self.top_k_final = int(os.getenv("TOP_K_FINAL", "5"))
        
        # LM Studio configuration
        self.lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        self.lm_studio_api_key = os.getenv("LM_STUDIO_API_KEY", "not-needed-for-local")
        
        # Hot reload tracking
        self.reload_marker = Path("data/.reload_trigger")
        self.last_reload_time = 0
        
        # Initialize models and database
        self._initialize_models()
        self._initialize_database()
        self._initialize_hybrid_search()
        self._initialize_query_routing()
        self._initialize_context_compression()
        
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
                # Get document count
                try:
                    count = self.table.count_rows()
                    logger.info(f"Connected to LanceDB table: {self.table_name} ({count} chunks)")
                except:
                    logger.info(f"Connected to LanceDB table: {self.table_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.table = None
    
    def _initialize_hybrid_search(self):
        """Initialize hybrid search (BM25 + Vector)."""
        self.bm25_index = None
        self.hybrid_searcher = None
        
        if not HYBRID_SEARCH_AVAILABLE:
            logger.info("⚠️  Hybrid search not available (missing dependencies)")
            return
        
        if not self.use_hybrid_search:
            logger.info("ℹ️  Hybrid search disabled in config")
            return
        
        try:
            # Initialize BM25 index
            logger.info("🔧 Initializing BM25 index...")
            self.bm25_index = BM25Index()
            
            if not self.bm25_index.is_built():
                logger.warning("⚠️  BM25 index not found. Run build_bm25_index.py to enable hybrid search.")
                logger.warning("   Falling back to vector-only search.")
                self.bm25_index = None
                return
            
            # Initialize hybrid searcher
            if self.table and self.bm25_index:
                logger.info("🔧 Initializing hybrid searcher...")
                self.hybrid_searcher = HybridSearcher(
                    self.bm25_index,
                    self.table,
                    self.embedding_model
                )
                logger.info("✅ Hybrid search (BM25 + Vector) enabled!")
            
        except Exception as e:
            logger.error(f"Error initializing hybrid search: {e}")
            self.bm25_index = None
            self.hybrid_searcher = None
            logger.warning("⚠️  Falling back to vector-only search")
    
    def _initialize_query_routing(self):
        """Initialize smart query routing."""
        self.query_router = None
        
        if not QUERY_ROUTING_AVAILABLE:
            logger.info("⚠️  Query routing not available (missing dependencies)")
            return
        
        if not self.use_query_routing:
            logger.info("ℹ️  Query routing disabled in config")
            return
        
        try:
            logger.info("🔧 Initializing query router...")
            classifier = QueryClassifier()
            self.query_router = QueryRouter(classifier)
            logger.info("✅ Smart query routing enabled!")
            
        except Exception as e:
            logger.error(f"Error initializing query routing: {e}")
            self.query_router = None
            logger.warning("⚠️  Query routing unavailable")
    
    def _initialize_context_compression(self):
        """Initialize context compression."""
        self.context_compressor = None
        
        if not CONTEXT_COMPRESSION_AVAILABLE:
            logger.info("⚠️  Context compression not available (missing dependencies)")
            return
        
        if not self.use_context_compression:
            logger.info("ℹ️  Context compression disabled in config")
            return
        
        try:
            logger.info("🔧 Initializing context compressor...")
            self.context_compressor = ContextCompressor(
                self.embedding_model,
                relevance_threshold=0.3
            )
            logger.info("✅ Context compression enabled!")
            
        except Exception as e:
            logger.error(f"Error initializing context compression: {e}")
            self.context_compressor = None
            logger.warning("⚠️  Context compression unavailable")
    
    def check_and_reload(self):
        """Check if database needs to be reloaded (new documents added)."""
        if not self.reload_marker.exists():
            return False
        
        marker_time = self.reload_marker.stat().st_mtime
        
        if marker_time > self.last_reload_time:
            logger.info("🔄 Reload trigger detected - reloading database...")
            self._initialize_database()
            self.last_reload_time = marker_time
            
            # Clean up marker
            try:
                self.reload_marker.unlink()
            except:
                pass
            
            logger.info("✅ Database reloaded successfully")
            return True
        
        return False
            
    async def search(self, query: str, k: Optional[int] = None, file_filter: Optional[str] = None, 
                     context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant documents with smart query routing.
        Uses hybrid search (BM25 + Vector) if available, otherwise falls back to vector only.

        Args:
            query: Search query
            k: Number of results to return (defaults to top_k_final)
            file_filter: Optional filename to filter results by
            context: Optional conversation context for routing

        Returns:
            List of relevant document chunks with metadata
        """
        # Check for new documents and reload if needed
        self.check_and_reload()
        if not self.table:
            raise Exception("Vector store not initialized. Please run ingest.py first.")

        retrieval_query = _normalize_query_for_retrieval(query)

        # Smart Query Routing
        routing_decision = None
        if self.query_router and self.use_query_routing:
            routing_decision = self.query_router.route(query, context)
            strategy = routing_decision["strategy"]
            k = k or strategy.get("top_k", self.top_k_final)
            initial_k = strategy.get("rerank_top_k", self.top_k_initial)
        else:
            k = k or self.top_k_final
            initial_k = self.top_k_initial

        # Use hybrid search if available
        if self.hybrid_searcher and self.use_hybrid_search:
            logger.debug("Using hybrid search (BM25 + Vector)")
            initial_results = self.hybrid_searcher.search(
                query=retrieval_query,
                k=initial_k,
                file_filter=file_filter
            )
        else:
            logger.debug("Using vector-only search")
            query_embedding = self.embedding_model.encode(retrieval_query)

            # Initial vector search with optional file filter
            search_query = self.table.search(query_embedding).limit(self.top_k_initial)

            # Apply file filter if specified
            if file_filter and file_filter != "all":
                search_query = search_query.where(f"file_name LIKE '%{file_filter}%'")

            initial_results = search_query.to_list()

        if not initial_results:
            return []

        # Apply lexical entity boost before final selection
        boosted = []
        for doc in initial_results:
            distance = doc.get("_distance", 1.0)
            base_sim = max(0.0, 1.0 - (distance / 2.0))
            boost = _lexical_entity_boost(retrieval_query, doc.get("text", ""))
            boosted.append((base_sim + boost, doc))

        boosted.sort(key=lambda x: x[0], reverse=True)
        boosted_results = [d for _, d in boosted]

        # Optional reranking
        if self.use_reranker and self.reranker and len(boosted_results) > k:
            # Prepare query-document pairs for reranking
            query_doc_pairs = [(retrieval_query, doc["text"]) for doc in boosted_results]

            # Get reranking scores
            rerank_scores = self.reranker.predict(query_doc_pairs)

            # Sort by reranking scores and take top k
            scored_results = list(zip(boosted_results, rerank_scores))
            scored_results.sort(key=lambda x: x[1], reverse=True)
            final_results = [doc for doc, score in scored_results[:k]]
        else:
            final_results = boosted_results[:k]

        return final_results
        
    async def answer(self, query: str, include_sources: bool = True, file_filter: Optional[str] = None,
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate an answer to a query using retrieved documents.

        Args:
            query: User question
            include_sources: Whether to include source documents in response
            file_filter: Optional filename to filter results by
            context: Optional conversation context for routing

        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Track performance timings
        timings = {}
        start_time = time.time()
        
        # Get routing decision for this query
        routing_decision = None
        if self.query_router and self.use_query_routing:
            routing_decision = self.query_router.route(query, context)
        
        # Retrieve relevant documents
        search_start = time.time()
        retrieved_docs = await self.search(query, file_filter=file_filter, context=context)
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
            context_parts.append(doc['text'])

            if include_sources:
                # Calculate relevance score.
                # Note: LanceDB default metric in this project is cosine distance (smaller is better).
                # Convert to similarity (0..1): similarity = 1 - distance (clamped).
                distance = float(doc.get("_distance", 1.0))
                similarity_score = max(0.0, min(1.0, 1.0 - distance))

                sources.append({
                    "index": i,
                    "file_name": doc.get("file_name", "Unknown"),
                    "page": doc.get("page_number", "N/A"),
                    "chunk_index": doc.get("chunk_index"),
                    "text": doc["text"],
                    "score": similarity_score
                })
        
        # Compress context if enabled
        compression_stats = None
        if self.context_compressor and self.use_context_compression:
            compress_start = time.time()
            context_parts, compression_stats = self.context_compressor.compress(
                query, context_parts, max_sentences=50
            )
            timings['compression'] = round(time.time() - compress_start, 3)
            logger.debug(f"Context compressed: {compression_stats['compression_ratio']:.1%}")
        
        # Format context with source numbers
        formatted_context = []
        for i, text in enumerate(context_parts, 1):
            formatted_context.append(f"[Source {i}]\n{text}")
                
        context = "\n\n".join(formatted_context)
        
        # Prepare prompt for LLM with routing-specific instructions
        if routing_decision:
            custom_instructions = self.query_router.get_response_instructions(
                routing_decision["classification"]
            )
            prompt = self._create_prompt(query, context, custom_instructions)
        else:
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
        
    def _create_prompt(self, query: str, context: str, custom_instructions: Optional[str] = None) -> str:
        """
        Create a prompt for the LLM.
        
        Args:
            query: User question
            context: Retrieved context
            custom_instructions: Optional routing-specific instructions
            
        Returns:
            Formatted prompt
        """
        instructions = custom_instructions or "Answer the question based on the context below. Be concise and accurate."
        
        return f"""{instructions}

Context:
{context}

Question: {query}

Answer:"""

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        status = {
            "embedding_model": self.embedding_model_name,
            "reranker_enabled": self.use_reranker,
            "database_connected": self.table is not None,
            "lm_studio_url": self.lm_studio_url,
            "hybrid_search_enabled": self.use_hybrid_search and self.hybrid_searcher is not None,
            "bm25_available": self.bm25_index is not None and self.bm25_index.is_built() if self.bm25_index else False,
            "query_routing_enabled": self.use_query_routing and self.query_router is not None,
            "context_compression_enabled": self.use_context_compression and self.context_compressor is not None
        }
        
        # Add routing stats if available
        if self.query_router:
            status["routing_stats"] = self.query_router.get_stats()
        
        # Add compression stats if available
        if self.context_compressor:
            status["compression_stats"] = self.context_compressor.get_stats()
        
        return status
        
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
