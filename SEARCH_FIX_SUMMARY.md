# Search Fix Summary - January 11, 2026

## Problem
The autocomplete showed 8000+ references for "Rama" but when searching "Who is Rama?", the system returned unhelpful responses like "The sources do not explicitly state who Rama is."

## Root Causes Identified
1. **Overly restrictive LLM prompt**: The system was telling the LLM to "State only facts explicitly mentioned" which was too conservative
2. **Insufficient query expansion**: Short queries like "Who is Rama?" didn't have enough semantic signal for good retrieval
3. **Low entity boost weight**: Entity matching wasn't prioritized strongly enough
4. **Too few sources retrieved**: Factual queries only retrieved 3 sources, missing important context

## Fixes Applied

### 1. Improved LLM Prompt (`app/rag_backend.py`)
Changed from:
```
"State only facts explicitly mentioned in the sources
Do not infer or assume relationships not clearly stated"
```
To:
```
"Synthesize information from multiple source passages when relevant
For character questions, describe who they are, their role, relationships, and significance
Quote or paraphrase specific passages to support your answer"
```

### 2. Enhanced Query Expansion (`app/rag_backend.py`)
Added comprehensive context terms for 20+ major characters:
- Rama: "Ramachandra son of King Dasaratha prince of Ayodhya hero of Ramayana avatar of Vishnu husband of Sita Ikshvaku dynasty Kosala"
- Sita: "Janaki daughter of King Janaka wife of Rama princess of Mithila Vaidehi abducted by Ravana"
- And 18 more characters...

### 3. Added Entity Synonyms (`app/rag_backend.py`)
Added common spelling variations for main characters:
- rama: ["rama", "raama", "ram", "ramachandra", "raghava", "raghunandan"]
- sita: ["sita", "seeta", "janaki", "vaidehi", "maithili"]
- And more...

### 4. Increased Entity Boost Weight
From 0.08 to 0.15 for better prioritization of entity-relevant chunks.

### 5. Increased Sources for Factual Queries (`app/query_classifier.py`)
Changed `top_k` from 3 to 5 for factual query types.

## Results
Before fix:
- "Who is Rama?" → "The sources do not explicitly state who Rama is."

After fix:
- "Who is Rama?" → "Rama is the hero of the Ramayana, described as 'full of fire, indomitable, victorious, powerful, intelligent and wise' who is the right hand and very life's breath of his father. He is also called 'the conqueror of hostile cities'..."

---

# New Feature: Related Questions Suggestion - January 12, 2026

## Overview
Added a "Related Questions" feature that suggests follow-up questions users might want to ask, based on their query and the answer provided.

## Files Created/Modified

### 1. New File: `app/related_questions.py`
Contains the `RelatedQuestionsGenerator` class with:
- **CHARACTER_RELATIONS**: Dictionary mapping major epic characters to their relationships
  - Example: Rama → father: Dasaratha, mother: Kausalya, wife: Sita, brothers: [Lakshmana, Bharata, Shatrughna], allies: [Hanuman, Sugriva], enemies: [Ravana]
- **QUESTION_TEMPLATES**: Templates for different query types (character, event, relationship, exploration)
- **Entity extraction**: Identifies characters mentioned in queries/answers
- **Related question generation**: Creates contextual follow-up questions

### 2. Modified: `app/main.py`
- Added import for `related_questions` module
- Added `POST /api/related-questions` endpoint for standalone use
- Integrated related questions into `/api/ask` response metadata

## API Endpoints

### Integrated in `/api/ask` response
```json
{
  "answer": "...",
  "sources": [...],
  "metadata": {
    "related_questions": [
      {"question": "Who is Sita?", "type": "character", "reason": "Related to Rama"},
      {"question": "What happened during Rama's exile?", "type": "event", "reason": "Key event for Rama"},
      ...
    ]
  }
}
```

### Standalone Endpoint: `POST /api/related-questions`
Request:
```json
{
  "query": "Who is Rama?",
  "answer": "Rama is the hero of the Ramayana...",
  "sources": [],
  "max_questions": 5
}
```

Response:
```json
{
  "available": true,
  "questions": [
    {"question": "Who is Dasaratha?", "type": "character", "reason": "Related to Rama"},
    {"question": "Who is Sita?", "type": "character", "reason": "Related to Rama"},
    {"question": "What happened during Rama's exile?", "type": "event", "reason": "Key event for Rama"}
  ],
  "query": "Who is Rama?"
}
```

## Supported Characters
The system knows relationships for: Rama, Sita, Hanuman, Ravana, Lakshmana, Bharata, Dasaratha, Kaikeyi, Kausalya, Vibhishana, Sugriva, Vali, Jatayu, Krishna, Arjuna, Yudhishthira, Bhima, Duryodhana, Karna, Draupadi, Bhishma, Drona

---

# New Feature: Character Knowledge Graph - January 12, 2026

## Overview
Added a knowledge graph of epic characters with their relationships, attributes, and key events. Supports both Ramayana and Mahabharata.

## Files Created/Modified

### 1. New File: `app/character_graph.py`
Contains:
- **Character** dataclass: name, aliases, title, description, epic, attributes, key_events
- **Relationship** dataclass: source, target, relation_type, description
- **CharacterKnowledgeGraph** class:
  - 25 characters (13 Ramayana, 12 Mahabharata)
  - 42 relationships
  - 10 relationship types (parent, child, spouse, sibling, ally, enemy, teacher, student, master, servant)

### 2. Modified: `app/main.py`
Added character graph endpoints.

## API Endpoints

### `GET /api/characters`
List all characters, optionally filtered by epic.
```
GET /api/characters?epic=Ramayana
```

### `GET /api/characters/{name}`
Get detailed character profile including relationships.
```json
{
  "name": "Rama",
  "aliases": ["Ramachandra", "Raghava", "Raghunandan"],
  "title": "Prince of Ayodhya, Avatar of Vishnu",
  "relationships_grouped": {
    "spouse": ["Sita"],
    "sibling": ["Lakshmana", "Bharata"],
    "ally": ["Sugriva", "Vibhishana", "Hanuman"],
    "enemy": ["Ravana"]
  }
}
```

### `GET /api/characters/{name}/relationships`
Get all relationships for a character.

### `GET /api/characters/{name}/family`
Get family tree (parents, children, siblings, spouses).

### `GET /api/characters/path/{source}/{target}`
Find relationship path between two characters using BFS.
```
GET /api/characters/path/Arjuna/Karna
→ Returns: Arjuna → (enemy) → Karna
```

### `GET /api/characters/search?q={query}`
Search characters by name, title, or description.

### `GET /api/characters-graph/stats`
Get knowledge graph statistics.
```json
{
  "total_characters": 25,
  "ramayana_characters": 13,
  "mahabharata_characters": 12,
  "total_relationships": 42
}
```

## Characters Included

### Ramayana (13)
Rama, Sita, Lakshmana, Bharata, Hanuman, Ravana, Dasaratha, Kaikeyi, Kausalya, Sugriva, Vali, Vibhishana, Jatayu

### Mahabharata (12)
Krishna, Arjuna, Yudhishthira, Bhima, Draupadi, Duryodhana, Karna, Bhishma, Drona, Dhritarashtra, Kunti, Gandhari

---

# New Feature: Timeline & Event Ordering - January 12, 2026

## Overview
Chronological timeline of 68 key events from both epics, with filtering by character, book, and tags.

## Files Created

### `app/timeline.py`
Contains:
- **Event** dataclass: id, title, description, epic, book, order, characters, location, significance, tags
- **TimelineManager** class with 30 Ramayana events and 38 Mahabharata events
- Events organized by Kandas (Ramayana) and Parvas (Mahabharata)

## API Endpoints

### `GET /api/timeline`
Get events with optional filters.
```
GET /api/timeline?epic=Ramayana
GET /api/timeline?character=Hanuman
GET /api/timeline?book=Yuddha%20Kanda
```

### `GET /api/timeline/event/{event_id}`
Get specific event details.
```
GET /api/timeline/event/ram_11  → Ravana Abducts Sita
```

### `GET /api/timeline/character/{name}`
Get all events for a character, organized by epic.

### `GET /api/timeline/books`
List all books/kandas/parvas with event counts.

### `GET /api/timeline/search?q={query}`
Search events by keyword in title, description, or tags.

### `GET /api/timeline/tag/{tag}`
Get events by tag (e.g., "death", "marriage", "battle").

### `GET /api/timeline/stats`
Get timeline statistics (68 events, 127 unique tags).

## Event Coverage

### Ramayana (30 events)
- **Bala Kanda**: Birth, Vishwamitra's yajna, Sita's swayamvara
- **Ayodhya Kanda**: Exile, Dasaratha's death, Bharata's refusal
- **Aranya Kanda**: Forest life, Surpanakha, Sita's abduction, Jatayu
- **Kishkindha Kanda**: Sugriva alliance, Vali's death, search parties
- **Sundara Kanda**: Hanuman's leap, finding Sita, burning Lanka
- **Yuddha Kanda**: Bridge, war, Ravana's death, Agni pariksha, coronation
- **Uttara Kanda**: Sita's exile, Lava-Kusha, Sita's return to earth

### Mahabharata (38 events)
- **Adi Parva**: Birth, Drona's training, Lakshagriha, Draupadi's swayamvara
- **Sabha Parva**: Rajasuya, dice game, Draupadi's disrobing
- **Vana Parva**: Exile, Pashupatastra, Yaksha's questions
- **Virata Parva**: Incognito year
- **Udyoga Parva**: Peace mission, Karna's identity
- **Bhishma Parva**: Bhagavad Gita, war begins, Bhishma's fall
- **Drona Parva**: Abhimanyu's death, Ghatotkacha, Drona's death
- **Karna Parva**: Karna's command and death
- **Shalya Parva**: Duryodhana's fall
- **Later Parvas**: Ashwatthama, Bhishma's teachings, final journey

---

# New Feature: Citation Export - January 12, 2026

## Overview
Generate academic citations for sources in BibTeX, Chicago, MLA, and APA formats.

## Files Created

### `app/citation_exporter.py`
Contains:
- **CitationExporter** class with document metadata for known sources
- Formatters for BibTeX, Chicago, MLA, APA styles
- Inline citation generation

## API Endpoints

### `POST /api/citations/export`
Export sources in specified format.
```json
{
  "sources": [
    {"file_name": "Ramayana.of.Valmiki.by.Hari.Prasad.Shastri.pdf", "page": 524}
  ],
  "format": "bibtex"
}
```

Response:
```json
{
  "citations": [{
    "citation": "@book{ramayana524, title={The Ramayana of Valmiki}, author={Valmiki}, translator={Hari Prasad Shastri}...}",
    "inline": "(Valmiki, 524)"
  }],
  "combined": "..."
}
```

### `GET /api/citations/formats`
List available citation formats with descriptions.

### `GET /api/citations/document/{file_name}?format=chicago`
Get bibliography entry for a document.

## Supported Formats

| Format | Use Case |
|--------|----------|
| **BibTeX** | LaTeX papers, theses |
| **Chicago** | Humanities, history |
| **MLA** | Literature, language studies |
| **APA** | Social sciences |

## Known Documents with Metadata
- Ramayana of Valmiki by Hari Prasad Shastri (1952, London)
- Mahabharata by Kisari Mohan Ganguli (1883-1896, Calcutta)
- Srimad Valmiki Ramayana Sanskrit (1933)

## Files Modified
1. `/app/rag_backend.py` - Prompt, query expansion, entity synonyms, boost weight
2. `/app/query_classifier.py` - Increased top_k for factual queries

## Testing
```bash
# Test character queries
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who is Rama?", "include_sources": true}'

curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who is Sita?", "include_sources": true}'
```
