"""
Main FastAPI application for Local RAG system.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.rag_backend import RAGBackend

# Try to import spelling suggester
try:
    from app.spelling_suggester import SpellingSuggester, get_spelling_suggester
    SPELLING_SUGGESTER_AVAILABLE = True
except ImportError:
    SPELLING_SUGGESTER_AVAILABLE = False

# Try to import text highlighter
try:
    from app.text_highlighter import TextHighlighter, get_text_highlighter
    TEXT_HIGHLIGHTER_AVAILABLE = True
except ImportError:
    TEXT_HIGHLIGHTER_AVAILABLE = False

# Try to import result exporter
try:
    from app.result_exporter import ResultExporter, get_result_exporter
    RESULT_EXPORTER_AVAILABLE = True
except ImportError:
    RESULT_EXPORTER_AVAILABLE = False

# Try to import query history
try:
    from app.query_history import QueryHistory, get_query_history
    QUERY_HISTORY_AVAILABLE = True
except ImportError:
    QUERY_HISTORY_AVAILABLE = False

# Try to import related questions generator
try:
    from app.related_questions import RelatedQuestionsGenerator, get_related_questions_generator
    RELATED_QUESTIONS_AVAILABLE = True
except ImportError:
    RELATED_QUESTIONS_AVAILABLE = False

# Try to import character knowledge graph
try:
    from app.character_graph import CharacterKnowledgeGraph, get_character_graph
    CHARACTER_GRAPH_AVAILABLE = True
except ImportError:
    CHARACTER_GRAPH_AVAILABLE = False

# Try to import timeline manager
try:
    from app.timeline import TimelineManager, get_timeline_manager
    TIMELINE_AVAILABLE = True
except ImportError:
    TIMELINE_AVAILABLE = False

# Try to import citation exporter
try:
    from app.citation_exporter import CitationExporter, get_citation_exporter
    CITATION_EXPORTER_AVAILABLE = True
except ImportError:
    CITATION_EXPORTER_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Local RAG System",
    description="Offline RAG system with local LLM integration",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates for HTML rendering
templates = Jinja2Templates(directory="app/templates")

# Initialize RAG backend
rag_backend = None

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing information"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    logger.info(
        f"path={request.url.path} "
        f"method={request.method} "
        f"status={response.status_code} "
        f"duration={process_time:.3f}s"
    )
    
    return response

@app.on_event("startup")
async def startup_event():
    """Initialize the RAG backend on startup."""
    global rag_backend
    try:
        logger.info("Initializing RAG backend...")
        rag_backend = RAGBackend()
        logger.info("✅ RAG backend initialized successfully")
        
        # Initialize spelling suggester if available
        if SPELLING_SUGGESTER_AVAILABLE:
            try:
                suggester = get_spelling_suggester()
                # Build index from LanceDB if empty
                if suggester.get_stats()["total_entities"] == 0 and rag_backend.table:
                    logger.info("Building spelling index from documents...")
                    suggester.build_from_lancedb(rag_backend.table)
                logger.info(f"✅ Spelling suggester initialized ({suggester.get_stats()['total_entities']} entities)")
            except Exception as e:
                logger.warning(f"Failed to initialize spelling suggester: {e}")
                
    except Exception as e:
        logger.error(f"Failed to initialize RAG backend: {e}")
        logger.warning("Server will start but RAG functionality may be limited")

class QuestionRequest(BaseModel):
    question: str
    include_sources: bool = True
    file_filter: str = "all"
    deep_search: bool = True

class AnswerResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class DebugRetrievalRequest(BaseModel):
    query: str
    k: int = 10
    file_filter: str = "all"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main UI page."""
    return templates.TemplateResponse("index_new.html", {"request": request})

@app.get("/classic", response_class=HTMLResponse)
async def home_classic(request: Request):
    """Serve the classic/legacy UI page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """
    Process a question and return an answer with sources.
    """
    if not rag_backend:
        raise HTTPException(status_code=503, detail="RAG backend not initialized")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        logger.info(f"Processing question: {request.question[:100]}...")

        # Get answer from RAG backend
        result = await rag_backend.answer(
            query=request.question,
            include_sources=request.include_sources,
            file_filter=request.file_filter,
            context={"deep_search": request.deep_search}
        )
        
        # Check if we should suggest spelling corrections
        # (when results are poor, no sources found, or answer indicates not found)
        if SPELLING_SUGGESTER_AVAILABLE:
            try:
                num_sources = result.get("metadata", {}).get("num_sources", 0)
                answer_text = result.get("answer", "").lower()
                
                # Check if answer indicates no info found
                no_info_indicators = [
                    "don't explicitly state",
                    "do not explicitly state",
                    "not explicitly",
                    "couldn't find",
                    "could not find",
                    "no information",
                    "not found",
                    "sources don't",
                    "sources do not",
                ]
                answer_indicates_no_info = any(ind in answer_text for ind in no_info_indicators)
                
                # Suggest corrections if few sources OR answer indicates no info
                if num_sources <= 2 or answer_indicates_no_info:
                    suggester = get_spelling_suggester()
                    did_you_mean = suggester.get_did_you_mean(request.question)
                    if did_you_mean:
                        result["metadata"]["did_you_mean"] = did_you_mean
                        result["metadata"]["spelling_suggestions"] = suggester.get_suggestions(
                            request.question, max_suggestions=3
                        )
            except Exception as e:
                logger.warning(f"Spelling suggestion failed: {e}")
        
        # Log timing if available
        if 'metadata' in result and 'timings' in result.get('metadata', {}):
            logger.info(f"Answer generated in {result['metadata']['timings']['total']}s")
        else:
            logger.info("Answer generated successfully")
        
        # Save to query history
        if QUERY_HISTORY_AVAILABLE:
            try:
                history = get_query_history()
                history.add_entry(
                    query=request.question,
                    answer=result["answer"],
                    sources=result["sources"],
                    metadata=result.get("metadata", {})
                )
            except Exception as e:
                logger.warning(f"Failed to save to query history: {e}")
        
        # Generate related questions for follow-up exploration
        if RELATED_QUESTIONS_AVAILABLE:
            try:
                generator = get_related_questions_generator()
                related_questions = generator.generate_related_questions(
                    query=request.question,
                    answer=result["answer"],
                    sources=result["sources"],
                    max_questions=5
                )
                result["metadata"]["related_questions"] = related_questions
            except Exception as e:
                logger.warning(f"Failed to generate related questions: {e}")
        
        return AnswerResponse(
            answer=result["answer"],
            sources=result["sources"],
            metadata=result["metadata"]
        )
    
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        
        # More user-friendly error messages
        error_msg = str(e)
        if "Vector store not initialized" in error_msg:
            error_msg = "No documents have been indexed yet. Please add documents to the 'documents/' folder and run: python phase1_extract.py --all && python phase2_embed.py --all"
        elif "LM Studio" in error_msg or "LLM" in error_msg:
            error_msg = "Cannot connect to LM Studio. Please ensure LM Studio is running with a model loaded at http://localhost:1234"
        
        raise HTTPException(status_code=400, detail=error_msg)


# ============= Documents Endpoint =============

@app.get("/api/documents")
async def list_documents():
    """
    List all indexed documents with basic info.
    Used for the document filter dropdown in the UI.
    """
    if not rag_backend:
        return {"documents": []}
    
    try:
        doc_stats = rag_backend.get_document_stats()
        documents = [
            {
                "id": name,
                "name": name.replace("_", " ").replace(".pdf", "").replace(".txt", ""),
                "chunks": stats.get("chunk_count", 0)
            }
            for name, stats in doc_stats.items()
        ]
        # Sort by name
        documents.sort(key=lambda x: x["name"])
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return {"documents": []}


# ============= Streaming Endpoint =============

@app.post("/api/ask/stream")
async def ask_question_stream(request: QuestionRequest):
    """
    Process a question and stream the answer using Server-Sent Events (SSE).

    Returns a stream of events:
        - {"type": "sources", "data": [...]} - Source documents (sent first)
        - {"type": "token", "data": "..."} - Individual tokens from LLM
        - {"type": "done", "data": {...}} - Final metadata when complete
        - {"type": "error", "data": "..."} - Error message if something fails
    """
    if not rag_backend:
        raise HTTPException(status_code=503, detail="RAG backend not initialized")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    async def generate():
        try:
            async for chunk in rag_backend.answer_streaming(
                query=request.question,
                include_sources=request.include_sources,
                file_filter=request.file_filter,
                context={"deep_search": request.deep_search}
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            import json
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ============= Text Highlighting Endpoint =============

class HighlightRequest(BaseModel):
    text: str
    query: str
    max_highlights: int = 50


@app.post("/api/highlight")
async def highlight_text(request: HighlightRequest):
    """
    Highlight query terms in text.
    
    Args:
        text: The text to highlight
        query: The search query containing terms to highlight
        max_highlights: Maximum number of highlights
        
    Returns:
        Highlighted text with HTML spans
    """
    if not TEXT_HIGHLIGHTER_AVAILABLE:
        return {"available": False, "highlighted_text": request.text}
    
    try:
        highlighter = get_text_highlighter()
        result = highlighter.highlight_text(
            request.text,
            request.query,
            max_highlights=request.max_highlights
        )
        return {
            "available": True,
            **result
        }
    except Exception as e:
        logger.error(f"Highlighting error: {e}")
        return {"available": False, "highlighted_text": request.text, "error": str(e)}


# ============= Export Endpoints =============

class ExportRequest(BaseModel):
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    format: str = "markdown"  # markdown, json, html
    metadata: Optional[Dict[str, Any]] = None


@app.post("/api/export")
async def export_results(request: ExportRequest):
    """
    Export query results to various formats.
    
    Args:
        query: Original question
        answer: Generated answer
        sources: Source documents
        format: Export format (markdown, json, html)
        metadata: Optional metadata
        
    Returns:
        File download or content based on format
    """
    if not RESULT_EXPORTER_AVAILABLE:
        raise HTTPException(status_code=501, detail="Export functionality not available")
    
    try:
        exporter = get_result_exporter()
        
        if request.format == "markdown" or request.format == "md":
            content = exporter.export_to_markdown(
                request.query,
                request.answer,
                request.sources,
                request.metadata
            )
            media_type = "text/markdown"
            filename = f"rag_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
        elif request.format == "json":
            content = exporter.export_to_json(
                request.query,
                request.answer,
                request.sources,
                request.metadata
            )
            media_type = "application/json"
            filename = f"rag_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        elif request.format == "html":
            content = exporter.export_to_html(
                request.query,
                request.answer,
                request.sources,
                request.metadata
            )
            media_type = "text/html"
            filename = f"rag_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/debug/retrieval")
async def debug_retrieval(request: DebugRetrievalRequest):
    """Debug retrieval pipeline (hybrid/vector, reranker, epic-bias, etc.).

    This is intended for development/UI diagnostics and returns detailed retrieval metadata.
    """
    if not rag_backend:
        raise HTTPException(status_code=503, detail="RAG backend not initialized")

    q = (request.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        return await rag_backend.debug_retrieval(
            query=q,
            k=request.k,
            file_filter=request.file_filter or "all",
        )
    except Exception as e:
        logger.error(f"Debug retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


class DecomposeQueryRequest(BaseModel):
    query: str
    use_llm: bool = True


class FeedbackRequest(BaseModel):
    query: str
    answer: str
    rating: int  # 1-5 scale
    sources: List[Dict[str, Any]] = []
    comment: str = None
    query_type: str = None


@app.post("/api/debug/decompose")
async def debug_decompose(payload: DecomposeQueryRequest):
    """
    Debug endpoint for testing query decomposition.
    Shows how a complex query would be broken into sub-queries.
    Guarded by ENABLE_DEBUG_ENDPOINTS.
    """
    if os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")

    if not rag_backend:
        raise HTTPException(status_code=503, detail="RAG backend not initialized")

    q = (payload.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if not rag_backend.query_decomposer:
        return {
            "error": "Query decomposition not available",
            "enabled": False,
            "reason": "USE_QUERY_DECOMPOSITION=false or module not available"
        }

    try:
        result = rag_backend.query_decomposer.decompose(q, use_llm=payload.use_llm)
        return {
            "enabled": True,
            "decomposition": result,
            "stats": rag_backend.query_decomposer.get_stats(),
        }
    except Exception as e:
        logger.error(f"Error in query decomposition: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/feedback")
async def submit_feedback(payload: FeedbackRequest):
    """
    Submit feedback on an answer.
    Rating scale: 1 (very bad) to 5 (excellent).
    """
    if not rag_backend:
        raise HTTPException(status_code=503, detail="RAG backend not initialized")
    
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if not 1 <= payload.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    try:
        result = rag_backend.record_feedback(
            query=payload.query,
            answer=payload.answer,
            rating=payload.rating,
            sources=payload.sources,
            comment=payload.comment,
            query_type=payload.query_type,
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "message": "Feedback recorded",
            "feedback_id": result.get("id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/feedback/stats")
async def get_feedback_stats():
    """Get feedback statistics."""
    if not rag_backend:
        raise HTTPException(status_code=503, detail="RAG backend not initialized")
    
    try:
        stats = rag_backend.get_feedback_stats()
        if "error" in stats:
            return {"enabled": False, "error": stats["error"]}
        
        return {
            "enabled": True,
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/feedback/low-rated")
async def get_low_rated_queries():
    """
    Get queries with low ratings for review.
    Guarded by ENABLE_DEBUG_ENDPOINTS.
    """
    if os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")
    
    if not rag_backend:
        raise HTTPException(status_code=503, detail="RAG backend not initialized")
    
    try:
        queries = rag_backend.get_low_rated_queries(limit=20)
        return {
            "count": len(queries),
            "queries": queries,
        }
    except Exception as e:
        logger.error(f"Error getting low-rated queries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get response cache statistics."""
    if not rag_backend:
        raise HTTPException(status_code=503, detail="RAG backend not initialized")
    
    try:
        stats = rag_backend.get_cache_stats()
        if "error" in stats:
            return {"enabled": False, "error": stats["error"]}
        
        return {
            "enabled": True,
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cache/clear")
async def clear_cache():
    """
    Clear the response cache.
    Guarded by ENABLE_DEBUG_ENDPOINTS.
    """
    if os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")
    
    if not rag_backend:
        raise HTTPException(status_code=503, detail="RAG backend not initialized")
    
    try:
        result = rag_backend.clear_cache()
        return {
            "status": "success",
            "message": "Cache cleared",
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============= Spelling Suggestion Endpoints =============

@app.get("/api/autocomplete")
async def autocomplete(q: str = "", limit: int = 10):
    """
    Get autocomplete suggestions for entity names while typing.
    
    Args:
        q: The prefix to autocomplete
        limit: Maximum number of suggestions (default 10)
    
    Returns:
        List of matching entity names from the corpus
    """
    if not SPELLING_SUGGESTER_AVAILABLE:
        return {"available": False, "suggestions": []}
    
    if not q or len(q) < 2:
        return {"available": True, "suggestions": []}
    
    try:
        suggester = get_spelling_suggester()
        results = suggester.get_autocomplete(q, max_results=limit)
        return {
            "available": True,
            "query": q,
            "suggestions": results,
        }
    except Exception as e:
        logger.error(f"Error in autocomplete: {e}")
        return {"available": True, "suggestions": [], "error": str(e)}


@app.get("/api/spelling/suggest")
async def spelling_suggest(q: str = "", limit: int = 5):
    """
    Get spelling suggestions for potentially misspelled words in a query.
    
    Args:
        q: The query to check for misspellings
        limit: Maximum number of suggestions per word
    
    Returns:
        List of spelling corrections with confidence scores
    """
    if not SPELLING_SUGGESTER_AVAILABLE:
        return {"available": False, "suggestions": []}
    
    if not q:
        return {"available": True, "suggestions": []}
    
    try:
        suggester = get_spelling_suggester()
        suggestions = suggester.get_suggestions(q, max_suggestions=limit)
        did_you_mean = suggester.get_did_you_mean(q)
        
        return {
            "available": True,
            "query": q,
            "suggestions": suggestions,
            "did_you_mean": did_you_mean,
        }
    except Exception as e:
        logger.error(f"Error in spelling suggest: {e}")
        return {"available": True, "suggestions": [], "error": str(e)}


@app.get("/api/spelling/stats")
async def spelling_stats():
    """Get statistics about the spelling index."""
    if not SPELLING_SUGGESTER_AVAILABLE:
        return {"available": False}
    
    try:
        suggester = get_spelling_suggester()
        stats = suggester.get_stats()
        return {
            "available": True,
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Error in spelling stats: {e}")
        return {"available": False, "error": str(e)}


@app.post("/api/spelling/rebuild")
async def rebuild_spelling_index():
    """
    Rebuild the spelling index from the document database.
    Guarded by ENABLE_DEBUG_ENDPOINTS.
    """
    if os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")
    
    if not SPELLING_SUGGESTER_AVAILABLE:
        return {"available": False, "error": "Spelling suggester not available"}
    
    if not rag_backend or not rag_backend.table:
        raise HTTPException(status_code=503, detail="RAG backend or database not initialized")
    
    try:
        suggester = get_spelling_suggester()
        # Clear existing index
        suggester.entities = {}
        suggester._rebuild_maps()
        # Rebuild from LanceDB
        count = suggester.build_from_lancedb(rag_backend.table)
        return {
            "status": "success",
            "entities_indexed": count,
            "total_entities": suggester.get_stats()["total_entities"],
        }
    except Exception as e:
        logger.error(f"Error rebuilding spelling index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Related Questions Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class RelatedQuestionsRequest(BaseModel):
    """Request model for related questions."""
    query: str
    answer: str = ""
    sources: list = []
    max_questions: int = 5


@app.post("/api/related-questions")
async def get_related_questions(request: RelatedQuestionsRequest):
    """
    Generate related follow-up questions based on the query and answer.
    
    This helps users explore topics deeper by suggesting relevant questions
    they might want to ask next.
    """
    if not RELATED_QUESTIONS_AVAILABLE:
        return {
            "available": False,
            "questions": [],
            "message": "Related questions feature not available"
        }
    
    try:
        generator = get_related_questions_generator()
        questions = generator.generate_related_questions(
            query=request.query,
            answer=request.answer,
            sources=request.sources,
            max_questions=request.max_questions
        )
        return {
            "available": True,
            "questions": questions,
            "query": request.query
        }
    except Exception as e:
        logger.error(f"Error generating related questions: {e}")
        return {
            "available": True,
            "questions": [],
            "error": str(e)
        }


# ─────────────────────────────────────────────────────────────────────────────
# Character Knowledge Graph Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/characters")
async def list_characters(epic: Optional[str] = None):
    """
    Get list of all characters in the knowledge graph.
    
    Query Parameters:
        epic: Optional filter by epic ("Ramayana" or "Mahabharata")
    """
    if not CHARACTER_GRAPH_AVAILABLE:
        return {"available": False, "message": "Character graph not available"}
    
    try:
        graph = get_character_graph()
        characters = graph.get_all_characters(epic)
        return {
            "available": True,
            "characters": characters,
            "count": len(characters),
            "filter": {"epic": epic} if epic else None
        }
    except Exception as e:
        logger.error(f"Error listing characters: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/characters/{name}")
async def get_character(name: str):
    """
    Get detailed information about a specific character.
    
    Path Parameters:
        name: Character name (e.g., "Rama", "Krishna", "Arjuna")
    """
    if not CHARACTER_GRAPH_AVAILABLE:
        return {"available": False, "message": "Character graph not available"}
    
    try:
        graph = get_character_graph()
        profile = graph.get_character_profile(name)
        
        if not profile:
            return {
                "available": True,
                "found": False,
                "message": f"Character '{name}' not found",
                "suggestions": graph.search_characters(name)[:5]
            }
        
        return {
            "available": True,
            "found": True,
            "character": profile
        }
    except Exception as e:
        logger.error(f"Error getting character {name}: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/characters/{name}/relationships")
async def get_character_relationships(name: str):
    """
    Get all relationships for a character.
    """
    if not CHARACTER_GRAPH_AVAILABLE:
        return {"available": False, "message": "Character graph not available"}
    
    try:
        graph = get_character_graph()
        relationships = graph.get_relationships(name)
        
        if not relationships:
            char = graph.get_character(name)
            if not char:
                return {
                    "available": True,
                    "found": False,
                    "message": f"Character '{name}' not found"
                }
        
        return {
            "available": True,
            "character": name,
            "relationships": relationships,
            "count": len(relationships)
        }
    except Exception as e:
        logger.error(f"Error getting relationships for {name}: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/characters/{name}/family")
async def get_character_family(name: str):
    """
    Get family tree for a character.
    """
    if not CHARACTER_GRAPH_AVAILABLE:
        return {"available": False, "message": "Character graph not available"}
    
    try:
        graph = get_character_graph()
        family = graph.get_family_tree(name)
        
        if "error" in family:
            return {
                "available": True,
                "found": False,
                "message": family["error"]
            }
        
        return {
            "available": True,
            "found": True,
            "family": family
        }
    except Exception as e:
        logger.error(f"Error getting family for {name}: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/characters/path/{source}/{target}")
async def find_character_path(source: str, target: str):
    """
    Find the relationship path between two characters.
    
    Example: /api/characters/path/Rama/Ravana
    """
    if not CHARACTER_GRAPH_AVAILABLE:
        return {"available": False, "message": "Character graph not available"}
    
    try:
        graph = get_character_graph()
        path = graph.find_path(source, target)
        
        if not path:
            return {
                "available": True,
                "found": False,
                "message": f"No path found between '{source}' and '{target}'",
                "source": source,
                "target": target
            }
        
        return {
            "available": True,
            "found": True,
            "source": source,
            "target": target,
            "path": path,
            "path_length": len(path) - 1
        }
    except Exception as e:
        logger.error(f"Error finding path {source} -> {target}: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/characters/search")
async def search_characters(q: str):
    """
    Search for characters by name, title, or description.
    
    Query Parameters:
        q: Search query
    """
    if not CHARACTER_GRAPH_AVAILABLE:
        return {"available": False, "message": "Character graph not available"}
    
    try:
        graph = get_character_graph()
        results = graph.search_characters(q)
        
        return {
            "available": True,
            "query": q,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching characters: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/characters-graph/stats")
async def character_graph_stats():
    """
    Get statistics about the character knowledge graph.
    """
    if not CHARACTER_GRAPH_AVAILABLE:
        return {"available": False, "message": "Character graph not available"}
    
    try:
        graph = get_character_graph()
        stats = graph.get_stats()
        
        return {
            "available": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting character graph stats: {e}")
        return {"available": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Timeline Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/timeline")
async def get_timeline(epic: Optional[str] = None, character: Optional[str] = None, book: Optional[str] = None):
    """
    Get chronological events from the epics.
    
    Query Parameters:
        epic: Filter by "Ramayana" or "Mahabharata"
        character: Filter by character name
        book: Filter by book/kanda/parva name
    """
    if not TIMELINE_AVAILABLE:
        return {"available": False, "message": "Timeline feature not available"}
    
    try:
        timeline = get_timeline_manager()
        events = timeline.get_timeline(epic=epic, character=character, book=book)
        
        return {
            "available": True,
            "events": events,
            "count": len(events),
            "filters": {
                "epic": epic,
                "character": character,
                "book": book
            }
        }
    except Exception as e:
        logger.error(f"Error getting timeline: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/timeline/event/{event_id}")
async def get_timeline_event(event_id: str):
    """
    Get a specific event by ID.
    """
    if not TIMELINE_AVAILABLE:
        return {"available": False, "message": "Timeline feature not available"}
    
    try:
        timeline = get_timeline_manager()
        event = timeline.get_event(event_id)
        
        if not event:
            return {
                "available": True,
                "found": False,
                "message": f"Event '{event_id}' not found"
            }
        
        return {
            "available": True,
            "found": True,
            "event": event
        }
    except Exception as e:
        logger.error(f"Error getting event: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/timeline/character/{name}")
async def get_character_timeline(name: str):
    """
    Get all events involving a specific character.
    """
    if not TIMELINE_AVAILABLE:
        return {"available": False, "message": "Timeline feature not available"}
    
    try:
        timeline = get_timeline_manager()
        result = timeline.get_character_timeline(name)
        
        return {
            "available": True,
            **result
        }
    except Exception as e:
        logger.error(f"Error getting character timeline: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/timeline/books")
async def get_timeline_books(epic: Optional[str] = None):
    """
    Get list of books/kandas/parvas with event counts.
    """
    if not TIMELINE_AVAILABLE:
        return {"available": False, "message": "Timeline feature not available"}
    
    try:
        timeline = get_timeline_manager()
        books = timeline.get_books(epic=epic)
        
        return {
            "available": True,
            "books": books,
            "count": len(books)
        }
    except Exception as e:
        logger.error(f"Error getting books: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/timeline/search")
async def search_timeline(q: str):
    """
    Search events by keyword.
    """
    if not TIMELINE_AVAILABLE:
        return {"available": False, "message": "Timeline feature not available"}
    
    try:
        timeline = get_timeline_manager()
        results = timeline.search_events(q)
        
        return {
            "available": True,
            "query": q,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching timeline: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/timeline/tag/{tag}")
async def get_events_by_tag(tag: str):
    """
    Get all events with a specific tag.
    """
    if not TIMELINE_AVAILABLE:
        return {"available": False, "message": "Timeline feature not available"}
    
    try:
        timeline = get_timeline_manager()
        events = timeline.get_events_by_tag(tag)
        
        return {
            "available": True,
            "tag": tag,
            "events": events,
            "count": len(events)
        }
    except Exception as e:
        logger.error(f"Error getting events by tag: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/timeline/stats")
async def timeline_stats():
    """
    Get timeline statistics.
    """
    if not TIMELINE_AVAILABLE:
        return {"available": False, "message": "Timeline feature not available"}
    
    try:
        timeline = get_timeline_manager()
        stats = timeline.get_stats()
        
        return {
            "available": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting timeline stats: {e}")
        return {"available": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Citation Export Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class CitationRequest(BaseModel):
    """Request model for citation export."""
    sources: List[Dict[str, Any]]
    format: str = "bibtex"  # bibtex, chicago, mla, apa


@app.post("/api/citations/export")
async def export_citations(request: CitationRequest):
    """
    Export citations in the specified academic format.
    
    Supported formats: bibtex, chicago, mla, apa
    """
    if not CITATION_EXPORTER_AVAILABLE:
        return {"available": False, "message": "Citation export not available"}
    
    try:
        exporter = get_citation_exporter()
        result = exporter.export_citations(
            sources=request.sources,
            format=request.format
        )
        
        return {
            "available": True,
            **result
        }
    except Exception as e:
        logger.error(f"Error exporting citations: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/citations/formats")
async def list_citation_formats():
    """
    List available citation formats.
    """
    return {
        "available": CITATION_EXPORTER_AVAILABLE,
        "formats": [
            {
                "id": "bibtex",
                "name": "BibTeX",
                "description": "For LaTeX documents and bibliography management",
                "use_case": "Academic papers, theses"
            },
            {
                "id": "chicago",
                "name": "Chicago Style",
                "description": "Chicago Manual of Style (Notes-Bibliography)",
                "use_case": "Humanities, history, arts"
            },
            {
                "id": "mla",
                "name": "MLA",
                "description": "Modern Language Association (9th edition)",
                "use_case": "Literature, language studies"
            },
            {
                "id": "apa",
                "name": "APA",
                "description": "American Psychological Association (7th edition)",
                "use_case": "Social sciences, psychology"
            }
        ]
    }


@app.get("/api/citations/document/{file_name:path}")
async def get_document_citation(file_name: str, format: str = "chicago"):
    """
    Get a bibliography entry for a document.
    """
    if not CITATION_EXPORTER_AVAILABLE:
        return {"available": False, "message": "Citation export not available"}
    
    try:
        exporter = get_citation_exporter()
        citation = exporter.get_bibliography_entry(file_name, format)
        
        return {
            "available": True,
            "file_name": file_name,
            "format": format,
            "citation": citation
        }
    except Exception as e:
        logger.error(f"Error getting document citation: {e}")
        return {"available": False, "error": str(e)}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    if not rag_backend:
        return {"status": "starting", "message": "RAG backend initializing"}
    
    try:
        status = rag_backend.get_status()
        return {
            "status": "healthy" if status["database_connected"] else "degraded",
            "backend_status": status,
            "message": "All systems operational" if status["database_connected"] else "Database not available",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "message": f"Backend error: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api/health/detailed")
async def detailed_health():
    """Detailed health check with component status"""
    checks = {}
    
    # Check database
    try:
        if rag_backend and rag_backend.table:
            count = rag_backend.table.count_rows()
            checks["database"] = {"status": "healthy", "chunks": count}
        else:
            checks["database"] = {"status": "unhealthy", "error": "Not connected"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
    
    # Check embedding model
    try:
        if rag_backend and rag_backend.embedding_model:
            checks["embedding_model"] = {
                "status": "healthy",
                "model": rag_backend.embedding_model_name
            }
        else:
            checks["embedding_model"] = {"status": "unhealthy", "error": "Not loaded"}
    except Exception as e:
        checks["embedding_model"] = {"status": "unhealthy", "error": str(e)}
    
    # Check LLM service
    try:
        if rag_backend:
            import requests
            response = requests.get(f"{rag_backend.lm_studio_url}/models", timeout=2)
            if response.status_code == 200:
                checks["llm_service"] = {
                    "status": "healthy",
                    "url": rag_backend.lm_studio_url
                }
            else:
                checks["llm_service"] = {
                    "status": "degraded",
                    "url": rag_backend.lm_studio_url
                }
        else:
            checks["llm_service"] = {"status": "unhealthy", "error": "Backend not initialized"}
    except Exception as e:
        checks["llm_service"] = {
            "status": "unhealthy",
            "error": "LM Studio not reachable",
            "message": str(e)
        }
    
    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_gb = free // (2**30)
        checks["disk_space"] = {
            "status": "healthy" if free_gb > 10 else "warning",
            "free_gb": free_gb
        }
    except Exception as e:
        checks["disk_space"] = {"status": "unknown", "error": str(e)}
    
    # Check memory
    try:
        import psutil
        memory = psutil.virtual_memory()
        checks["memory"] = {
            "status": "healthy" if memory.percent < 90 else "warning",
            "used_percent": round(memory.percent, 1),
            "available_gb": round(memory.available / (1024**3), 2)
        }
    except Exception as e:
        checks["memory"] = {"status": "unknown", "error": str(e)}
    
    # Overall status
    all_healthy = all(
        check.get("status") == "healthy" 
        for check in checks.values()
    )
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/stats")
async def get_stats():
    """Get system statistics."""
    if not rag_backend:
        raise HTTPException(status_code=503, detail="RAG backend not initialized")

    try:
        stats = rag_backend.get_status()

        # Per-file stats (can be expensive on large corpora, so keep optional)
        include_files = os.getenv("STATS_INCLUDE_PER_FILE", "true").lower() == "true"
        if include_files:
            per_file = rag_backend.get_document_stats()
            stats["per_file"] = per_file
            stats["totals"] = {
                "num_files": len(per_file),
                "total_chunks": sum(v.get("chunk_count", 0) for v in per_file.values()),
            }

            # Convenience: top files by chunk count
            top_n = int(os.getenv("STATS_TOP_FILES_N", "10"))
            stats["top_files_by_chunks"] = sorted(
                (
                    {"file_name": k, **v}
                    for k, v in per_file.items()
                ),
                key=lambda x: x.get("chunk_count", 0),
                reverse=True,
            )[: max(0, top_n)]
        
        # Add character graph stats
        if CHARACTER_GRAPH_AVAILABLE:
            try:
                graph = get_character_graph()
                graph_stats = graph.get_stats()
                stats["characters_count"] = graph_stats.get("total_characters", 0)
                stats["relationships_count"] = graph_stats.get("total_relationships", 0)
            except Exception as e:
                logger.warning(f"Failed to get character stats: {e}")
                stats["characters_count"] = 0
                stats["relationships_count"] = 0
        else:
            stats["characters_count"] = 0
            stats["relationships_count"] = 0
        
        # Add timeline stats
        if TIMELINE_AVAILABLE:
            try:
                timeline = get_timeline_manager()
                timeline_stats = timeline.get_stats()
                stats["events_count"] = timeline_stats.get("total_events", 0)
            except Exception as e:
                logger.warning(f"Failed to get timeline stats: {e}")
                stats["events_count"] = 0
        else:
            stats["events_count"] = 0

        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


# ============= Query History Endpoints =============

@app.get("/api/history")
async def get_history(limit: int = 50, search: Optional[str] = None):
    """
    Get recent query history.
    
    Args:
        limit: Maximum number of entries to return (default 50)
        search: Optional search term to filter history
        
    Returns:
        List of history entries with query, answer preview, timestamp
    """
    if not QUERY_HISTORY_AVAILABLE:
        return {"available": False, "entries": [], "message": "Query history not available"}
    
    try:
        history = get_query_history()
        entries = history.get_history(limit=limit, search_term=search)
        stats = history.get_stats()
        
        return {
            "available": True,
            "entries": entries,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting query history: {e}")
        return {"available": False, "entries": [], "error": str(e)}


@app.get("/api/history/{entry_id}")
async def get_history_entry(entry_id: str):
    """
    Get a specific history entry by ID.
    
    Args:
        entry_id: The ID of the history entry
        
    Returns:
        Full history entry including query, answer, and sources
    """
    if not QUERY_HISTORY_AVAILABLE:
        raise HTTPException(status_code=501, detail="Query history not available")
    
    try:
        history = get_query_history()
        entry = history.get_entry(entry_id)
        
        if entry is None:
            raise HTTPException(status_code=404, detail="History entry not found")
        
        return {"available": True, "entry": entry}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/history/{entry_id}")
async def delete_history_entry(entry_id: str):
    """
    Delete a specific history entry.
    
    Args:
        entry_id: The ID of the history entry to delete
        
    Returns:
        Success status
    """
    if not QUERY_HISTORY_AVAILABLE:
        raise HTTPException(status_code=501, detail="Query history not available")
    
    try:
        history = get_query_history()
        success = history.delete_entry(entry_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="History entry not found")
        
        return {"success": True, "message": "Entry deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting history entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/history")
async def clear_history():
    """
    Clear all query history.
    
    Returns:
        Success status with count of deleted entries
    """
    if not QUERY_HISTORY_AVAILABLE:
        raise HTTPException(status_code=501, detail="Query history not available")
    
    try:
        history = get_query_history()
        deleted_count = history.clear_history()
        
        return {"success": True, "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Provide user-friendly error messages"""
    user_friendly_messages = {
        503: "The system is starting up. Please wait a moment and try again.",
        500: "Something went wrong. Please check the logs.",
        400: "Please check your input and try again.",
        404: "The requested resource was not found.",
        429: "Too many requests. Please slow down."
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": user_friendly_messages.get(exc.status_code, str(exc.detail)),
            "code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )
