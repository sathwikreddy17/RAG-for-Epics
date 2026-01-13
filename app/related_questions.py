"""
Related Questions Generator for RAG System.
Suggests follow-up questions based on the current query and answer.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)

# Major characters and their related topics for epic texts
CHARACTER_RELATIONS = {
    "rama": {
        "family": ["Dasaratha", "Sita", "Lakshmana", "Bharata", "Shatrughna", "Kaushalya"],
        "allies": ["Hanuman", "Sugriva", "Vibhishana", "Jambavan"],
        "enemies": ["Ravana", "Kumbhakarna", "Indrajit", "Khara", "Dushana"],
        "events": ["exile", "Sita's abduction", "Lanka battle", "coronation", "Ayodhya"],
        "concepts": ["dharma", "avatar", "Ramayana"],
    },
    "sita": {
        "family": ["Janaka", "Rama", "Lava", "Kusha"],
        "events": ["swayamvara", "abduction", "Ashoka grove", "fire ordeal", "exile"],
        "places": ["Mithila", "Lanka", "Ayodhya"],
        "concepts": ["devotion", "purity", "suffering"],
    },
    "hanuman": {
        "family": ["Anjana", "Vayu", "Kesari"],
        "allies": ["Rama", "Sugriva", "Angada"],
        "events": ["Lanka leap", "Sanjeevani", "burning Lanka", "finding Sita"],
        "concepts": ["devotion", "strength", "celibacy"],
    },
    "ravana": {
        "family": ["Vishrava", "Kaikesi", "Kumbhakarna", "Vibhishana", "Shurpanakha", "Indrajit"],
        "events": ["abducting Sita", "war with Rama", "boons from Brahma"],
        "places": ["Lanka"],
        "concepts": ["ten heads", "demon king", "scholar"],
    },
    "krishna": {
        "family": ["Vasudeva", "Devaki", "Yashoda", "Nanda", "Balarama", "Rukmini", "Radha"],
        "allies": ["Arjuna", "Pandavas", "Sudama"],
        "enemies": ["Kamsa", "Shishupala", "Jarasandha"],
        "events": ["Bhagavad Gita", "Kurukshetra", "Mathura", "Dwarka", "Govardhan"],
        "concepts": ["avatar", "dharma", "yoga", "leela"],
    },
    "arjuna": {
        "family": ["Kunti", "Pandu", "Draupadi", "Subhadra", "Abhimanyu"],
        "allies": ["Krishna", "Bhima", "Yudhishthira"],
        "enemies": ["Karna", "Drona", "Bhishma", "Duryodhana"],
        "events": ["Gandiva bow", "Kurukshetra", "Bhagavad Gita", "exile"],
        "concepts": ["archery", "warrior", "doubt"],
    },
    "yudhishthira": {
        "family": ["Kunti", "Pandu", "Draupadi", "Dharma"],
        "events": ["dice game", "exile", "Kurukshetra", "coronation"],
        "concepts": ["dharma", "truth", "righteousness"],
    },
    "bhima": {
        "family": ["Kunti", "Pandu", "Vayu", "Hidimbi", "Ghatotkacha"],
        "events": ["killing Dushasana", "killing Duryodhana", "Bakasura"],
        "concepts": ["strength", "mace", "appetite"],
    },
    "draupadi": {
        "family": ["Drupada", "Dhrishtadyumna", "Pandavas"],
        "events": ["swayamvara", "disrobing", "exile", "revenge"],
        "concepts": ["honor", "vengeance", "devotion"],
    },
    "karna": {
        "family": ["Kunti", "Surya", "Radha", "Adhiratha"],
        "allies": ["Duryodhana"],
        "events": ["charity", "Kurukshetra", "death"],
        "concepts": ["generosity", "loyalty", "tragedy"],
    },
    "bhishma": {
        "family": ["Shantanu", "Ganga", "Satyavati"],
        "events": ["vow of celibacy", "Kurukshetra", "bed of arrows"],
        "concepts": ["oath", "sacrifice", "wisdom"],
    },
    "duryodhana": {
        "family": ["Dhritarashtra", "Gandhari", "Dushasana"],
        "events": ["dice game", "Kurukshetra", "Lakshagriha"],
        "concepts": ["jealousy", "pride", "ambition"],
    },
}

# Question templates for different types
QUESTION_TEMPLATES = {
    "character": [
        "Who is {entity}?",
        "What is the role of {entity} in the story?",
        "What happened to {entity}?",
        "How is {entity} related to {related}?",
    ],
    "event": [
        "What happened during {event}?",
        "Why did {event} occur?",
        "What were the consequences of {event}?",
        "Who was involved in {event}?",
    ],
    "relationship": [
        "What is the relationship between {entity1} and {entity2}?",
        "How did {entity1} and {entity2} interact?",
    ],
    "concept": [
        "What does {concept} mean?",
        "How is {concept} portrayed in the text?",
        "What is the significance of {concept}?",
    ],
    "comparison": [
        "How does {entity1} compare to {entity2}?",
        "What are the differences between {entity1} and {entity2}?",
    ],
}


class RelatedQuestionsGenerator:
    """
    Generates related/follow-up questions based on query and answer content.
    """
    
    def __init__(self, spelling_suggester=None):
        """
        Initialize the generator.
        
        Args:
            spelling_suggester: Optional SpellingSuggester for entity recognition
        """
        self.spelling_suggester = spelling_suggester
        self.character_relations = CHARACTER_RELATIONS
        self.question_templates = QUESTION_TEMPLATES
        
        # Build reverse lookup for faster entity detection
        self._build_entity_index()
        
        # Stats tracking
        self._stats = {
            "total_generations": 0,
            "avg_suggestions": 0,
        }
    
    def _build_entity_index(self):
        """Build an index of all known entities for quick lookup."""
        self.known_entities = set()
        self.entity_lowercase_map = {}  # lowercase -> proper case
        
        for char, relations in self.character_relations.items():
            self.known_entities.add(char)
            self.entity_lowercase_map[char.lower()] = char.capitalize()
            
            for category, items in relations.items():
                for item in items:
                    self.known_entities.add(item.lower())
                    self.entity_lowercase_map[item.lower()] = item
    
    def extract_entities(self, text: str) -> Set[str]:
        """
        Extract entity mentions from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Set of recognized entities
        """
        if not text:
            return set()
        
        text_lower = text.lower()
        found_entities = set()
        
        # Check for known entities
        for entity in self.known_entities:
            if entity.lower() in text_lower:
                # Get proper case version
                proper = self.entity_lowercase_map.get(entity.lower(), entity.capitalize())
                found_entities.add(proper)
        
        # Also extract capitalized words that might be names
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        for word in words:
            if len(word) > 2 and word.lower() not in {'the', 'and', 'for', 'but', 'not'}:
                found_entities.add(word)
        
        return found_entities
    
    def generate_related_questions(
        self,
        query: str,
        answer: str = "",
        sources: Optional[List[Dict[str, Any]]] = None,
        max_questions: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate related questions based on the current query and answer.
        
        Args:
            query: Original user query
            answer: Generated answer (optional)
            sources: Retrieved sources (optional)
            max_questions: Maximum number of suggestions
            
        Returns:
            List of suggested questions with metadata
        """
        suggestions = []
        seen_questions = {query.lower().strip()}  # Don't suggest the original query
        
        # Extract entities from query and answer
        query_entities = self.extract_entities(query)
        answer_entities = self.extract_entities(answer) if answer else set()
        
        # Combine source texts for entity extraction
        source_text = ""
        if sources:
            source_text = " ".join(s.get("text", "")[:500] for s in sources[:3])
        source_entities = self.extract_entities(source_text)
        
        # All entities, prioritizing those in query
        all_entities = query_entities | answer_entities | source_entities
        
        # 1. Generate questions about related characters/entities
        for entity in query_entities:
            entity_lower = entity.lower()
            if entity_lower in self.character_relations:
                relations = self.character_relations[entity_lower]
                
                # Suggest questions about family members
                for family_member in relations.get("family", [])[:2]:
                    if family_member.lower() not in query.lower():
                        q = f"Who is {family_member}?"
                        if q.lower() not in seen_questions:
                            suggestions.append({
                                "question": q,
                                "type": "character",
                                "reason": f"Related to {entity}",
                            })
                            seen_questions.add(q.lower())
                
                # Suggest questions about events
                for event in relations.get("events", [])[:2]:
                    q = f"What happened during {entity}'s {event}?"
                    if q.lower() not in seen_questions:
                        suggestions.append({
                            "question": q,
                            "type": "event",
                            "reason": f"Key event for {entity}",
                        })
                        seen_questions.add(q.lower())
                
                # Suggest relationship questions
                for ally in relations.get("allies", [])[:1]:
                    q = f"What is the relationship between {entity} and {ally}?"
                    if q.lower() not in seen_questions:
                        suggestions.append({
                            "question": q,
                            "type": "relationship",
                            "reason": "Related characters",
                        })
                        seen_questions.add(q.lower())
        
        # 2. Generate questions about entities mentioned in answer but not query
        new_entities = answer_entities - query_entities
        for entity in list(new_entities)[:3]:
            if len(entity) > 2:
                q = f"Who is {entity}?"
                if q.lower() not in seen_questions:
                    suggestions.append({
                        "question": q,
                        "type": "character",
                        "reason": "Mentioned in answer",
                    })
                    seen_questions.add(q.lower())
        
        # 3. Generate deeper questions based on query type
        query_lower = query.lower()
        
        if query_lower.startswith(("who is", "who was")):
            # For character questions, suggest event/role questions
            for entity in query_entities:
                q = f"What is {entity}'s role in the story?"
                if q.lower() not in seen_questions:
                    suggestions.append({
                        "question": q,
                        "type": "analytical",
                        "reason": "Deeper understanding",
                    })
                    seen_questions.add(q.lower())
        
        elif query_lower.startswith(("what happened", "what did")):
            # For event questions, suggest cause/effect questions
            for entity in query_entities:
                q = f"Why did this happen to {entity}?"
                if q.lower() not in seen_questions:
                    suggestions.append({
                        "question": q,
                        "type": "analytical",
                        "reason": "Understand causes",
                    })
                    seen_questions.add(q.lower())
        
        elif query_lower.startswith("why"):
            # For why questions, suggest consequence questions
            q = "What were the consequences of this?"
            if q.lower() not in seen_questions:
                suggestions.append({
                    "question": q,
                    "type": "analytical",
                    "reason": "Understand effects",
                })
                seen_questions.add(q.lower())
        
        # 4. Suggest comparison questions if multiple entities
        if len(query_entities) >= 2:
            entities_list = list(query_entities)[:2]
            q = f"How does {entities_list[0]} compare to {entities_list[1]}?"
            if q.lower() not in seen_questions:
                suggestions.append({
                    "question": q,
                    "type": "comparison",
                    "reason": "Compare characters",
                })
                seen_questions.add(q.lower())
        
        # Update stats
        self._stats["total_generations"] += 1
        num_suggestions = len(suggestions[:max_questions])
        self._stats["avg_suggestions"] = (
            (self._stats["avg_suggestions"] * (self._stats["total_generations"] - 1) + num_suggestions)
            / self._stats["total_generations"]
        )
        
        return suggestions[:max_questions]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics."""
        return {
            "total_generations": self._stats["total_generations"],
            "avg_suggestions": round(self._stats["avg_suggestions"], 2),
            "known_characters": len(self.character_relations),
            "known_entities": len(self.known_entities),
        }


# Singleton instance
_generator = None


def get_related_questions_generator() -> RelatedQuestionsGenerator:
    """Get the singleton generator instance."""
    global _generator
    if _generator is None:
        _generator = RelatedQuestionsGenerator()
    return _generator
