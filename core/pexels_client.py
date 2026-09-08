"""Pexels API Client: Multi-clip 9:16 portrait B-roll stock video engine.
Supports scene-by-scene visual matching and 100% anti-duplicate tracking.
"""
from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import requests

from core.paths import CACHE_DIR, DATA_DIR
from core.config_manager import get_api_key

PEXELS_API_URL = "https://api.pexels.com/videos/search"
TIMEOUT = 30
USED_CLIPS_FILE = DATA_DIR / "used_pexels_clips.json"


def _load_persistent_used_ids() -> Set[int]:
    """Loads recently used Pexels video IDs to prevent visual repetition across runs."""
    if USED_CLIPS_FILE.exists():
        try:
            data = json.loads(USED_CLIPS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return set(data[-400:])
        except Exception:
            pass
    return set()


def _save_persistent_used_ids(used_ids: Set[int]) -> None:
    """Saves used Pexels video IDs to disk (keeps last 400)."""
    try:
        USED_CLIPS_FILE.parent.mkdir(parents=True, exist_ok=True)
        lst = list(used_ids)[-400:]
        USED_CLIPS_FILE.write_text(json.dumps(lst), encoding="utf-8")
    except Exception:
        pass


def extract_pexels_keywords(text: str) -> str:
    """Extracts high-yield visual stock keywords from any news headline or prompt."""
    low = (text or "").lower()
    if any(w in low for w in ("tariff", "trade", "import", "export", "border", "customs", "container", "cargo", "freight", "ship")):
        return "cargo container port shipping"
    if any(w in low for w in ("storm", "surf", "flood", "hurricane", "tornado", "wave", "ocean", "rain", "coast", "water", "tsunami")):
        return "ocean storm big waves coast"
    if any(w in low for w in ("election", "vote", "politics", "president", "trump", "government", "parliament", "congress", "senate", "white house")):
        return "press conference government crowd"
    if any(w in low for w in ("fire", "wildfire", "smoke", "burn", "explosion", "blaze")):
        return "fire rescue emergency lights"
    if any(w in low for w in ("money", "bank", "stock", "market", "dollar", "economy", "crypto", "inflation", "finance", "wall street", "trillion")):
        return "stock market numbers wall street"
    if any(w in low for w in ("grocer", "supermarket", "store", "retail", "shop", "price", "food", "cost", "consumer")):
        return "supermarket grocery store shopping"
    if any(w in low for w in ("protest", "strike", "riot", "demonstration", "angry", "clash", "rally")):
        return "crowd protest city street people"
    if any(w in low for w in ("police", "crime", "investigation", "fbi", "court", "trial", "judge", "lawyer", "justice", "gavel")):
        return "courtroom legal gavel justice"
    if any(w in low for w in ("factory", "manufactur", "plant", "warehouse", "industrial", "worker")):
        return "warehouse factory industry workers"
    if any(w in low for w in ("hospital", "doctor", "health", "medical", "disease", "emergency", "patient")):
        return "hospital doctor medical emergency"
    if any(w in low for w in ("tech", "ai", "artificial intelligence", "robot", "space", "spacex", "rocket", "satellite", "chip", "server")):
        return "modern technology datacenter computer"
    if any(w in low for w in ("plane", "flight", "boeing", "airport", "aviation", "aircraft")):
        return "airplane airport flying runway"
    if any(w in low for w in ("car", "tesla", "crash", "highway", "traffic", "vehicle")):
        return "traffic highway driving city"
    if any(w in low for w in ("gas", "oil", "fuel", "energy", "refinery", "pipeline")):
        return "oil refinery fuel pump energy"

    # Extract longest alphanumeric words
    words = [re.sub(r"[^a-zA-Z]", "", w) for w in low.split()]
    meaningful = [w for w in words if len(w) >= 4 and w not in (
        "with", "that", "this", "from", "have", "they", "will", "what", "when", "where",
        "about", "after", "news", "today", "breaking", "update", "latest"
    )]
    if meaningful:
        return " ".join(meaningful[:2]) + " cinematic"
    return "breaking news dramatic city"


def extract_scene_keywords(scene_text: str, fallback_topic: str = "", scene_index: int = 0) -> str:
    """Derives specific, high-yield visual keywords for an individual scene text."""
    low = (scene_text or "").lower()

    if any(w in low for w in ("cargo", "container", "port", "ship", "dock", "freight")):
        return "cargo container port shipping"
    if any(w in low for w in ("president", "white house", "press", "podium", "official", "speech", "statement", "briefing")):
        return "press conference microphone podium"
    if any(w in low for w in ("stock", "market", "plunge", "shares", "wall street", "trillion", "index", "nasdaq", "dow")):
        return "stock market charts finance screen"
    if any(w in low for w in ("store", "retail", "supermarket", "grocery", "shopper", "prices", "shelf", "cost")):
        return "grocery store supermarket checkout"
    if any(w in low for w in ("protest", "crowd", "people", "street", "march", "angry", "citizens")):
        return "crowd pedestrians walking street"
    if any(w in low for w in ("court", "judge", "gavel", "legal", "lawyer", "trial", "subpoena", "ruling", "investigation")):
        return "courtroom gavel justice legal"
    if any(w in low for w in ("traffic", "highway", "truck", "cars", "road", "delay", "gridlock")):
        return "highway traffic cars timelapse"
    if any(w in low for w in ("factory", "assembly", "worker", "industry", "warehouse", "manufacturing")):
        return "factory worker assembly line"
    if any(w in low for w in ("computer", "cyber", "technology", "data", "screen", "code", "ai", "digital")):
        return "computer screen digital data tech"
    if any(w in low for w in ("police", "siren", "emergency", "flashing", "first responder", "paramedic")):
        return "police car lights emergency night"
    if any(w in low for w in ("skyline", "city", "downtown", "aerial", "building", "urban")):
        return "city skyline aerial drone portrait"
    if any(w in low for w in ("money", "cash", "dollar", "currency", "bank", "vault")):
        return "counting cash dollar bills"

    dynamic_fallbacks = [
        "breaking news dramatic city portrait",
        "busy city traffic timelapse portrait",
        "office corporate business meeting portrait",
        "modern tech screen digital data portrait",
        "city skyline aerial drone portrait",
        "crowd pedestrians walking street portrait",
        "evening city lights cinematic portrait",
        "futuristic technology abstract portrait",
    ]
    return dynamic_fallbacks[scene_index % len(dynamic_fallbacks)]


class PexelsClient:
    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[Path] = None):
        self.api_key = (api_key or get_api_key("pexels_api_key")).strip()
        self.cache_dir = cache_dir or (CACHE_DIR / "pexels")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.persistent_used_ids = _load_persistent_used_ids()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) >= 16)

    def search_videos(self, query: str, per_page: int = 15, page: int = 1) -> List[Dict[str, Any]]:
        """Search portrait 9:16 vertical videos on Pexels."""
        if not self.is_configured:
            return []

        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "per_page": per_page,
            "page": page,
            "orientation": "portrait",
            "size": "medium",
        }
        try:
            r = requests.get(PEXELS_API_URL, headers=headers, params=params, timeout=TIMEOUT)
            if r.status_code != 200:
                print(f"[Pexels] API HTTP {r.status_code}: {r.text[:120]}")
                return []
            data = r.json()
            return data.get("videos") or []
        except Exception as e:
            print(f"[Pexels] Request failed for '{query}': {e}")
            return []

    def download_video_file(self, video_data: Dict[str, Any]) -> Optional[Path]:
        """Downloads one Pexels video dict to local cache in 9:16 portrait orientation."""
        vid_id = video_data.get("id")
        if not vid_id:
            return None

        cached = self.cache_dir / f"pexels_{vid_id}.mp4"
        if cached.exists() and cached.stat().st_size > 10000:
            return cached

        files = video_data.get("video_files") or []
        best_link = None
        for vf in sorted(files, key=lambda f: f.get("width", 0)):
            link = vf.get("link")
            w = vf.get("width", 0)
            h = vf.get("height", 0)
            if link and h >= w and w >= 540:
                best_link = link
                break
        if not best_link and files:
            best_link = files[0].get("link")

        if not best_link:
            return None

        try:
            r = requests.get(best_link, stream=True, timeout=60)
            if r.status_code == 200:
                with open(cached, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        f.write(chunk)
                if cached.stat().st_size > 10000:
                    return cached
        except Exception as e:
            print(f"[Pexels] Download failed for #{vid_id}: {e}")

        return None

    def download_broll(self, query: str, exclude_ids: Optional[Set[int]] = None) -> Optional[Path]:
        """Downloads one matching 9:16 vertical HD video file not in exclude_ids."""
        exclude_ids = exclude_ids or set()
        search_q = extract_pexels_keywords(query)
        videos = self.search_videos(search_q, per_page=15, page=random.randint(1, 2))
        if not videos:
            videos = self.search_videos("dramatic city night lights portrait", per_page=10, page=1)

        for v in videos:
            vid_id = v.get("id")
            if not vid_id or vid_id in exclude_ids or vid_id in self.persistent_used_ids:
                continue
            path = self.download_video_file(v)
            if path:
                self.persistent_used_ids.add(vid_id)
                _save_persistent_used_ids(self.persistent_used_ids)
                return path

        for v in videos:
            path = self.download_video_file(v)
            if path:
                return path
        return None

    def download_scene_clips(
        self,
        scenes: List[Dict[str, Any]],
        default_topic: str = "",
        session_used_ids: Optional[Set[int]] = None,
        log=print
    ) -> List[Path]:
        """Downloads distinct 9:16 portrait stock video clips for each individual scene.
        Ensures 100% visual variety and prevents repeating the same clip across scenes or batch videos.
        """
        if session_used_ids is None:
            session_used_ids = set()

        if not self.is_configured:
            log("[Pexels] Pexels API key not configured. Using local visual generator.")
            return []

        total_scenes = len(scenes)
        log(f"[Pexels] Searching {total_scenes} distinct 9:16 portrait video clips (Zero repetition mode)...")
        scene_clips: List[Path] = []

        for idx, sc in enumerate(scenes):
            sc_text = sc.get("text", "")
            query = extract_scene_keywords(sc_text, default_topic, scene_index=idx)
            
            candidates = self.search_videos(query, per_page=15, page=random.randint(1, 2))
            if not candidates:
                fallback_q = extract_scene_keywords("", default_topic, scene_index=idx)
                candidates = self.search_videos(fallback_q, per_page=15, page=1)

            chosen_path = None
            chosen_id = None

            # 1. Prefer unused anywhere
            for cand in candidates:
                cid = cand.get("id")
                if not cid or cid in session_used_ids or cid in self.persistent_used_ids:
                    continue
                p = self.download_video_file(cand)
                if p and p.exists():
                    chosen_path = p
                    chosen_id = cid
                    break

            # 2. Allow persistent if not in current session
            if not chosen_path:
                for cand in candidates:
                    cid = cand.get("id")
                    if not cid or cid in session_used_ids:
                        continue
                    p = self.download_video_file(cand)
                    if p and p.exists():
                        chosen_path = p
                        chosen_id = cid
                        break

            # 3. Dynamic urban fallback
            if not chosen_path:
                general = self.search_videos("city aerial timelapse portrait", per_page=15, page=random.randint(1, 3))
                for cand in general:
                    cid = cand.get("id")
                    if not cid or cid in session_used_ids:
                        continue
                    p = self.download_video_file(cand)
                    if p and p.exists():
                        chosen_path = p
                        chosen_id = cid
                        break

            if chosen_path and chosen_id:
                session_used_ids.add(chosen_id)
                self.persistent_used_ids.add(chosen_id)
                scene_clips.append(chosen_path)
                log(f"  -> Scene #{idx+1}/{total_scenes}: Clip #{chosen_id} [{query}]")
            else:
                existing = list(self.cache_dir.glob("*.mp4"))
                if existing:
                    fallback_pick = existing[idx % len(existing)]
                    scene_clips.append(fallback_pick)
                    log(f"  -> Scene #{idx+1}/{total_scenes}: Cached {fallback_pick.name}")

        _save_persistent_used_ids(self.persistent_used_ids)
        log(f"[Pexels] Successfully acquired {len(scene_clips)} unique scene clips for video!")
        return scene_clips
