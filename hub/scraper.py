"""Scraper for viral Shorts videos using yt-dlp.

Finds and downloads high-retention viral clips based on queries or channel URLs,
extracting metadata for AI commentary generation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yt_dlp

from hub.paths import CODE

DEFAULT_CONFIG_PATH = CODE / "hub" / "viral_config.json"


def load_viral_config(path: Optional[Path] = None) -> Dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG_PATH
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "queries": [
            "unexpected caught on camera shorts",
            "crazy science experiment shorts",
            "wild animals unexpected encounters shorts",
            "incredible human skill shorts",
            "bizarre mystery phenomena shorts",
        ],
        "channels": [],
        "min_duration": 15,
        "max_duration": 60,
        "min_views": 10000,
        "cache_dir": "cache/viral_sources",
    }


class ViralScraper:
    def __init__(self, config: Optional[Dict[str, Any]] = None, cache_dir: Optional[Path] = None):
        self.cfg = config or load_viral_config()
        base_dir = CODE
        self.cache_dir = cache_dir or (base_dir / self.cfg.get("cache_dir", "cache/viral_sources"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _ydl_opts(self, out_template: str, download: bool = True) -> Dict[str, Any]:
        return {
            "outtmpl": out_template,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "extract_flat": not download,
            "socket_timeout": 30,
            "retries": 3,
        }

    def search_shorts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search YouTube for viral Shorts matching query."""
        clean_q = query if "#shorts" in query.lower() else f"#shorts {query}"
        batch_size = max(limit * 15, 30)
        search_query = f"ytsearch{batch_size}:{clean_q}"
        opts = self._ydl_opts("", download=False)
        candidates = []
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                result = ydl.extract_info(search_query, download=False)
            except Exception as e:
                print(f"[scraper] Search failed for '{query}': {e}")
                return []

            entries = result.get("entries") or []
            min_dur = self.cfg.get("min_duration", 10)
            max_dur = self.cfg.get("max_duration", 60)
            min_views = self.cfg.get("min_views", 0)

            recent_topics = set()
            try:
                from hub import state as hub_state
                recent_topics = hub_state.recent_topics(60)
            except Exception:
                pass

            for entry in entries:
                if not entry:
                    continue
                duration = entry.get("duration")
                views = entry.get("view_count") or 0
                vid_id = entry.get("id")
                title = entry.get("title", "")
                if not vid_id:
                    continue

                if f"viral_{vid_id}" in recent_topics:
                    continue

                # Filter duration: target Shorts (10s to 60s)
                if duration is not None:
                    if duration < min_dur or duration > max_dur:
                        continue
                else:
                    # Flat extraction might not have duration; check title for shorts keyword
                    if "#shorts" not in title.lower() and "short" not in title.lower():
                        continue

                # If minimum views filter is set and view count is known
                if min_views > 0 and views > 0 and views < min_views:
                    continue

                # Check if already cached
                if (self.cache_dir / f"{vid_id}.mp4").exists():
                    continue

                candidates.append({
                    "id": vid_id,
                    "title": entry.get("title", ""),
                    "url": entry.get("webpage_url") or f"https://www.youtube.com/watch?v={vid_id}",
                    "duration": duration,
                    "view_count": views,
                    "uploader": entry.get("uploader", ""),
                })
                if len(candidates) >= limit:
                    break

        return candidates

    def download_clip(self, url: str) -> Optional[Dict[str, Any]]:
        """Download one video clip and extract full metadata."""
        out_tmpl = str(self.cache_dir / "%(id)s.%(ext)s")
        opts = {
            "outtmpl": out_tmpl,
            "format": "bestvideo[height<=1920][ext=mp4]+bestaudio[ext=m4a]/best[height<=1920][ext=mp4]/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "socket_timeout": 60,
            "retries": 3,
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
            except Exception as e:
                print(f"[scraper] Download failed for {url}: {e}")
                return None

            if not info:
                return None

            vid_id = info.get("id")
            dur = info.get("duration") or 0
            if dur > 90:
                print(f"[scraper] Clip {vid_id} is too long ({dur}s > 90s), skipping")
                target_file = self.cache_dir / f"{vid_id}.mp4"
                if target_file.exists():
                    target_file.unlink(missing_ok=True)
                return None

            target_file = self.cache_dir / f"{vid_id}.mp4"
            if not target_file.exists():
                # Check for possible different extension
                candidates = list(self.cache_dir.glob(f"{vid_id}.*"))
                candidates = [c for c in candidates if c.suffix != ".json"]
                if candidates:
                    target_file = candidates[0]
                else:
                    return None

            meta = {
                "id": vid_id,
                "title": info.get("title", ""),
                "description": info.get("description", ""),
                "uploader": info.get("uploader", ""),
                "duration": info.get("duration", 0),
                "view_count": info.get("view_count", 0),
                "tags": info.get("tags") or [],
                "categories": info.get("categories") or [],
                "url": info.get("webpage_url") or url,
                "video_path": str(target_file.resolve()),
            }

            meta_file = self.cache_dir / f"{vid_id}.meta.json"
            meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
            return meta

    def fetch_batch(self, count: int = 1, query: Optional[str] = None, language: str = "us") -> List[Dict[str, Any]]:
        """Fetch a batch of fresh viral clips."""
        if query:
            queries = [query]
        elif language in ("mx", "es"):
            queries = list(self.cfg.get("queries_mx", [])) or ["videos virales momentos insolitos shorts"]
        else:
            queries = list(self.cfg.get("queries", [])) or ["unexpected caught on camera shorts"]

        import random
        random.shuffle(queries)

        downloaded = []
        for q in queries:
            print(f"[scraper] Searching for: '{q}'...")
            candidates = self.search_shorts(q, limit=count)
            for cand in candidates:
                print(f"[scraper] Downloading: {cand['title'][:50]} ({cand['url']})...")
                meta = self.download_clip(cand["url"])
                if meta:
                    downloaded.append(meta)
                    print(f"[scraper] OK: {meta['id']} saved to {meta['video_path']}")
                    if len(downloaded) >= count:
                        return downloaded
        return downloaded
