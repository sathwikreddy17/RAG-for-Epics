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
# Configure via .env:
#   ENTITY_SYNONYMS_JSON={"sugreeva":["sugreeva","sugriva"],"krishna":["krishna","krsna"]}
#   ENTITY_BOOST_WEIGHT=0.08
# If unset/invalid, falls back to a minimal built-in set.
_DEFAULT_ENTITY_SYNONYMS = {
    "sugreeva": ["sugreeva", "sugriva", "sugriwa"],
    "sugriva": ["sugreeva", "sugriva", "sugriwa"],
    "rama": ["rama", "raama", "ram", "ramachandra", "ramacandra", "raghava", "raghunandan"],
    "sita": ["sita", "seeta", "janaki", "vaidehi", "maithili"],
    "ravana": ["ravana", "ravan", "dashanana", "dashanan", "lankesh"],
    "hanuman": ["hanuman", "hanumat", "anjaneya", "maruti", "hanumaan"],
    "lakshmana": ["lakshmana", "lakshman", "laxman", "laksman"],
    "krishna": ["krishna", "krsna", "keshava", "govinda", "vasudeva"],
    "arjuna": ["arjuna", "arjun", "partha", "dhananjaya", "kiriti"],
    "bharata": ["bharata", "bharat"],
    "dasaratha": ["dasaratha", "dasharath", "dashrath"],
    # Ramayana: key aliases that often cause cross-epic drift if not normalized
    "meghanada": ["meghanada", "meganada", "meghanad", "meghnath", "meganath", "indrajit"],
    "indrajit": ["indrajit", "indrajeet", "meghanada", "meghnath", "meghanad", "meganath"],
    "valmiki": ["valmiki", "vālmīki", "valmiki's"],
    "vibhishana": ["vibhishana", "vibhishan", "bibhishana", "bibhishan"],
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
_ENTITY_BOOST_WEIGHT = float(os.getenv("ENTITY_BOOST_WEIGHT", "0.15") or 0.15)  # Increased for better entity matching

# Epic-aware retrieval bias (soft boost): helps prevent cross-epic mixing when deep search increases recall.
_EPIC_BOOST_WEIGHT = float(os.getenv("EPIC_BOOST_WEIGHT", "0.20") or 0.20)
_EPIC_MISMATCH_PENALTY = float(os.getenv("EPIC_MISMATCH_PENALTY", "0.10") or 0.10)

# Epic hard filter (optional): when confident about intended epic, drop cross-epic documents.
# This is off by default to avoid breaking comparative/cross-epic questions.
_USE_EPIC_HARD_FILTER = os.getenv("USE_EPIC_HARD_FILTER", "false").lower() == "true"
# Minimum cue margin required to enable hard filter (hits difference between epics).
_EPIC_HARD_FILTER_MARGIN = int(os.getenv("EPIC_HARD_FILTER_MARGIN", "2") or 2)


def _expand_simple_query(query: str) -> str:
    """Expand simple 'who/what is X' queries to improve retrieval.
    
    Short queries like "Who is Rama?" often fail to retrieve the best results
    because they don't contain enough semantic signal. This function expands
    them with relevant context terms.
    """
    import re
    
    query_lower = query.lower().strip()
    
    # Pattern: "who is X" or "what is X" or "tell me about X"
    patterns = [
        r'^who\s+is\s+(\w+)\s*\??$',
        r'^what\s+is\s+(\w+)\s*\??$',
        r'^tell\s+me\s+about\s+(\w+)\s*\??$',
        r'^describe\s+(\w+)\s*\??$',
        r'^who\s+was\s+(\w+)\s*\??$',
        r'^what\s+was\s+(\w+)\s*\??$',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, query_lower)
        if match:
            entity = match.group(1)
            # Expand with comprehensive contextual terms for major characters
            expansions = {
                'rama': 'Rama Ramachandra son of King Dasaratha prince of Ayodhya hero of Ramayana avatar of Vishnu husband of Sita Ikshvaku dynasty Kosala',
                'sita': 'Sita Janaki daughter of King Janaka wife of Rama princess of Mithila Vaidehi abducted by Ravana',
                'hanuman': 'Hanuman son of Anjana devotee of Rama monkey god messenger to Lanka servant Vayu',
                'ravana': 'Ravana king of Lanka rakshasa demon ten heads villain abducted Sita brother of Vibhishana Kumbhakarna',
                'lakshmana': 'Lakshmana brother of Rama son of Dasaratha and Sumitra loyal companion Urmila devoted',
                'dasaratha': 'Dasaratha king of Ayodhya father of Rama Bharata Lakshmana Shatrughna Kosala Ikshvaku dynasty',
                'bharata': 'Bharata son of Dasaratha and Kaikeyi brother of Rama ruled Ayodhya sandals of Rama Nandigrama',
                'kaikeyi': 'Kaikeyi queen wife of Dasaratha mother of Bharata boons Manthara exile of Rama',
                'krishna': 'Krishna avatar of Vishnu charioteer of Arjuna Bhagavad Gita Vrindavan Mathura Dwarka son of Vasudeva Devaki',
                'arjuna': 'Arjuna Pandava warrior archer Mahabharata son of Kunti Pandu third Pandava Gandiva bow',
                'yudhishthira': 'Yudhishthira Dharmaraja eldest Pandava king son of Kunti Dharma righteous gambling dice',
                'bhima': 'Bhima Pandava strong warrior mace Vrikodara son of Kunti Vayu killer of Dushasana',
                'draupadi': 'Draupadi wife of Pandavas princess of Panchala Krishnaa daughter of Drupada Yajnaseni',
                'karna': 'Karna warrior Kunti son Surya chariot driver generous Radheya ear-rings armor Duryodhana friend',
                'duryodhana': 'Duryodhana Kaurava prince eldest son of Dhritarashtra villain Mahabharata enemy of Pandavas',
                'bhishma': 'Bhishma grandsire patriarch vow Ganga son Devavrata Hastinapura bed of arrows',
                'drona': 'Drona Dronacharya teacher guru of Kauravas and Pandavas Ashwatthama father warrior',
                'vibhishana': 'Vibhishana brother of Ravana joined Rama righteous Lanka king dharma devotee',
                'sugriva': 'Sugriva Sugreeva monkey king Kishkindha Vali brother Rama ally Hanuman',
                'vali': 'Vali Bali monkey king Kishkindha powerful Sugriva brother killed by Rama',
            }
            
            expansion = expansions.get(entity.lower(), '')
            if expansion:
                return f"{query} {expansion}"
    
    return query


def _normalize_query_for_retrieval(query: str) -> str:
    # First expand simple queries
    query = _expand_simple_query(query)
    
    q = " ".join(query.strip().split())
    q_lower = q.lower()

    # If any configured entity key appears in the query, expand it with variants.
    for key, variants in _ENTITY_SYNONYMS.items():
        if not key or key not in q_lower:
            continue
        extra = " ".join(v for v in variants if v and v not in q_lower)
        if extra:
            return f"{q} {extra}"

    return q


def _lexical_entity_boost(query: str, text: str) -> float:
    """Return a small additive boost if configured entity tokens appear in the chunk text."""
    q = query.lower()
    t = (text or "").lower()

    boost = 0.0
    for key, variants in _ENTITY_SYNONYMS.items():
        if key and key in q:
            # If any variant appears in the text, boost.
            if any(v and v in t for v in variants):
                boost += _ENTITY_BOOST_WEIGHT

    return boost


def _detect_epic_bias(query: str, file_filter: Optional[str] = None) -> Optional[str]:
    """Infer an intended epic from the query/filter.

    Returns: "ramayana", "mahabharata", or None.
    """
    q = (query or "").lower()

    # If user explicitly selected a file filter, treat it as a strong hint.
    ff = (file_filter or "").lower().strip()
    if ff and ff != "all":
        if "ramayana" in ff or "ramayan" in ff or "valmiki" in ff:
            return "ramayana"
        if "mahabharata" in ff or "mahabharat" in ff:
            return "mahabharata"

    # Query cues (entity + explicit epic terms)
    ramayana_cues = [
        "ramayana", "ramayan", "valmiki",
        "rama", "sita", "hanuman", "ravana", "lanka", "ayodhya",
        "lakshmana", "bharata", "shatrughna", "dasharatha", "janaka",
        "meghanada", "meghnath", "indrajit", "vibhishana", "kumbhakarna",
        "sugreeva", "sugriva", "kishkindha", "vali", "bali",
    ]
    mahabharata_cues = [
        "mahabharata", "mahabharat",
        "pandava", "kaurava", "kurukshetra",
        "arjuna", "krishna", "yudhishthira", "bhima", "draupadi",
        "duryodhana", "karna", "bhishma", "drona", "ashwatthama",
        "hastinapura",
    ]

    ramayana_hits = sum(1 for c in ramayana_cues if c in q)
    mahabharata_hits = sum(1 for c in mahabharata_cues if c in q)

    if ramayana_hits == 0 and mahabharata_hits == 0:
        return None
    if ramayana_hits >= mahabharata_hits:
        return "ramayana"
    return "mahabharata"


# --- Epic hard filter helpers ---

def _is_cross_epic_query(query: str) -> bool:
    q = (query or "").lower()
    return (
        "compare" in q
        or "difference" in q
        or "both" in q
        or ("ramayana" in q and "mahabharata" in q)
    )


def _detect_epic_bias_with_confidence(query: str, file_filter: Optional[str] = None) -> Dict[str, Any]:
    """Infer intended epic with a lightweight confidence signal."""
    q = (query or "").lower()

    ff = (file_filter or "").lower().strip()
    if ff and ff != "all":
        if "ramayana" in ff or "ramayan" in ff or "valmiki" in ff:
            return {
                "intended_epic": "ramayana",
                "ramayana_hits": None,
                "mahabharata_hits": None,
                "margin": None,
                "source": "file_filter",
            }
        if "mahabharata" in ff or "mahabharat" in ff:
            return {
                "intended_epic": "mahabharata",
                "ramayana_hits": None,
                "mahabharata_hits": None,
                "margin": None,
                "source": "file_filter",
            }

    ramayana_cues = [
        "ramayana", "ramayan", "valmiki",
        "rama", "sita", "hanuman", "ravana", "lanka", "ayodhya",
        "lakshmana", "bharata", "shatrughna", "dasharatha", "janaka",
        "meghanada", "meghnath", "indrajit", "vibhishana", "kumbhakarna",
        "sugreeva", "sugriva", "kishkindha", "vali", "bali",
    ]
    mahabharata_cues = [
        "mahabharata", "mahabharat",
        "pandava", "kaurava", "kurukshetra",
        "arjuna", "krishna", "yudhishthira", "bhima", "draupadi",
        "duryodhana", "karna", "bhishma", "drona", "ashwatthama",
        "hastinapura",
    ]

    ramayana_hits = sum(1 for c in ramayana_cues if c in q)
    mahabharata_hits = sum(1 for c in mahabharata_cues if c in q)

    intended = None
    if ramayana_hits == 0 and mahabharata_hits == 0:
        intended = None
    elif ramayana_hits >= mahabharata_hits:
        intended = "ramayana"
    else:
        intended = "mahabharata"

    return {
        "intended_epic": intended,
        "ramayana_hits": ramayana_hits,
        "mahabharata_hits": mahabharata_hits,
        "margin": abs(ramayana_hits - mahabharata_hits),
        "source": "query" if intended else None,
    }


def _should_apply_epic_hard_filter(query: str, file_filter: Optional[str]) -> Dict[str, Any]:
    """Decide whether epic hard filtering should run for this query."""
    if not _USE_EPIC_HARD_FILTER:
        return {"enabled": False, "reason": "disabled"}

    if _is_cross_epic_query(query):
        return {"enabled": False, "reason": "cross_epic_query"}

    info = _detect_epic_bias_with_confidence(query, file_filter)
    intended = info.get("intended_epic")
    if not intended:
        return {"enabled": False, "reason": "no_intended_epic", **info}

    if info.get("source") == "file_filter":
        return {"enabled": True, "reason": "file_filter", **info}

    margin = info.get("margin")
    if isinstance(margin, int) and margin >= _EPIC_HARD_FILTER_MARGIN:
        return {"enabled": True, "reason": f"margin>={_EPIC_HARD_FILTER_MARGIN}", **info}

    return {"enabled": False, "reason": "low_confidence", **info}


def _infer_doc_epic(file_name: str) -> Optional[str]:
    """Heuristic: infer epic from filename."""
    f = (file_name or "").lower()
    if not f:
        return None
    if "ramayana" in f or "ramayan" in f or "valmiki" in f:
        return "ramayana"
    if "mahabharata" in f or "mahabharat" in f:
        return "mahabharata"
    return None


def _epic_bias_adjustment(
    base_score: float,
    query: str,
    file_name: str,
    intended_epic: Optional[str],
) -> float:
    """Apply a small boost/penalty based on epic match.

    This is deliberately soft to avoid breaking cross-epic comparison questions.
    """
    if not intended_epic:
        return base_score

    doc_epic = _infer_doc_epic(file_name)
    if not doc_epic:
        return base_score

    if doc_epic == intended_epic:
        return base_score + _EPIC_BOOST_WEIGHT

    # If query clearly asks for cross-epic comparison, avoid penalizing.
    q = (query or "").lower()
    if "compare" in q or "difference" in q or "both" in q or ("ramayana" in q and "mahabharata" in q):
        return base_score

    return max(0.0, base_score - _EPIC_MISMATCH_PENALTY)


# --- Source Quality Filtering (configurable) ---
# Configure via .env:
#   USE_QUALITY_FILTERS=true|false
#   SOURCE_WEIGHTS_JSON={"dictallcheck.pdf": 0.5, "reference.pdf": 0.3}
#   QUALITY_NON_ALPHA_THRESHOLD=0.4  (chunks with >40% non-alphanumeric get penalized)
#   QUALITY_REPETITION_THRESHOLD=0.3 (chunks with >30% repeated tokens get penalized)
#   QUALITY_SHORT_TOKEN_THRESHOLD=0.5 (chunks with >50% very short tokens get penalized)
#   MIN_CHUNK_LENGTH=50 (minimum characters for a chunk to be considered)

_USE_QUALITY_FILTERS = os.getenv("USE_QUALITY_FILTERS", "true").lower() == "true"
_QUALITY_PENALTY_WEIGHT = float(os.getenv("QUALITY_PENALTY_WEIGHT", "0.15") or 0.15)
_MIN_CHUNK_LENGTH = int(os.getenv("MIN_CHUNK_LENGTH", "50") or 50)
_MIN_ALPHA_RATIO = float(os.getenv("MIN_ALPHA_RATIO", "0.3") or 0.3)


def _load_source_weights() -> Dict[str, float]:
    """Load per-file weight multipliers from SOURCE_WEIGHTS_JSON."""
    raw = os.getenv("SOURCE_WEIGHTS_JSON", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        # Validate: keys are strings, values are floats between 0 and 2
        cleaned = {}
        for k, v in data.items():
            if isinstance(k, str) and isinstance(v, (int, float)):
                weight = float(v)
                if 0.0 <= weight <= 2.0:
                    cleaned[k.strip()] = weight
        return cleaned
    except Exception:
        return {}


_SOURCE_WEIGHTS = _load_source_weights()


def _is_chunk_valid(text: str) -> bool:
    """Check if a chunk passes minimum quality requirements.
    
    Returns True if the chunk should be included, False if it should be filtered out.
    This is a HARD filter - chunks failing this are completely excluded.
    """
    if not text or not text.strip():
        return False
    
    # Filter out chunks that are too short
    if len(text.strip()) < _MIN_CHUNK_LENGTH:
        return False
    
    # Filter out chunks that are mostly non-text (OCR garbage)
    alpha_count = sum(1 for c in text if c.isalnum() or c.isspace())
    alpha_ratio = alpha_count / len(text) if len(text) > 0 else 0
    if alpha_ratio < _MIN_ALPHA_RATIO:
        return False
    
    # Filter out chunks that are just control characters or garbled
    printable_count = sum(1 for c in text if c.isprintable() or c in '\n\t')
    printable_ratio = printable_count / len(text) if len(text) > 0 else 0
    if printable_ratio < 0.8:
        return False
    
    # Filter out chunks that are marked as corrupted translations
    text_lower = text.lower()
    corrupted_markers = [
        'corrupted or fragmentary',
        'corrupted or incomplete',
        'corrupted or nonsensical',
        'garbled wording',
        'nonsensical or garble',
        "can't provide a meaningful translation",
        "cannot provide a meaningful translation",
        "i'm sorry, but the passage appears to be corrupted",
        "i'm sorry, but the text appears to be corrupted",
    ]
    for marker in corrupted_markers:
        if marker in text_lower:
            return False
    
    return True


def _compute_quality_score(text: str) -> Dict[str, float]:
    """Compute quality signals for a chunk of text.
    
    Returns dict with:
        - non_alpha_ratio: fraction of non-alphanumeric characters (high = noisy OCR)
        - repetition_ratio: fraction of repeated consecutive tokens (high = garbled text)
        - short_token_ratio: fraction of very short tokens (high = fragmented text)
        - quality_score: overall quality 0-1 (1 = good quality)
    """
    if not text or not text.strip():
        return {
            "non_alpha_ratio": 1.0,
            "repetition_ratio": 1.0,
            "short_token_ratio": 1.0,
            "quality_score": 0.0,
        }
    
    # Non-alphanumeric ratio (OCR noise indicator)
    alpha_count = sum(1 for c in text if c.isalnum() or c.isspace())
    non_alpha_ratio = 1.0 - (alpha_count / len(text)) if len(text) > 0 else 0.0
    
    # Repetition ratio (repeated consecutive tokens = garbled text)
    tokens = text.lower().split()
    if len(tokens) > 1:
        repeated = sum(1 for i in range(1, len(tokens)) if tokens[i] == tokens[i-1])
        repetition_ratio = repeated / (len(tokens) - 1)
    else:
        repetition_ratio = 0.0
    
    # Short token ratio (fragmented OCR produces many 1-2 char tokens)
    if tokens:
        short_tokens = sum(1 for t in tokens if len(t) <= 2)
        short_token_ratio = short_tokens / len(tokens)
    else:
        short_token_ratio = 0.0
    
    # Combine into overall quality score (1 = good, 0 = bad)
    # Penalize high non_alpha, high repetition, high short_token
    quality_score = 1.0
    quality_score -= min(0.4, non_alpha_ratio)  # Max 0.4 penalty for non-alpha
    quality_score -= min(0.3, repetition_ratio)  # Max 0.3 penalty for repetition
    quality_score -= min(0.3, short_token_ratio * 0.5)  # Max 0.15 penalty for short tokens
    quality_score = max(0.0, quality_score)
    
    return {
        "non_alpha_ratio": round(non_alpha_ratio, 3),
        "repetition_ratio": round(repetition_ratio, 3),
        "short_token_ratio": round(short_token_ratio, 3),
        "quality_score": round(quality_score, 3),
    }


def _get_source_weight(file_name: str) -> float:
    """Get the weight multiplier for a source file.
    
    Returns a value between 0 and 2:
        - 1.0 = normal weight (default)
        - <1.0 = down-weighted (e.g., dictionary, reference)
        - >1.0 = up-weighted (e.g., primary source)
    """
    if not file_name:
        return 1.0
    
    # Check for exact match first
    if file_name in _SOURCE_WEIGHTS:
        return _SOURCE_WEIGHTS[file_name]
    
    # Check for partial match (filename contains key)
    for key, weight in _SOURCE_WEIGHTS.items():
        if key.lower() in file_name.lower():
            return weight
    
    return 1.0


def _apply_quality_adjustment(base_score: float, text: str, file_name: str) -> tuple:
    """Apply quality-based score adjustment.
    
    Returns: (adjusted_score, quality_info_dict)
    """
    if not _USE_QUALITY_FILTERS:
        return base_score, {"enabled": False}
    
    # Get source weight
    source_weight = _get_source_weight(file_name)
    
    # Compute quality score
    quality = _compute_quality_score(text)
    quality_score = quality["quality_score"]
    
    # Apply adjustments:
    # 1. Multiply by source weight (allows manual up/down weighting)
    # 2. Apply small penalty for low-quality chunks
    quality_penalty = (1.0 - quality_score) * _QUALITY_PENALTY_WEIGHT
    adjusted_score = base_score * source_weight - quality_penalty
    
    return adjusted_score, {
        "enabled": True,
        "source_weight": source_weight,
        "quality_score": quality_score,
        "quality_penalty": round(quality_penalty, 4),
        "details": quality,
    }

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

# 2026 Upgrade: Evidence Extraction (quote-level grounding)
try:
    from app.evidence_extractor import EvidenceExtractor
    EVIDENCE_EXTRACTION_AVAILABLE = True
except ImportError:
    EVIDENCE_EXTRACTION_AVAILABLE = False
    logger.warning("⚠️  Evidence extraction not available")

# 2026 Upgrade: Diversity Ranking (MMR / de-dup)
try:
    from app.diversity_ranker import DiversityRanker
    DIVERSITY_RANKING_AVAILABLE = True
except ImportError:
    DIVERSITY_RANKING_AVAILABLE = False
    logger.warning("⚠️  Diversity ranking not available")

# 2026 Upgrade: Query Decomposition (multi-hop reasoning)
try:
    from app.query_decomposer import QueryDecomposer
    QUERY_DECOMPOSITION_AVAILABLE = True
except ImportError:
    QUERY_DECOMPOSITION_AVAILABLE = False
    logger.warning("⚠️  Query decomposition not available")

# 2026 Upgrade: Feedback Collection (retrieval quality tracking)
try:
    from app.feedback_collector import FeedbackCollector
    FEEDBACK_COLLECTION_AVAILABLE = True
except ImportError:
    FEEDBACK_COLLECTION_AVAILABLE = False
    logger.warning("⚠️  Feedback collection not available")

# 2026 Upgrade: Response Cache (frequently asked questions)
try:
    from app.response_cache import ResponseCache
    RESPONSE_CACHE_AVAILABLE = True
except ImportError:
    RESPONSE_CACHE_AVAILABLE = False
    logger.warning("⚠️  Response cache not available")

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
        self.use_evidence_extraction = os.getenv("USE_EVIDENCE_EXTRACTION", "true").lower() == "true"
        self.use_diversity_ranking = os.getenv("USE_DIVERSITY_RANKING", "true").lower() == "true"
        self.lancedb_path = os.getenv("LANCEDB_PATH", "./data/index")
        self.table_name = os.getenv("TABLE_NAME", "docs")
        self.top_k_initial = int(os.getenv("TOP_K_INITIAL", "50"))  # Increased from 20 to compensate for quality filtering
        self.top_k_final = int(os.getenv("TOP_K_FINAL", "5"))
        self.rerank_top_n = int(os.getenv("RERANK_TOP_N", str(self.top_k_initial)))  # How many candidates to rerank
        
        # Evidence extraction settings
        self.evidence_max_sentences = int(os.getenv("EVIDENCE_MAX_SENTENCES", "8"))
        self.evidence_similarity_threshold = float(os.getenv("EVIDENCE_SIMILARITY_THRESHOLD", "0.3"))
        
        # Diversity ranking settings (MMR)
        self.mmr_lambda = float(os.getenv("MMR_LAMBDA", "0.7"))  # 0=diversity, 1=relevance
        self.mmr_similarity_threshold = float(os.getenv("MMR_SIMILARITY_THRESHOLD", "0.85"))
        self.max_chunks_per_page = int(os.getenv("MAX_CHUNKS_PER_PAGE", "2"))
        
        # Context length limit (to prevent exceeding LLM context window)
        # Default 6000 chars is safe for most 4K-8K context models
        self.max_context_chars = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))
        
        # Query decomposition settings (multi-hop reasoning)
        self.use_query_decomposition = os.getenv("USE_QUERY_DECOMPOSITION", "true").lower() == "true"
        self.decomposition_use_llm = os.getenv("DECOMPOSITION_USE_LLM", "true").lower() == "true"
        
        # Feedback collection settings
        self.use_feedback_collection = os.getenv("USE_FEEDBACK_COLLECTION", "true").lower() == "true"
        
        # Response cache settings
        self.use_response_cache = os.getenv("USE_RESPONSE_CACHE", "true").lower() == "true"
        
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
        self._initialize_evidence_extraction()
        self._initialize_diversity_ranking()
        self._initialize_query_decomposition()
        self._initialize_feedback_collection()
        self._initialize_response_cache()
        
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
    
    def _initialize_evidence_extraction(self):
        """Initialize evidence extraction for quote-level grounding."""
        self.evidence_extractor = None
        
        if not EVIDENCE_EXTRACTION_AVAILABLE:
            logger.info("⚠️  Evidence extraction not available (missing dependencies)")
            return
        
        if not self.use_evidence_extraction:
            logger.info("ℹ️  Evidence extraction disabled in config")
            return
        
        try:
            logger.info("🔧 Initializing evidence extractor...")
            self.evidence_extractor = EvidenceExtractor(
                self.embedding_model,
                similarity_threshold=self.evidence_similarity_threshold,
            )
            logger.info("✅ Evidence extraction enabled!")
            
        except Exception as e:
            logger.error(f"Error initializing evidence extraction: {e}")
            self.evidence_extractor = None
            logger.warning("⚠️  Evidence extraction unavailable")
    
    def _initialize_diversity_ranking(self):
        """Initialize diversity ranking (MMR) for result diversification."""
        self.diversity_ranker = None
        
        if not DIVERSITY_RANKING_AVAILABLE:
            logger.info("⚠️  Diversity ranking not available (missing dependencies)")
            return
        
        if not self.use_diversity_ranking:
            logger.info("ℹ️  Diversity ranking disabled in config")
            return
        
        try:
            logger.info("🔧 Initializing diversity ranker...")
            self.diversity_ranker = DiversityRanker(
                self.embedding_model,
                lambda_param=self.mmr_lambda,
                similarity_threshold=self.mmr_similarity_threshold,
            )
            logger.info("✅ Diversity ranking (MMR) enabled!")
            
        except Exception as e:
            logger.error(f"Error initializing diversity ranking: {e}")
            self.diversity_ranker = None
            logger.warning("⚠️  Diversity ranking unavailable")
    
    def _initialize_query_decomposition(self):
        """Initialize query decomposition for multi-hop reasoning."""
        self.query_decomposer = None
        
        if not QUERY_DECOMPOSITION_AVAILABLE:
            logger.info("⚠️  Query decomposition not available (missing dependencies)")
            return
        
        if not self.use_query_decomposition:
            logger.info("ℹ️  Query decomposition disabled in config")
            return
        
        try:
            logger.info("🔧 Initializing query decomposer...")
            # Pass LLM client if LLM decomposition is enabled
            llm_client = self.llm_client if self.decomposition_use_llm else None
            self.query_decomposer = QueryDecomposer(llm_client=llm_client)
            logger.info("✅ Query decomposition (multi-hop) enabled!")
            
        except Exception as e:
            logger.error(f"Error initializing query decomposition: {e}")
            self.query_decomposer = None
            logger.warning("⚠️  Query decomposition unavailable")
    
    def _initialize_feedback_collection(self):
        """Initialize feedback collection for retrieval quality tracking."""
        self.feedback_collector = None
        
        if not FEEDBACK_COLLECTION_AVAILABLE:
            logger.info("⚠️  Feedback collection not available (missing dependencies)")
            return
        
        if not self.use_feedback_collection:
            logger.info("ℹ️  Feedback collection disabled in config")
            return
        
        try:
            logger.info("🔧 Initializing feedback collector...")
            self.feedback_collector = FeedbackCollector()
            logger.info("✅ Feedback collection enabled!")
            
        except Exception as e:
            logger.error(f"Error initializing feedback collection: {e}")
            self.feedback_collector = None
            logger.warning("⚠️  Feedback collection unavailable")
    
    def _initialize_response_cache(self):
        """Initialize response cache for frequently asked questions."""
        self.response_cache = None
        
        if not RESPONSE_CACHE_AVAILABLE:
            logger.info("⚠️  Response cache not available (missing dependencies)")
            return
        
        if not self.use_response_cache:
            logger.info("ℹ️  Response cache disabled in config")
            return
        
        try:
            logger.info("🔧 Initializing response cache...")
            self.response_cache = ResponseCache()
            logger.info("✅ Response cache enabled!")
            
        except Exception as e:
            logger.error(f"Error initializing response cache: {e}")
            self.response_cache = None
            logger.warning("⚠️  Response cache unavailable")
    
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

        # Normalize query for retrieval (handles common transliteration variants)
        retrieval_query = _normalize_query_for_retrieval(query)

        # Epic bias: use query + explicit filter to prefer the right epic during retrieval
        intended_epic = _detect_epic_bias(query=retrieval_query, file_filter=file_filter)

        # Smart Query Routing
        routing_decision = None
        if self.query_router and self.use_query_routing:
            routing_decision = self.query_router.route(query, context)
            strategy = routing_decision["strategy"]
            logger.debug(f"Query routed to: {routing_decision['route']} "
                        f"(type: {routing_decision['classification']['type'].value})")

            # Use strategy parameters
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
            # Fallback to vector-only search
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

        # HARD FILTER: Remove chunks that don't meet minimum quality requirements
        # This filters out very short chunks, OCR garbage, control characters, etc.
        valid_results = [doc for doc in initial_results if _is_chunk_valid(doc.get("text", ""))]
        logger.debug(f"Quality filter: {len(initial_results)} -> {len(valid_results)} chunks "
                    f"({len(initial_results) - len(valid_results)} filtered out)")
        
        if not valid_results:
            logger.warning("All retrieved chunks were filtered out by quality filter")
            return []

        # Apply lexical entity boost and quality adjustments before final selection
        boosted = []
        for doc in valid_results:
            distance = doc.get("_distance", 1.0)
            # Convert distance to a similarity-like score (0-1)
            base_sim = max(0.0, 1.0 - (distance / 2.0))
            
            # Add entity boost
            boost = _lexical_entity_boost(retrieval_query, doc.get("text", ""))
            boosted_score = base_sim + boost

            # Epic-aware boost/penalty (soft)
            boosted_score = _epic_bias_adjustment(
                base_score=boosted_score,
                query=retrieval_query,
                file_name=doc.get("file_name", ""),
                intended_epic=intended_epic,
            )

            # Apply quality adjustment (source weight + quality penalty)
            adjusted_score, _ = _apply_quality_adjustment(
                boosted_score,
                doc.get("text", ""),
                doc.get("file_name", "")
            )
            boosted.append((adjusted_score, doc))

        boosted.sort(key=lambda x: x[0], reverse=True)
        boosted_results = [d for _, d in boosted]

        # Optional reranking
        if self.use_reranker and self.reranker and len(boosted_results) > k:
            # Limit reranking to top RERANK_TOP_N candidates for efficiency
            candidates_to_rerank = boosted_results[:self.rerank_top_n]
            query_doc_pairs = [(retrieval_query, doc["text"]) for doc in candidates_to_rerank]
            rerank_scores = self.reranker.predict(query_doc_pairs)

            scored_results = list(zip(candidates_to_rerank, rerank_scores))
            scored_results.sort(key=lambda x: x[1], reverse=True)
            reranked_results = [doc for doc, score in scored_results]
            reranked_scores = [score for doc, score in scored_results]
            logger.debug(f"Reranked {len(candidates_to_rerank)} candidates")
        else:
            reranked_results = boosted_results
            reranked_scores = [s for s, _ in boosted]  # Use boosted scores
        
        # Optional diversity ranking (MMR) to reduce near-duplicates
        if self.diversity_ranker and self.use_diversity_ranking and len(reranked_results) > k:
            # First, apply page-level deduplication
            deduped_results, _ = self.diversity_ranker.deduplicate_by_page(
                reranked_results, max_per_page=self.max_chunks_per_page
            )
            
            # Then apply MMR if we still have more candidates than needed
            if len(deduped_results) > k:
                # Get scores for deduped results
                deduped_scores = []
                for doc in deduped_results:
                    # Find the score for this doc
                    for i, orig_doc in enumerate(reranked_results):
                        if orig_doc.get("id") == doc.get("id") or orig_doc.get("text") == doc.get("text"):
                            deduped_scores.append(reranked_scores[i] if i < len(reranked_scores) else 0.0)
                            break
                    else:
                        deduped_scores.append(0.0)
                
                final_results, mmr_info = self.diversity_ranker.rerank_mmr(
                    query=retrieval_query,
                    candidates=deduped_results,
                    relevance_scores=deduped_scores,
                    k=k,
                    use_embeddings=True,
                )
                logger.debug(f"MMR diversification: {mmr_info.get('duplicates_suppressed', 0)} duplicates suppressed")
            else:
                final_results = deduped_results[:k]
        else:
            final_results = reranked_results[:k]

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

        # Normalize context
        context = context or {}
        deep_search = bool(context.get("deep_search", True))

        # Deep-search tuning knobs (higher recall; can be slower)
        deep_max_sub_queries = int(os.getenv("DEEP_SEARCH_MAX_SUB_QUERIES", "5") or 5)
        deep_docs_per_subquery = int(os.getenv("DEEP_SEARCH_DOCS_PER_SUBQUERY", "6") or 6)
        deep_top_k_multiplier = float(os.getenv("DEEP_SEARCH_TOPK_MULTIPLIER", "2.0") or 2.0)

        # Check cache first
        cached_response = None
        if self.response_cache and self.use_response_cache:
            cached_response = self.response_cache.get(query, file_filter)
            if cached_response:
                cached_response["metadata"]["from_cache"] = True
                cached_response["metadata"]["cache_hit"] = True
                timings["total"] = round(time.time() - start_time, 3)
                cached_response["timings"] = timings
                logger.info(f"Cache hit for query: '{query[:50]}...'")
                return cached_response

        # Get routing decision for this query
        routing_decision = None
        if self.query_router and self.use_query_routing:
            routing_decision = self.query_router.route(query, context)

        # Check if we should decompose this query (for multi-hop reasoning)
        decomposition_result = None
        should_decompose = (
            self.query_decomposer
            and self.use_query_decomposition
            and routing_decision
            and routing_decision.get("strategy", {}).get("decompose_query", False)
        )

        # Also decompose if query router detects multi-hop type
        if (self.query_decomposer
            and self.use_query_decomposition
            and routing_decision
            and routing_decision.get("classification", {})):
            query_type = routing_decision["classification"].get("type")
            # Handle both enum and string comparison
            type_value = query_type.value if hasattr(query_type, 'value') else str(query_type)
            if type_value in ("multi_hop", "comparative", "analytical"):
                should_decompose = True

        # If user explicitly asked for deep search, force decomposition (when available)
        if deep_search and self.query_decomposer and self.use_query_decomposition:
            should_decompose = True

        # Retrieve relevant documents (with optional decomposition)
        search_start = time.time()

        if should_decompose:
            # Decompose and search for each sub-query
            decomposition_result = self.query_decomposer.decompose(query, use_llm=self.decomposition_use_llm)
            sub_queries = decomposition_result.get("sub_queries", [query])

            # Limit sub-queries to prevent excessive retrieval
            max_sub_queries = deep_max_sub_queries if deep_search else 3
            if len(sub_queries) > max_sub_queries:
                logger.debug(f"Limiting sub-queries from {len(sub_queries)} to {max_sub_queries}")
                sub_queries = sub_queries[:max_sub_queries]

            # Search for each sub-query and aggregate results
            # Use fewer docs per sub-query to prevent context overflow
            if deep_search:
                docs_per_subquery = max(3, deep_docs_per_subquery)
            else:
                docs_per_subquery = min(3, self.top_k_final // 2 + 1)

            all_docs = []
            seen_texts = set()

            for sub_q in sub_queries:
                try:
                    sub_docs = await self.search(sub_q, k=docs_per_subquery, file_filter=file_filter, context=context)
                    for doc in sub_docs:
                        text = doc.get("text", "")
                        if text and text not in seen_texts:
                            seen_texts.add(text)
                            doc["_sub_query"] = sub_q  # Track which sub-query found this
                            all_docs.append(doc)
                except Exception as e:
                    logger.warning(f"Error searching sub-query '{sub_q}': {e}")

            # Limit total results and re-rank by relevance to original query
            if all_docs and self.reranker and self.use_reranker:
                query_doc_pairs = [(query, doc["text"]) for doc in all_docs]
                rerank_scores = self.reranker.predict(query_doc_pairs)
                scored = list(zip(all_docs, rerank_scores))
                scored.sort(key=lambda x: x[1], reverse=True)

                if deep_search:
                    k_final = int(max(self.top_k_final, round(self.top_k_final * deep_top_k_multiplier)))
                else:
                    k_final = self.top_k_final

                retrieved_docs = [doc for doc, score in scored[:k_final]]
            else:
                retrieved_docs = all_docs[: self.top_k_final * (3 if deep_search else 2)]

            logger.debug(f"Multi-hop: {len(sub_queries)} sub-queries → {len(retrieved_docs)} unique docs")
        else:
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

        # Compress context if enabled
        compression_stats = None
        if self.context_compressor and self.use_context_compression:
            compress_start = time.time()
            context_parts, compression_stats = self.context_compressor.compress(
                query, context_parts, max_sentences=50
            )
            timings['compression'] = round(time.time() - compress_start, 3)
            logger.debug(f"Context compressed: {compression_stats['compression_ratio']:.1%}")
        
        # Extract evidence sentences for quote-level grounding
        evidence_text = ""
        evidence_stats = None
        if self.evidence_extractor and self.use_evidence_extraction:
            evidence_start = time.time()
            evidence_result = self.evidence_extractor.extract_evidence(
                query=query,
                chunks=retrieved_docs,
                max_sentences_per_chunk=3,
                max_total_sentences=self.evidence_max_sentences,
            )
            evidence_text = self.evidence_extractor.format_evidence_for_prompt(evidence_result)
            evidence_stats = evidence_result.get("summary", {})
            timings['evidence_extraction'] = round(time.time() - evidence_start, 3)
            logger.debug(f"Extracted {evidence_stats.get('sentences_extracted', 0)} evidence sentences")
        
        # Format context with source numbers
        formatted_context = []
        for i, text in enumerate(context_parts, 1):
            formatted_context.append(f"[Source {i}]\n{text}")
                
        context = "\n\n".join(formatted_context)
        
        # Truncate context if it exceeds max length (to prevent LLM context overflow)
        context_truncated = False
        if len(context) > self.max_context_chars:
            logger.warning(f"Context too long ({len(context)} chars), truncating to {self.max_context_chars} chars")
            context = context[:self.max_context_chars]
            # Try to end at a sentence boundary
            last_period = context.rfind('.')
            last_newline = context.rfind('\n')
            cut_point = max(last_period, last_newline)
            if cut_point > self.max_context_chars * 0.8:  # Only use if we don't lose too much
                context = context[:cut_point + 1]
            context += "\n\n[Context truncated due to length...]"
            context_truncated = True
        
        # Prepare prompt for LLM with routing-specific instructions
        if routing_decision:
            custom_instructions = self.query_router.get_response_instructions(
                routing_decision["classification"]
            )
            prompt = self._create_prompt(query, context, custom_instructions, evidence_text)
        else:
            prompt = self._create_prompt(query, context, evidence=evidence_text)
        
        # Get answer from LLM
        llm_start = time.time()
        try:
            response = self.llm_client.chat.completions.create(
                model="local-model",  # LM Studio doesn't require specific model name
                messages=[
                    {"role": "system", "content": """You are a precise research assistant that answers questions ONLY based on the provided context.

CRITICAL RULES:
1. ONLY state facts that are explicitly mentioned in the context
2. DO NOT make inferences or assumptions beyond what's written
3. DO NOT confuse relationships (e.g., wife vs daughter, father vs son)
4. If the context doesn't clearly answer the question, say "The sources don't explicitly state..."
5. Quote directly from sources when possible
6. Be concise and factually accurate"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.05,
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
        
        # Build response
        result = {
            "answer": answer,
            "sources": sources if include_sources else [],
            "metadata": {
                "num_sources": len(retrieved_docs),
                "query": query,
                "context_length": len(context),
                "context_truncated": context_truncated,
                "reranker_used": self.use_reranker and self.reranker is not None,
                "evidence_extracted": evidence_stats.get("sentences_extracted", 0) if evidence_stats else 0,
                "decomposition_used": decomposition_result is not None,
                "sub_queries": decomposition_result.get("sub_queries") if decomposition_result else None,
                "from_cache": False,
                "deep_search": deep_search,  # Reflect deep search status
            },
            "timings": timings
        }
        
        # Cache the response (only cache successful responses)
        if self.response_cache and self.use_response_cache and not answer.startswith("Error"):
            query_type_str = None
            if routing_decision and routing_decision.get("classification"):
                qt = routing_decision["classification"].get("type")
                query_type_str = qt.value if hasattr(qt, 'value') else str(qt)
            
            self.response_cache.set(
                query=query,
                response=result,
                file_filter=file_filter,
                query_type=query_type_str,
            )
        
        return result
        
    def _create_prompt(self, query: str, context: str, custom_instructions: Optional[str] = None, evidence: Optional[str] = None) -> str:
        """
        Create a prompt for the LLM.
        
        Args:
            query: User question
            context: Retrieved context
            custom_instructions: Optional routing-specific instructions
            evidence: Optional extracted evidence sentences for quote-level grounding
            
        Returns:
            Formatted prompt
        """
        instructions = custom_instructions or """Answer the question based on the context below.
- Synthesize information from multiple source passages when relevant
- For character questions, describe who they are, their role, relationships, and significance
- For event questions, explain what happened, who was involved, and why it matters
- Quote or paraphrase specific passages to support your answer
- If the sources don't contain enough information, say what you found and note the limitation
- Be comprehensive but concise."""
        
        # Add evidence section if provided
        evidence_section = ""
        if evidence:
            evidence_section = f"""
{evidence}

Use the key evidence quotes above to support your answer. Cite them when relevant.
"""
        
        return f"""{instructions}

Context:
{context}
{evidence_section}
Question: {query}

Answer:"""

    async def answer_streaming(
        self,
        query: str,
        include_sources: bool = True,
        file_filter: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Generate a streaming answer using Server-Sent Events (SSE).
        
        Yields JSON events:
            - {"type": "sources", "data": [...]} - Source documents
            - {"type": "token", "data": "..."} - Token from LLM
            - {"type": "done", "data": {...}} - Final metadata
            - {"type": "error", "data": "..."} - Error message
        
        Args:
            query: User question
            include_sources: Whether to include source documents
            file_filter: Optional filename filter
            context: Optional conversation context
        """
        import json
        
        start_time = time.time()
        timings = {}
        
        try:
            # Get routing decision
            routing_decision = None
            if self.query_router and self.use_query_routing:
                routing_decision = self.query_router.route(query, context)
            
            # Retrieve relevant documents
            search_start = time.time()
            retrieved_docs = await self.search(query, file_filter=file_filter, context=context)
            timings['search'] = round(time.time() - search_start, 3)
            
            if not retrieved_docs:
                yield f"data: {json.dumps({'type': 'error', 'data': 'No relevant documents found.'})}\n\n"
                return
            
            # Prepare sources
            sources = []
            context_parts = []
            
            for i, doc in enumerate(retrieved_docs, 1):
                context_parts.append(doc['text'])
                
                if include_sources:
                    distance = doc.get("_distance", 1.0)
                    similarity_score = max(0, 1 - (distance / 2))
                    
                    sources.append({
                        "index": i,
                        "file_name": doc.get("file_name", "Unknown"),
                        "page": doc.get("page_number", "N/A"),
                        "chunk_index": doc.get("chunk_index"),
                        "text": doc["text"],
                        "score": similarity_score
                    })
            
            # Send sources immediately
            yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
            
            # Compress context if enabled
            if self.context_compressor and self.use_context_compression:
                context_parts, _ = self.context_compressor.compress(query, context_parts, max_sentences=50)
            
            # Format context
            formatted_context = []
            for i, text in enumerate(context_parts, 1):
                formatted_context.append(f"[Source {i}]\n{text}")
            
            context_text = "\n\n".join(formatted_context)
            
            # Truncate if needed
            if len(context_text) > self.max_context_chars:
                context_text = context_text[:self.max_context_chars]
                last_period = context_text.rfind('.')
                if last_period > self.max_context_chars * 0.8:
                    context_text = context_text[:last_period + 1]
                context_text += "\n\n[Context truncated...]"
            
            # Create prompt
            if routing_decision:
                custom_instructions = self.query_router.get_response_instructions(
                    routing_decision["classification"]
                )
                prompt = self._create_prompt(query, context_text, custom_instructions)
            else:
                prompt = self._create_prompt(query, context_text)
            
            # Stream from LLM
            llm_start = time.time()
            full_answer = ""
            
            try:
                stream = self.llm_client.chat.completions.create(
                    model="local-model",
                    messages=[
                        {"role": "system", "content": """You are a precise research assistant that answers questions ONLY based on the provided context.

CRITICAL RULES:
1. ONLY state facts that are explicitly mentioned in the context
2. DO NOT make inferences or assumptions beyond what's written
3. If the context doesn't clearly answer the question, say "The sources don't explicitly state..."
4. Quote directly from sources when possible
5. Be concise and factually accurate"""},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.05,
                    max_tokens=1000,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_answer += token
                        yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"
                
            except Exception as e:
                logger.error(f"LLM streaming error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
                return
            
            timings['llm'] = round(time.time() - llm_start, 3)
            timings['total'] = round(time.time() - start_time, 3)
            
            # Send completion event with metadata
            yield f"data: {json.dumps({'type': 'done', 'data': {'answer': full_answer, 'timings': timings, 'num_sources': len(sources)}})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        status = {
            "embedding_model": self.embedding_model_name,
            "reranker_enabled": self.use_reranker,
            "reranker_model": self.reranker_model_name if self.use_reranker else None,
            "rerank_top_n": self.rerank_top_n if self.use_reranker else None,
            "database_connected": self.table is not None,
            "lm_studio_url": self.lm_studio_url,
            "hybrid_search_enabled": self.use_hybrid_search and self.hybrid_searcher is not None,
            "bm25_available": self.bm25_index is not None and self.bm25_index.is_built() if self.bm25_index else False,
            "query_routing_enabled": self.use_query_routing and self.query_router is not None,
            "context_compression_enabled": self.use_context_compression and self.context_compressor is not None,
            "evidence_extraction_enabled": self.use_evidence_extraction and self.evidence_extractor is not None,
            "diversity_ranking_enabled": self.use_diversity_ranking and self.diversity_ranker is not None,
            "query_decomposition_enabled": self.use_query_decomposition and self.query_decomposer is not None,
            "feedback_collection_enabled": self.use_feedback_collection and self.feedback_collector is not None,
            "response_cache_enabled": self.use_response_cache and self.response_cache is not None,
            "quality_filters_enabled": _USE_QUALITY_FILTERS,
            "source_weights": _SOURCE_WEIGHTS if _USE_QUALITY_FILTERS else None,
        }
        
        # Add routing stats if available
        if self.query_router:
            status["routing_stats"] = self.query_router.get_stats()
        
        # Add compression stats if available
        if self.context_compressor:
            status["compression_stats"] = self.context_compressor.get_stats()
        
        # Add evidence extraction stats if available
        if self.evidence_extractor:
            status["evidence_stats"] = self.evidence_extractor.get_stats()
        
        # Add diversity ranking stats if available
        if self.diversity_ranker:
            status["diversity_stats"] = self.diversity_ranker.get_stats()
        
        # Add query decomposition stats if available
        if self.query_decomposer:
            status["decomposition_stats"] = self.query_decomposer.get_stats()
        
        # Add feedback collection stats if available
        if self.feedback_collector:
            status["feedback_stats"] = self.feedback_collector.get_stats()
        
        # Add response cache stats if available
        if self.response_cache:
            status["cache_stats"] = self.response_cache.get_stats()
        
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
    
    def record_feedback(
        self,
        query: str,
        answer: str,
        rating: int,
        sources: Optional[List[Dict[str, Any]]] = None,
        comment: Optional[str] = None,
        query_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record user feedback on an answer.
        
        Args:
            query: Original query
            answer: Generated answer
            rating: User rating 1-5
            sources: Sources used in answer
            comment: Optional user comment
            query_type: Query type classification
            metadata: Additional metadata
            
        Returns:
            Feedback record
        """
        if not self.feedback_collector:
            return {"error": "Feedback collection not enabled"}
        
        return self.feedback_collector.record_feedback(
            query=query,
            answer=answer,
            rating=rating,
            sources=sources,
            comment=comment,
            query_type=query_type,
            metadata=metadata,
        )
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        if not self.feedback_collector:
            return {"error": "Feedback collection not enabled"}
        
        return self.feedback_collector.get_stats()
    
    def get_low_rated_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get queries with low ratings for review."""
        if not self.feedback_collector:
            return []
        
        return self.feedback_collector.get_low_rated_queries(limit)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.response_cache:
            return {"error": "Response cache not enabled"}
        
        return self.response_cache.get_stats()
    
    def clear_cache(self, query: Optional[str] = None):
        """Clear cache entries."""
        if not self.response_cache:
            return {"error": "Response cache not enabled"}
        
        self.response_cache.invalidate(query)
        return {"status": "success"}
    
    async def debug_retrieval(
        self,
        query: str,
        k: int = 10,
        file_filter: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        include_reranker: bool = True,
    ) -> Dict[str, Any]:
        """Run retrieval and return a score breakdown for observability/debugging.
        
        Args:
            query: Search query
            k: Number of results to return
            file_filter: Optional filename filter
            context: Optional conversation context
            include_reranker: Whether to compute and include reranker scores (if enabled)
        """
        self.check_and_reload()

        if not self.table:
            raise Exception("Vector store not initialized. Please run ingest.py first.")

        retrieval_query = _normalize_query_for_retrieval(query)

        # Epic hard-filter decision (debug visibility)
        epic_filter_decision = _should_apply_epic_hard_filter(query, file_filter)
        intended_epic = None
        if epic_filter_decision.get("enabled"):
            intended_epic = epic_filter_decision.get("intended_epic")
        else:
            intended_epic = _detect_epic_bias(query, file_filter)

        # Mirror routing-driven top-k behavior (but default to debug-friendly k)
        routing_decision = None
        if self.query_router and self.use_query_routing:
            routing_decision = self.query_router.route(query, context)

        initial_k = max(self.top_k_initial, k * 4)

        bm25_map: Dict[str, Dict[str, Any]] = {}
        vector_map: Dict[str, Dict[str, Any]] = {}
        fused_rows: List[Dict[str, Any]] = []

        # --- BM25 ---
        if self.bm25_index and self.bm25_index.is_built() and self.use_hybrid_search:
            bm25_results = self.bm25_index.search(retrieval_query, k=initial_k)
            # Apply epic hard filter if enabled (filter by inferred epic from filename)
            if epic_filter_decision.get("enabled") and intended_epic:
                bm25_results = [r for r in bm25_results if _infer_doc_epic(r.get("file_name", "")) == intended_epic]
            for r in bm25_results:
                doc_id = r.get("doc_id")
                if doc_id:
                    bm25_map[str(doc_id)] = r

        # --- Vector ---
        query_embedding = self.embedding_model.encode(retrieval_query)
        vec_q = self.table.search(query_embedding).limit(initial_k)
        if file_filter and file_filter != "all":
            vec_q = vec_q.where(f"file_name LIKE '%{file_filter}%'")
        vector_results = vec_q.to_list()
        # Apply epic hard filter if enabled
        if epic_filter_decision.get("enabled") and intended_epic:
            vector_results = [r for r in vector_results if _infer_doc_epic(r.get("file_name", "")) == intended_epic]
        for r in vector_results:
            doc_id = r.get("id")
            if doc_id is None:
                continue
            vector_map[str(doc_id)] = r

        # --- Fusion (if hybrid available), else vector-only ---
        if self.hybrid_searcher and self.use_hybrid_search:
            fused_rows = self.hybrid_searcher.search(
                query=retrieval_query,
                k=initial_k,  # Get more candidates for reranking
                file_filter=file_filter,
            )
            # Apply epic hard filter if enabled
            if epic_filter_decision.get("enabled") and intended_epic:
                fused_rows = [r for r in fused_rows if _infer_doc_epic(r.get("file_name", "")) == intended_epic]
        else:
            fused_rows = vector_results[:initial_k]

        # --- Compute reranker scores if enabled and requested ---
        reranker_map: Dict[str, float] = {}
        reranker_used = False
        if include_reranker and self.use_reranker and self.reranker and len(fused_rows) > 0:
            try:
                candidates_to_rerank = fused_rows[:self.rerank_top_n]
                texts = []
                doc_ids = []
                for row in candidates_to_rerank:
                    doc_id = str(row.get("id") or row.get("doc_id") or "")
                    vec_row = vector_map.get(doc_id) or row
                    text = (vec_row or {}).get("text", "")
                    if doc_id and text:
                        doc_ids.append(doc_id)
                        texts.append(text)
                
                if texts:
                    query_doc_pairs = [(retrieval_query, text) for text in texts]
                    rerank_scores = self.reranker.predict(query_doc_pairs)
                    for doc_id, score in zip(doc_ids, rerank_scores):
                        reranker_map[doc_id] = float(score)
                    reranker_used = True
            except Exception as e:
                logger.warning(f"Error computing reranker scores: {e}")

        # --- Sort by reranker score if available, otherwise by fused score ---
        if reranker_used and reranker_map:
            # Re-sort fused_rows by reranker score
            def get_rerank_score(row):
                doc_id = str(row.get("id") or row.get("doc_id") or "")
                return reranker_map.get(doc_id, -999)
            
            fused_rows = sorted(fused_rows, key=get_rerank_score, reverse=True)

        # --- Build breakdown rows ---
        candidates: List[Dict[str, Any]] = []
        for rank, row in enumerate(fused_rows[:k], start=1):
            doc_id = str(row.get("id") or row.get("doc_id") or "")
            vec_row = vector_map.get(doc_id) or row
            bm25_row = bm25_map.get(doc_id)

            distance = (vec_row or {}).get("_distance", None)
            vector_score = None
            if distance is not None:
                vector_score = max(0.0, 1.0 - (float(distance) / 2.0))

            bm25_score = float(bm25_row.get("bm25_score")) if bm25_row and bm25_row.get("bm25_score") is not None else None

            entity_boost = _lexical_entity_boost(retrieval_query, (vec_row or {}).get("text", ""))

            fused_score = row.get("hybrid_score")
            if fused_score is None:
                # vector-only path: treat boosted vector similarity as fused
                fused_score = (vector_score if vector_score is not None else 0.0) + entity_boost

            # Get reranker score for this candidate
            reranker_score = reranker_map.get(doc_id) if reranker_used else None

            # Compute quality adjustment for this candidate
            text = (vec_row or {}).get("text", "")
            file_name = (vec_row or {}).get("file_name", "")
            _, quality_info = _apply_quality_adjustment(fused_score, text, file_name)

            candidates.append(
                {
                    "rank": rank,
                    "id": doc_id or None,
                    "scores": {
                        "vector": vector_score,
                        "bm25": bm25_score,
                        "fused": float(fused_score) if fused_score is not None else None,
                        "entity_boost": float(entity_boost),
                        "reranker": reranker_score,
                    },
                    "quality": quality_info,
                    "fusion": {
                        "method": row.get("fusion_method") if isinstance(row, dict) else None,
                        "bm25_rank": row.get("bm25_rank") if isinstance(row, dict) else None,
                        "vector_rank": row.get("vector_rank") if isinstance(row, dict) else None,
                    },
                    "metadata": {
                        "file_name": file_name,
                        "page": (vec_row or {}).get("page_number"),
                        "chunk_index": (vec_row or {}).get("chunk_index"),
                                               "text_preview": (text[:200] + "...") if text else None,
                    },
                }
            )

        # Extract evidence if enabled
        evidence_result = None
        if self.evidence_extractor and self.use_evidence_extraction:
            # Build chunk list from candidates for evidence extraction
            chunks_for_evidence = []
            for c in candidates:
                doc_id = c.get("id", "")
                vec_row = vector_map.get(doc_id) or {}
                chunks_for_evidence.append({
                    "text": vec_row.get("text", ""),
                    "file_name": c["metadata"]["file_name"],
                    "page_number": c["metadata"]["page"],
                })
            
            evidence_result = self.evidence_extractor.extract_evidence(
                query=query,
                chunks=chunks_for_evidence,
                max_sentences_per_chunk=3,
                max_total_sentences=self.evidence_max_sentences,
            )

        return {
            "query": query,
            "retrieval_query": retrieval_query,
            "k": k,
            "file_filter": file_filter or "all",
            "routing": routing_decision,
            "epic_filter": {
                "enabled": bool(epic_filter_decision.get("enabled")),
                "intended_epic": intended_epic,
                "decision": epic_filter_decision,
                "use_epic_hard_filter": _USE_EPIC_HARD_FILTER,
                "hard_filter_margin": _EPIC_HARD_FILTER_MARGIN,
            },
            "reranker": {
                "enabled": self.use_reranker,
                "used_in_debug": reranker_used,
                "model": self.reranker_model_name if self.use_reranker else None,
                "rerank_top_n": self.rerank_top_n,
            },
            "quality_filters": {
                "enabled": _USE_QUALITY_FILTERS,
                "source_weights": _SOURCE_WEIGHTS,
                "penalty_weight": _QUALITY_PENALTY_WEIGHT,
            },
            "evidence_extraction": {
                "enabled": self.use_evidence_extraction and self.evidence_extractor is not None,
                "result": evidence_result,
            },
            "diversity_ranking": {
                "enabled": self.use_diversity_ranking and self.diversity_ranker is not None,
                "mmr_lambda": self.mmr_lambda,
                "max_chunks_per_page": self.max_chunks_per_page,
            },
            "candidates": candidates,
            "notes": {
                "vector_score": "Derived from LanceDB _distance as max(0, 1 - distance/2).",
                "entity_boost": f"Additive boost configured by ENTITY_BOOST_WEIGHT (currently {_ENTITY_BOOST_WEIGHT}).",
                "reranker_score": "Cross-encoder score (higher = more relevant). Results sorted by reranker if enabled.",
                "quality_score": "Overall chunk quality 0-1 (1=good). Factors: non-alpha ratio, repetition, short tokens.",
                "source_weight": "Per-file weight multiplier from SOURCE_WEIGHTS_JSON (1.0=normal, <1=down-weighted).",
                "evidence": "Most relevant sentences extracted from chunks for quote-level grounding.",
                "diversity": "MMR balances relevance and diversity. Page dedup limits chunks per (file, page) combo.",
            },
        }
