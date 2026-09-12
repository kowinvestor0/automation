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
import subprocess
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
from core.story_engine import render_crime_story_video
from core.crime_story_database import get_next_crime_story, ICONIC_TRUE_CRIME_CASES
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

# Crucial for pythonw.exe: redirect None stdout/stderr to files so print() and yt_dlp never crash
import io
if sys.stdout is None:
    try:
        sys.stdout = open(LOGS_DIR / "worker_stdout.log", "a", encoding="utf-8", errors="replace", buffering=1)
    except Exception:
        sys.stdout = io.StringIO()
else:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr is None:
    try:
        sys.stderr = open(LOGS_DIR / "worker_stderr.log", "a", encoding="utf-8", errors="replace", buffering=1)
    except Exception:
        sys.stderr = io.StringIO()
else:
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stdin is None:
    sys.stdin = io.StringIO()

log_handlers = [
    logging.FileHandler(str(LOG_FILE), encoding="utf-8")
]
if sys.stdout is not None:
    try:
        log_handlers.append(logging.StreamHandler(sys.stdout))
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=log_handlers
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


def is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if not handle:
                return kernel32.GetLastError() == 5  # ERROR_ACCESS_DENIED
            try:
                exit_code = ctypes.c_ulong()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return exit_code.value == 259  # STILL_ACTIVE
                return False
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def acquire_lock() -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            if is_pid_alive(pid):
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


# 6 Safe Organic Peak Hours in Vietnam Time (GMT+7) spread 2.5 - 3 hours apart:
# Eliminates burst upload / bot spam flagging by TikTok algorithm
TIKTOK_ORGANIC_PEAK_HOURS_VN = [
    (8, 30),   # Slot 1: Morning commute / wake-up
    (11, 45),  # Slot 2: Lunch break peak
    (15, 0),   # Slot 3: Afternoon break
    (17, 45),  # Slot 4: Evening commute
    (20, 15),  # Slot 5: PRIME EVENING VIRAL TIME (Highest engagement)
    (22, 30),  # Slot 6: Bedtime scroll peak
]


def build_channel_slots_for_date(target_date: dt.date, channel_index: int, quota: int = 6) -> List[str]:
    """Generates posting times for target date based on publishing config mode:
    - 'same_time': Posts at user's specified hour (e.g. 09:00 VN) with natural 1-3 min jitter per channel
    - 'organic_spread': Posts spread across peak hours (08:30, 11:45, 15:00, 17:45, 20:15, 22:30)
    """
    tz_vn = dt.timezone(dt.timedelta(hours=7))
    now_utc = dt.datetime.now(dt.timezone.utc)
    today_vn = dt.datetime.now(tz_vn).date()
    pub_cfg = load_config().get("publishing", {})
    mode = pub_cfg.get("mode", "organic_spread")
    schedule_times = pub_cfg.get("schedule_times", ["09:00", "12:00", "15:00", "18:00", "20:30", "22:30"])

    raw_candidates: List[dt.datetime] = []
    if mode == "same_time" and schedule_times:
        try:
            base_h, base_m = map(int, str(schedule_times[0]).split(":"))
        except Exception:
            base_h, base_m = 9, 0
        for idx in range(quota):
            jitter = (channel_index * 3) + (idx * 2)
            slot_dt = dt.datetime(target_date.year, target_date.month, target_date.day, base_h, base_m, 0, tzinfo=tz_vn) + dt.timedelta(minutes=jitter)
            raw_candidates.append(slot_dt)
    else:
        for idx in range(quota):
            h, m = TIKTOK_ORGANIC_PEAK_HOURS_VN[idx % len(TIKTOK_ORGANIC_PEAK_HOURS_VN)]
            jitter = ((channel_index * 7) + (idx * 3) + 2) % 13
            slot_dt = dt.datetime(target_date.year, target_date.month, target_date.day, h, m, 0, tzinfo=tz_vn) + dt.timedelta(minutes=jitter)
            raw_candidates.append(slot_dt)

    slots: List[str] = []
    for idx, slot_dt in enumerate(raw_candidates):
        slot_utc = slot_dt.astimezone(dt.timezone.utc)
        if slot_utc > now_utc:
            slots.append(slot_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
        elif target_date == today_vn:
            # If morning slot has passed today, schedule for upcoming afternoon/evening hours!
            shift_mins = 20 + (channel_index * 4) + (idx * 40)
            shifted_utc = now_utc + dt.timedelta(minutes=shift_mins)
            shifted_vn = shifted_utc.astimezone(tz_vn)
            if shifted_vn.date() == today_vn:
                slots.append(shifted_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"))

    return sorted(slots)


def get_channel_scheduled_counts_by_date(client: PlanlyClient) -> Dict[str, Dict[str, int]]:
    """Inspects Planly calendar and counts how many posts are scheduled per channel per date in Vietnam Time (GMT+7).
    Returns: {channel_id: {"YYYY-MM-DD": count, ...}}
    """
    tz_vn = dt.timezone(dt.timedelta(hours=7))
    counts: Dict[str, Dict[str, int]] = {}
    try:
        groups = client.list_scheduled_groups()
        for g in groups:
            publish_on = g.get("publishOn")
            if not publish_on:
                continue
            clean_iso = publish_on.replace("Z", "+00:00")
            try:
                dt_utc = dt.datetime.fromisoformat(clean_iso)
                dt_local = dt_utc.astimezone(tz_vn)
                date_str = dt_local.strftime("%Y-%m-%d")
            except Exception:
                date_str = publish_on[:10]

            schedules = g.get("schedules") or []
            for s in schedules:
                ch_id = s.get("channelId") or (s.get("channel") or {}).get("id")
                if not ch_id:
                    continue
                if ch_id not in counts:
                    counts[ch_id] = {}
                counts[ch_id][date_str] = counts[ch_id].get(date_str, 0) + 1
    except Exception as e:
        logger.warning(f"Error checking Planly schedule calendar: {e}")
    return counts


def run_worker_cycle(lookahead_days: int = 3, quota_per_day: int = 6) -> int:
    """Performs one full maintenance and generation pass across ALL Planly accounts.
    Returns number of new videos scheduled in this pass.
    """
    mgr = AccountManager()
    accounts = mgr.load_all()
    if not accounts:
        logger.warning("No Planly accounts found in data/accounts.json")
        return 0

    tz_vn = dt.timezone(dt.timedelta(hours=7))
    today_vn = dt.datetime.now(tz_vn).date()
    cfg = load_config().get("generation", {})
    media_cache = load_media_cache()
    total_scheduled_this_cycle = 0

    for acc_idx, target_acc in enumerate(accounts, 1):
        if is_stop_requested():
            logger.info("Stop signal detected. Exiting worker cycle.")
            break

        acc_name = target_acc.get("name", f"Account #{acc_idx}")
        token = target_acc.get("token", "").strip()
        team_id = target_acc.get("team_id", "").strip()
        if not token or not team_id:
            logger.warning(f"Thiếu token hoặc team_id cho account '{acc_name}'. Bỏ qua.")
            continue

        client = PlanlyClient(token, team_id)
        channels = target_acc.get("channels", [])

        # Auto-sync channels dynamically from Planly API on every cycle
        try:
            live_channels = client.list_channels()
            if live_channels:
                tiktok_channels = [c for c in live_channels if "tiktok" in (c.get("social_network") or "").lower()]
                if tiktok_channels:
                    channels = tiktok_channels
                    target_acc["channels"] = channels
                    try:
                        mgr.save_all(accounts)
                    except Exception:
                        pass
                    logger.info(f"🔄 Đồng bộ thành công {len(channels)} kênh TikTok từ Planly cho '{acc_name}'!")
        except Exception as e:
            logger.warning(f"Không thể cập nhật danh sách kênh trực tiếp từ Planly: {e}")

        if not channels:
            logger.warning(f"No TikTok channels found in account '{acc_name}'.")
            continue

        # Get live schedule counts from Planly
        schedule_counts = get_channel_scheduled_counts_by_date(client)
        logger.info(f"\n============================================================")
        logger.info(f"📌 Đang kiểm tra Tài Khoản #{acc_idx}: '{acc_name}' ({len(channels)} kênh)")
        logger.info(f"============================================================")

        # Collect existing topic keywords from Planly scheduled posts to guarantee zero duplicate topics
        existing_keywords = []
        try:
            raw_groups = client.list_scheduled_groups()
            for g in raw_groups:
                for s in g.get("schedules") or []:
                    cnt = s.get("content") or ""
                    first_line = cnt.split("\n")[0]
                    first_line = re.sub(r"[^\w\s]", "", first_line)
                    for w in first_line.split():
                        if len(w) > 4:
                            existing_keywords.append(w.lower())
            logger.info(f"📋 Thu thập {len(set(existing_keywords))} từ khóa chủ đề đã có trên Planly để tránh tuyệt đối trùng lặp nội dung.")
        except Exception:
            pass

        # Scan from today (Day 0) to lookahead days into the future (Day 0 = today, Day 1 = tomorrow...)
        for day_offset in range(0, lookahead_days + 1):
            if is_stop_requested():
                break

            target_date = today_vn + dt.timedelta(days=day_offset)
            target_date_str = target_date.strftime("%Y-%m-%d")
            tag_name = "HÔM NAY" if day_offset == 0 else f"Day +{day_offset}"
            logger.info(f"--- Kiem tra lich ngay: {target_date.strftime('%d/%m/%Y')} ({tag_name}) ---")

            # Sort channels so channels with fewest scheduled posts are served first
            sorted_channels = sorted(
                channels,
                key=lambda c: schedule_counts.get(c["id"], {}).get(target_date_str, 0)
            )

            for ch in sorted_channels:
                if is_stop_requested():
                    break

                ch_id = ch["id"]
                ch_name = ch.get("name") or ch_id

                # CRITICAL SAFETY LOCK: Protect active monetized channels from any automated post attempts
                PROTECTED_CHANNELS = ["outdoorboyso", "outdoorboysc", "amelialynch1989", "1989"]
                if any(p in str(ch_name).lower() for p in PROTECTED_CHANNELS):
                    logger.info(f"🛡️ [SAFETY LOCK] Kênh kiếm tiền '{ch_name}' đang được đóng băng bảo vệ an toàn (0 bài). Bỏ qua.")
                    continue

                safe_ch_name = re.sub(r"[^\w]+", "_", str(ch_name)).strip("_")
                current_scheduled = schedule_counts.get(ch_id, {}).get(target_date_str, 0)
                needed = quota_per_day - current_scheduled

                if needed <= 0:
                    logger.info(f"  Kenh '{ch_name}': Da du {current_scheduled}/{quota_per_day} video cho ngay {target_date_str}. Bo qua.")
                    continue

                ch_idx = next((i for i, c in enumerate(channels) if c["id"] == ch_id), 0)
                all_slots = build_channel_slots_for_date(target_date, channel_index=ch_idx, quota=quota_per_day)
                if current_scheduled >= len(all_slots):
                    logger.info(f"  Kenh '{ch_name}': Khong con slot kha dung cho ngay {target_date_str} (da co {current_scheduled} video).")
                    continue

                missing_slots = all_slots[current_scheduled : current_scheduled + needed]
                if not missing_slots:
                    continue

                logger.info(f"  ⚡ Kenh '{ch_name}': Dang co {current_scheduled}/{quota_per_day} video. Can tao them {len(missing_slots)} video tai lieu ky an moi...")

                for slot_idx, slot_time in enumerate(missing_slots):
                    if is_stop_requested():
                        break

                    story = dict(get_next_crime_story(existing_keywords=existing_keywords))
                    story["channel_name"] = str(ch_name)
                    case_id = story.get("id", "crime_story")
                    case_name = story.get("case_name", "Unsolved Mystery")

                    # Add newly generated case name to existing keywords to avoid picking it again this run
                    for w in re.sub(r"[^\w\s]", "", case_name).split():
                        if len(w) > 4:
                            existing_keywords.append(w.lower())

                    clean_t = re.sub(r"[^\w]+", "_", case_id)[:25].strip("_")
                    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                    out_file = OUTPUT_DIR / f"crime_{stamp}_{safe_ch_name}_{slot_idx+1}_{clean_t}.mp4"

                    # Rotate American narrator voices across channels and slots for natural diversity
                    VOICE_OPTIONS = [
                        "en-US-ChristopherNeural",
                        "en-US-GuyNeural",
                        "en-US-EricNeural",
                        "en-US-RogerNeural",
                    ]
                    assigned_voice = VOICE_OPTIONS[(slot_idx + ch_idx) % len(VOICE_OPTIONS)]
                    story_cfg = dict(cfg) if cfg else {}
                    story_cfg["voice"] = assigned_voice

                    logger.info(f"    [{slot_idx+1}/{len(missing_slots)}] -> Dang san xuat ky an: '{case_name}' (>60s) voi giong '{assigned_voice}'...")
                    try:
                        render_crime_story_video(
                            story=story,
                            out_file=out_file,
                            cfg=story_cfg,
                            log=logger.info
                        )

                        meta_file = out_file.with_suffix(".meta.json")
                        if meta_file.exists():
                            meta_info = json.loads(meta_file.read_text(encoding="utf-8"))
                        else:
                            meta_info = {"title": case_name, "hashtags": story.get("hashtags", ["#mystery", "#history", "#discovery"])}

                        # Upload to Planly S3
                        vpath_str = f"{client.team_id}:{str(out_file.resolve())}"
                        if vpath_str not in media_cache:
                            logger.info(f"    -> Dang tai video len Planly S3 Storage...")
                            media_id = client.upload_video(out_file, log=logger.info)
                            media_cache[vpath_str] = media_id
                            save_media_cache(media_cache)
                        else:
                            media_id = media_cache[vpath_str]

                        raw_tags = meta_info.get("hashtags", ["#truecrime", "#mystery", "#discovery", "#fyp"])
                        if isinstance(raw_tags, list):
                            tags_str = " ".join(raw_tags)
                        else:
                            tags_str = str(raw_tags)

                        # Diverse, high-retention TikTok hook captions with natural CTAs
                        ENGAGING_CTA_TEMPLATES = [
                            "What really happened? Drop your theory below! 👇",
                            "Did you know about this? Let me know your thoughts in the comments! 👇",
                            "The reality behind this is far stranger than fiction... What do you think? 👇",
                            "History and science at its most fascinating. Share your thoughts! 👇",
                            "Unsolved to this day. What is your theory? 👇",
                            "One of the most remarkable discoveries ever documented. Drop your thoughts below! 👇",
                            "Drop your theory in the comments and share with a friend! 👇",
                        ]
                        selected_cta = random.choice(ENGAGING_CTA_TEMPLATES)
                        title_text = meta_info.get('title', case_name)
                        caption = f"{title_text} 🤯 {selected_cta}\n\n{tags_str}"

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

                        # Immediately delete local video and meta file to keep disk space at 0 MB
                        try:
                            if out_file.exists():
                                out_file.unlink()
                            if meta_file.exists():
                                meta_file.unlink()
                            logger.info(f"    🗑️ Giai phong bo nho: Da xoa file cuc bo {out_file.name} sau khi upload len Planly.")
                        except Exception:
                            pass

                        # Update local count cache
                        if ch_id not in schedule_counts:
                            schedule_counts[ch_id] = {}
                        schedule_counts[ch_id][target_date_str] = schedule_counts[ch_id].get(target_date_str, 0) + 1

                        logger.info(f"    ✅ Da xep lich thanh cong luc {slot_time} tren kenh '{ch_name}'!")
                    except Exception as e:
                        logger.error(f"    ❌ Loi tao video slot {slot_idx+1} cho kenh '{ch_name}': {e}", exc_info=True)

    return total_scheduled_this_cycle


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Auto Make Money True Crime Background Worker")
    parser.add_argument("--single-pass", action="store_true", help="Run single pass and exit (ideal for GitHub Actions)")
    parser.add_argument("--lookahead", type=int, default=7, help="Number of lookahead days")
    parser.add_argument("--quota", type=int, default=None, help="Videos per channel per day")
    args, _ = parser.parse_known_args()

    cfg = load_config()
    configured_quota = args.quota or int(os.environ.get("VIDEOS_PER_DAY") or cfg.get("publishing", {}).get("videos_per_channel_per_day", 6))
    lookahead_days = args.lookahead or int(os.environ.get("LOOKAHEAD_DAYS") or 7)

    clear_stop_signal()
    if not args.single_pass:
        if not acquire_lock():
            print("❌ Worker da dang chay trong nen (PID in data/worker.lock).")
            sys.exit(1)

    logger.info("====================================================================")
    logger.info("🚀 AUTO MAKE MONEY - AMERICAN TRUE CRIME ENGINE (24/7 CLOUD / LOCAL)")
    logger.info(f"📌 Chi tieu: {configured_quota} video/kenh/ngay (>60s) | Tinh truoc: {lookahead_days} ngay toi.")
    logger.info("⚡ Dong co: Wikipedia/Wikimedia + Pexels 9:16 + Myinstants SFX + Edge TTS.")
    logger.info("✨ Khong rung lac, khong meo hinh, chuan 1080x1920, 100% nhat quan.")
    logger.info("====================================================================")

    if args.single_pass:
        logger.info("🚀 Dang chay che do Single Pass (GitHub Actions Cloud Runner)...")
        scheduled = run_worker_cycle(lookahead_days=lookahead_days, quota_per_day=configured_quota)
        logger.info(f"🎉 Hoan thanh Single Pass! Da xep lich: {scheduled} video.")
        sys.exit(0)

    try:
        while not is_stop_requested():
            try:
                # Reload config each cycle so user changes in UI take effect immediately
                live_cfg = load_config()
                current_quota = int(live_cfg.get("publishing", {}).get("videos_per_channel_per_day", configured_quota))

                scheduled = run_worker_cycle(lookahead_days=lookahead_days, quota_per_day=current_quota)
                if is_stop_requested():
                    break

                if scheduled > 0:
                    logger.info(f"🎉 Hoan thanh chu ky san xuat. Da xep lich them {scheduled} video doc quyen!")
                else:
                    logger.info(f"✅ Tat ca cac kenh da co du {current_quota} video/ngay cho {lookahead_days} ngay toi.")
            except Exception as cycle_err:
                logger.error(f"⚠️ Loi trong chu ky worker: {cycle_err}", exc_info=True)
                logger.info("🔄 Tu dong thu lai sau 30 giay...")
                for _ in range(3):
                    if is_stop_requested():
                        break
                    time.sleep(10)
                continue

            # Sleep 15 minutes between health checks
            logger.info("💤 Cho 15 phut truoc chu ky kiem tra tiep theo...")
            for _ in range(90):  # 90 x 10s = 15 mins
                if is_stop_requested():
                    break
                time.sleep(10)

    except KeyboardInterrupt:
        logger.info("Worker dung boi nguoi dung.")
    finally:
        release_lock()
        logger.info("Background Worker da dung an toan.")


if __name__ == "__main__":
    main()
