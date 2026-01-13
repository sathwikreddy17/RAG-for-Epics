"""
Spelling Suggester for RAG System.
Handles name/entity variations and suggests corrections for misspelled queries.

Features:
1. Extracts unique entity names from indexed documents
2. Provides fuzzy matching for misspelled queries
3. Supports autocomplete suggestions while typing
4. Handles transliteration variations (e.g., Meghanada, Meganath, Meghnath)
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Common Indian name transliteration patterns
TRANSLITERATION_PATTERNS = [
    # Vowel variations
    (r'aa', 'a'), (r'a', 'aa'),
    (r'ee', 'i'), (r'i', 'ee'),
    (r'oo', 'u'), (r'u', 'oo'),
    # Consonant variations  
    (r'th', 't'), (r't', 'th'),
    (r'dh', 'd'), (r'd', 'dh'),
    (r'bh', 'b'), (r'b', 'bh'),
    (r'ph', 'p'), (r'p', 'ph'),
    (r'kh', 'k'), (r'k', 'kh'),
    (r'gh', 'g'), (r'g', 'gh'),
    (r'ch', 'c'), (r'c', 'ch'),
    (r'sh', 's'), (r's', 'sh'),
    # Ending variations
    (r'a$', ''), (r'$', 'a'),
    (r'am$', 'a'), (r'a$', 'am'),
    # Common substitutions
    (r'v', 'w'), (r'w', 'v'),
    (r'y', 'j'), (r'j', 'y'),
]


def normalize_for_comparison(text: str) -> str:
    """Normalize text for fuzzy comparison."""
    # Lowercase and remove special chars
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]', '', text)
    return text


def get_simplified_key(word: str) -> str:
    """Generate a simplified key that handles common Indian name transliterations.
    
    This handles variations like:
    - meganath -> megn
    - meghanada -> megn
    - Meghnath -> megn
    """
    word = word.lower()
    # Remove double letters
    word = re.sub(r'(.)\1+', r'\1', word)
    
    # Normalize aspirated consonants (th, dh, bh, etc. -> t, d, b)
    replacements = [
        ('ph', 'p'), ('bh', 'b'), ('th', 't'), ('dh', 'd'),
        ('kh', 'k'), ('gh', 'g'), ('ch', 'c'), ('sh', 's'),
        # Vowel normalizations
        ('aa', 'a'), ('ee', 'i'), ('ii', 'i'), ('oo', 'u'), ('uu', 'u'),
        ('ai', 'e'), ('ei', 'e'), ('ou', 'o'), ('au', 'o'),
    ]
    
    for pattern, replacement in replacements:
        word = word.replace(pattern, replacement)
    
    # Remove common endings to get the root
    # This handles: meghanada, meganath, meghnath -> megn
    ending_patterns = [
        r'nada$', r'nath$', r'nad$', r'nat$', r'na$',  # Name endings
        r'ada$', r'atha$', r'ana$', r'ika$', r'ita$',  # Other endings
    ]
    
    for pattern in ending_patterns:
        word = re.sub(pattern, 'n', word)
    
    # Remove trailing vowels
    word = re.sub(r'[aeiou]+$', '', word)
    
    return word


def get_phonetic_key(word: str) -> str:
    """Generate a simplified phonetic key for matching similar-sounding names."""
    word = word.lower()
    # Remove double letters
    word = re.sub(r'(.)\1+', r'\1', word)
    # Normalize common variations
    replacements = [
        (r'ph', 'f'),
        (r'gh', 'g'),
        (r'kh', 'k'),
        (r'th', 't'),
        (r'dh', 'd'),
        (r'bh', 'b'),
        (r'ch', 'c'),
        (r'sh', 's'),
        (r'aa', 'a'),
        (r'ee', 'i'),
        (r'oo', 'u'),
        (r'[aeiou]', ''),  # Remove vowels except first
    ]
    for pattern, replacement in replacements:
        if pattern == r'[aeiou]':
            # Keep first vowel
            if word:
                first_vowel_match = re.search(r'[aeiou]', word)
                if first_vowel_match:
                    idx = first_vowel_match.start()
                    word = word[:idx+1] + re.sub(pattern, replacement, word[idx+1:])
        else:
            word = re.sub(pattern, replacement, word)
    return word


class SpellingSuggester:
    """
    Suggests correct spellings for entity names based on indexed documents.
    """
    
    def __init__(self, index_path: str = "./data/spelling_index"):
        """
        Initialize the spelling suggester.
        
        Args:
            index_path: Path to store the spelling index
        """
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Entity storage
        self.entities: Dict[str, int] = {}  # entity -> frequency count
        self.normalized_map: Dict[str, Set[str]] = {}  # normalized -> {original variants}
        self.phonetic_map: Dict[str, Set[str]] = {}  # phonetic_key -> {original names}
        self.simplified_map: Dict[str, Set[str]] = {}  # simplified_key -> {original names}
        
        # Load existing index if available
        self._load_index()
        
        logger.info(f"SpellingSuggester initialized with {len(self.entities)} entities")
    
    def _load_index(self):
        """Load the spelling index from disk."""
        index_file = self.index_path / "entities.json"
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entities = data.get("entities", {})
                    # Rebuild maps
                    self._rebuild_maps()
                    logger.info(f"Loaded {len(self.entities)} entities from index")
            except Exception as e:
                logger.error(f"Error loading spelling index: {e}")
    
    def _save_index(self):
        """Save the spelling index to disk."""
        index_file = self.index_path / "entities.json"
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "entities": self.entities,
                    "version": "1.0"
                }, f, indent=2)
            logger.info(f"Saved {len(self.entities)} entities to index")
        except Exception as e:
            logger.error(f"Error saving spelling index: {e}")
    
    def _rebuild_maps(self):
        """Rebuild normalized and phonetic maps from entities."""
        self.normalized_map = {}
        self.phonetic_map = {}
        self.simplified_map = {}  # New: simplified key for transliteration matching
        
        for entity in self.entities:
            # Normalized map
            normalized = normalize_for_comparison(entity)
            if normalized not in self.normalized_map:
                self.normalized_map[normalized] = set()
            self.normalized_map[normalized].add(entity)
            
            # Phonetic map
            phonetic = get_phonetic_key(entity)
            if phonetic not in self.phonetic_map:
                self.phonetic_map[phonetic] = set()
            self.phonetic_map[phonetic].add(entity)
            
            # Simplified map (for Indian name transliterations)
            simplified = get_simplified_key(entity)
            if simplified not in self.simplified_map:
                self.simplified_map[simplified] = set()
            self.simplified_map[simplified].add(entity)
    
    def extract_entities_from_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """
        Extract potential entity names from document chunks.
        
        Args:
            chunks: List of document chunks with 'text' field
            
        Returns:
            Number of new entities added
        """
        initial_count = len(self.entities)
        
        # Pattern to find capitalized words (potential names)
        # Matches: Rama, Sita, Ravana, Meghanada, etc.
        name_pattern = re.compile(r'\b([A-Z][a-z]{2,}(?:[a-z]*)?)\b')
        
        # Words to exclude (common English words that are capitalized)
        exclude_words = {
            'The', 'This', 'That', 'These', 'Those', 'There', 'Then', 'Thus',
            'When', 'Where', 'What', 'Which', 'Who', 'Whom', 'Whose', 'Why', 'How',
            'And', 'But', 'For', 'Nor', 'Yet', 'Also', 'Both', 'Each', 'Every',
            'After', 'Before', 'During', 'About', 'Above', 'Below', 'Between',
            'Chapter', 'Book', 'Part', 'Section', 'Page', 'Volume',
            'King', 'Queen', 'Prince', 'Princess', 'Lord', 'Lady', 'God', 'Goddess',
            'Great', 'Noble', 'Holy', 'Sacred', 'Divine', 'Royal', 'Ancient',
            'One', 'Two', 'Three', 'Four', 'Five', 'First', 'Second', 'Third',
            'Having', 'Being', 'Going', 'Coming', 'Taking', 'Making', 'Seeing',
            'Said', 'Spoke', 'Replied', 'Asked', 'Answered', 'Told',
            'May', 'Shall', 'Will', 'Would', 'Could', 'Should', 'Must',
            'His', 'Her', 'Its', 'Their', 'Your', 'Our',
            'From', 'Into', 'Upon', 'With', 'Without', 'Within',
        }
        
        for chunk in chunks:
            text = chunk.get('text', '')
            matches = name_pattern.findall(text)
            
            for match in matches:
                if match not in exclude_words and len(match) >= 3:
                    # Count frequency
                    if match in self.entities:
                        self.entities[match] += 1
                    else:
                        self.entities[match] = 1
        
        # Filter out rare occurrences (likely OCR errors)
        min_frequency = 2
        self.entities = {k: v for k, v in self.entities.items() if v >= min_frequency}
        
        # Rebuild maps
        self._rebuild_maps()
        
        # Save updated index
        self._save_index()
        
        new_count = len(self.entities) - initial_count
        logger.info(f"Extracted {new_count} new entities (total: {len(self.entities)})")
        return new_count
    
    def build_from_lancedb(self, table) -> int:
        """
        Build spelling index from LanceDB table.
        
        Args:
            table: LanceDB table object
            
        Returns:
            Number of entities indexed
        """
        try:
            # Get all chunks
            chunks = table.to_pandas().to_dict('records')
            return self.extract_entities_from_chunks(chunks)
        except Exception as e:
            logger.error(f"Error building from LanceDB: {e}")
            return 0
    
    def get_suggestions(self, query: str, max_suggestions: int = 5) -> List[Dict[str, Any]]:
        """
        Get spelling suggestions for a query.
        
        Args:
            query: User's query text
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of suggestions with scores
        """
        if not self.entities:
            return []
        
        # Extract potential entity words from query
        words = re.findall(r'\b([A-Za-z]{3,})\b', query)
        
        all_suggestions = []
        
        for word in words:
            word_lower = word.lower()
            normalized = normalize_for_comparison(word)
            phonetic = get_phonetic_key(word)
            simplified = get_simplified_key(word)
            
            # Check if exact match exists
            if word in self.entities or word.capitalize() in self.entities:
                continue  # No suggestion needed for this word
            
            word_suggestions = []
            
            # 1. Check normalized matches (handles case variations)
            if normalized in self.normalized_map:
                for variant in self.normalized_map[normalized]:
                    word_suggestions.append({
                        "original": word,
                        "suggestion": variant,
                        "score": 0.95,
                        "match_type": "normalized",
                        "frequency": self.entities.get(variant, 0)
                    })
            
            # 2. Check simplified matches (handles Indian name transliterations)
            if simplified in self.simplified_map:
                for variant in self.simplified_map[simplified]:
                    if variant.lower() != word_lower:
                        word_suggestions.append({
                            "original": word,
                            "suggestion": variant,
                            "score": 0.90,  # High score for transliteration matches
                            "match_type": "transliteration",
                            "frequency": self.entities.get(variant, 0)
                        })
            
            # 3. Check phonetic matches (handles transliteration)
            if phonetic in self.phonetic_map:
                for variant in self.phonetic_map[phonetic]:
                    if variant.lower() != word_lower:
                        word_suggestions.append({
                            "original": word,
                            "suggestion": variant,
                            "score": 0.85,
                            "match_type": "phonetic",
                            "frequency": self.entities.get(variant, 0)
                        })
            
            # 4. Fuzzy match using sequence matcher
            for entity in self.entities:
                entity_lower = entity.lower()
                if entity_lower == word_lower:
                    continue
                
                # Calculate similarity
                ratio = SequenceMatcher(None, word_lower, entity_lower).ratio()
                
                if ratio >= 0.6:  # 60% similarity threshold
                    word_suggestions.append({
                        "original": word,
                        "suggestion": entity,
                        "score": ratio,
                        "match_type": "fuzzy",
                        "frequency": self.entities.get(entity, 0)
                    })
            
            all_suggestions.extend(word_suggestions)
        
        # Deduplicate and sort by score * frequency
        seen = set()
        unique_suggestions = []
        for s in all_suggestions:
            key = (s["original"].lower(), s["suggestion"])
            if key not in seen:
                seen.add(key)
                # Boost score by frequency (log scale to prevent huge differences)
                import math
                freq_boost = 1 + math.log10(max(1, s["frequency"])) * 0.1
                s["final_score"] = s["score"] * freq_boost
                unique_suggestions.append(s)
        
        # Sort by final score
        unique_suggestions.sort(key=lambda x: x["final_score"], reverse=True)
        
        return unique_suggestions[:max_suggestions]
    
    def get_autocomplete(self, prefix: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Get autocomplete suggestions for a prefix.
        
        Args:
            prefix: The prefix to autocomplete
            max_results: Maximum number of results
            
        Returns:
            List of matching entities with frequencies
        """
        if not prefix or len(prefix) < 2:
            return []
        
        prefix_lower = prefix.lower()
        matches = []
        
        for entity, freq in self.entities.items():
            if entity.lower().startswith(prefix_lower):
                matches.append({
                    "entity": entity,
                    "frequency": freq,
                    "match_type": "prefix"
                })
            elif prefix_lower in entity.lower():
                matches.append({
                    "entity": entity,
                    "frequency": freq,
                    "match_type": "contains"
                })
        
        # Sort by frequency (most common first), then by match type
        matches.sort(key=lambda x: (x["match_type"] == "prefix", x["frequency"]), reverse=True)
        
        return matches[:max_results]
    
    def get_did_you_mean(self, query: str, threshold: float = 0.6) -> Optional[str]:
        """
        Get a "Did you mean?" suggestion for the entire query.
        
        Args:
            query: User's full query
            threshold: Minimum score to suggest
            
        Returns:
            Suggested corrected query, or None
        """
        suggestions = self.get_suggestions(query, max_suggestions=3)
        
        if not suggestions:
            return None
        
        # Only suggest if we have high-confidence matches
        high_conf = [s for s in suggestions if s["score"] >= threshold]
        
        if not high_conf:
            return None
        
        # Replace words in query with suggestions
        corrected_query = query
        for s in high_conf:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(s["original"]), re.IGNORECASE)
            corrected_query = pattern.sub(s["suggestion"], corrected_query)
        
        if corrected_query.lower() != query.lower():
            return corrected_query
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the spelling index."""
        return {
            "total_entities": len(self.entities),
            "total_variants": sum(len(v) for v in self.normalized_map.values()),
            "phonetic_groups": len(self.phonetic_map),
            "top_entities": sorted(
                self.entities.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:20]
        }


# Singleton instance
_suggester_instance: Optional[SpellingSuggester] = None


def get_spelling_suggester() -> SpellingSuggester:
    """Get or create the global spelling suggester instance."""
    global _suggester_instance
    if _suggester_instance is None:
        _suggester_instance = SpellingSuggester()
    return _suggester_instance
