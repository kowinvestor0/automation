"""Vox Breaking News Scheduler for Planly.
Fetches real-time viral breaking news stories, generates punchy Vox explainer scripts,
synthesizes dynamic 9:16 vertical videos with energetic voiceover and ducked background music,
and schedules them directly to Planly channels to fill all upcoming open slots.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from core.paths import CACHE_DIR, DATA_DIR, OUTPUT_DIR
from core.config_manager import load_config
from core.account_manager import AccountManager
from core.planly_client import PlanlyClient
from core.trending_news import fetch_diverse_viral_stories, is_topic_used, mark_topic_used
from core.vox_engine import generate_vox_news_script, generate_vox_explainer_video
from core.background_worker import (
    TIKTOK_ORGANIC_PEAK_HOURS_VN,
    build_channel_slots_for_date,
    get_channel_scheduled_counts_by_date,
    load_media_cache,
    save_media_cache,
    mark_posted,
)

logger = logging.getLogger("VoxNewsScheduler")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

PROTECTED_CHANNELS = {
    "amelialynch1989",
    "outdoorboyso",
    "outdoorboysc",
}

VOICE_ROTATION = [
    "en-US-AndrewNeural",
    "en-US-GuyNeural",
    "en-US-BrianNeural",
    "en-US-SteffanNeural",
]


def schedule_vox_news_batch(max_videos: int = 10, lookahead_days: int = 2, channel_filter: Optional[str] = None) -> int:
    """Produces and schedules Vox-style breaking news videos to fill upcoming Planly slots."""
    mgr = AccountManager()
    accounts = mgr.load_all()
    if not accounts:
        logger.error("Khong tim thay tai khoan Planly nao.")
        return 0

    media_cache = load_media_cache()
    total_scheduled = 0

    tz_vn = dt.timezone(dt.timedelta(hours=7))
    today_vn = dt.datetime.now(tz_vn).date()
    target_dates = [today_vn + dt.timedelta(days=i) for i in range(lookahead_days)]

    # Collect trending stories
    logger.info("📡 Dang quet tin tuc nong hoi tu Google News RSS...")
    raw_stories = fetch_diverse_viral_stories(count=max(25, max_videos * 2))
    fresh_stories = [s for s in raw_stories if not is_topic_used(s.get("title", ""))]
    logger.info(f"📰 Tim thay {len(fresh_stories)} tin tuc nong hoi chua tung su dung.")

    story_cursor = 0

    # Date-first, Round-Robin scheduling across ALL Planly accounts and active channels
    for t_date in target_dates:
        if total_scheduled >= max_videos:
            break

        date_str = t_date.strftime("%Y-%m-%d")
        logger.info(f"📅 =================== Xep lich cho ngay: {date_str} ===================")

        all_channel_needs = []
        global_ch_idx = 0

        for acc_idx, target_acc in enumerate(accounts, 1):
            token = target_acc.get("token", "")
            team_id = target_acc.get("team_id", "")
            acc_name = target_acc.get("name", f"Account {acc_idx}")

            if not token or not team_id:
                continue

            client = PlanlyClient(token, team_id)
            channels = [
                c for c in target_acc.get("channels", [])
                if str(c.get("name", "")).lower().lstrip("@") not in PROTECTED_CHANNELS
                and "amelia" not in str(c.get("name", "")).lower()
            ]

            if channel_filter:
                clean_filter = channel_filter.lower().lstrip("@")
                channels = [
                    c for c in channels
                    if clean_filter in str(c.get("name", "")).lower()
                ]

            if not channels:
                continue

            try:
                scheduled_counts = get_channel_scheduled_counts_by_date(client)
            except Exception as e:
                logger.error(f"  Loi lay lich kenh cho {acc_name}: {e}")
                continue

            for ch in channels:
                ch_id = ch.get("id")
                ch_name = ch.get("name")
                if not ch_id or not ch_name:
                    continue

                global_ch_idx += 1
                curr_count = scheduled_counts.get(ch_id, {}).get(date_str, 0)
                needed = max(0, 6 - curr_count)
                if needed <= 0:
                    continue

                slots = build_channel_slots_for_date(t_date, global_ch_idx, quota=6)
                missing_slots = slots[curr_count:6]
                if missing_slots:
                    all_channel_needs.append({
                        "acc_name": acc_name,
                        "client": client,
                        "ch_idx": global_ch_idx,
                        "ch_id": ch_id,
                        "ch_name": ch_name,
                        "missing_slots": missing_slots,
                        "date_str": date_str,
                        "scheduled_counts": scheduled_counts,
                    })
                    logger.info(f"  🎯 [{acc_name}] Kenh @{ch_name:24} (hien co {curr_count}/6) -> can them {len(missing_slots)} video.")

        if not all_channel_needs:
            logger.info(f"  ✨ Tat ca cac kenh tren TAT CA tai khoan da DU 6/6 bai cho ngay {date_str}!")
            continue

        max_missing = max([len(cn["missing_slots"]) for cn in all_channel_needs], default=0)

        # Round robin: Give 1 video to each channel, then 2nd video, etc.
        for step in range(max_missing):
            if total_scheduled >= max_videos:
                break

            for cn in all_channel_needs:
                if total_scheduled >= max_videos:
                    break

                if step >= len(cn["missing_slots"]):
                    continue

                slot_time = cn["missing_slots"][step]
                ch_name = cn["ch_name"]
                ch_id = cn["ch_id"]
                ch_idx = cn["ch_idx"]
                client = cn["client"]
                acc_name = cn["acc_name"]
                scheduled_counts = cn["scheduled_counts"]
                date_str = cn["date_str"]

                # Pick next fresh news story
                if story_cursor >= len(fresh_stories):
                    # Re-fetch or wrap around with evergreen
                    fresh_stories = fetch_diverse_viral_stories(count=30)
                    fresh_stories = [s for s in fresh_stories if not is_topic_used(s.get("title", ""))]
                    story_cursor = 0

                if not fresh_stories:
                    fresh_stories = fetch_diverse_viral_stories(count=30)
                    story_cursor = 0

                current_news = fresh_stories[story_cursor % len(fresh_stories)]
                story_cursor += 1

                news_title = current_news.get("title", "Breaking News")
                logger.info(f"👉 [{total_scheduled+1}/{max_videos}] [{acc_name}] Kenh @{ch_name} (Slot {step+1}): '{news_title[:55]}'...")

                # Check if there are already rendered vox videos waiting to be uploaded
                existing_vox = sorted([f for f in OUTPUT_DIR.glob("vox_*.mp4") if f.name != "vox_breaking_news_demo.mp4" and f.stat().st_size > 1_000_000])
                if existing_vox:
                    out_video = existing_vox[0]
                    logger.info(f"  ⚡ Phat hien video da render san: {out_video.name} ({out_video.stat().st_size / (1<<20):.1f} MB), su dung ngay!")
                    headline = out_video.stem.replace("vox_", "").split("_", 4)[-1].replace("_", " ").upper()
                    vox_data = {
                        "title": headline,
                        "hashtags": ["#breakingnews", "#science", "#tech", "#vox", "#fyp"],
                        "discussion_question": "What do you think about this breakthrough? Let me know below!"
                    }
                    mark_topic_used(news_title)
                    mark_topic_used(headline)
                else:
                    # Generate Vox explainer script via Gemini
                    try:
                        vox_data = generate_vox_news_script(current_news)
                    except Exception as e:
                        logger.warning(f"  Loi tao kịch ban: {e}, bo qua.")
                        continue

                    headline = vox_data.get("title", news_title)
                    mark_topic_used(news_title)

                    # Voice rotation
                    chosen_voice = VOICE_ROTATION[(total_scheduled + ch_idx) % len(VOICE_ROTATION)]

                    # File output path
                    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_head = re.sub(r"[^\w]+", "_", headline)[:22].strip("_")
                    out_video = OUTPUT_DIR / f"vox_{stamp}_{ch_name}_{step+1}_{safe_head}.mp4"

                    logger.info(f"  🎬 Render video Vox 9:16 ({chosen_voice})...")
                    try:
                        generate_vox_explainer_video(
                            story_data=vox_data,
                            out_video_path=out_video,
                            voice_name=chosen_voice
                        )
                    except Exception as exc:
                        logger.error(f"  Loi render video: {exc}")
                        continue

                # Upload to Planly S3
                vpath_str = f"{client.team_id}:{str(out_video.resolve())}"
                try:
                    if vpath_str not in media_cache:
                        logger.info(f"  ☁️ Uploading to Planly S3 ({acc_name})...")
                        media_id = client.upload_video(out_video, log=logger.info)
                        media_cache[vpath_str] = media_id
                        save_media_cache(media_cache)
                    else:
                        media_id = media_cache[vpath_str]

                    # Build engaging caption
                    tags = vox_data.get("hashtags", ["#news", "#science", "#technology", "#fyp"])
                    tags_str = " ".join(tags)
                    q_cta = vox_data.get("discussion_question", "Drop your thoughts below! 👇")
                    caption = f"{headline} 🤯 {q_cta}\n\n{tags_str}"

                    post_entry = {
                        "channel_id": ch_id,
                        "media_id": media_id,
                        "publish_on": slot_time,
                        "caption": caption[:2000],
                        "options": {
                            "postType": 0,
                            "disableDuet": True,
                            "disableStitch": True,
                            "disableComment": False
                        }
                    }

                    logger.info(f"  📅 Scheduling to [{acc_name}] @{ch_name} at {slot_time}...")
                    client.schedule_posts([post_entry])
                    mark_posted(out_video.name, ch_id, slot_time)
                    total_scheduled += 1

                    # Delete local video to preserve disk space
                    try:
                        if out_video.exists():
                            out_video.unlink()
                    except Exception:
                        pass

                    # Update in-memory count
                    scheduled_counts.setdefault(ch_id, {})[date_str] = scheduled_counts.get(ch_id, {}).get(date_str, 0) + 1
                    time.sleep(1.5)

                except Exception as e:
                    logger.error(f"  Loi khi len lich len Planly: {e}")

    logger.info(f"✅ HOAN THANH: Da san xuat va xep lich thanh cong {total_scheduled} video Vox News len Planly!")
    return total_scheduled


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Schedule Vox News videos to Planly")
    parser.add_argument("--count", type=int, default=6, help="Maximum number of videos to schedule in this run")
    parser.add_argument("--days", type=int, default=2, help="Number of lookahead days")
    parser.add_argument("--channel", type=str, default=None, help="Filter to specific channel (e.g. outdoorboysoo)")
    args = parser.parse_args()

    schedule_vox_news_batch(max_videos=args.count, lookahead_days=args.days, channel_filter=args.channel)
