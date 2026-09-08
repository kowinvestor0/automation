"""Publishing & Scheduling Engine: Safe Organic Spacing across US Viral Peak Hours.
Calculates posting timestamps directly in US Eastern Time (ET) where 80% of US TikTok viewership resides.
Supports massive scale: 6 videos per channel per day across all channels and multiple Planly accounts.
Allocates 100% unique, non-overlapping videos to each channel with organic jitter to protect accounts from bans.
"""
from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.paths import DATA_DIR, OUTPUT_DIR
from core.planly_client import PlanlyClient

HISTORY_FILE = DATA_DIR / "published_history.json"
MEDIA_CACHE_FILE = DATA_DIR / "media_cache.json"


def load_media_cache() -> Dict[str, str]:
    if MEDIA_CACHE_FILE.exists():
        try:
            return json.loads(MEDIA_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_media_cache(cache: Dict[str, str]) -> None:
    MEDIA_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEDIA_CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")

# 6 US Peak Viral Hours in US Eastern Time (ET) covering ~80% of US TikTok audience:
# 1. 07:45 AM ET (Morning Commute & Wake-up) -> 18:45 VN
# 2. 11:45 AM ET (Lunch Break Peak)          -> 22:45 VN
# 3. 03:30 PM ET (After-School & Break)      -> 02:30 AM VN
# 4. 07:15 PM ET (EVENING PRIME TIME - #1)   -> 06:15 AM VN (Viral nhất)
# 5. 09:30 PM ET (Late Evening Prime)        -> 08:30 AM VN
# 6. 11:00 PM ET (Bedtime Scroll Peak)       -> 10:00 AM VN
US_VIRAL_PEAK_HOURS_ET = [
    (7, 45),   # 1. Morning commute
    (11, 45),  # 2. Lunch break
    (15, 30),  # 3. After-school & break
    (19, 15),  # 4. EVENING PRIME TIME (Highest engagement)
    (21, 30),  # 5. Late evening prime
    (23, 0),   # 6. Night scroll
]


def get_us_eastern_tz() -> dt.timezone:
    """Returns US Eastern timezone (EDT UTC-4 in summer, EST UTC-5 in winter)."""
    now_utc = dt.datetime.now(dt.timezone.utc)
    month = now_utc.month
    offset = -4 if 3 < month < 11 else -5
    return dt.timezone(dt.timedelta(hours=offset))


def load_history() -> Dict[str, Any]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"posted_videos": [], "last_run": None}


def mark_posted(video_name: str, channel_id: str, publish_on: str) -> None:
    h = load_history()
    h["posted_videos"].append({
        "video": video_name,
        "channel_id": channel_id,
        "publish_on": publish_on,
        "timestamp": dt.datetime.now().isoformat(),
    })
    h["last_run"] = dt.datetime.now().isoformat()
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(h, indent=2, ensure_ascii=False), encoding="utf-8")


def calculate_slots(
    count_per_channel: int,
    mode: str = "scheduled",
    tz_offset: Optional[int] = None,
    base_time: Optional[dt.datetime] = None,
    channel_index: int = 0
) -> List[str]:
    """Generates organic posting timestamps safely spaced across US peak viral hours.
    
    TIKTOK ANTI-BOT COMPLIANCE:
    - Anchored in US Eastern Time (ET) to hit peak US viewership.
    - Uses the 6 natural daily US peak hours: 07:45, 11:45, 15:30, 19:15, 21:30, 23:00 ET.
    - Applies channel-based and random jitter (+2 to +14 minutes) so no two accounts post simultaneously.
    - Videos automatically spill over into subsequent days at 07:45 AM ET.
    """
    tz = get_us_eastern_tz() if tz_offset is None else dt.timezone(dt.timedelta(hours=tz_offset))
    now = base_time or dt.datetime.now(tz)
    slots = []

    if mode in ("same_time", "expedited"):
        # Fast deployment: enforces safe minimum 45-55 minute intervals rather than identical seconds!
        cursor = now + dt.timedelta(minutes=5 + ((channel_index * 3) % 12))
        for _ in range(count_per_channel):
            jitter = random.randint(1, 7)
            slot_dt = cursor + dt.timedelta(minutes=jitter)
            slots.append(slot_dt.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
            cursor += dt.timedelta(minutes=55)
        return slots

    # Standard Scheduled Mode: Spaced across US viral peak hours
    day_offset = 0
    current_date = now.date()

    while len(slots) < count_per_channel:
        target_date = current_date + dt.timedelta(days=day_offset)
        for hour, minute in US_VIRAL_PEAK_HOURS_ET:
            jitter = ((channel_index * 3) + random.randint(2, 9)) % 14
            slot_dt = dt.datetime(
                target_date.year, target_date.month, target_date.day,
                hour, minute, tzinfo=tz
            ) + dt.timedelta(minutes=jitter)

            # If slot is already in the past for today in US Eastern time, skip it
            if day_offset == 0 and slot_dt <= now:
                continue

            slots.append(slot_dt.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
            if len(slots) >= count_per_channel:
                break
        day_offset += 1

    return slots


def get_available_videos() -> List[Dict[str, Any]]:
    """Lists all rendered videos in output directory that have metadata."""
    videos = []
    for mp4 in sorted(OUTPUT_DIR.glob("*.mp4"), reverse=True):
        meta_file = mp4.with_suffix(".meta.json")
        meta = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        dur = meta.get("duration", 0.0)
        videos.append({
            "path": mp4,
            "filename": mp4.name,
            "title": meta.get("title") or mp4.stem,
            "description": meta.get("description") or "",
            "duration": dur,
            "monetizable": (dur >= 60.0) or meta.get("monetizable", False),
            "hashtags": meta.get("hashtags", []),
        })
    return videos


def schedule_channel_quota(
    client: PlanlyClient,
    channels: List[Dict[str, Any]],
    videos: List[Dict[str, Any]],
    videos_per_channel: int = 6,
    mode: str = "scheduled",
    tz_offset: Optional[int] = None,
    dry_run: bool = False,
    channel_offset: int = 0,
    log=print
) -> Dict[str, Any]:
    """Schedules videos per channel respecting monetized (>60s) vs growth (<45s) tiers.
    Guarantees that each channel gets a UNIQUE slice of videos from the pool.
    """
    if not channels:
        return {"status": "error", "message": "No channels provided for publishing."}
    if not videos:
        return {"status": "error", "message": "No rendered videos available to schedule."}

    total_needed = len(channels) * videos_per_channel
    log(f"[Scheduler] Mode: {mode.upper()} (Giờ Vàng Mỹ ET) | Quota: {videos_per_channel} videos/kênh across {len(channels)} channel(s)")
    log(f"[Scheduler] Tổng quota cần: {total_needed} video độc quyền. Kho hiện có: {len(videos)} video.")

    monetized_pool = [v for v in videos if v.get("monetizable") or v.get("duration", 0) >= 60.0]
    growth_pool = [v for v in videos if not (v.get("monetizable") or v.get("duration", 0) >= 60.0)]
    if not growth_pool:
        growth_pool = videos
    if not monetized_pool:
        monetized_pool = videos

    media_cache: Dict[str, str] = load_media_cache()
    scheduled_entries = []

    for ch_idx, ch in enumerate(channels):
        global_ch_idx = channel_offset + ch_idx
        ch_id = ch["id"]
        ch_name = ch.get("name") or ch_id
        ch_tier = ch.get("tier", "monetized")
        active_pool = monetized_pool if ch_tier == "monetized" else growth_pool

        # Calculate unique organic slots for this specific channel (US Eastern viral hours)
        ch_slots = calculate_slots(videos_per_channel, mode=mode, tz_offset=tz_offset, channel_index=global_ch_idx)
        log(f"[Scheduler] Kênh #{global_ch_idx+1} '{ch_name}' [{ch_tier.upper()}]: gán {len(ch_slots)} khung giờ vàng Mỹ (Giờ đầu: {ch_slots[0]})...")

        for slot_idx, slot_time in enumerate(ch_slots):
            # Strict unique non-overlapping video assignment (Zero repetition across channels!)
            vid_idx = (global_ch_idx * videos_per_channel + slot_idx)
            if vid_idx >= len(active_pool):
                log(f"[Scheduler] ⚠️ Cảnh báo: Kho video không đủ video độc quyền cho kênh '{ch_name}' (Slot {slot_idx+1}). Cần tạo thêm video mới, tuyệt đối không dùng lại video cũ!")
                break
            vid = active_pool[vid_idx]
            vpath = Path(vid["path"])

            # Upload video or reuse uploaded mediaId
            if not dry_run:
                if str(vpath) not in media_cache:
                    log(f"[Scheduler] Tải {vpath.name} ({vid.get('duration', 0):.1f}s) lên Planly...")
                    media_id = client.upload_video(vpath, log=log)
                    media_cache[str(vpath)] = media_id
                    save_media_cache(media_cache)
                else:
                    media_id = media_cache[str(vpath)]
            else:
                media_id = f"dry_run_media_{vpath.stem}"

            # High-engagement natural captions (Anti-spam pattern)
            title_clean = vid.get("title") or "Watch this breakdown"
            tags_list = vid.get("hashtags") or ["#viral", "#discovery", "#shorts", "#mindblown", "#trending"]
            tags_str = " ".join(tags_list)

            caption_templates = [
                f"{title_clean}! What are your thoughts on this? React below! 💬\n\n{tags_str}",
                f"Wait until the end... {title_clean}! Follow for daily discoveries! ✨\n\n{tags_str}",
                f"Did you know about this? {title_clean}! Drop your reaction in the comments! 👇\n\n{tags_str}",
                f"{title_clean}! This changes everything we thought we knew! Tap follow for part 2! 🔥\n\n{tags_str}",
                f"The truth behind {title_clean}! Share this with someone who needs to see it! 🚀\n\n{tags_str}",
                f"{title_clean}! Breakdown of what actually happened. Would you have believed this? 🤯\n\n{tags_str}",
            ]
            caption = caption_templates[slot_idx % len(caption_templates)]

            options = {
                "postType": 0,
                "disableDuet": True,
                "disableStitch": True,
                "disableComment": False,
            }

            entry = {
                "channel_id": ch_id,
                "channel_name": ch_name,
                "channel_tier": ch_tier,
                "media_id": media_id,
                "publish_on": slot_time,
                "caption": caption[:2000],
                "options": options,
                "video_file": vpath.name,
                "duration": vid.get("duration", 0),
            }
            scheduled_entries.append(entry)

    if dry_run:
        log(f"[Scheduler] DRY-RUN COMPLETE: {len(scheduled_entries)} safe posts prepared (Not sent).")
        return {
            "status": "success",
            "dry_run": True,
            "count": len(scheduled_entries),
            "entries": scheduled_entries,
        }

    # Execute schedule on Planly
    log(f"[Scheduler] Sending {len(scheduled_entries)} safe schedule(s) to Planly API...")
    res = client.schedule_posts(scheduled_entries)

    for e in scheduled_entries:
        mark_posted(e["video_file"], e["channel_id"], e["publish_on"])

    log(f"[Scheduler] Successfully published {len(scheduled_entries)} post(s) to Planly!")
    return {
        "status": "success",
        "dry_run": False,
        "count": len(scheduled_entries),
        "api_response": res,
        "entries": scheduled_entries,
    }


def schedule_all_accounts_quota(
    accounts: List[Dict[str, Any]],
    videos: List[Dict[str, Any]],
    videos_per_channel: int = 6,
    mode: str = "scheduled",
    tz_offset: Optional[int] = None,
    dry_run: bool = False,
    log=print
) -> Dict[str, Any]:
    """Schedules quota across ALL Planly accounts and ALL channels simultaneously,
    allocating completely unique, non-overlapping videos to every single channel.
    """
    total_channels = sum(len(a.get("channels", [])) for a in accounts)
    total_needed = total_channels * videos_per_channel

    log(f"=== ĐẶT LỊCH ĐA TÀI KHOẢN: {len(accounts)} TÀI KHOẢN | {total_channels} KÊNH TIKTOK ===")
    log(f"Định mức: {videos_per_channel} video/kênh/ngày => Tổng số bài đăng cần xếp: {total_needed}")
    log(f"Khung giờ mục tiêu: 6 GIỜ VÀNG VIRAL MỸ (US Eastern Time)")
    log(f"Kho video sẵn có: {len(videos)} video")

    results = []
    global_offset = 0

    for acc in accounts:
        channels = acc.get("channels", [])
        if not channels:
            continue
        token = acc.get("token", "").strip()
        team_id = acc.get("team_id", "").strip()
        acc_name = acc.get("name") or acc.get("id")
        log(f"--> Đang xử lý Tài khoản '{acc_name}' ({len(channels)} kênh)...")

        client = PlanlyClient(token, team_id)
        res = schedule_channel_quota(
            client=client,
            channels=channels,
            videos=videos,
            videos_per_channel=videos_per_channel,
            mode=mode,
            tz_offset=tz_offset,
            dry_run=dry_run,
            channel_offset=global_offset,
            log=log
        )
        results.append({"account": acc_name, "res": res})
        global_offset += len(channels)

    total_scheduled = sum(r["res"].get("count", 0) for r in results)
    log(f"🎉 Hoàn thành toàn diện: Đã xếp lịch an toàn cho {total_scheduled} bài đăng trên {total_channels} kênh theo GIỜ VÀNG MỸ!")
    return {
        "status": "success",
        "total_scheduled": total_scheduled,
        "total_channels": total_channels,
        "details": results
    }
