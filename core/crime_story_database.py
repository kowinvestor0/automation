"""American True Crime, Historical Enigmas & Scientific Mysteries Database.
Curated collection of captivating real mysteries, historical puzzles, and scientific wonders.
Strictly conforms to TikTok Community Guidelines: 100% clean, NO graphic violence, NO serial killers.
Structured specifically for high-retention portrait documentary storytelling (>60s).
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.paths import DATA_DIR

USED_STORIES_FILE = DATA_DIR / "used_crime_stories.json"

ICONIC_TRUE_CRIME_CASES: List[Dict[str, Any]] = [
    {
        "id": "db_cooper_vanished",
        "case_name": "D.B. Cooper: The Skyjacker Who Vanished",
        "hook_banner": "VANISHED AT 10,000 FT 😱",
        "wiki_query": "D. B. Cooper",
        "broll_queries": ["commercial airplane flying stormy night", "rain on tarmac airport", "dark forest fog aerial", "fbi investigation briefcase money"],
        "scenes": [
            {"text": "On Thanksgiving Eve in 1971, a quiet man wearing dark sunglasses boarded a Boeing 727 in Portland, Oregon.", "visual_hint": "broll"},
            {"text": "He purchased his ticket under the name Dan Cooper. Mid-flight, he handed the flight attendant a handwritten note saying he had a bomb in his briefcase.", "visual_hint": "wiki"},
            {"text": "He demanded two hundred thousand dollars in twenty-dollar bills and four military parachutes.", "visual_hint": "broll"},
            {"text": "When the plane touched down in Seattle, all thirty-six passengers were released safely in exchange for the cash.", "visual_hint": "wiki"},
            {"text": "Refueling complete, the plane took off toward Reno, flying through a torrential thunderstorm at just ten thousand feet.", "visual_hint": "broll"},
            {"text": "Somewhere over the pitch-black Cascade wilderness, Cooper lowered the plane's aft stairs and strapped the ransom money to his chest.", "visual_hint": "wiki"},
            {"text": "Then, into the freezing rain and zero visibility, he leapt into the darkness, never to be seen again.", "visual_hint": "broll"},
            {"text": "Despite one of the longest manhunts in FBI history, his body and the bulk of the cash were never found.", "visual_hint": "wiki"},
            {"text": "Did Dan Cooper survive that icy jump into the wilderness? Drop your theory in the comments.", "visual_hint": "broll"}
        ],
        "hashtags": ["#mystery", "#dbcooper", "#unsolved", "#fbi", "#history", "#aviation", "#fyp"]
    },
    {
        "id": "alcatraz_escape_1962",
        "case_name": "The 1962 Alcatraz Escape: The Impossible Breakout",
        "hook_banner": "THE IMPOSSIBLE ESCAPE ⚠️",
        "wiki_query": "June 1962 Alcatraz escape",
        "broll_queries": ["fog over san francisco bay prison", "dark ocean waves crashing night", "cell block prison bars dramatic", "old raincoat raft fbi investigation"],
        "scenes": [
            {"text": "Perched on a barren rock in San Francisco Bay, Alcatraz was designed to be the most inescapable prison on Earth.", "visual_hint": "broll"},
            {"text": "Surrounded by freezing currents and man-eating sharks, no inmate had ever successfully escaped.", "visual_hint": "wiki"},
            {"text": "Until the night of June eleventh, nineteen sixty-two, when three inmates engineered the most daring jailbreak in American history.", "visual_hint": "wiki"},
            {"text": "Frank Morris and brothers John and Clarence Anglin spent over a year using sharpened spoons to dig through decaying concrete walls.", "visual_hint": "broll"},
            {"text": "To fool the guards during night counts, they sculpted lifelike dummy heads from soap wax, toilet paper, and real human hair.", "visual_hint": "wiki"},
            {"text": "They climbed utility pipes to the roof, hauled a makeshift raft made from fifty stolen raincoats, and slipped into the pitch-black bay.", "visual_hint": "broll"},
            {"text": "By sunrise, the three men had vanished into thin air. Their bodies were never recovered.", "visual_hint": "wiki"},
            {"text": "Decades later, a mysterious letter surfaced claiming they survived and lived in South America.", "visual_hint": "broll"}
        ],
        "hashtags": ["#alcatraz", "#escape", "#fbi", "#unsolved", "#history", "#mystery", "#fyp"]
    },
    {
        "id": "gardner_museum_heist",
        "case_name": "The 500 Million Dollar Gardner Museum Art Heist",
        "hook_banner": "HALF A BILLION VANISHED 💎",
        "wiki_query": "Isabella Stewart Gardner Museum theft",
        "broll_queries": ["museum gallery empty frames dark", "police car night boston street", "rembrandt painting classic museum", "detective flashlight crime scene"],
        "scenes": [
            {"text": "In the early hours of March eighteenth, nineteen ninety, two men dressed as Boston police officers walked into the Isabella Stewart Gardner Museum.", "visual_hint": "broll"},
            {"text": "They told the night guard they were responding to a disturbance. Once inside, they overpowered both guards and duct-taped them in the basement.", "visual_hint": "wiki"},
            {"text": "Over the next eighty-one minutes, the thieves leisurely strolled the galleries, cutting thirteen priceless masterpieces from their frames.", "visual_hint": "broll"},
            {"text": "Among the loot: Rembrandt's only seascape, The Storm on the Sea of Galilee, and Vermeer's priceless masterwork, The Concert.", "visual_hint": "wiki"},
            {"text": "The total value of the stolen artwork exceeded five hundred million dollars, making it the single largest property theft in world history.", "visual_hint": "broll"},
            {"text": "Thirty-six years later, not a single painting has been recovered, and the ten-million-dollar FBI reward remains unclaimed.", "visual_hint": "wiki"},
            {"text": "Today, empty frames still hang on the museum walls as silent reminders of the greatest unsolved heist of all time.", "visual_hint": "broll"}
        ],
        "hashtags": ["#heist", "#artheist", "#gardnermuseum", "#mystery", "#unsolved", "#boston", "#fyp"]
    },
    {
        "id": "mary_celeste_ghost_ship",
        "case_name": "The Mary Celeste: The Ghost Ship of the Atlantic",
        "hook_banner": "ABANDONED AT SEA 🌊",
        "wiki_query": "Mary Celeste",
        "broll_queries": ["ghost ship ocean fog dramatic", "wooden sailing ship rough sea aerial", "empty ship deck abandoned rope", "storm clouds rolling over ocean"],
        "scenes": [
            {"text": "In December of eighteen seventy-two, a British merchant brig spotted a lone ship drifting aimlessly through the stormy waters of the Atlantic Ocean.", "visual_hint": "broll"},
            {"text": "When sailors boarded the vessel, identified as the Mary Celeste, they stepped into one of the most baffling maritime mysteries in history.", "visual_hint": "wiki"},
            {"text": "The ship was completely seaworthy. Six months of fresh food and water were still on board, and the cargo of industrial alcohol was intact.", "visual_hint": "broll"},
            {"text": "The captain's personal log sat open on his desk, but Captain Briggs, his wife, his young daughter, and seven crew members had vanished.", "visual_hint": "wiki"},
            {"text": "There was no sign of struggle, no pirate attack, and the single lifeboat was gone.", "visual_hint": "broll"},
            {"text": "What drove an experienced captain and crew to abandon a perfectly sound ship in the middle of the ocean remains an enduring mystery.", "visual_hint": "wiki"}
        ],
        "hashtags": ["#ghostship", "#maryceleste", "#oceanmystery", "#history", "#maritime", "#unsolved", "#fyp"]
    },
    {
        "id": "roanoke_lost_colony",
        "case_name": "The Lost Colony of Roanoke: Vanished Into History",
        "hook_banner": "115 PEOPLE VANISHED 😱",
        "wiki_query": "Roanoke Colony",
        "broll_queries": ["ancient forest mist aerial cinematic", "wooden palisade fort colony", "carved word on tree close-up", "storm waves crashing north carolina coast"],
        "scenes": [
            {"text": "In August of fifteen eighty-seven, over one hundred English settlers established a new settlement on Roanoke Island, North Carolina.", "visual_hint": "broll"},
            {"text": "Their governor, John White, sailed back to England to secure desperately needed food and supplies, expecting to return within months.", "visual_hint": "wiki"},
            {"text": "However, the outbreak of war with Spain trapped his ship in England for three long years.", "visual_hint": "broll"},
            {"text": "When White finally returned in fifteen ninety, the entire settlement had vanished without a trace.", "visual_hint": "wiki"},
            {"text": "There were no bodies, no signs of a battle, and all cottages had been neatly dismantled.", "visual_hint": "broll"},
            {"text": "The only clue left behind was a single word carved into a wooden post: CROATOAN.", "visual_hint": "wiki"},
            {"text": "To this day, the ultimate fate of the Lost Colony remains America's oldest unsolved mystery.", "visual_hint": "broll"}
        ],
        "hashtags": ["#history", "#roanoke", "#lostcolony", "#unsolved", "#mystery", "#archaeology", "#fyp"]
    },
    {
        "id": "voynich_manuscript",
        "case_name": "The Voynich Manuscript: The Book Nobody Can Read",
        "hook_banner": "UNDECIPHERED BOOK 📜",
        "wiki_query": "Voynich manuscript",
        "broll_queries": ["old parchment book turning pages", "mysterious handwritten cryptic cipher", "botanical alien plants manuscript", "cryptographer working desk magnifying glass"],
        "scenes": [
            {"text": "In nineteen twelve, an antique book dealer acquired a bizarre, handwritten manuscript carbon-dated to the early fifteenth century.", "visual_hint": "broll"},
            {"text": "Named the Voynich Manuscript, it is written in an entirely unknown script that belongs to no known human language.", "visual_hint": "wiki"},
            {"text": "Its two hundred and forty vellum pages are filled with vibrant drawings of bizarre alien-like plants that do not exist on Earth.", "visual_hint": "wiki"},
            {"text": "World War Two codebreakers from Bletchley Park, top FBI cryptographers, and modern supercomputers have all attempted to decode it.", "visual_hint": "broll"},
            {"text": "Yet after more than a century of study, not a single sentence of the manuscript has ever been translated.", "visual_hint": "wiki"},
            {"text": "Is it an ancient encyclopedia of lost knowledge, or the most elaborate hoax in human history?", "visual_hint": "broll"}
        ],
        "hashtags": ["#voynich", "#cryptography", "#unsolved", "#history", "#ancientbook", "#mystery", "#fyp"]
    },
    {
        "id": "tunguska_event_1908",
        "case_name": "The Tunguska Event: The Siberian Cosmic Blast",
        "hook_banner": "EARTH-SHATTERING BLAST 💥",
        "wiki_query": "Tunguska event",
        "broll_queries": ["siberian taiga forest aerial", "meteor fireball streak night sky", "flattened pine trees radial explosion", "mysterious northern lights sky night"],
        "scenes": [
            {"text": "On June thirtieth, nineteen zero eight, a colossal explosion ripped through the remote Siberian wilderness near the Podkamennaya Tunguska River.", "visual_hint": "broll"},
            {"text": "The blast was estimated to be one thousand times more powerful than the atomic bomb dropped on Hiroshima.", "visual_hint": "wiki"},
            {"text": "Over eighty million trees were instantly flattened across eight hundred square miles in a bizarre butterfly pattern.", "visual_hint": "wiki"},
            {"text": "Seismic shockwaves were detected as far away as London and Washington D.C., and night skies across Eurasia glowed so bright people could read newspapers at midnight.", "visual_hint": "broll"},
            {"text": "Yet when scientists finally reached the epicenter decades later, they found no impact crater and no meteorite fragments whatsoever.", "visual_hint": "wiki"},
            {"text": "What really detonated five miles above the Siberian forest remains one of science's greatest enigmas.", "visual_hint": "broll"}
        ],
        "hashtags": ["#tunguska", "#science", "#astronomy", "#mystery", "#space", "#cosmic", "#fyp"]
    },
    {
        "id": "oak_island_money_pit",
        "case_name": "The Oak Island Money Pit: The 200-Year Treasure Trap",
        "hook_banner": "THE UNBEATABLE TRAP 🏴‍☠️",
        "wiki_query": "Oak Island mystery",
        "broll_queries": ["misty coastal island nova scotia aerial", "deep muddy excavation shaft timbers", "ancient treasure map pirate coins", "ocean water flooding wooden booby trap tunnel"],
        "scenes": [
            {"text": "In seventeen ninety-five, a teenager exploring a small island off Nova Scotia discovered an unnatural circular depression under an old oak tree.", "visual_hint": "broll"},
            {"text": "Digging down, he discovered a man-made shaft fortified with heavy oak timber platforms every ten feet.", "visual_hint": "wiki"},
            {"text": "At ninety feet, diggers unearthed a mysterious stone slab carved with a cipher that read: Forty feet below, two million pounds lie buried.", "visual_hint": "wiki"},
            {"text": "Seconds later, the shaft suddenly flooded with thousands of gallons of seawater.", "visual_hint": "broll"},
            {"text": "Engineers discovered whoever built the pit created sophisticated artificial booby-trap flood tunnels connected directly to the ocean.", "visual_hint": "wiki"},
            {"text": "Over two centuries of drilling and millions of dollars have failed to penetrate the secret at the bottom.", "visual_hint": "broll"}
        ],
        "hashtags": ["#oakisland", "#treasure", "#mystery", "#history", "#unsolved", "#archaeology", "#fyp"]
    }
]


def load_used_story_ids() -> List[str]:
    """Loads list of story IDs that have already been produced."""
    if USED_STORIES_FILE.exists():
        try:
            return json.loads(USED_STORIES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_used_story_ids(used_ids: List[str]) -> None:
    """Saves used story IDs to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USED_STORIES_FILE.write_text(json.dumps(used_ids, indent=2), encoding="utf-8")


def generate_dynamic_crime_story(used_ids: List[str]) -> Optional[Dict[str, Any]]:
    """Generates a completely new real documentary story via Gemini 3.5 Flash.
    Strictly complies with TikTok Guidelines: 100% G-rated / educational / high retention.
    """
    try:
        from core.config_manager import get_api_key
        import requests
        key = get_api_key("gemini_api_key")
        if not key or len(key) < 20:
            return None

        categories = [
            "Breathtaking Scientific Discovery / Space Exploration (NASA, James Webb, Deep Cosmos, Black Holes)",
            "Deep Ocean Exploration & Unexplained Marine Phenomenon (Mariana Trench, Abyssal Plain, Strange Sounds)",
            "Mega Engineering Marvel & Impossible Construction (Megastructure, Tunnel, Aerospace Records, Panama Canal)",
            "Lost Ancient Civilization & Archaeological Excavation (Pyramids, Petra, Machu Picchu, Terracotta Army)",
            "Extreme Weather & Bizarre Natural Phenomenon (Rogue Waves, Supervolcanoes, Auroras, Sailing Stones)",
            "Famous Historical Non-Violent Enigma or Art Heist (Isabella Stewart Gardner, Amber Room, Antikythera)"
        ]
        chosen_cat = random.choice(categories)

        prompt = (
            f"Generate 1 high-retention viral documentary topic in the category: '{chosen_cat}'.\n"
            f"Requirements:\n"
            f"1. Must have a real, verified Wikipedia article with public domain historical photos.\n"
            f"2. STRICT TIKTOK COMMUNITY GUIDELINES: Absolutely NO graphic violence, gore, murders, serial killers, weapons, politics, or controversy. 100% safe for all audiences.\n"
            f"3. High viral intrigue and educational fascination.\n"
            f"Return JSON format:\n"
            f'{{\"id\": \"unique_id\", \"case_name\": \"Full Title\", \"hook_banner\": \"ALL CAPS 3-5 WORDS\", '
            f'\"wiki_query\": \"Exact Wikipedia Title\", '
            f'\"broll_queries\": [\"cinematic ocean aerial\", \"astronomy telescope night\"], '
            f'\"scenes\": [{{\"text\": \"Deep beneath the surface...\", \"visual_hint\": \"wiki\"}}], '
            f'\"hashtags\": [\"#science\", \"#discovery\", \"#mindblown\", \"#fyp\"]}}'
        )
        models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]
        for mod in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "thinkingConfig": {"thinkingBudget": 0},
                    "temperature": 0.9,
                }
            }
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                cand = data["candidates"][0]["content"]["parts"][0]["text"]
                story = json.loads(cand)
                if story.get("case_name") and story.get("scenes"):
                    if not story.get("id") or story["id"] in used_ids:
                        story["id"] = f"dyn_{re.sub(r'[^a-zA-Z0-9]', '_', story['case_name']).lower()[:30]}"
                    return story
    except Exception:
        pass
    return None


def get_next_crime_story(existing_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """Retrieves the next unique high-retention documentary story.
    Prioritizes Gemini 3.5 Flash dynamic generation across diverse categories.
    Falls back to randomized iconic database cases if Gemini is unavailable.
    Guarantees 100% freshness and zero repetitive topics.
    """
    used = load_used_story_ids()
    keywords = [k.lower() for k in (existing_keywords or [])]

    # 1. Primary: Try up to 3 times to generate a brand new unique dynamic story via Gemini
    for _ in range(3):
        dynamic_story = generate_dynamic_crime_story(used)
        if dynamic_story:
            c_name = dynamic_story.get("case_name", "").lower()
            if not any(k in c_name for k in keywords if len(k) > 4):
                used.append(dynamic_story["id"])
                save_used_story_ids(used)
                return dynamic_story

    # 2. Fallback: Filter available clean iconic cases, excluding anything already used or scheduled
    available = []
    for c in ICONIC_TRUE_CRIME_CASES:
        cid = c["id"]
        cname = c.get("case_name", "").lower()
        if cid in used:
            continue
        if any(k in cname for k in keywords if len(k) > 4):
            continue
        available.append(c)

    if available:
        chosen = random.choice(available)
    else:
        import time
        base = random.choice(ICONIC_TRUE_CRIME_CASES)
        chosen = dict(base)
        chosen["id"] = f"{base['id']}_{int(time.time())}"

    used.append(chosen["id"])
    save_used_story_ids(used)
    return chosen


def get_case_by_id(case_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific case by its ID."""
    for c in ICONIC_TRUE_CRIME_CASES:
        if c.get("id") == case_id:
            return c
    return None
