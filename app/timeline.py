"""
Timeline and Event Ordering Module

Provides chronological ordering of key events from the Ramayana and Mahabharata epics.
Events are organized by:
- Book/Kanda (major divisions)
- Relative chronological order within each epic
- Key characters involved
- Significance/Impact

Features:
- Get timeline for specific characters
- Get events by book/section
- Search events by keyword
- Compare parallel events across epics
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Epic(Enum):
    RAMAYANA = "Ramayana"
    MAHABHARATA = "Mahabharata"


@dataclass
class Event:
    """Represents a significant event in an epic."""
    id: str
    title: str
    description: str
    epic: Epic
    book: str  # Kanda for Ramayana, Parva for Mahabharata
    order: int  # Relative order within the epic (1 = earliest)
    characters: List[str] = field(default_factory=list)
    location: str = ""
    significance: str = ""
    tags: List[str] = field(default_factory=list)


class TimelineManager:
    """
    Manages chronological events from the epics.
    """
    
    def __init__(self):
        """Initialize the timeline with pre-defined events."""
        self.events: Dict[str, Event] = {}
        self._build_ramayana_timeline()
        self._build_mahabharata_timeline()
        logger.info(f"Timeline initialized: {len(self.events)} events")
    
    def _build_ramayana_timeline(self):
        """Build the Ramayana timeline."""
        events = [
            # Bala Kanda (Book 1)
            Event(
                id="ram_01", title="Birth of Rama and Brothers",
                description="King Dasaratha performs Putrakameshti yajna. His three queens give birth to four sons: Rama (Kausalya), Bharata (Kaikeyi), and twins Lakshmana and Shatrughna (Sumitra).",
                epic=Epic.RAMAYANA, book="Bala Kanda", order=1,
                characters=["Rama", "Dasaratha", "Kausalya", "Kaikeyi", "Bharata", "Lakshmana", "Shatrughna"],
                location="Ayodhya",
                significance="Divine incarnation of Vishnu as Rama to defeat Ravana",
                tags=["birth", "divine", "beginning"]
            ),
            Event(
                id="ram_02", title="Rama and Lakshmana Protect Vishwamitra's Yajna",
                description="Sage Vishwamitra takes young Rama and Lakshmana to protect his sacrifice from demons Tataka, Maricha, and Subahu. Rama kills Tataka and defeats the demons.",
                epic=Epic.RAMAYANA, book="Bala Kanda", order=2,
                characters=["Rama", "Lakshmana", "Vishwamitra", "Tataka", "Maricha"],
                location="Dandaka Forest",
                significance="Rama's first demonstration of martial prowess",
                tags=["battle", "demons", "protection"]
            ),
            Event(
                id="ram_03", title="Sita's Swayamvara - Breaking of Shiva's Bow",
                description="At King Janaka's court, Rama strings and breaks Lord Shiva's mighty bow, winning Sita's hand in marriage. The four brothers marry the four daughters of Janaka and his brother.",
                epic=Epic.RAMAYANA, book="Bala Kanda", order=3,
                characters=["Rama", "Sita", "Janaka", "Lakshmana", "Bharata", "Shatrughna"],
                location="Mithila",
                significance="Union of Rama and Sita, central to the epic's plot",
                tags=["marriage", "swayamvara", "bow"]
            ),
            
            # Ayodhya Kanda (Book 2)
            Event(
                id="ram_04", title="Kaikeyi's Boons - Rama's Exile Announced",
                description="On the eve of Rama's coronation, Queen Kaikeyi demands two boons from Dasaratha: Bharata's coronation and Rama's 14-year exile to the forest.",
                epic=Epic.RAMAYANA, book="Ayodhya Kanda", order=4,
                characters=["Kaikeyi", "Dasaratha", "Rama", "Bharata", "Manthara"],
                location="Ayodhya",
                significance="Turning point that sets the epic's main conflict in motion",
                tags=["exile", "boon", "betrayal", "turning_point"]
            ),
            Event(
                id="ram_05", title="Rama, Sita, and Lakshmana Depart for Forest",
                description="Rama accepts exile with equanimity. Sita and Lakshmana insist on accompanying him. They leave Ayodhya dressed as ascetics.",
                epic=Epic.RAMAYANA, book="Ayodhya Kanda", order=5,
                characters=["Rama", "Sita", "Lakshmana", "Kausalya", "Sumitra"],
                location="Ayodhya to Chitrakuta",
                significance="Beginning of the exile journey, demonstration of dharma",
                tags=["exile", "departure", "sacrifice"]
            ),
            Event(
                id="ram_06", title="Death of King Dasaratha",
                description="Overcome with grief at Rama's departure, King Dasaratha dies, calling out Rama's name. The kingdom mourns.",
                epic=Epic.RAMAYANA, book="Ayodhya Kanda", order=6,
                characters=["Dasaratha", "Kausalya", "Kaikeyi"],
                location="Ayodhya",
                significance="Consequences of separation from Rama",
                tags=["death", "grief", "tragedy"]
            ),
            Event(
                id="ram_07", title="Bharata Refuses the Throne",
                description="Bharata returns to find his father dead and Rama exiled. He goes to the forest to bring Rama back, but Rama refuses. Bharata takes Rama's sandals to rule as regent.",
                epic=Epic.RAMAYANA, book="Ayodhya Kanda", order=7,
                characters=["Bharata", "Rama", "Lakshmana", "Sita"],
                location="Chitrakuta",
                significance="Demonstration of Bharata's righteousness and brotherly love",
                tags=["righteousness", "loyalty", "sandals"]
            ),
            
            # Aranya Kanda (Book 3)
            Event(
                id="ram_08", title="Life in Dandaka Forest",
                description="Rama, Sita, and Lakshmana live as forest dwellers, visiting various sages. Rama protects the sages by killing demons who disturb their penances.",
                epic=Epic.RAMAYANA, book="Aranya Kanda", order=8,
                characters=["Rama", "Sita", "Lakshmana"],
                location="Dandaka Forest",
                significance="Ten years of peaceful exile before the main conflict",
                tags=["forest", "hermitage", "peace"]
            ),
            Event(
                id="ram_09", title="Surpanakha's Humiliation",
                description="Ravana's sister Surpanakha approaches Rama with desire. Rejected, she attacks Sita. Lakshmana cuts off her nose and ears.",
                epic=Epic.RAMAYANA, book="Aranya Kanda", order=9,
                characters=["Surpanakha", "Rama", "Sita", "Lakshmana"],
                location="Panchavati",
                significance="Catalyst for Ravana's involvement",
                tags=["conflict", "humiliation", "catalyst"]
            ),
            Event(
                id="ram_10", title="Rama Defeats Khara and Dushana",
                description="Surpanakha's brothers Khara and Dushana attack with 14,000 demons. Rama single-handedly destroys the entire army.",
                epic=Epic.RAMAYANA, book="Aranya Kanda", order=10,
                characters=["Rama", "Khara", "Dushana"],
                location="Janasthana",
                significance="Rama's might demonstrated; news reaches Ravana",
                tags=["battle", "victory", "demons"]
            ),
            Event(
                id="ram_11", title="Ravana Abducts Sita",
                description="Maricha, disguised as a golden deer, lures Rama away. Ravana, disguised as a sage, abducts Sita. Jatayu fights Ravana but is mortally wounded.",
                epic=Epic.RAMAYANA, book="Aranya Kanda", order=11,
                characters=["Ravana", "Sita", "Maricha", "Jatayu", "Rama", "Lakshmana"],
                location="Panchavati to Lanka",
                significance="Central crisis of the epic; Sita's abduction",
                tags=["abduction", "deception", "crisis", "turning_point"]
            ),
            Event(
                id="ram_12", title="Jatayu's Last Message",
                description="Rama and Lakshmana find the dying Jatayu, who tells them Ravana took Sita southward. Rama performs Jatayu's last rites.",
                epic=Epic.RAMAYANA, book="Aranya Kanda", order=12,
                characters=["Rama", "Lakshmana", "Jatayu"],
                location="Dandaka Forest",
                significance="First clue to Sita's whereabouts",
                tags=["death", "loyalty", "clue"]
            ),
            
            # Kishkindha Kanda (Book 4)
            Event(
                id="ram_13", title="Alliance with Sugriva",
                description="Rama meets Hanuman and then Sugriva on Rishyamukha mountain. Rama agrees to help Sugriva defeat Vali in exchange for help finding Sita.",
                epic=Epic.RAMAYANA, book="Kishkindha Kanda", order=13,
                characters=["Rama", "Hanuman", "Sugriva", "Lakshmana"],
                location="Rishyamukha Mountain",
                significance="Formation of the alliance that will defeat Ravana",
                tags=["alliance", "friendship", "strategy"]
            ),
            Event(
                id="ram_14", title="Rama Kills Vali",
                description="In Sugriva's fight with Vali, Rama shoots Vali from hiding. Vali questions the ethics but accepts his fate. Sugriva becomes king of Kishkindha.",
                epic=Epic.RAMAYANA, book="Kishkindha Kanda", order=14,
                characters=["Rama", "Vali", "Sugriva"],
                location="Kishkindha",
                significance="Controversial act that secures the vanara alliance",
                tags=["death", "ethics", "kingship"]
            ),
            Event(
                id="ram_15", title="Search Parties Sent for Sita",
                description="Sugriva organizes massive search parties of vanaras in all directions. The southern party, led by Angada with Hanuman, receives special attention.",
                epic=Epic.RAMAYANA, book="Kishkindha Kanda", order=15,
                characters=["Sugriva", "Hanuman", "Angada"],
                location="Kishkindha",
                significance="Systematic search begins for Sita",
                tags=["search", "organization", "mission"]
            ),
            
            # Sundara Kanda (Book 5)
            Event(
                id="ram_16", title="Hanuman's Leap to Lanka",
                description="Hanuman leaps across the ocean to Lanka, overcoming obstacles like Surasa (serpent) and Simhika (shadow-grasping demoness).",
                epic=Epic.RAMAYANA, book="Sundara Kanda", order=16,
                characters=["Hanuman", "Surasa", "Simhika"],
                location="Ocean crossing",
                significance="Hanuman's devotion and power demonstrated",
                tags=["leap", "ocean", "obstacles", "devotion"]
            ),
            Event(
                id="ram_17", title="Hanuman Finds Sita in Ashoka Grove",
                description="Hanuman searches Lanka and finds Sita in the Ashoka grove, guarded by demonesses. He reveals himself and gives her Rama's ring as proof.",
                epic=Epic.RAMAYANA, book="Sundara Kanda", order=17,
                characters=["Hanuman", "Sita"],
                location="Lanka, Ashoka Grove",
                significance="Sita found; message delivered; hope restored",
                tags=["discovery", "message", "hope"]
            ),
            Event(
                id="ram_18", title="Hanuman Burns Lanka",
                description="Hanuman allows himself to be captured, meets Ravana, and has his tail set on fire. He uses the burning tail to set Lanka ablaze.",
                epic=Epic.RAMAYANA, book="Sundara Kanda", order=18,
                characters=["Hanuman", "Ravana", "Indrajit"],
                location="Lanka",
                significance="Demonstration of vanara might; Lanka's vulnerability exposed",
                tags=["fire", "destruction", "defiance"]
            ),
            
            # Yuddha Kanda (Book 6)
            Event(
                id="ram_19", title="Building the Bridge to Lanka",
                description="The vanara army, led by Nala, builds a bridge (Rama Setu) across the ocean to Lanka using rocks that float when inscribed with Rama's name.",
                epic=Epic.RAMAYANA, book="Yuddha Kanda", order=19,
                characters=["Rama", "Nala", "Sugriva", "Hanuman"],
                location="Ocean (Rama Setu)",
                significance="Engineering marvel enabling the invasion of Lanka",
                tags=["bridge", "construction", "army"]
            ),
            Event(
                id="ram_20", title="Vibhishana Joins Rama",
                description="Ravana's righteous brother Vibhishana defects to Rama's side after Ravana ignores his counsel. Rama welcomes him and promises him Lanka's throne.",
                epic=Epic.RAMAYANA, book="Yuddha Kanda", order=20,
                characters=["Vibhishana", "Rama", "Ravana"],
                location="Seashore",
                significance="Key intelligence and moral support for Rama",
                tags=["defection", "righteousness", "alliance"]
            ),
            Event(
                id="ram_21", title="War Begins - Major Battles",
                description="The great war between Rama's vanara army and Ravana's demon forces begins. Many warriors fall on both sides.",
                epic=Epic.RAMAYANA, book="Yuddha Kanda", order=21,
                characters=["Rama", "Ravana", "Hanuman", "Sugriva", "Angada"],
                location="Lanka",
                significance="Epic battle between good and evil",
                tags=["war", "battle", "army"]
            ),
            Event(
                id="ram_22", title="Indrajit's Nagastra - Rama and Lakshmana Fall",
                description="Indrajit (Meghnad) uses the Nagastra (serpent weapon), binding Rama and Lakshmana. Garuda arrives to free them.",
                epic=Epic.RAMAYANA, book="Yuddha Kanda", order=22,
                characters=["Indrajit", "Rama", "Lakshmana", "Garuda"],
                location="Lanka battlefield",
                significance="Moment of crisis overcome by divine intervention",
                tags=["weapon", "crisis", "rescue"]
            ),
            Event(
                id="ram_23", title="Kumbhakarna Awakened and Slain",
                description="Ravana awakens his giant brother Kumbhakarna. Despite causing havoc, Kumbhakarna is eventually slain by Rama.",
                epic=Epic.RAMAYANA, book="Yuddha Kanda", order=23,
                characters=["Kumbhakarna", "Rama", "Ravana"],
                location="Lanka battlefield",
                significance="Fall of one of Ravana's mightiest warriors",
                tags=["giant", "battle", "death"]
            ),
            Event(
                id="ram_24", title="Lakshmana Kills Indrajit",
                description="After Indrajit uses deception multiple times, Lakshmana finally defeats and kills him in single combat with Brahmastra.",
                epic=Epic.RAMAYANA, book="Yuddha Kanda", order=24,
                characters=["Lakshmana", "Indrajit"],
                location="Lanka battlefield",
                significance="Ravana loses his most powerful son",
                tags=["battle", "death", "victory"]
            ),
            Event(
                id="ram_25", title="Hanuman Brings Sanjeevani",
                description="When Lakshmana is mortally wounded, Hanuman flies to the Himalayas and brings the entire Dronagiri mountain with the Sanjeevani herb to revive him.",
                epic=Epic.RAMAYANA, book="Yuddha Kanda", order=25,
                characters=["Hanuman", "Lakshmana"],
                location="Himalayas to Lanka",
                significance="Ultimate act of devotion and service",
                tags=["devotion", "healing", "mountain"]
            ),
            Event(
                id="ram_26", title="Rama Kills Ravana",
                description="In the final battle, after a long duel, Rama uses the Brahmastra to kill Ravana by striking his navel where his life force resided.",
                epic=Epic.RAMAYANA, book="Yuddha Kanda", order=26,
                characters=["Rama", "Ravana"],
                location="Lanka battlefield",
                significance="Triumph of good over evil; climax of the epic",
                tags=["death", "victory", "climax"]
            ),
            Event(
                id="ram_27", title="Sita's Agni Pariksha (Fire Ordeal)",
                description="To prove her purity after captivity, Sita enters fire. Agni (fire god) returns her unharmed, proving her chastity.",
                epic=Epic.RAMAYANA, book="Yuddha Kanda", order=27,
                characters=["Sita", "Rama", "Agni"],
                location="Lanka",
                significance="Controversial test of Sita's purity",
                tags=["trial", "purity", "fire"]
            ),
            Event(
                id="ram_28", title="Return to Ayodhya - Rama's Coronation",
                description="Rama, Sita, and Lakshmana return to Ayodhya on the Pushpaka Vimana. Rama is crowned king. The kingdom celebrates.",
                epic=Epic.RAMAYANA, book="Yuddha Kanda", order=28,
                characters=["Rama", "Sita", "Lakshmana", "Bharata", "Hanuman"],
                location="Ayodhya",
                significance="Establishment of Rama Rajya (ideal kingdom)",
                tags=["coronation", "return", "celebration", "ending"]
            ),
            
            # Uttara Kanda (Book 7) - Epilogue
            Event(
                id="ram_29", title="Sita's Exile and Birth of Lava and Kusha",
                description="Due to public doubt about Sita's purity, Rama sends pregnant Sita to the forest. She gives birth to twins Lava and Kusha at Valmiki's hermitage.",
                epic=Epic.RAMAYANA, book="Uttara Kanda", order=29,
                characters=["Sita", "Rama", "Lava", "Kusha", "Valmiki"],
                location="Valmiki's Ashrama",
                significance="Tragic separation; continuation of Rama's lineage",
                tags=["exile", "birth", "tragedy"]
            ),
            Event(
                id="ram_30", title="Sita Returns to Earth",
                description="When Rama asks Sita to prove her purity again, she calls upon her mother Earth, who opens to receive her. Sita disappears forever.",
                epic=Epic.RAMAYANA, book="Uttara Kanda", order=30,
                characters=["Sita", "Rama", "Earth"],
                location="Ayodhya",
                significance="Tragic end of Sita's earthly life",
                tags=["death", "earth", "tragedy", "ending"]
            ),
        ]
        
        for event in events:
            self.events[event.id] = event
    
    def _build_mahabharata_timeline(self):
        """Build the Mahabharata timeline."""
        events = [
            # Adi Parva (Book 1)
            Event(
                id="mah_01", title="Birth of the Pandavas and Kauravas",
                description="Gandhari gives birth to 100 sons (Kauravas) led by Duryodhana. Kunti uses divine mantras to have Yudhishthira (Dharma), Bhima (Vayu), and Arjuna (Indra). Madri has twins Nakula and Sahadeva (Ashwini Kumaras).",
                epic=Epic.MAHABHARATA, book="Adi Parva", order=1,
                characters=["Yudhishthira", "Bhima", "Arjuna", "Duryodhana", "Kunti", "Gandhari"],
                location="Hastinapura",
                significance="Birth of the two rival factions",
                tags=["birth", "beginning", "divine"]
            ),
            Event(
                id="mah_02", title="Training Under Drona",
                description="Drona becomes the guru of both Pandavas and Kauravas. Arjuna emerges as Drona's favorite and best student, especially in archery.",
                epic=Epic.MAHABHARATA, book="Adi Parva", order=2,
                characters=["Drona", "Arjuna", "Duryodhana", "Bhima", "Yudhishthira", "Karna"],
                location="Hastinapura",
                significance="Establishes Arjuna as supreme warrior",
                tags=["training", "archery", "education"]
            ),
            Event(
                id="mah_03", title="Karna's Humiliation at the Tournament",
                description="At the graduation tournament, Karna challenges Arjuna but is mocked for his low birth. Duryodhana makes him king of Anga, earning his eternal loyalty.",
                epic=Epic.MAHABHARATA, book="Adi Parva", order=3,
                characters=["Karna", "Arjuna", "Duryodhana", "Kunti"],
                location="Hastinapura",
                significance="Forges Karna-Duryodhana friendship; seeds of conflict",
                tags=["rivalry", "friendship", "humiliation"]
            ),
            Event(
                id="mah_04", title="Lakshagriha - House of Lac",
                description="Duryodhana plots to burn the Pandavas alive in a house made of lac. Warned by Vidura, they escape through a tunnel.",
                epic=Epic.MAHABHARATA, book="Adi Parva", order=4,
                characters=["Pandavas", "Duryodhana", "Vidura", "Kunti"],
                location="Varanavata",
                significance="First murder attempt; Pandavas go into hiding",
                tags=["plot", "escape", "fire"]
            ),
            Event(
                id="mah_05", title="Bhima Kills Hidimba - Marries Hidimbi",
                description="While in hiding, Bhima kills the demon Hidimba and marries his sister Hidimbi. Their son Ghatotkacha is born.",
                epic=Epic.MAHABHARATA, book="Adi Parva", order=5,
                characters=["Bhima", "Hidimba", "Hidimbi", "Ghatotkacha"],
                location="Forest",
                significance="Ghatotkacha later plays crucial role in war",
                tags=["marriage", "demon", "son"]
            ),
            Event(
                id="mah_06", title="Draupadi's Swayamvara",
                description="Disguised as Brahmins, Arjuna wins Draupadi by shooting the eye of a rotating fish. Due to Kunti's words, Draupadi becomes wife to all five Pandavas.",
                epic=Epic.MAHABHARATA, book="Adi Parva", order=6,
                characters=["Arjuna", "Draupadi", "Kunti", "Drupada"],
                location="Panchala",
                significance="Unusual marriage that binds Pandavas together",
                tags=["marriage", "swayamvara", "archery"]
            ),
            Event(
                id="mah_07", title="Pandavas Receive Indraprastha",
                description="The kingdom is divided. Pandavas receive the Khandava forest, which they clear (with Krishna and Arjuna's help) to build the magnificent city of Indraprastha.",
                epic=Epic.MAHABHARATA, book="Adi Parva", order=7,
                characters=["Pandavas", "Krishna", "Arjuna", "Maya"],
                location="Indraprastha",
                significance="Pandavas establish their own prosperous kingdom",
                tags=["kingdom", "city", "construction"]
            ),
            
            # Sabha Parva (Book 2)
            Event(
                id="mah_08", title="Rajasuya Yajna - Yudhishthira's Imperial Sacrifice",
                description="Yudhishthira performs the Rajasuya yajna, establishing himself as emperor. Krishna is honored as chief guest. Shishupala objects and is killed by Krishna.",
                epic=Epic.MAHABHARATA, book="Sabha Parva", order=8,
                characters=["Yudhishthira", "Krishna", "Shishupala"],
                location="Indraprastha",
                significance="Height of Pandava glory; Duryodhana's jealousy intensifies",
                tags=["yajna", "emperor", "glory"]
            ),
            Event(
                id="mah_09", title="Duryodhana Humiliated in Maya's Palace",
                description="Visiting Indraprastha, Duryodhana mistakes floors for pools and pools for floors. Draupadi and others laugh at him.",
                epic=Epic.MAHABHARATA, book="Sabha Parva", order=9,
                characters=["Duryodhana", "Draupadi"],
                location="Indraprastha",
                significance="Duryodhana's humiliation fuels his hatred",
                tags=["humiliation", "palace", "jealousy"]
            ),
            Event(
                id="mah_10", title="The Dice Game - Yudhishthira Loses Everything",
                description="In a rigged dice game against Shakuni, Yudhishthira loses his wealth, kingdom, brothers, himself, and finally Draupadi.",
                epic=Epic.MAHABHARATA, book="Sabha Parva", order=10,
                characters=["Yudhishthira", "Shakuni", "Duryodhana", "Draupadi"],
                location="Hastinapura",
                significance="Critical turning point leading to war",
                tags=["dice", "gambling", "loss", "turning_point"]
            ),
            Event(
                id="mah_11", title="Draupadi's Vastraharan (Disrobing)",
                description="Duryodhana orders Dushasana to disrobe Draupadi in the assembly. Krishna miraculously provides endless cloth. Draupadi vows revenge.",
                epic=Epic.MAHABHARATA, book="Sabha Parva", order=11,
                characters=["Draupadi", "Dushasana", "Duryodhana", "Krishna", "Bhima"],
                location="Hastinapura",
                significance="Most humiliating moment; Bhima vows to kill Dushasana",
                tags=["humiliation", "miracle", "vow", "injustice"]
            ),
            Event(
                id="mah_12", title="Second Dice Game - 13 Years of Exile",
                description="In a second game, Yudhishthira loses again. Pandavas must spend 12 years in exile and 1 year incognito, or face another 12 years.",
                epic=Epic.MAHABHARATA, book="Sabha Parva", order=12,
                characters=["Yudhishthira", "Shakuni", "Pandavas"],
                location="Hastinapura",
                significance="Sets up the exile period",
                tags=["dice", "exile", "condition"]
            ),
            
            # Vana Parva (Book 3)
            Event(
                id="mah_13", title="Exile in the Forest",
                description="Pandavas live in the Kamyaka forest with Draupadi. Many sages visit them. Arjuna goes to heaven to obtain divine weapons.",
                epic=Epic.MAHABHARATA, book="Vana Parva", order=13,
                characters=["Pandavas", "Draupadi", "Arjuna"],
                location="Kamyaka Forest",
                significance="Period of preparation and divine weapon acquisition",
                tags=["exile", "forest", "weapons"]
            ),
            Event(
                id="mah_14", title="Arjuna Obtains Pashupatastra from Shiva",
                description="Arjuna performs severe penance. Shiva tests him as a hunter (Kirata). Impressed by Arjuna's valor, Shiva grants him the Pashupatastra.",
                epic=Epic.MAHABHARATA, book="Vana Parva", order=14,
                characters=["Arjuna", "Shiva"],
                location="Himalayas",
                significance="Arjuna receives the most powerful weapon",
                tags=["weapon", "divine", "test"]
            ),
            Event(
                id="mah_15", title="Yaksha Prashna - Questions of the Yaksha",
                description="A Yaksha (Yama in disguise) asks Yudhishthira philosophical questions. Only Yudhishthira answers correctly and can revive his brothers.",
                epic=Epic.MAHABHARATA, book="Vana Parva", order=15,
                characters=["Yudhishthira", "Yama (Yaksha)", "Pandavas"],
                location="Forest lake",
                significance="Demonstrates Yudhishthira's wisdom",
                tags=["test", "wisdom", "questions"]
            ),
            
            # Virata Parva (Book 4)
            Event(
                id="mah_16", title="Year of Incognito at Virata's Court",
                description="Pandavas spend their 13th year disguised in King Virata's court. Yudhishthira as Brahmin, Bhima as cook, Arjuna as dance teacher Brihannala, Draupadi as maid.",
                epic=Epic.MAHABHARATA, book="Virata Parva", order=16,
                characters=["Pandavas", "Draupadi", "Virata"],
                location="Matsya Kingdom",
                significance="Successful completion of exile condition",
                tags=["disguise", "incognito", "service"]
            ),
            Event(
                id="mah_17", title="Arjuna Defeats Kauravas Single-handedly",
                description="When Kauravas attack Virata's kingdom, Arjuna (as Brihannala) reveals himself and defeats the entire Kaurava army, including Bhishma, Drona, and Karna.",
                epic=Epic.MAHABHARATA, book="Virata Parva", order=17,
                characters=["Arjuna", "Bhishma", "Drona", "Karna", "Duryodhana"],
                location="Matsya Kingdom",
                significance="Pandavas revealed; exile complete",
                tags=["battle", "revelation", "victory"]
            ),
            
            # Udyoga Parva (Book 5)
            Event(
                id="mah_18", title="Krishna's Peace Mission Fails",
                description="Krishna goes to Hastinapura as peace envoy. Duryodhana refuses to give even five villages. He tries to capture Krishna, who reveals his cosmic form.",
                epic=Epic.MAHABHARATA, book="Udyoga Parva", order=18,
                characters=["Krishna", "Duryodhana", "Dhritarashtra"],
                location="Hastinapura",
                significance="War becomes inevitable",
                tags=["peace", "failure", "cosmic_form"]
            ),
            Event(
                id="mah_19", title="Karna Learns His True Identity",
                description="Kunti reveals to Karna that he is her firstborn son, elder to the Pandavas. She asks him to join them. Karna refuses but promises to spare all except Arjuna.",
                epic=Epic.MAHABHARATA, book="Udyoga Parva", order=19,
                characters=["Karna", "Kunti"],
                location="Ganga river bank",
                significance="Karna's tragic choice; keeps his promise",
                tags=["revelation", "identity", "loyalty"]
            ),
            
            # Bhishma Parva (Book 6)
            Event(
                id="mah_20", title="Bhagavad Gita - Krishna's Teachings",
                description="On the battlefield, Arjuna despairs at fighting his kin. Krishna delivers the Bhagavad Gita, teaching duty, devotion, and the nature of reality.",
                epic=Epic.MAHABHARATA, book="Bhishma Parva", order=20,
                characters=["Krishna", "Arjuna"],
                location="Kurukshetra",
                significance="Greatest philosophical text; Arjuna's resolve restored",
                tags=["philosophy", "duty", "teaching", "gita"]
            ),
            Event(
                id="mah_21", title="War Begins - First 10 Days Under Bhishma",
                description="The 18-day war begins. Bhishma leads Kaurava forces for 10 days, causing massive casualties but refusing to kill Shikhandi (a woman reborn).",
                epic=Epic.MAHABHARATA, book="Bhishma Parva", order=21,
                characters=["Bhishma", "Arjuna", "Pandavas", "Kauravas"],
                location="Kurukshetra",
                significance="Beginning of the great war",
                tags=["war", "battle", "beginning"]
            ),
            Event(
                id="mah_22", title="Fall of Bhishma",
                description="Arjuna uses Shikhandi as a shield. Bhishma, unwilling to fight Shikhandi, is struck by Arjuna's arrows and falls on a bed of arrows, waiting for auspicious death.",
                epic=Epic.MAHABHARATA, book="Bhishma Parva", order=22,
                characters=["Bhishma", "Arjuna", "Shikhandi"],
                location="Kurukshetra",
                significance="End of the invincible patriarch's fighting",
                tags=["death", "bed_of_arrows", "fall"]
            ),
            
            # Drona Parva (Book 7)
            Event(
                id="mah_23", title="Drona Becomes Commander - Abhimanyu's Death",
                description="Drona takes command. The Kauravas form the Chakravyuha. Young Abhimanyu enters but cannot exit. He is surrounded and killed unfairly by multiple warriors.",
                epic=Epic.MAHABHARATA, book="Drona Parva", order=23,
                characters=["Abhimanyu", "Drona", "Jayadratha", "Karna"],
                location="Kurukshetra",
                significance="Most tragic death; Arjuna vows revenge",
                tags=["death", "chakravyuha", "tragedy", "unfair"]
            ),
            Event(
                id="mah_24", title="Arjuna Kills Jayadratha",
                description="Arjuna vows to kill Jayadratha (who blocked Abhimanyu's escape) before sunset or self-immolate. Krishna creates an eclipse; Arjuna beheads Jayadratha.",
                epic=Epic.MAHABHARATA, book="Drona Parva", order=24,
                characters=["Arjuna", "Jayadratha", "Krishna"],
                location="Kurukshetra",
                significance="Arjuna fulfills his vow with divine help",
                tags=["vow", "revenge", "eclipse"]
            ),
            Event(
                id="mah_25", title="Ghatotkacha's Sacrifice",
                description="Ghatotkacha (Bhima's demon son) wreaks havoc at night. Karna uses the Shakti (given by Indra) to kill him, saving it for Arjuna.",
                epic=Epic.MAHABHARATA, book="Drona Parva", order=25,
                characters=["Ghatotkacha", "Karna"],
                location="Kurukshetra",
                significance="Karna loses his secret weapon meant for Arjuna",
                tags=["death", "weapon", "sacrifice"]
            ),
            Event(
                id="mah_26", title="Drona's Death by Deception",
                description="Yudhishthira lies that 'Ashwatthama (an elephant) is dead.' Drona, believing his son dead, puts down his weapons in grief and is beheaded by Dhrishtadyumna.",
                epic=Epic.MAHABHARATA, book="Drona Parva", order=26,
                characters=["Drona", "Yudhishthira", "Dhrishtadyumna", "Krishna"],
                location="Kurukshetra",
                significance="Yudhishthira's only lie; Drona falls",
                tags=["death", "deception", "lie"]
            ),
            
            # Karna Parva (Book 8)
            Event(
                id="mah_27", title="Karna Becomes Commander",
                description="Karna takes command of Kaurava forces. He fights valiantly for two days, fulfilling his promise not to kill Pandavas except Arjuna.",
                epic=Epic.MAHABHARATA, book="Karna Parva", order=27,
                characters=["Karna", "Pandavas"],
                location="Kurukshetra",
                significance="Karna's brief command; keeps his word to Kunti",
                tags=["command", "promise", "battle"]
            ),
            Event(
                id="mah_28", title="Karna's Death",
                description="In the final duel, Karna's chariot wheel sinks. As he tries to lift it, Arjuna (urged by Krishna) kills the unarmed Karna.",
                epic=Epic.MAHABHARATA, book="Karna Parva", order=28,
                characters=["Karna", "Arjuna", "Krishna"],
                location="Kurukshetra",
                significance="Death of the tragic hero; controversial killing",
                tags=["death", "duel", "controversy"]
            ),
            
            # Shalya Parva (Book 9)
            Event(
                id="mah_29", title="Shalya's Brief Command and Death",
                description="Shalya becomes the last Kaurava commander. He is killed by Yudhishthira in single combat.",
                epic=Epic.MAHABHARATA, book="Shalya Parva", order=29,
                characters=["Shalya", "Yudhishthira"],
                location="Kurukshetra",
                significance="Yudhishthira proves his warrior skills",
                tags=["death", "command", "duel"]
            ),
            Event(
                id="mah_30", title="Duryodhana's Fall - Bhima's Revenge",
                description="Only Duryodhana survives, hiding in a lake. He is challenged to a mace duel by Bhima. Bhima strikes his thigh (unfairly), fulfilling his vow.",
                epic=Epic.MAHABHARATA, book="Shalya Parva", order=30,
                characters=["Duryodhana", "Bhima", "Krishna"],
                location="Kurukshetra",
                significance="Effective end of war; Bhima fulfills vow",
                tags=["death", "mace", "vow", "unfair"]
            ),
            
            # Sauptika Parva (Book 10)
            Event(
                id="mah_31", title="Ashwatthama's Night Massacre",
                description="The vengeful Ashwatthama attacks the Pandava camp at night, killing Dhrishtadyumna and Draupadi's five sons (thinking they were Pandavas).",
                epic=Epic.MAHABHARATA, book="Sauptika Parva", order=31,
                characters=["Ashwatthama", "Dhrishtadyumna", "Upapandavas"],
                location="Pandava camp",
                significance="Final tragedy; Draupadi loses all her sons",
                tags=["massacre", "night", "revenge", "tragedy"]
            ),
            Event(
                id="mah_32", title="Ashwatthama's Brahmastra and Curse",
                description="Ashwatthama launches Brahmastra at Uttara's womb. Krishna saves the unborn child (Parikshit) and curses Ashwatthama to immortal suffering.",
                epic=Epic.MAHABHARATA, book="Sauptika Parva", order=32,
                characters=["Ashwatthama", "Krishna", "Uttara", "Parikshit"],
                location="Pandava camp",
                significance="Kuru lineage preserved; Ashwatthama cursed",
                tags=["curse", "weapon", "lineage"]
            ),
            
            # Shanti & Anushasana Parvas (Books 12-13)
            Event(
                id="mah_33", title="Bhishma's Teachings from the Bed of Arrows",
                description="The dying Bhishma teaches Yudhishthira about dharma, statecraft, and philosophy for 58 days, waiting for the auspicious moment to die.",
                epic=Epic.MAHABHARATA, book="Shanti Parva", order=33,
                characters=["Bhishma", "Yudhishthira", "Pandavas"],
                location="Kurukshetra",
                significance="Transmission of wisdom; Bhishma's final gift",
                tags=["teaching", "wisdom", "deathbed"]
            ),
            
            # Ashvamedhika Parva (Book 14)
            Event(
                id="mah_34", title="Yudhishthira's Ashvamedha Yajna",
                description="Yudhishthira performs the horse sacrifice to establish his imperial rule and atone for the war's sins.",
                epic=Epic.MAHABHARATA, book="Ashvamedhika Parva", order=34,
                characters=["Yudhishthira", "Arjuna", "Pandavas"],
                location="Hastinapura",
                significance="Atonement and establishment of righteous rule",
                tags=["yajna", "emperor", "atonement"]
            ),
            
            # Mausala Parva (Book 16)
            Event(
                id="mah_35", title="Destruction of the Yadavas",
                description="The Yadava clan destroys itself in a drunken brawl at Prabhasa, fulfilling a curse. Krishna's era comes to an end.",
                epic=Epic.MAHABHARATA, book="Mausala Parva", order=35,
                characters=["Krishna", "Yadavas", "Balarama"],
                location="Prabhasa",
                significance="End of Krishna's dynasty",
                tags=["destruction", "curse", "end"]
            ),
            Event(
                id="mah_36", title="Krishna's Death",
                description="A hunter named Jara mistakes Krishna's foot for a deer and shoots him. Krishna forgives him and departs to his divine abode.",
                epic=Epic.MAHABHARATA, book="Mausala Parva", order=36,
                characters=["Krishna", "Jara"],
                location="Prabhasa",
                significance="End of Dvapara Yuga; beginning of Kali Yuga",
                tags=["death", "departure", "divine"]
            ),
            
            # Mahaprasthanika & Svargarohana Parvas (Books 17-18)
            Event(
                id="mah_37", title="Pandavas' Final Journey - Mahaprasthana",
                description="The Pandavas renounce their kingdom and walk toward the Himalayas. One by one, Draupadi and four brothers fall. Only Yudhishthira reaches heaven alive.",
                epic=Epic.MAHABHARATA, book="Mahaprasthanika Parva", order=37,
                characters=["Yudhishthira", "Pandavas", "Draupadi"],
                location="Himalayas",
                significance="Final journey; moral assessment of each",
                tags=["journey", "death", "heaven", "ending"]
            ),
            Event(
                id="mah_38", title="Yudhishthira's Test in Heaven",
                description="Yudhishthira finds his enemies in heaven and family in hell. It is revealed as a final test. All are reunited in heaven.",
                epic=Epic.MAHABHARATA, book="Svargarohana Parva", order=38,
                characters=["Yudhishthira", "Indra", "Pandavas", "Kauravas"],
                location="Heaven",
                significance="Final resolution; ultimate justice",
                tags=["test", "heaven", "resolution", "ending"]
            ),
        ]
        
        for event in events:
            self.events[event.id] = event
    
    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific event by ID."""
        event = self.events.get(event_id)
        if not event:
            return None
        return self._event_to_dict(event)
    
    def _event_to_dict(self, event: Event) -> Dict[str, Any]:
        """Convert an Event to a dictionary."""
        return {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "epic": event.epic.value,
            "book": event.book,
            "order": event.order,
            "characters": event.characters,
            "location": event.location,
            "significance": event.significance,
            "tags": event.tags,
        }
    
    def get_timeline(self, epic: Optional[str] = None, 
                     character: Optional[str] = None,
                     book: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get events in chronological order with optional filters.
        
        Args:
            epic: Filter by epic ("Ramayana" or "Mahabharata")
            character: Filter by character name
            book: Filter by book/kanda/parva name
        """
        results = []
        
        for event in self.events.values():
            # Apply filters
            if epic and event.epic.value.lower() != epic.lower():
                continue
            
            if character:
                char_lower = character.lower()
                if not any(char_lower in c.lower() for c in event.characters):
                    continue
            
            if book:
                book_lower = book.lower()
                if book_lower not in event.book.lower():
                    continue
            
            results.append(self._event_to_dict(event))
        
        # Sort by epic then order
        results.sort(key=lambda x: (x["epic"], x["order"]))
        return results
    
    def get_character_timeline(self, character: str) -> Dict[str, Any]:
        """Get all events involving a character, organized by epic."""
        events = self.get_timeline(character=character)
        
        ramayana_events = [e for e in events if e["epic"] == "Ramayana"]
        mahabharata_events = [e for e in events if e["epic"] == "Mahabharata"]
        
        return {
            "character": character,
            "total_events": len(events),
            "ramayana": {
                "count": len(ramayana_events),
                "events": ramayana_events
            },
            "mahabharata": {
                "count": len(mahabharata_events),
                "events": mahabharata_events
            }
        }
    
    def get_books(self, epic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of books/kandas/parvas with event counts."""
        book_counts: Dict[str, Dict[str, int]] = {}
        
        for event in self.events.values():
            if epic and event.epic.value.lower() != epic.lower():
                continue
            
            key = f"{event.epic.value}:{event.book}"
            if key not in book_counts:
                book_counts[key] = {"epic": event.epic.value, "book": event.book, "count": 0, "min_order": event.order}
            book_counts[key]["count"] += 1
            book_counts[key]["min_order"] = min(book_counts[key]["min_order"], event.order)
        
        result = list(book_counts.values())
        result.sort(key=lambda x: (x["epic"], x["min_order"]))
        
        # Remove min_order from output
        for item in result:
            del item["min_order"]
        
        return result
    
    def search_events(self, query: str) -> List[Dict[str, Any]]:
        """Search events by keyword in title, description, or tags."""
        query_lower = query.lower()
        results = []
        
        for event in self.events.values():
            score = 0
            
            if query_lower in event.title.lower():
                score += 10
            
            if query_lower in event.description.lower():
                score += 5
            
            for tag in event.tags:
                if query_lower in tag.lower():
                    score += 3
            
            for char in event.characters:
                if query_lower in char.lower():
                    score += 2
            
            if score > 0:
                result = self._event_to_dict(event)
                result["search_score"] = score
                results.append(result)
        
        results.sort(key=lambda x: (-x["search_score"], x["epic"], x["order"]))
        return results
    
    def get_events_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get all events with a specific tag."""
        results = []
        
        for event in self.events.values():
            if tag.lower() in [t.lower() for t in event.tags]:
                results.append(self._event_to_dict(event))
        
        results.sort(key=lambda x: (x["epic"], x["order"]))
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get timeline statistics."""
        ramayana_count = sum(1 for e in self.events.values() if e.epic == Epic.RAMAYANA)
        mahabharata_count = sum(1 for e in self.events.values() if e.epic == Epic.MAHABHARATA)
        
        all_tags = set()
        all_characters = set()
        for event in self.events.values():
            all_tags.update(event.tags)
            all_characters.update(event.characters)
        
        return {
            "total_events": len(self.events),
            "ramayana_events": ramayana_count,
            "mahabharata_events": mahabharata_count,
            "unique_characters": len(all_characters),
            "unique_tags": len(all_tags),
            "tags": sorted(list(all_tags)),
        }


# Singleton instance
_timeline_manager: Optional[TimelineManager] = None


def get_timeline_manager() -> TimelineManager:
    """Get or create the timeline manager singleton."""
    global _timeline_manager
    if _timeline_manager is None:
        _timeline_manager = TimelineManager()
    return _timeline_manager
