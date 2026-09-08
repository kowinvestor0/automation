"""Scraper for high-retention viral video clips using yt-dlp."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yt_dlp

from core.paths import CACHE_DIR
from core.config_manager import load_config


class VideoScraper:
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (CACHE_DIR / "sources")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _ydl_base_opts(self, out_template: str, download: bool = True) -> Dict[str, Any]:
        return {
            "outtmpl": out_template,
            "format": "bestvideo[height<=1920][ext=mp4]+bestaudio[ext=m4a]/best[height<=1920][ext=mp4]/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "extract_flat": not download,
            "socket_timeout": 35,
            "retries": 3,
        }

    def search_viral_clips(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search YouTube for high-view viral clips (prioritizing duration >= 60s)."""
        search_query = f"ytsearch{limit * 8}:{query}"
        opts = self._ydl_base_opts("", download=False)
        candidates = []

        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                res = ydl.extract_info(search_query, download=False)
            except Exception as e:
                print(f"[Scraper] Search failed for '{query}': {e}")
                return []

            entries = res.get("entries") or []
            for entry in entries:
                if not entry:
                    continue
                vid_id = entry.get("id")
                title = entry.get("title", "")
                dur = entry.get("duration")
                views = entry.get("view_count") or 0

                if not vid_id:
                    continue
                # Accept clips from 20s to 360s
                if dur is not None and (dur < 20 or dur > 360):
                    continue

                candidates.append({
                    "id": vid_id,
                    "title": title,
                    "url": entry.get("webpage_url") or f"https://www.youtube.com/watch?v={vid_id}",
                    "duration": dur or 65.0,
                    "view_count": views,
                    "description": entry.get("description", ""),
                    "uploader": entry.get("uploader", ""),
                })

        # User priority: prioritize videos >= 60 seconds (> 1 minute for TikTok monetization)
        candidates.sort(key=lambda x: (x["duration"] >= 60.0, x["view_count"]), reverse=True)
        return candidates[:limit]

    def download_clip(self, url: str) -> Optional[Dict[str, Any]]:
        """Download one video clip and return full metadata and local path."""
        out_tmpl = str(self.cache_dir / "%(id)s.%(ext)s")
        opts = self._ydl_base_opts(out_tmpl, download=True)

        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
            except Exception as e:
                print(f"[Scraper] Download failed for {url}: {e}")
                return None

            if not info:
                return None

            vid_id = info.get("id")
            vid_path = self.cache_dir / f"{vid_id}.mp4"
            if not vid_path.exists():
                # Search if saved under another extension
                for f in self.cache_dir.glob(f"{vid_id}.*"):
                    if f.suffix in (".mp4", ".mkv", ".webm"):
                        vid_path = f
                        break

            return {
                "id": vid_id,
                "title": info.get("title", ""),
                "url": url,
                "video_path": str(vid_path),
                "duration": float(info.get("duration") or 35.0),
                "description": (info.get("description") or "")[:500],
                "uploader": info.get("uploader", ""),
            }

    def fetch_batch_for_generation(self, count: int = 1, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches and downloads a batch of viral clips ready for rendering."""
        cfg = load_config()
        queries = cfg.get("search_queries", ["unexpected viral shorts"])
        active_q = query or queries[0]

        print(f"[Scraper] Searching clips for: '{active_q}'...")
        candidates = self.search_viral_clips(active_q, limit=max(count * 2, 4))
        downloaded = []

        for c in candidates:
            if len(downloaded) >= count:
                break
            meta = self.download_clip(c["url"])
            if meta and Path(meta["video_path"]).exists():
                downloaded.append(meta)

        return downloaded
