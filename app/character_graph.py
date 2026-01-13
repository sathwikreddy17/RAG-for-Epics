"""
Character Knowledge Graph Module

Builds and queries a knowledge graph of characters from the Ramayana and Mahabharata,
including their relationships, attributes, and key events.

Features:
- Pre-defined character relationships for major epic characters
- Dynamic relationship discovery from search results
- Graph traversal for finding connections between characters
- Character profiles with attributes and key events
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RelationType(Enum):
    """Types of relationships between characters."""
    PARENT = "parent"
    CHILD = "child"
    SPOUSE = "spouse"
    SIBLING = "sibling"
    ALLY = "ally"
    ENEMY = "enemy"
    TEACHER = "teacher"
    STUDENT = "student"
    SERVANT = "servant"
    MASTER = "master"
    FRIEND = "friend"
    ADVISOR = "advisor"
    KING = "king"
    SUBJECT = "subject"


@dataclass
class Character:
    """Represents a character in the epic."""
    name: str
    aliases: List[str] = field(default_factory=list)
    title: str = ""
    description: str = ""
    epic: str = ""  # "Ramayana", "Mahabharata", or "Both"
    attributes: Dict[str, str] = field(default_factory=dict)
    key_events: List[str] = field(default_factory=list)


@dataclass
class Relationship:
    """Represents a relationship between two characters."""
    source: str
    target: str
    relation_type: RelationType
    description: str = ""
    bidirectional: bool = False


class CharacterKnowledgeGraph:
    """
    Knowledge graph of epic characters and their relationships.
    """
    
    def __init__(self):
        """Initialize the character knowledge graph."""
        self.characters: Dict[str, Character] = {}
        self.relationships: List[Relationship] = []
        self._adjacency: Dict[str, List[Tuple[str, RelationType, str]]] = {}  # name -> [(target, type, desc)]
        
        # Build the graph
        self._build_characters()
        self._build_relationships()
        self._build_adjacency()
        
        logger.info(f"Character graph initialized: {len(self.characters)} characters, {len(self.relationships)} relationships")
    
    def _build_characters(self):
        """Build the character database."""
        # ===== RAMAYANA CHARACTERS =====
        self.characters["rama"] = Character(
            name="Rama",
            aliases=["Ramachandra", "Raghava", "Raghunandan", "Dasarathi", "Kosala Prince"],
            title="Prince of Ayodhya, Avatar of Vishnu",
            description="The hero of the Ramayana, ideal king and husband",
            epic="Ramayana",
            attributes={
                "kingdom": "Kosala (Ayodhya)",
                "weapon": "Kodanda (bow)",
                "quality": "Dharma (righteousness)",
            },
            key_events=["Exile to forest", "Sita's abduction", "War with Ravana", "Coronation"]
        )
        
        self.characters["sita"] = Character(
            name="Sita",
            aliases=["Janaki", "Vaidehi", "Maithili", "Bhumija"],
            title="Princess of Mithila, Wife of Rama",
            description="Daughter of King Janaka, paragon of virtue and devotion",
            epic="Ramayana",
            attributes={
                "kingdom": "Videha (Mithila)",
                "quality": "Pativrata (devotion to husband)",
            },
            key_events=["Swayamvara", "Exile with Rama", "Abduction by Ravana", "Agni Pariksha"]
        )
        
        self.characters["lakshmana"] = Character(
            name="Lakshmana",
            aliases=["Lakshman", "Saumitri", "Ramanuja"],
            title="Prince of Ayodhya, Brother of Rama",
            description="Devoted brother who accompanied Rama in exile",
            epic="Ramayana",
            attributes={
                "quality": "Fraternal devotion",
                "weapon": "Bow and sword",
            },
            key_events=["Accompanied Rama to exile", "Guarded Sita", "Fought in Lanka war"]
        )
        
        self.characters["hanuman"] = Character(
            name="Hanuman",
            aliases=["Anjaneya", "Maruti", "Pawanputra", "Bajrangbali"],
            title="Vanara Warrior, Son of Vayu",
            description="The mighty monkey god, devoted servant of Rama",
            epic="Ramayana",
            attributes={
                "father": "Vayu (Wind God)",
                "mother": "Anjana",
                "quality": "Bhakti (devotion), Strength",
            },
            key_events=["Finding Sita in Lanka", "Burning Lanka", "Bringing Sanjeevani"]
        )
        
        self.characters["ravana"] = Character(
            name="Ravana",
            aliases=["Dashanana", "Lankeshwara", "Dasagriva"],
            title="King of Lanka, Demon King",
            description="The ten-headed demon king who abducted Sita",
            epic="Ramayana",
            attributes={
                "kingdom": "Lanka",
                "heads": "Ten",
                "quality": "Scholar, but arrogant",
            },
            key_events=["Abducting Sita", "War with Rama", "Death at Rama's hands"]
        )
        
        self.characters["dasaratha"] = Character(
            name="Dasaratha",
            aliases=["Dasarath"],
            title="King of Ayodhya",
            description="Father of Rama, king of Kosala",
            epic="Ramayana",
            attributes={
                "kingdom": "Kosala (Ayodhya)",
                "dynasty": "Ikshvaku (Solar)",
            },
            key_events=["Putrakameshti yajna", "Granting boons to Kaikeyi", "Death from grief"]
        )
        
        self.characters["bharata"] = Character(
            name="Bharata",
            aliases=["Bharat"],
            title="Prince of Ayodhya",
            description="Son of Kaikeyi, devoted to Rama",
            epic="Ramayana",
            attributes={
                "mother": "Kaikeyi",
                "quality": "Righteousness",
            },
            key_events=["Rejected throne", "Ruled as Rama's regent", "Placed Rama's sandals on throne"]
        )
        
        self.characters["kaikeyi"] = Character(
            name="Kaikeyi",
            aliases=[],
            title="Queen of Ayodhya",
            description="Second wife of Dasaratha, mother of Bharata",
            epic="Ramayana",
            attributes={
                "kingdom": "Kekaya (origin)",
            },
            key_events=["Asked for boons", "Caused Rama's exile"]
        )
        
        self.characters["kausalya"] = Character(
            name="Kausalya",
            aliases=["Kaushalya"],
            title="Queen of Ayodhya",
            description="First wife of Dasaratha, mother of Rama",
            epic="Ramayana",
            key_events=["Birth of Rama"]
        )
        
        self.characters["vibhishana"] = Character(
            name="Vibhishana",
            aliases=["Vibhishan"],
            title="Brother of Ravana, Later King of Lanka",
            description="Righteous demon who joined Rama",
            epic="Ramayana",
            attributes={
                "quality": "Dharma",
            },
            key_events=["Defected to Rama", "Revealed Ravana's secrets", "Crowned King of Lanka"]
        )
        
        self.characters["sugriva"] = Character(
            name="Sugriva",
            aliases=["Sugreeva"],
            title="King of Kishkindha",
            description="Vanara king who allied with Rama",
            epic="Ramayana",
            key_events=["Alliance with Rama", "Sent Hanuman to find Sita", "Fought in Lanka war"]
        )
        
        self.characters["vali"] = Character(
            name="Vali",
            aliases=["Bali"],
            title="King of Kishkindha",
            description="Powerful vanara king, brother of Sugriva",
            epic="Ramayana",
            key_events=["Exile of Sugriva", "Death at Rama's hands"]
        )
        
        self.characters["jatayu"] = Character(
            name="Jatayu",
            aliases=[],
            title="King of Vultures",
            description="Brave vulture who tried to save Sita",
            epic="Ramayana",
            key_events=["Fought Ravana to save Sita", "Informed Rama about Sita's abduction"]
        )
        
        # ===== MAHABHARATA CHARACTERS =====
        self.characters["krishna"] = Character(
            name="Krishna",
            aliases=["Vasudeva", "Govinda", "Keshava", "Madhava", "Hari"],
            title="King of Dwaraka, Avatar of Vishnu",
            description="Divine guide of the Pandavas, speaker of the Bhagavad Gita",
            epic="Mahabharata",
            attributes={
                "kingdom": "Dwaraka",
                "weapon": "Sudarshana Chakra",
                "role": "Charioteer of Arjuna",
            },
            key_events=["Spoke Bhagavad Gita", "Guided Pandavas", "Killed Shishupala"]
        )
        
        self.characters["arjuna"] = Character(
            name="Arjuna",
            aliases=["Partha", "Dhananjaya", "Vijaya", "Phalguna", "Savyasachi"],
            title="Pandava Prince, Greatest Archer",
            description="Third Pandava, the supreme warrior and archer",
            epic="Mahabharata",
            attributes={
                "father": "Indra (divine)",
                "weapon": "Gandiva (bow)",
                "quality": "Skill, Focus",
            },
            key_events=["Won Draupadi", "Received Bhagavad Gita", "Killed Karna", "Won the war"]
        )
        
        self.characters["yudhishthira"] = Character(
            name="Yudhishthira",
            aliases=["Dharmaraja", "Ajatashatru"],
            title="Eldest Pandava, King",
            description="The righteous king, embodiment of dharma",
            epic="Mahabharata",
            attributes={
                "father": "Yama (Dharma)",
                "quality": "Truthfulness, Righteousness",
            },
            key_events=["Lost dice game", "Exile", "Became King after war"]
        )
        
        self.characters["bhima"] = Character(
            name="Bhima",
            aliases=["Bhimasena", "Vrikodara"],
            title="Second Pandava",
            description="The mighty warrior with immense strength",
            epic="Mahabharata",
            attributes={
                "father": "Vayu",
                "weapon": "Mace (Gada)",
                "quality": "Strength",
            },
            key_events=["Killed Dushasana", "Killed Duryodhana", "Killed many Kauravas"]
        )
        
        self.characters["draupadi"] = Character(
            name="Draupadi",
            aliases=["Panchali", "Krishnaa", "Yajnaseni"],
            title="Queen of Pandavas",
            description="Wife of the five Pandavas, born from fire",
            epic="Mahabharata",
            attributes={
                "father": "Drupada",
                "quality": "Spirit, Dignity",
            },
            key_events=["Swayamvara", "Vastraharan (disrobing)", "Vowed revenge"]
        )
        
        self.characters["duryodhana"] = Character(
            name="Duryodhana",
            aliases=["Suyodhana"],
            title="Eldest Kaurava, Crown Prince",
            description="The antagonist, leader of the Kauravas",
            epic="Mahabharata",
            attributes={
                "father": "Dhritarashtra",
                "weapon": "Mace",
                "quality": "Ambition, Jealousy",
            },
            key_events=["Dice game", "Refused to give Pandavas' share", "Death by Bhima"]
        )
        
        self.characters["karna"] = Character(
            name="Karna",
            aliases=["Radheya", "Suryaputra", "Vasusena", "Angaraja"],
            title="King of Anga",
            description="Son of Surya, tragic hero, loyal to Duryodhana",
            epic="Mahabharata",
            attributes={
                "father": "Surya (Sun God)",
                "mother": "Kunti",
                "weapon": "Vijaya bow",
                "quality": "Generosity, Loyalty",
            },
            key_events=["Abandoned at birth", "Friendship with Duryodhana", "Death by Arjuna"]
        )
        
        self.characters["bhishma"] = Character(
            name="Bhishma",
            aliases=["Devavrata", "Gangaputra", "Pitamaha"],
            title="Grand Patriarch of Kuru Dynasty",
            description="The great grandsire, bound by terrible vow",
            epic="Mahabharata",
            attributes={
                "father": "Shantanu",
                "mother": "Ganga",
                "vow": "Celibacy",
                "boon": "Death at will (Iccha Mrityu)",
            },
            key_events=["Took vow of celibacy", "Fought for Kauravas", "Death on bed of arrows"]
        )
        
        self.characters["drona"] = Character(
            name="Drona",
            aliases=["Dronacharya", "Bharadwaja"],
            title="Teacher of Princes",
            description="The great teacher of martial arts",
            epic="Mahabharata",
            attributes={
                "weapon": "Brahmastra",
                "role": "Guru of Kauravas and Pandavas",
            },
            key_events=["Trained the princes", "Fought for Kauravas", "Death by deception"]
        )
        
        self.characters["dhritarashtra"] = Character(
            name="Dhritarashtra",
            aliases=[],
            title="Blind King of Hastinapura",
            description="Father of the Kauravas, blind from birth",
            epic="Mahabharata",
            attributes={
                "quality": "Attachment to sons",
            },
            key_events=["Allowed dice game", "Failed to stop injustice"]
        )
        
        self.characters["kunti"] = Character(
            name="Kunti",
            aliases=["Pritha"],
            title="Queen, Mother of Pandavas",
            description="Mother of Yudhishthira, Bhima, Arjuna, and Karna",
            epic="Mahabharata",
            key_events=["Invoked gods for sons", "Abandoned Karna", "Revealed Karna's identity"]
        )
        
        self.characters["gandhari"] = Character(
            name="Gandhari",
            aliases=[],
            title="Queen of Hastinapura",
            description="Wife of Dhritarashtra, mother of 100 Kauravas",
            epic="Mahabharata",
            attributes={
                "quality": "Devotion (blindfolded herself)",
            },
            key_events=["Cursed Krishna after war"]
        )
    
    def _build_relationships(self):
        """Build the relationship database."""
        # Ramayana relationships
        self._add_relation("dasaratha", "rama", RelationType.PARENT, "Father of Rama")
        self._add_relation("dasaratha", "bharata", RelationType.PARENT, "Father of Bharata")
        self._add_relation("dasaratha", "lakshmana", RelationType.PARENT, "Father of Lakshmana")
        self._add_relation("kausalya", "rama", RelationType.PARENT, "Mother of Rama")
        self._add_relation("kaikeyi", "bharata", RelationType.PARENT, "Mother of Bharata")
        
        self._add_relation("rama", "sita", RelationType.SPOUSE, "Married in swayamvara", True)
        self._add_relation("rama", "lakshmana", RelationType.SIBLING, "Brothers", True)
        self._add_relation("rama", "bharata", RelationType.SIBLING, "Brothers", True)
        self._add_relation("lakshmana", "bharata", RelationType.SIBLING, "Brothers", True)
        
        self._add_relation("rama", "hanuman", RelationType.MASTER, "Lord and devotee")
        self._add_relation("hanuman", "rama", RelationType.SERVANT, "Devoted servant")
        self._add_relation("rama", "sugriva", RelationType.ALLY, "Alliance to defeat Vali and Ravana", True)
        self._add_relation("rama", "vibhishana", RelationType.ALLY, "Alliance against Ravana", True)
        
        self._add_relation("rama", "ravana", RelationType.ENEMY, "Ravana abducted Sita", True)
        self._add_relation("ravana", "vibhishana", RelationType.SIBLING, "Brothers", True)
        self._add_relation("sugriva", "vali", RelationType.SIBLING, "Brothers in conflict", True)
        
        self._add_relation("dasaratha", "kaikeyi", RelationType.SPOUSE, "King and Queen", True)
        self._add_relation("dasaratha", "kausalya", RelationType.SPOUSE, "King and Queen", True)
        
        # Mahabharata relationships
        self._add_relation("kunti", "yudhishthira", RelationType.PARENT, "Mother of Yudhishthira")
        self._add_relation("kunti", "bhima", RelationType.PARENT, "Mother of Bhima")
        self._add_relation("kunti", "arjuna", RelationType.PARENT, "Mother of Arjuna")
        self._add_relation("kunti", "karna", RelationType.PARENT, "Biological mother, abandoned him")
        
        self._add_relation("dhritarashtra", "duryodhana", RelationType.PARENT, "Father of Duryodhana")
        self._add_relation("gandhari", "duryodhana", RelationType.PARENT, "Mother of Duryodhana")
        
        self._add_relation("yudhishthira", "bhima", RelationType.SIBLING, "Pandava brothers", True)
        self._add_relation("yudhishthira", "arjuna", RelationType.SIBLING, "Pandava brothers", True)
        self._add_relation("bhima", "arjuna", RelationType.SIBLING, "Pandava brothers", True)
        
        self._add_relation("arjuna", "draupadi", RelationType.SPOUSE, "Won her in swayamvara", True)
        self._add_relation("yudhishthira", "draupadi", RelationType.SPOUSE, "Shared wife", True)
        self._add_relation("bhima", "draupadi", RelationType.SPOUSE, "Shared wife", True)
        
        self._add_relation("arjuna", "krishna", RelationType.FRIEND, "Divine friendship", True)
        self._add_relation("krishna", "arjuna", RelationType.ADVISOR, "Spoke Bhagavad Gita")
        
        self._add_relation("duryodhana", "karna", RelationType.FRIEND, "Loyal friendship", True)
        
        self._add_relation("drona", "arjuna", RelationType.TEACHER, "Favorite student")
        self._add_relation("drona", "duryodhana", RelationType.TEACHER, "Taught martial arts")
        self._add_relation("drona", "karna", RelationType.TEACHER, "Refused to teach initially")
        
        self._add_relation("bhishma", "dhritarashtra", RelationType.ADVISOR, "Grand patriarch")
        self._add_relation("bhishma", "yudhishthira", RelationType.ADVISOR, "Grand patriarch")
        
        self._add_relation("arjuna", "duryodhana", RelationType.ENEMY, "Cousins at war", True)
        self._add_relation("arjuna", "karna", RelationType.ENEMY, "Rivals, unknown brothers", True)
        self._add_relation("bhima", "duryodhana", RelationType.ENEMY, "Sworn enemies", True)
        
        self._add_relation("dhritarashtra", "gandhari", RelationType.SPOUSE, "King and Queen", True)
    
    def _add_relation(self, source: str, target: str, rel_type: RelationType, 
                      description: str = "", bidirectional: bool = False):
        """Add a relationship to the graph."""
        self.relationships.append(Relationship(
            source=source,
            target=target,
            relation_type=rel_type,
            description=description,
            bidirectional=bidirectional
        ))
    
    def _build_adjacency(self):
        """Build adjacency list for graph traversal."""
        self._adjacency = {name: [] for name in self.characters}
        
        for rel in self.relationships:
            if rel.source in self._adjacency:
                self._adjacency[rel.source].append((rel.target, rel.relation_type, rel.description))
            
            if rel.bidirectional and rel.target in self._adjacency:
                # Add reverse relationship
                reverse_type = self._get_reverse_relation(rel.relation_type)
                self._adjacency[rel.target].append((rel.source, reverse_type, rel.description))
    
    def _get_reverse_relation(self, rel_type: RelationType) -> RelationType:
        """Get the reverse of a relationship type."""
        reverse_map = {
            RelationType.PARENT: RelationType.CHILD,
            RelationType.CHILD: RelationType.PARENT,
            RelationType.TEACHER: RelationType.STUDENT,
            RelationType.STUDENT: RelationType.TEACHER,
            RelationType.MASTER: RelationType.SERVANT,
            RelationType.SERVANT: RelationType.MASTER,
            RelationType.KING: RelationType.SUBJECT,
            RelationType.SUBJECT: RelationType.KING,
        }
        return reverse_map.get(rel_type, rel_type)  # Same type for symmetric relations
    
    def _normalize_name(self, name: str) -> Optional[str]:
        """Normalize a character name to the canonical form."""
        name_lower = name.lower().strip()
        
        # Direct match
        if name_lower in self.characters:
            return name_lower
        
        # Check aliases
        for char_name, char in self.characters.items():
            if name_lower in [a.lower() for a in char.aliases]:
                return char_name
        
        return None
    
    def get_character(self, name: str) -> Optional[Dict[str, Any]]:
        """Get character information."""
        normalized = self._normalize_name(name)
        if not normalized:
            return None
        
        char = self.characters[normalized]
        return {
            "name": char.name,
            "aliases": char.aliases,
            "title": char.title,
            "description": char.description,
            "epic": char.epic,
            "attributes": char.attributes,
            "key_events": char.key_events,
        }
    
    def get_relationships(self, name: str) -> List[Dict[str, Any]]:
        """Get all relationships for a character."""
        normalized = self._normalize_name(name)
        if not normalized or normalized not in self._adjacency:
            return []
        
        relationships = []
        for target, rel_type, description in self._adjacency[normalized]:
            target_char = self.characters.get(target)
            relationships.append({
                "character": target_char.name if target_char else target,
                "relationship": rel_type.value,
                "description": description,
            })
        
        return relationships
    
    def get_character_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Get complete character profile including relationships."""
        char_info = self.get_character(name)
        if not char_info:
            return None
        
        relationships = self.get_relationships(name)
        
        # Group relationships by type
        grouped = {}
        for rel in relationships:
            rel_type = rel["relationship"]
            if rel_type not in grouped:
                grouped[rel_type] = []
            grouped[rel_type].append(rel["character"])
        
        return {
            **char_info,
            "relationships": relationships,
            "relationships_grouped": grouped,
        }
    
    def find_path(self, source: str, target: str, max_depth: int = 4) -> Optional[List[Dict[str, Any]]]:
        """Find the relationship path between two characters using BFS."""
        source_norm = self._normalize_name(source)
        target_norm = self._normalize_name(target)
        
        if not source_norm or not target_norm:
            return None
        
        if source_norm == target_norm:
            return [{"character": self.characters[source_norm].name, "relationship": "self"}]
        
        # BFS
        visited = {source_norm}
        queue = [(source_norm, [(source_norm, None, None)])]  # (current, path)
        
        while queue:
            current, path = queue.pop(0)
            
            if len(path) > max_depth:
                continue
            
            for neighbor, rel_type, desc in self._adjacency.get(current, []):
                if neighbor == target_norm:
                    # Found!
                    result = []
                    for char, rel, _ in path:
                        char_obj = self.characters.get(char)
                        result.append({
                            "character": char_obj.name if char_obj else char,
                            "relationship": rel.value if rel else "start",
                        })
                    target_char = self.characters.get(target_norm)
                    result.append({
                        "character": target_char.name if target_char else target_norm,
                        "relationship": rel_type.value,
                    })
                    return result
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = path + [(neighbor, rel_type, desc)]
                    queue.append((neighbor, new_path))
        
        return None  # No path found
    
    def get_family_tree(self, name: str) -> Dict[str, Any]:
        """Get family tree for a character."""
        normalized = self._normalize_name(name)
        if not normalized:
            return {"error": "Character not found"}
        
        char = self.characters[normalized]
        relationships = self._adjacency.get(normalized, [])
        
        family = {
            "character": char.name,
            "parents": [],
            "children": [],
            "siblings": [],
            "spouses": [],
        }
        
        for target, rel_type, desc in relationships:
            target_char = self.characters.get(target)
            target_name = target_char.name if target_char else target
            
            if rel_type == RelationType.CHILD:
                family["parents"].append(target_name)
            elif rel_type == RelationType.PARENT:
                family["children"].append(target_name)
            elif rel_type == RelationType.SIBLING:
                family["siblings"].append(target_name)
            elif rel_type == RelationType.SPOUSE:
                family["spouses"].append(target_name)
        
        return family
    
    def search_characters(self, query: str) -> List[Dict[str, Any]]:
        """Search for characters matching a query."""
        query_lower = query.lower()
        results = []
        
        for name, char in self.characters.items():
            score = 0
            
            # Check name match
            if query_lower in char.name.lower():
                score += 10
            
            # Check aliases
            for alias in char.aliases:
                if query_lower in alias.lower():
                    score += 8
                    break
            
            # Check title
            if query_lower in char.title.lower():
                score += 5
            
            # Check description
            if query_lower in char.description.lower():
                score += 3
            
            if score > 0:
                results.append({
                    "name": char.name,
                    "title": char.title,
                    "epic": char.epic,
                    "score": score,
                })
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
    
    def get_all_characters(self, epic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all characters, optionally filtered by epic."""
        result = []
        for name, char in self.characters.items():
            if epic and char.epic.lower() != epic.lower() and char.epic != "Both":
                continue
            result.append({
                "name": char.name,
                "title": char.title,
                "epic": char.epic,
            })
        return sorted(result, key=lambda x: x["name"])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        ramayana_chars = sum(1 for c in self.characters.values() if c.epic == "Ramayana")
        mahabharata_chars = sum(1 for c in self.characters.values() if c.epic == "Mahabharata")
        
        return {
            "total_characters": len(self.characters),
            "ramayana_characters": ramayana_chars,
            "mahabharata_characters": mahabharata_chars,
            "total_relationships": len(self.relationships),
            "relationship_types": list(set(r.relation_type.value for r in self.relationships)),
        }


# Singleton instance
_character_graph: Optional[CharacterKnowledgeGraph] = None


def get_character_graph() -> CharacterKnowledgeGraph:
    """Get or create the character knowledge graph singleton."""
    global _character_graph
    if _character_graph is None:
        _character_graph = CharacterKnowledgeGraph()
    return _character_graph
