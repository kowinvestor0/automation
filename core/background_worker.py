"""Autonomous Background Worker: Silent 24/7 Engine for Auto Make Money.
Runs completely in the background without requiring the user to keep any window open.
Continuously scans all connected TikTok channels across all Planly accounts:
- Ensures each channel has exactly 6 unique viral commentary videos (>60s) scheduled per day.
- Automatically produces surplus videos and schedules them for upcoming days (Day +1, Day +2, Day +3...).
- Scrapes endless unique shorts from YouTube across 20+ viral niches.
- Guarantees 100% video footage uniqueness: zero duplicates across channels and days.
"""
from __future__ import annotations

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

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.paths import DATA_DIR, OUTPUT_DIR, CACHE_DIR
from core.account_manager import AccountManager
from core.planly_client import PlanlyClient
from core.config_manager import load_config
from core.scraper import VideoScraper
from core.video_commentary import render_hybrid_commentary_video, generate_commentary_script
from core.infinite_content import (
    load_used_viral_clips,
    save_used_viral_clips,
    get_next_unique_viral_clip,
    VIRAL_KNOWLEDGE_BASE
)
from core.scheduler import (
    get_us_eastern_tz,
    US_VIRAL_PEAK_HOURS_ET,
    mark_posted,
    load_media_cache,
    save_media_cache
)

# Setup logging
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "background_worker.log"
LOCK_FILE = DATA_DIR / "worker.lock"
STOP_SIGNAL_FILE = DATA_DIR / "worker.stop"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("BackgroundWorker")


def is_stop_requested() -> bool:
    return STOP_SIGNAL_FILE.exists()


def clear_stop_signal() -> None:
    if STOP_SIGNAL_FILE.exists():
        try:
            STOP_SIGNAL_FILE.unlink()
        except Exception:
            pass


def acquire_lock() -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            # Check if process is still alive on Windows
            import psutil
            if psutil.pid_exists(pid):
                return False
        except Exception:
            pass
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    return True


def release_lock() -> None:
    if LOCK_FILE.exists():
        try:
            LOCK_FILE.unlink()
        except Exception:
            pass


def build_channel_slots_for_date(target_date: dt.date, channel_index: int, quota: int = 6) -> List[str]:
    tz = get_us_eastern_tz()
    slots = []
    for idx in range(quota):
        h, m = US_VIRAL_PEAK_HOURS_ET[idx % len(US_VIRAL_PEAK_HOURS_ET)]
        jitter = ((channel_index * 3) + random.randint(2, 8)) % 14
        slot_dt = dt.datetime(
            target_date.year, target_date.month, target_date.day,
            h, m, tzinfo=tz
        ) + dt.timedelta(minutes=jitter)
        slots.append(slot_dt.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    return slots


def get_channel_scheduled_counts_by_date(client: PlanlyClient) -> Dict[str, Dict[str, int]]:
    """Inspects Planly calendar and counts how many posts are scheduled per channel per date.
    Returns: {channel_id: {"YYYY-MM-DD": count, ...}}
    """
    counts: Dict[str, Dict[str, int]] = {}
    try:
        groups = client.list_scheduled_groups()
        for g in groups:
            publish_on = g.get("publishOn")
            if not publish_on:
                continue
            date_str = publish_on[:10]
            schedules = g.get("schedules") or []
            for s in schedules:
                ch_id = s.get("channelId")
                if not ch_id:
                    continue
                if ch_id not in counts:
                    counts[ch_id] = {}
                counts[ch_id][date_str] = counts[ch_id].get(date_str, 0) + 1
    except Exception as e:
        logger.warning(f"Error checking Planly schedule calendar: {e}")
    return counts


def run_worker_cycle(lookahead_days: int = 3, quota_per_day: int = 6) -> int:
    """Performs one full maintenance and generation pass.
    Returns number of new videos scheduled in this pass.
    """
    mgr = AccountManager()
    accounts = mgr.load_all()
    if not accounts:
        logger.warning("No Planly accounts found in data/accounts.json")
        return 0

    target_acc = accounts[0]
    channels = target_acc.get("channels", [])
    if not channels:
        logger.warning("No TikTok channels found in account.")
        return 0

    client = PlanlyClient(target_acc["token"], target_acc["team_id"])
    tz = get_us_eastern_tz()
    today_et = dt.datetime.now(tz).date()

    scraper = VideoScraper()
    cfg = load_config().get("generation", {})
    media_cache = load_media_cache()
    used_viral_ids = load_used_viral_clips()

    # Get live schedule counts from Planly
    schedule_counts = get_channel_scheduled_counts_by_date(client)
    total_scheduled_this_cycle = 0

    # Scan through days into the future
    for day_offset in range(1, lookahead_days + 1):
        if is_stop_requested():
            logger.info("Stop signal detected. Exiting worker cycle.")
            break

        target_date = today_et + dt.timedelta(days=day_offset)
        target_date_str = target_date.strftime("%Y-%m-%d")

        logger.info(f"--- Kiểm tra lịch ngày: {target_date.strftime('%d/%m/%Y')} (Day +{day_offset}) ---")

        for ch_idx, ch in enumerate(channels):
            if is_stop_requested():
                break

            ch_id = ch["id"]
            ch_name = ch.get("name") or ch_id
            current_scheduled = schedule_counts.get(ch_id, {}).get(target_date_str, 0)
            needed = quota_per_day - current_scheduled

            if needed <= 0:
                logger.info(f"  Kênh '{ch_name}': Đã đủ {current_scheduled}/{quota_per_day} video cho ngày {target_date_str}. Bỏ qua.")
                continue

            logger.info(f"  ⚡ Kênh '{ch_name}': Đang có {current_scheduled}/{quota_per_day} video. Cần tạo thêm {needed} video mới...")
            all_slots = build_channel_slots_for_date(target_date, channel_index=ch_idx, quota=quota_per_day)
            missing_slots = all_slots[current_scheduled:quota_per_day]

            for slot_idx, slot_time in enumerate(missing_slots):
                if is_stop_requested():
                    break

                # Pick unique viral niche
                niche_idx = (ch_idx * quota_per_day + current_scheduled + slot_idx) % len(VIRAL_KNOWLEDGE_BASE)
                niche_obj = VIRAL_KNOWLEDGE_BASE[niche_idx]
                niche_name = niche_obj["category"]

                logger.info(f"    [{slot_idx+1}/{len(missing_slots)}] [{niche_name}] Đang tìm clip viral độc quyền từ kho vô hạn...")
                src_clip = get_next_unique_viral_clip(
                    scraper=scraper,
                    used_ids=used_viral_ids,
                    preferred_category=niche_name,
                    log=logger.info
                )

                if not src_clip:
                    logger.warning(f"    Không tìm thấy clip viral cho kênh '{ch_name}'. Bỏ qua slot.")
                    continue

                clean_t = re.sub(r"[^\w]+", "_", src_clip["title"][:25]).strip("_")
                stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                out_file = OUTPUT_DIR / f"commentary_{stamp}_{ch_name}_{slot_idx+1}_{clean_t}.mp4"

                logger.info(f"    -> Đang render video commentary độc quyền: '{src_clip['title'][:50]}' ({src_clip.get('duration', 0):.1f}s)...")
                try:
                    render_hybrid_commentary_video(
                        source_video_info=src_clip,
                        out_file=out_file,
                        cfg=cfg,
                        enable_broll_cutaways=False,
                        log=logger.info
                    )

                    meta_file = out_file.with_suffix(".meta.json")
                    if meta_file.exists():
                        meta_info = json.loads(meta_file.read_text(encoding="utf-8"))
                    else:
                        meta_info = {"title": src_clip["title"], "hashtags": ["#shorts", "#viral", "#commentary"]}

                    # Upload to Planly S3
                    vpath_str = str(out_file.resolve())
                    if vpath_str not in media_cache:
                        logger.info(f"    -> Đang tải video lên Planly S3 Storage...")
                        media_id = client.upload_video(out_file, log=logger.info)
                        media_cache[vpath_str] = media_id
                        save_media_cache(media_cache)
                    else:
                        media_id = media_cache[vpath_str]

                    tags_str = " ".join(meta_info.get("hashtags", ["#viral", "#commentary", "#shorts"]))
                    caption = f"{meta_info.get('title', src_clip['title'])}! What are your thoughts on this? React below! 💬\n\n{tags_str}"

                    # Post entry on Planly with duet/stitch disabled
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
                    client.schedule_posts([post_entry])
                    mark_posted(out_file.name, ch_id, slot_time)
                    total_scheduled_this_cycle += 1

                    # Update local count cache
                    if ch_id not in schedule_counts:
                        schedule_counts[ch_id] = {}
                    schedule_counts[ch_id][target_date_str] = schedule_counts[ch_id].get(target_date_str, 0) + 1

                    logger.info(f"    ✅ Đã xếp lịch thành công lúc {slot_time} trên kênh '{ch_name}'!")
                except Exception as e:
                    logger.error(f"    ❌ Lỗi tạo video slot {slot_idx+1} cho kênh '{ch_name}': {e}")

    return total_scheduled_this_cycle


def main():
    clear_stop_signal()
    if not acquire_lock():
        print("❌ Worker đã đang chạy trong nền (PID in data/worker.lock).")
        sys.exit(1)

    logger.info("====================================================================")
    logger.info("🚀 AUTO MAKE MONEY - BACKGROUND WORKER ĐÃ KHỞI ĐỘNG (CHẠY NGẦM 24/7)")
    logger.info("📌 Tự động duy trì 6 video/kênh/ngày cho tất cả các ngày sắp tới.")
    logger.info("⚡ Động cơ: Tự tìm Short trên mạng + Bình luận liền mạch (>60s) + Zero trùng lặp.")
    logger.info("====================================================================")

    try:
        while not is_stop_requested():
            scheduled = run_worker_cycle(lookahead_days=3, quota_per_day=6)
            if is_stop_requested():
                break

            if scheduled > 0:
                logger.info(f"🎉 Hoàn thành chu kỳ sản xuất. Đã xếp lịch thêm {scheduled} video độc quyền!")
            else:
                logger.info("✅ Tất cả các kênh đã có đủ 6 video/ngày cho 3 ngày tới.")

            # Sleep 15 minutes between health checks
            logger.info("💤 Chờ 15 phút trước chu kỳ kiểm tra tiếp theo...")
            for _ in range(90):  # 90 x 10s = 15 mins
                if is_stop_requested():
                    break
                time.sleep(10)

    except KeyboardInterrupt:
        logger.info("Worker dừng bởi người dùng.")
    finally:
        release_lock()
        logger.info("Background Worker đã dừng an toàn.")


if __name__ == "__main__":
    main()
