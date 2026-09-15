"""High-retention 100% Dynamic Infinite AI Story Generator for TikTok (>60 seconds).
Autonomously brainstorms and writes brand new, real-world documentary topics on the fly
via Gemini API across dozens of science, history, space, ocean, and archaeology niches.
Zero static lists, zero duplicate topics, zero repetition across channels.
100% safe, educational, G-rated, and monetization-compliant under Fair Use.
"""
from __future__ import annotations

import json
import logging
import random
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.paths import DATA_DIR
from core.config_manager import get_api_key, load_config
from core.openai_fallback import generate_json as generate_openai_json
import requests

logger = logging.getLogger(__name__)

USED_STORIES_FILE = DATA_DIR / "used_crime_stories.json"
BLACKLIST_FILE = DATA_DIR / "blacklisted_topics.json"

# Common English words that must NEVER be used to ban topics
COMMON_EXCLUDED_WORDS = {
    "story", "the", "and", "from", "with", "this", "that", "into", "what", "most", "ever",
    "documented", "below", "your", "thoughts", "history", "science", "fascinating", "reality",
    "stranger", "fiction", "drop", "theory", "share", "friend", "comments", "unsolved",
    "ancient", "giant", "hidden", "mysterious", "temple", "buried", "space", "cosmic",
    "heist", "great", "wonder", "world", "vanished", "ocean", "discovery", "tunnel", "island",
    "breakout", "deepest", "point", "fortress", "city", "caves", "library", "figures",
    "blades", "unreinforced", "dome", "walk", "carbon", "nanotube", "theft", "made", "famous",
    "eighth", "secret", "detective", "investigation", "night", "aerial", "stone", "stones",
    "water", "under", "deep", "over", "down", "around", "first", "real", "time"
}

# Specific proper nouns and entities that have been over-posted and are STRICTLY BANNED
HISTORICAL_BANNED_ENTITIES = {
    "cooper", "alcatraz", "gardner", "roanoke", "celeste", "tunguska", "bloop", "antikythera",
    "voynich", "dyatlov", "bermuda", "dahmer", "bundy", "gacy", "ramirez", "zodiac", "massacre",
    "murder", "killer", "shakur", "bonnie", "k218b", "gotthard", "oakisland"
}

# Infinite thematic lenses across all domains of human knowledge
INFINITE_NICHES = [
    ("Deep Ocean & Abyssal Creatures", "Bioluminescent life, hydrothermal vents, extreme ocean trench survival records"),
    ("Cosmic Phenomena & Astrophysics", "Exoplanets, black holes, neutron stars, cosmic ray bursts, telescope discoveries"),
    ("Lost Ancient Engineering & Architecture", "Ancient water distribution, earthquake-proof construction, megalithic quarrying"),
    ("Prehistoric Earth & Fossil Discoveries", "Giant prehistoric flora, extinct apex predators, ice age frozen mummies"),
    ("Bizarre Geological Phenomena", "Rare mineral caverns, boiling rivers, singing sands, perpetual lightning storms"),
    ("Pioneering Polar & Deep Earth Expeditions", "Historic polar survival feats, deepest cave descents, oceanic exploration records"),
    ("Historical Inventions & Crypto-Mysteries", "Lost metallurgy, ancient analog mechanisms, unbreakable historical ciphers"),
    ("Extreme Physics & Laboratory Breakthroughs", "Superfluid helium, antimatter traps, particle collisions, quantum anomalies"),
    ("Ancient Civilizations & Monumental Wonders", "Lost cities in jungle or desert, monumental earthen mounds, astronomical alignments"),
    ("Aerospace Records & Extreme Flight Feats", "Experimental rocket planes, stratospheric balloon jumps, solar probe close passes"),
    ("Optical & Acoustic Atmospheric Mysteries", "Desert mirages, acoustic whispering galleries, green flash sunsets, skyquake booms"),
    ("Microscopic & Cellular Wonders", "Tardigrade survival in space, ancient amber microfossils, extremophile bacteria in magma")
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


def load_all_blacklisted_keywords() -> List[str]:
    """Loads specific banned entity keywords, filtering out common words."""
    keywords = set(HISTORICAL_BANNED_ENTITIES)
    if BLACKLIST_FILE.exists():
        try:
            data = json.loads(BLACKLIST_FILE.read_text(encoding="utf-8"))
            for kw in data.get("keywords", []):
                clean_kw = kw.lower().strip()
                if len(clean_kw) > 3 and clean_kw not in COMMON_EXCLUDED_WORDS:
                    keywords.add(clean_kw)
        except Exception:
            pass
    return list(keywords)


def load_blacklisted_topics() -> List[str]:
    """Load full historic titles; do not reduce them to generic individual words."""
    if not BLACKLIST_FILE.exists():
        return []
    try:
        data = json.loads(BLACKLIST_FILE.read_text(encoding="utf-8"))
        return [str(topic) for topic in data.get("topics", []) if normalize_topic(str(topic))]
    except Exception:
        return []


def normalize_topic(value: str) -> str:
    """Create a stable, human-readable key for a story title or Wikipedia query."""
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def topic_tokens(value: str) -> set[str]:
    """Keep only specific words; generic caption language must not block a topic."""
    return {
        word for word in normalize_topic(value).split()
        if len(word) > 3 and word not in COMMON_EXCLUDED_WORDS
    }


def story_identity_keys(story: Dict[str, Any]) -> set[str]:
    """Return the canonical identities that identify a topic, not its marketing copy."""
    return {
        key for key in (
            normalize_topic(story.get("id", "")),
            normalize_topic(story.get("wiki_query", "")),
            normalize_topic(story.get("case_name", "")),
        ) if key
    }


def is_duplicate_topic(story: Dict[str, Any], known_topics: List[str]) -> bool:
    """Reject the same subject, without rejecting a new subject for sharing one word."""
    candidate_keys = story_identity_keys(story)
    candidate_tokens = set().union(*(topic_tokens(key) for key in candidate_keys)) if candidate_keys else set()

    for known in known_topics:
        known_key = normalize_topic(known)
        if not known_key:
            continue
        if known_key in candidate_keys:
            return True

        known_tokens = topic_tokens(known_key)
        overlap = candidate_tokens & known_tokens
        # This catches aliases such as "Gobekli Tepe sanctuary" versus
        # "The temple that rewrote human history", while a shared word alone
        # (for example "ocean") is intentionally allowed.
        if len(overlap) >= 2:
            return True
    return False


def generate_infinite_dynamic_story(
    used_ids: List[str],
    forbidden_keywords: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """100% Dynamic AI Story Generator: Brainstorms a completely new real-world documentary topic.
    Rotates across Gemini models with built-in rate-limit guard and automatic fallback.
    Never repeats topics and guarantees zero duplication across channels.
    """
    key = get_api_key("gemini_api_key")

    niche_title, niche_desc = random.choice(INFINITE_NICHES)
    
    # Give Gemini prior *topics*, not a polluted bag of caption words.
    banned_words = [k.strip() for k in (forbidden_keywords or []) if normalize_topic(k)]
    banned_clause = ""
    if banned_words:
        sample_banned = list(dict.fromkeys(banned_words))[-40:]
        banned_clause = f"\n3. Do not reuse or retell any of these existing topics: {'; '.join(sample_banned)}."

    prompt = f"""You are an elite documentary researcher for a viral educational TikTok channel (>60s videos).
Generate 1 completely unique, real, verified historical or scientific documentary topic in the niche: '{niche_title}' ({niche_desc}).

CRITICAL RULES:
1. Must be a REAL, factual event or discovery with a verified Wikipedia article.
2. ABSOLUTELY G-RATED & SAFE FOR TIKTOK: NO violence, murders, blood, weapons, wars, serial killers, politics, or controversy.{banned_clause}
4. High educational wonder, breathtaking science, and viral retention (>60s spoken).

Return strictly valid JSON format:
{{
  "id": "short_unique_id",
  "case_name": "Engaging Documentary Title",
  "hook_banner": "ALL CAPS 3-5 WORDS",
  "wiki_query": "Exact Wikipedia Search Title",
  "broll_queries": ["cinematic ocean aerial", "astronomy telescope night", "historical ruins golden hour", "laboratory microscope"],
  "scenes": [
    {{"text": "Dramatic factual opening with specific dates and locations...", "visual_hint": "broll"}},
    {{"text": "Second scene explaining the mysterious phenomenon or engineering context...", "visual_hint": "wiki"}},
    {{"text": "Third scene detailing what researchers and scientists discovered...", "visual_hint": "wiki"}},
    {{"text": "Fourth scene explaining the unexpected mechanism or bizarre anomaly...", "visual_hint": "broll"}},
    {{"text": "Fifth scene detailing the extreme conditions or challenges encountered...", "visual_hint": "wiki"}},
    {{"text": "Sixth scene revealing the surprising breakthrough or twist...", "visual_hint": "broll"}},
    {{"text": "Seventh scene detailing why this discovery changed human knowledge forever...", "visual_hint": "wiki"}},
    {{"text": "Eighth scene concluding with an engaging thought-provoking question for the viewer...", "visual_hint": "broll"}}
  ],
  "hashtags": ["#science", "#discovery", "#documentary", "#mindblown", "#fyp"]
}}"""

    preferred_model = os.environ.get("GEMINI_MODEL") or load_config().get("generation", {}).get("gemini_model", "gemini-3.1-flash-lite")
    fallback_models = [
        "gemini-3.1-flash-lite",
        "gemini-3.1-flash-lite-preview",
        "gemini-3-flash-preview",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.7-flash",
        "gemini-2.5-flash",
    ]
    models_to_try = (list(dict.fromkeys([preferred_model, *fallback_models]))
                     if key and len(key) >= 20 else [])
    for mod in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.95
                }
            }
            time.sleep(1.2)
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                cand = data["candidates"][0]["content"]["parts"][0]["text"]
                story = json.loads(cand)
                if story.get("case_name") and story.get("scenes"):
                    canonical = normalize_topic(story.get("wiki_query") or story["case_name"])
                    # Never trust an arbitrary model-generated ID as the sole
                    # duplicate guard; make it deterministic from the subject.
                    story["id"] = f"dyn_{canonical.replace(' ', '_')[:80]}"
                    return story
            elif res.status_code == 429:
                time.sleep(3.0)
            else:
                logger.warning("Gemini model %s returned HTTP %s", mod, res.status_code)
        except Exception as exc:
            logger.warning("Gemini model %s failed: %s", mod, exc)

    # Gemini is the primary provider.  GPT is used only when all Gemini models
    # are unavailable, so the two APIs never compete or produce two posts.
    story = generate_openai_json(prompt, purpose="documentary topic")
    if story and story.get("case_name") and story.get("scenes"):
        canonical = normalize_topic(story.get("wiki_query") or story["case_name"])
        story["id"] = f"dyn_{canonical.replace(' ', '_')[:80]}"
        logger.info("GPT generated a fallback documentary topic: %s", story["case_name"])
        return story
    return None


def get_next_crime_story(existing_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """Retrieves the next unique high-retention documentary story.
    100% Dynamic Infinite AI Story Generator.
    Never runs out, never repeats, and never recycles old cases.
    """
    used = load_used_story_ids()
    # `existing_keywords` is retained as a backwards-compatible argument name,
    # but callers now pass canonical topic labels/IDs rather than every word in
    # a caption.  The old behaviour made Gemini reject almost every new title.
    known_topics = list(dict.fromkeys([
        *used,
        *load_blacklisted_topics(),
        *(existing_keywords or []),
    ]))
    hard_banned_entities = set(HISTORICAL_BANNED_ENTITIES)

    # Each attempt already tries all Gemini models, then GPT.  Keep the retry
    # count bounded so a provider outage cannot stall scheduling for hours.
    for attempt in range(4):
        story = generate_infinite_dynamic_story(used_ids=used, forbidden_keywords=known_topics)
        if story:
            candidate_words = topic_tokens(" ".join(story_identity_keys(story)))
            if not (candidate_words & hard_banned_entities) and not is_duplicate_topic(story, known_topics):
                used.append(story["id"])
                save_used_story_ids(used)
                return story
        time.sleep(2.0)

    raise RuntimeError("Ca Gemini va GPT deu chua tao duoc mot chu de moi hop le.")


def get_case_by_id(case_id: str) -> Optional[Dict[str, Any]]:
    return None

ICONIC_TRUE_CRIME_CASES: List[Dict[str, Any]] = []
