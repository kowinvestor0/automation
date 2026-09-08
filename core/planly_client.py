"""Planly API client for Multi-Account support and reliable publishing."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import requests

BASE_URL = "https://app.planly.com/api/v2"
TIMEOUT = 120
UPLOAD_TIMEOUT = 900


class PlanlyError(RuntimeError):
    pass


class PlanlyClient:
    def __init__(self, token: str, team_id: str):
        self.token = token.strip()
        self.team_id = team_id.strip()

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _post(self, endpoint: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{BASE_URL}{endpoint}"
        try:
            r = requests.post(url, headers=self.headers, json=body, timeout=TIMEOUT)
        except Exception as e:
            raise PlanlyError(f"Network error calling {endpoint}: {e}")

        if r.status_code == 401:
            raise PlanlyError("Planly rejected the API key (401 Unauthorized). Check Settings > Security in Planly.")
        if r.status_code == 429:
            raise PlanlyError("Planly rate limit reached (429). Please wait a moment.")
        if r.status_code >= 400:
            raise PlanlyError(f"{endpoint} failed with HTTP {r.status_code}: {r.text[:200]}")

        try:
            data = r.json()
        except ValueError:
            raise PlanlyError(f"Invalid JSON returned from {endpoint}: {r.text[:200]}")

        if isinstance(data, dict) and data.get("error"):
            raise PlanlyError(f"{endpoint} returned error: {data['error']}")
        return data

    def test_connection(self) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Validate token & team_id and fetch available channels."""
        if not self.token or len(self.token) < 16:
            return False, "API token is missing or too short.", []
        if not self.team_id:
            return False, "Team ID is required.", []

        try:
            channels = self.list_channels()
            networks = sorted({(c.get("social_network") or "?") for c in channels})
            msg = f"Connected successfully: {len(channels)} channels ({', '.join(networks)})"
            return True, msg, channels
        except Exception as e:
            return False, str(e), []

    def list_channels(self) -> List[Dict[str, Any]]:
        """Fetch all connected social channels for this team."""
        res = self._post("/channels/list", {"team_id": self.team_id})
        return res.get("data") or []

    def upload_video(self, video_path: Path, log=print) -> str:
        """Upload video via Planly 3-step presigned S3 URL. Returns mediaId."""
        p = Path(video_path)
        if not p.exists():
            raise FileNotFoundError(f"Video file not found: {p}")

        size = p.stat().st_size
        name = p.name

        log(f"[Planly] 1/3 Starting upload for {name} ({size / (1 << 20):.1f} MB)...")
        start = self._post("/media/start-upload", {
            "teamId": self.team_id,
            "contentLength": size,
            "contentType": "video/mp4",
            "fileName": name,
        })
        media_id = start.get("mediaId")
        upload_url = start.get("uploadUrl")
        if not media_id or not upload_url:
            raise PlanlyError(f"Planly start-upload returned no upload target: {str(start)[:200]}")

        put_headers = start.get("headers") or {
            "Content-Type": "video/mp4",
            "Content-Length": str(size),
        }

        log(f"[Planly] 2/3 Streaming file to S3...")
        with open(p, "rb") as f:
            r = requests.put(upload_url, data=f, headers=put_headers, timeout=UPLOAD_TIMEOUT)
        if r.status_code >= 400:
            raise PlanlyError(f"S3 upload failed with HTTP {r.status_code}: {r.text[:200]}")

        log(f"[Planly] 3/3 Finalizing upload for mediaId {media_id}...")
        done = self._post("/media/finish-upload", {"mediaId": media_id})
        info = done.get("data") or {}
        res = info.get("resolution") or {}
        log(f"[Planly] Uploaded {name} successfully (mediaId: {media_id})")
        return str(media_id)

    def schedule_posts(self, schedules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create posts on Planly calendar using /schedule-groups/create.

        Each entry:
        {
            "channel_id": "...",
            "media_id": "...",
            "publish_on": "2026-09-07T02:00:00.000Z" or None (immediate),
            "caption": "...",
            "options": {"postType": 0, "disableDuet": True, ...}
        }
        """
        groups = []
        for s in schedules:
            opts = dict(s.get("options") or {})
            opts["postType"] = opts.get("postType", 0)
            # TikTok & Planly strict rule: videos over 60s MUST have duet and stitch disabled
            opts["disableDuet"] = True
            opts["disableStitch"] = True
            if "disableComment" not in opts:
                opts["disableComment"] = False

            sch = {
                "channelId": s["channel_id"],
                "content": s.get("caption", ""),
                "status": 1,
                "media": [{"id": s["media_id"]}],
                "options": opts,
            }
            grp = {"schedules": [sch]}
            if s.get("publish_on"):
                grp["publishOn"] = s["publish_on"]
            groups.append(grp)

        chunk_size = 10
        all_results = []
        for i in range(0, len(groups), chunk_size):
            chunk = groups[i:i + chunk_size]
            res = self._post("/schedule-groups/create", {
                "teamId": self.team_id,
                "scheduleGroups": chunk,
            })
            all_results.append(res)

        return {"status": "success", "batches": len(all_results), "data": all_results}

    def list_scheduled_groups(self) -> List[Dict[str, Any]]:
        """List all scheduled groups currently waiting on Planly calendar."""
        all_groups = []
        seen_ids = set()
        next_token = None
        for _ in range(50):  # Safety bound
            body = {"teamId": self.team_id, "status": "scheduled"}
            if next_token:
                body["next"] = next_token
            res = self._post("/schedule-groups/list", body)
            data = res.get("data") or {}
            rows = data.get("rows") or []
            new_added = 0
            for r in rows:
                rid = r.get("id")
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    all_groups.append(r)
                    new_added += 1
            next_token = data.get("next")
            if not next_token or new_added == 0:
                break
        return all_groups

    def delete_schedule_groups(self, group_ids: List[str]) -> bool:
        """Delete multiple schedule groups in batch from Planly."""
        if not group_ids:
            return True
        res = self._post("/schedule-groups/delete", {
            "teamId": self.team_id,
            "ids": group_ids
        })
        return bool(res.get("data", False))

    def delete_schedule_group(self, group_id: str) -> bool:
        """Delete a single schedule group from Planly."""
        return self.delete_schedule_groups([group_id])

    def clear_all_scheduled_posts(self, log=print) -> int:
        """Deletes all scheduled posts from Planly calendar using batch delete."""
        total_deleted = 0
        while True:
            res = self._post("/schedule-groups/list", {"teamId": self.team_id, "status": "scheduled"})
            data = res.get("data") or {}
            rows = data.get("rows") or []
            if not rows:
                break
            ids = [r["id"] for r in rows if "id" in r]
            if not ids:
                break
            self.delete_schedule_groups(ids)
            total_deleted += len(ids)
            log(f"[Planly] Đã xóa lô {len(ids)} bài viết. Tổng cộng đã xóa: {total_deleted}...")
        log(f"[Planly] Hoàn tất: Đã xóa toàn bộ {total_deleted} bài viết trên Planly.")
        return total_deleted
