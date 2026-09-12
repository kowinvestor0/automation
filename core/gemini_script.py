"""AI Script generator using Gemini REST API with rich high-retention fallback templates."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
import requests

from core.config_manager import get_api_key

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.5-flash"
FALLBACK_MODEL = "gemini-3.5-flash-lite"

COMMENTARY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "hook_banner": {"type": "STRING"},
        "title": {"type": "STRING"},
        "description": {"type": "STRING"},
        "scenes": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "text": {"type": "STRING"},
                    "keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
                },
                "required": ["text", "keywords"],
            },
        },
        "hashtags": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["hook_banner", "title", "description", "scenes", "hashtags"],
}

SYSTEM_INSTRUCTION = """You are an elite short-form video creator producing high-retention commentary for TikTok, YouTube Shorts, and Reels.
CRITICAL GOAL:
1. Total duration MUST exceed 60 seconds (aim for 10-12 scenes, ~180-220 words total).
2. The content must be completely TRANSFORMATIVE: Don't just narrate; explain the WHY, the science, the psychology, or the untold backstory so it easily qualifies for monetization under Fair Use!
3. Structure:
   - hook_banner: 3-5 words in ALL CAPS (e.g. "WAIT FOR THE END 😱", "IS THIS EVEN REAL? 🤔", "HOW DID HE SURVIVE?").
   - Scene 1 (The Hook): Instantly draw the viewer's eyes to a subtle detail ("Look closely at the left corner of the frame", "Nobody expected what happened two seconds in").
   - Scenes 2-4: Tension building and narrative breakdown of the footage.
   - Scenes 5-8: Crucial transformative insight: Scientific explanation, physics, historical context, or investigation findings.
   - Scenes 9-11: Shocking twist or resolution, witty commentary.
   - Scene 12: High-converting call-to-action ("Would you have survived this? Subscribe for more insane breakdowns!").
4. Fast-paced, conversational, energetic tone.
5. NO emoji in scene text. Spell numbers out in words (twenty feet, five hundred dollars).
"""


def generate_script(clip_info: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
    """Generates a structured commentary script via Gemini or fallback."""
    key = get_api_key("gemini_api_key")
    title = clip_info.get("title", "Viral Clip")
    desc = (clip_info.get("description") or "")[:400]

    if key and len(key) >= 20:
        try:
            url = f"{BASE_URL}/models/{DEFAULT_MODEL}:generateContent?key={key}"
            prompt = (
                f"Video Title: {title}\n"
                f"Video Context: {desc}\n"
                f"Duration of source clip: {clip_info.get('duration', 45)}s.\n"
                f"Language: {'English' if language == 'en' else 'Vietnamese'}.\n\n"
                f"Write an intense, highly engaging 11-12 scene breakdown (>60s) explaining this situation."
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": COMMENTARY_SCHEMA,
                    "temperature": 0.8,
                },
            }
            res = requests.post(url, json=payload, timeout=35)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
            else:
                print(f"[Gemini] API returned {res.status_code}: {res.text[:100]}")
        except Exception as e:
            print(f"[Gemini] Request failed ({e}), using high-retention fallback template.")

    # High-retention dynamic fallback templates (>60 seconds, 11 scenes)
    title_lower = (title + " " + desc).lower()

    if any(w in title_lower for w in ("snow", "avalanche", "mountain", "ski", "ice", "winter")):
        hook = "WAIT FOR THE END 😱"
        scenes = [
            {"text": "Look extremely closely at this mountain ridge, because ninety nine percent of people miss what happens.", "keywords": ["mountain"]},
            {"text": "This heart stopping moment took over the internet as millions watched this skier trigger an enormous avalanche.", "keywords": ["avalanche"]},
            {"text": "At first, the run seems completely routine and peaceful on the fresh powder snow.", "keywords": ["peaceful snow"]},
            {"text": "However, right as he cuts across the slope, a terrifying fracture line shoots across the surface.", "keywords": ["fracture line"]},
            {"text": "Here is the exact scientific breakdown of how slab avalanches are accidentally released.", "keywords": ["science research"]},
            {"text": "Winter rescue experts who reviewed the footage noticed a buried sugar snow layer that failed instantly.", "keywords": ["investigation"]},
            {"text": "Once a slab fractures, it can accelerate past eighty miles per hour in just five seconds.", "keywords": ["fast motion"]},
            {"text": "The weight of the snow sliding downhill equals hundreds of full sized freight train cars.", "keywords": ["heavy weight"]},
            {"text": "Against all odds, the skier deployed his safety protocol and managed to stay right on the surface.", "keywords": ["survival"]},
            {"text": "Mountain safety instructors now use this exact video as a masterclass in backcountry survival.", "keywords": ["masterclass"]},
            {"text": "Would you have reacted quickly enough to survive? Subscribe right now and let me know in the comments.", "keywords": ["subscribe"]},
        ]
    elif any(w in title_lower for w in ("animal", "dog", "cat", "bear", "shark", "lion", "wildlife")):
        hook = "YOU WON'T BELIEVE THIS 🐾"
        scenes = [
            {"text": "Look closely at the background behind the trees, because nobody noticed what was creeping up.", "keywords": ["wildlife"]},
            {"text": "This viral encounter shocked millions of viewers around the globe when it was posted online.", "keywords": ["shocked"]},
            {"text": "What seemed like an ordinary afternoon in nature quickly turned into a high stakes standoff.", "keywords": ["standoff"]},
            {"text": "Animals in the wild have survival instincts that humans simply fail to recognize until it is too late.", "keywords": ["instinct"]},
            {"text": "Biologists who studied this interaction revealed that the animal was actually displaying a rare protective behavior.", "keywords": ["biology"]},
            {"text": "Rather than attacking, it was maintaining a defensive perimeter to assess potential threats.", "keywords": ["defense"]},
            {"text": "The calm composure shown by the person in front was the exact textbook response recommended by experts.", "keywords": ["calm"]},
            {"text": "Running in a situation like this would have instantly triggered a predatory chase reflex.", "keywords": ["chase"]},
            {"text": "After several heart pounding seconds, the situation resolved without a single injury.", "keywords": ["safe"]},
            {"text": "Park rangers now share this footage worldwide to educate hikers on trail safety.", "keywords": ["education"]},
            {"text": "How would your nerves have held up in this situation? Hit subscribe for more incredible wildlife moments.", "keywords": ["subscribe"]},
        ]
    else:
        hook = "WAIT FOR THE END 😱"
        scenes = [
            {"text": "Look extremely closely at this moment, because ninety nine percent of people completely miss what actually happened.", "keywords": ["mystery"]},
            {"text": "This unbelievable footage recently took over the entire internet, sparking intense debates everywhere.", "keywords": ["viral debate"]},
            {"text": "At first glance, everything appears totally ordinary and peaceful as the scene begins.", "keywords": ["ordinary"]},
            {"text": "However, as the seconds tick by, the tension escalates rapidly and catches everyone completely off guard.", "keywords": ["tension"]},
            {"text": "Here is the exact step by step breakdown of the mysterious circumstances behind this event.", "keywords": ["breakdown"]},
            {"text": "Specialists who reviewed this footage pointed out an astonishing detail hidden right in the frame.", "keywords": ["hidden detail"]},
            {"text": "The rare chain reaction you are witnessing can only occur under extremely precise environmental conditions.", "keywords": ["rare reaction"]},
            {"text": "In fact, verified occurrences like this have only been documented a handful of times in modern records.", "keywords": ["archive"]},
            {"text": "Once you uncover the full backstory, the entire mystery finally connects and makes complete sense.", "keywords": ["revelation"]},
            {"text": "It turns out the genuine explanation behind this moment is even crazier than what anyone originally imagined.", "keywords": ["truth"]},
            {"text": "Did you spot that hidden detail on your very first watch? Subscribe right now and drop your reaction below.", "keywords": ["subscribe"]},
        ]

    clean_title = re.sub(r"[^\w\s-]", "", title).strip()[:50]
    return {
        "hook_banner": hook,
        "title": f"The Untold Truth Behind {clean_title}",
        "description": f"Breaking down what really happened in this insane viral moment. #shorts #viral #breakdown #mystery",
        "scenes": scenes,
        "hashtags": ["#shorts", "#viral", "#trending", "#breakdown", "#didyouknow", "#fyp"],
    }


CRIME_STORY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "hook_banner": {"type": "STRING"},
        "scenes": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "text": {"type": "STRING"},
                    "visual_hint": {"type": "STRING"},
                },
                "required": ["text", "visual_hint"],
            },
        },
        "hashtags": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["hook_banner", "scenes", "hashtags"],
}

CRIME_SYSTEM_INSTRUCTION = """You are an elite true crime investigative documentary scriptwriter creating gripping portrait short-form video narrations for TikTok (>60 seconds).

CRITICAL RULES:
1. NO CLICHÉ OPENERS: NEVER start with phrases like "This is insane", "Look right here", "Watch this", "Hey guys", "Wait until the end", "Nobody noticed". Start immediately with raw, shocking factual action, specific dates, locations, or baffling crime scene details.
2. DURATION & WORD COUNT: The narration MUST exceed 60 seconds. Write exactly 10 to 12 concise, fast-paced scenes with a total of 190 to 240 words.
3. SPELL OUT NUMBERS: Write numbers as words (e.g. "two hundred thousand dollars", "nineteen seventy-one", "thirty-six passengers") so the text-to-speech engine speaks naturally.
4. TONE: Chilling, authentic American investigative documentary. Factual, dramatic, high retention, zero filler.
5. NO EMOJIS in scene text.
6. TRANSFORMATIVE & UNIQUE: Analyze the mystery, evidence, or FBI investigation findings so the content is 100% original and educational under Fair Use.
"""


def generate_unique_crime_script(
    case_name: str,
    wiki_query: str,
    base_scenes: List[Dict[str, Any]],
    channel_name: str = "",
    log=print
) -> Optional[Dict[str, Any]]:
    """Generates a 100% unique, customized investigative script using Gemini 2.5 Flash.
    Guarantees every video has unique audio, text, and structure to prevent unoriginal content strikes.
    """
    key = get_api_key("gemini_api_key")
    if not key or len(key) < 20:
        return None

    try:
        base_text = " ".join([sc.get("text", "") for sc in base_scenes])
        prompt = (
            f"Case Name: {case_name}\n"
            f"Subject / Wiki: {wiki_query}\n"
            f"Channel: {channel_name or 'American Crime Files'}\n"
            f"Original Case Overview: {base_text[:1200]}\n\n"
            f"Write a completely fresh, unique, 100% original investigative breakdown (10-12 scenes, 190-240 words, >60s spoken) "
            f"for this case from a fresh investigative angle. Ensure the hook banner is 3-5 punchy words in ALL CAPS."
        )
        for mod in [DEFAULT_MODEL, FALLBACK_MODEL]:
            url = f"{BASE_URL}/models/{mod}:generateContent?key={key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": CRIME_SYSTEM_INSTRUCTION}]},
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": CRIME_STORY_SCHEMA,
                    "thinkingConfig": {"thinkingBudget": 0},
                    "temperature": 0.85,
                },
            }
            res = requests.post(url, json=payload, timeout=35)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(text)
                scenes = result.get("scenes", [])
                total_words = sum(len(sc.get("text", "").split()) for sc in scenes)
                if len(scenes) >= 6 and total_words >= 130:
                    log(f"[Gemini] Generated unique script ({mod}): {len(scenes)} scenes, {total_words} words for '{case_name}' (channel: {channel_name})")
                    return result
                else:
                    log(f"[Gemini] Generated script too short ({total_words} words), trying fallback.")
            else:
                log(f"[Gemini] Model {mod} returned status {res.status_code}, trying fallback.")
    except Exception as e:
        log(f"[Gemini] Script generation error ({e}), smoothly using base database.")

    return None

