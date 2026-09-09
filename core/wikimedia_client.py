"""Wikimedia Commons & Wikipedia Client.
Searches and downloads authentic historical archive photos, crime scene images,
suspect portraits, and official investigation documents via public MediaWiki API.
100% Free, no API key required.
"""
from __future__ import annotations

import os
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from core.paths import CACHE_DIR

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIMEDIA_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "TrueCrimeAutomation/2.0 (educational documentary media; contact@automation.local)"


class WikimediaClient:
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = (cache_dir or CACHE_DIR) / "wikimedia"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {"User-Agent": USER_AGENT}

    def search_page_images(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """Searches Wikipedia article images related to a historical case or person."""
        images = []
        try:
            # 1. Search Wikipedia for most relevant article title
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "utf8": 1,
                "srlimit": 3
            }
            r = requests.get(WIKIPEDIA_API, params=search_params, headers=self.headers, timeout=12)
            if r.status_code != 200:
                return []

            search_results = r.json().get("query", {}).get("search", [])
            if not search_results:
                return []

            page_title = search_results[0]["title"]

            # 2. Get lead image / thumbnail and page images
            info_params = {
                "action": "query",
                "titles": page_title,
                "prop": "pageimages|images",
                "pithumbsize": 1080,
                "format": "json",
                "utf8": 1
            }
            r_info = requests.get(WIKIPEDIA_API, params=info_params, headers=self.headers, timeout=12)
            if r_info.status_code == 200:
                pages = r_info.json().get("query", {}).get("pages", {})
                for pid, pdata in pages.items():
                    if "thumbnail" in pdata:
                        images.append({
                            "title": page_title,
                            "url": pdata["thumbnail"]["source"],
                            "width": pdata["thumbnail"].get("width", 1080),
                            "height": pdata["thumbnail"].get("height", 1080)
                        })

            # 3. Search Wikimedia Commons for additional archival photos
            commons_params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": f"{query} filetype:bitmap",
                "gsrlimit": limit,
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
                "iiurlwidth": 1080,
                "format": "json",
                "utf8": 1
            }
            r_comm = requests.get(WIKIMEDIA_COMMONS_API, params=commons_params, headers=self.headers, timeout=15)
            if r_comm.status_code == 200:
                comm_pages = r_comm.json().get("query", {}).get("pages", {})
                for pid, cdata in comm_pages.items():
                    infos = cdata.get("imageinfo", [])
                    if infos:
                        info = infos[0]
                        img_url = info.get("thumburl") or info.get("url")
                        mime = info.get("mime", "")
                        if img_url and ("image/jpeg" in mime or "image/png" in mime or "image/webp" in mime):
                            images.append({
                                "title": cdata.get("title", ""),
                                "url": img_url,
                                "width": info.get("width", 1080),
                                "height": info.get("height", 1080)
                            })
        except Exception as e:
            print(f"[Wikimedia] Error searching images for '{query}': {e}")

        # Deduplicate by URL
        seen = set()
        deduped = []
        for img in images:
            if img["url"] not in seen:
                seen.add(img["url"])
                deduped.append(img)
        return deduped[:limit]

    def download_image(self, url: str, prefix: str = "wiki") -> Optional[Path]:
        """Downloads an image from URL and caches it locally."""
        try:
            # Generate deterministic filename from URL
            url_clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", Path(urllib.parse.urlparse(url).path).name)
            if not url_clean or len(url_clean) < 4:
                url_clean = f"img_{abs(hash(url))}.jpg"
            if not any(url_clean.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                url_clean += ".jpg"

            dest = self.cache_dir / f"{prefix}_{url_clean}"
            if dest.exists() and dest.stat().st_size > 5000:
                return dest

            r = requests.get(url, headers=self.headers, timeout=20)
            if r.status_code == 200 and len(r.content) > 5000:
                with open(dest, "wb") as f:
                    f.write(r.content)
                return dest
        except Exception as e:
            print(f"[Wikimedia] Download error for {url}: {e}")
        return None

    def get_case_visuals(self, case_query: str, count: int = 4) -> List[Path]:
        """Fetches and downloads top authentic historical photos for a case."""
        results = self.search_page_images(case_query, limit=count * 2)
        downloaded = []
        for res in results:
            if len(downloaded) >= count:
                break
            p = self.download_image(res["url"], prefix="case")
            if p and p.exists():
                downloaded.append(p)
        return downloaded
