"""MyInstants integration: Free search & automatic download of viral SFX."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from core.paths import SFX_DIR

MYINSTANTS_API = "https://www.myinstants.com/api/v1/instants/"
TIMEOUT = 15


class MyInstantsClient:
    def __init__(self, sfx_dir: Optional[Path] = None):
        self.sfx_dir = sfx_dir or SFX_DIR
        self.sfx_dir.mkdir(parents=True, exist_ok=True)

    def search_sounds(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search MyInstants for sound effects (Free, no API key required)."""
        try:
            r = requests.get(MYINSTANTS_API, params={"name": query}, timeout=TIMEOUT)
            if r.status_code == 200:
                results = r.json().get("results") or []
                return results[:limit]
        except Exception as e:
            print(f"[MyInstants] Search error for '{query}': {e}")
        return []

    def download_sound(self, sound_name_or_query: str) -> Optional[Path]:
        """Download sound effect by name/keyword and cache locally."""
        # Sanitize filename
        safe_name = "".join(c for c in sound_name_or_query.lower() if c.isalnum() or c in ("-", "_")).strip()
        local_target = self.sfx_dir / f"{safe_name}.mp3"

        if local_target.exists() and local_target.stat().st_size > 1000:
            return local_target

        results = self.search_sounds(sound_name_or_query, limit=3)
        if not results:
            return None

        top_sound = results[0]
        sound_url = top_sound.get("sound")
        if not sound_url:
            return None

        try:
            r = requests.get(sound_url, timeout=TIMEOUT)
            if r.status_code == 200:
                with open(local_target, "wb") as f:
                    f.write(r.content)
                print(f"[MyInstants] Downloaded: {top_sound.get('name')} -> {local_target.name}")
                return local_target
        except Exception as e:
            print(f"[MyInstants] Download error from {sound_url}: {e}")

        return None


def download_popular_viral_sfx() -> List[Path]:
    """Pre-downloads essential viral TikTok meme SFX."""
    client = MyInstantsClient()
    popular = [
        "vine boom",
        "bruh sound effect",
        "record scratch",
        "metal pipe falling",
        "dramatic dun dun dun",
        "anime wow",
    ]
    downloaded = []
    for s in popular:
        p = client.download_sound(s)
        if p and p.exists():
            downloaded.append(p)
    return downloaded
