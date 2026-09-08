"""Headless Zero-Touch Runner: Schedules and manages videos directly without browser.
Builds 100% independent non-political viral commentary from real web clips (>60s)
and schedules them safely across daily peak hours.
Supports multi-account scaling: 6 videos per TikTok channel per day (e.g. 14 channels = 84 unique videos/day).
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.account_manager import AccountManager
from core.planly_client import PlanlyClient
from core.scheduler import get_available_videos, schedule_channel_quota, schedule_all_accounts_quota
from core.config_manager import load_config
from core.video_commentary import download_or_load_source_video, generate_commentary_script, fetch_viral_batch_sources, render_hybrid_commentary_video
from core.paths import OUTPUT_DIR

# Configure UTF-8 output for Windows console
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def generate_commentary_batch(count: int, log=print) -> int:
    """Renders N completely distinct, non-political commentary videos from real web clips (>60s)."""
    if count <= 0:
        return 0
    log(f"\n⚡ Đang tìm kiếm và tải {count} clip viral từ các ngách khác nhau trên mạng...")
    sources = fetch_viral_batch_sources(count=count, log=log)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    cfg = load_config().get("generation", {})
    rendered = 0

    for idx, src in enumerate(sources, 1):
        log(f"\n   [{idx}/{len(sources)}] '{src.get('title', '')[:50]}' ({src.get('duration', 0):.1f}s)...")
        clean_t = re.sub(r"[^\w]+", "_", src.get("title", "clip")[:20]).strip("_")
        out_f = OUTPUT_DIR / f"commentary_{stamp}_{idx}_{clean_t}.mp4"
        try:
            render_hybrid_commentary_video(
                source_video_info=src,
                out_file=out_f,
                cfg=cfg,
                enable_broll_cutaways=False,
                log=lambda m: log(f"      {m}")
            )
            rendered += 1
            log(f"   ✅ Đã xong video #{idx}: {out_f.name}")
        except Exception as e:
            log(f"   ❌ Lỗi render video #{idx}: {e}")

    return rendered


def main():
    parser = argparse.ArgumentParser(description="Auto Make Money Headless Runner")
    parser.add_argument("--dry-run", action="store_true", help="Simulate scheduling without uploading")
    parser.add_argument("--quota", type=int, default=6, help="Videos per channel per day (default: 6)")
    parser.add_argument("--account", type=str, default=None, help="Specific Planly Account ID (defaults to all accounts)")
    parser.add_argument("--mode", type=str, default="scheduled", choices=["scheduled", "same_time", "expedited"], help="Schedule mode (default: scheduled across peak hours)")
    parser.add_argument("--auto-fulfill", action="store_true", help="Automatically generate any missing videos so all channels have their full 6 videos")
    parser.add_argument("--generate-batch", type=int, default=0, help="Generate N brand-new viral commentary videos (e.g. 6, 12, 84)")
    parser.add_argument("--commentary-batch", type=int, default=0, help="Generate N brand-new commentary videos from diverse viral niches")
    parser.add_argument("--generate-url", type=str, default=None, help="Generate commentary for a specific URL before scheduling")
    parser.add_argument("--schedule-days", type=int, default=0, help="Autonomously generate and schedule unique videos for N days into the future")
    parser.add_argument("--open-folder", action="store_true", help="Open output folder in Windows File Explorer")
    args = parser.parse_args()

    if args.open_folder:
        import os
        os.startfile(str(OUTPUT_DIR))
        print(f"📂 Đã mở thư mục video: {OUTPUT_DIR}")
        return

    print("====================================================================")
    print("🚀 AUTO MAKE MONEY - TIẾN TRÌNH XẾP LỊCH TỰ ĐỘNG (ZERO-TOUCH RUNNER)")
    print("====================================================================")

    # 1. Load Accounts & Discover All Channels
    mgr = AccountManager()
    all_accounts = mgr.load_all()
    if not all_accounts:
        print("❌ Không tìm thấy tài khoản Planly trong hệ thống data/accounts.json!")
        return

    target_accounts = [a for a in all_accounts if (not args.account or a.get("id") == args.account)]
    if not target_accounts:
        print(f"❌ Không tìm thấy tài khoản hợp lệ với ID: {args.account}")
        return

    total_channels = sum(len(a.get("channels", [])) for a in target_accounts)
    total_needed = total_channels * args.quota
    print(f"📌 Đang quản lý: {len(target_accounts)} tài khoản Planly | Tổng số: {total_channels} kênh TikTok")
    print(f"🎯 Định mức: {args.quota} video/kênh/ngày => Tổng số video độc quyền cần: {total_needed}")

    # 2. Multi-Day Autonomous Schedule (if specified)
    if args.schedule_days > 0:
        from core.auto_publisher import run_auto_publisher_batch
        for day in range(1, args.schedule_days + 1):
            print(f"\n====================================================================")
            print(f"⚡ BẮT ĐẦU TẠO & XẾP LỊCH CHO NGÀY THỨ +{day} TRONG TƯƠNG LAI...")
            print(f"====================================================================")
            run_auto_publisher_batch(target_day_offset=day, quota_per_channel=args.quota, log=print)
        print("\n🎉 Hoàn thành sản xuất và xếp lịch đa ngày độc quyền!")
        return

    # 3. Explicit Batch Generation (if specified)
    batch_count = args.generate_batch or args.commentary_batch
    if batch_count > 0:
        generate_commentary_batch(batch_count)

    # 4. Optional: Generate commentary video from specific URL
    if args.generate_url:
        print(f"\n🎬 Đang tải và tạo commentary video từ URL: {args.generate_url}...")
        v_info = download_or_load_source_video(args.generate_url)
        print(f"   -> Tiêu đề: {v_info.get('title')} ({v_info.get('duration', 0):.1f}s)")
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_f = OUTPUT_DIR / f"commentary_{stamp}_{v_info.get('id', 'clip')}.mp4"
        cfg = load_config().get("generation", {})
        render_hybrid_commentary_video(v_info, out_f, cfg, enable_broll_cutaways=False)
        print(f"   ✅ Đã render xong: {out_f.name}")

    # 5. Check Available Videos & Auto-Fulfill if needed
    videos = get_available_videos()
    print(f"\n🎬 Kho video hiện tại trong output/: {len(videos)} video")
    
    if args.auto_fulfill and len(videos) < total_needed:
        missing = total_needed - len(videos)
        print(f"⚡ [Auto-Fulfill] Kho video còn thiếu {missing} video độc quyền. Bắt đầu tự động tạo từ video mạng...")
        generate_commentary_batch(missing)
        videos = get_available_videos()
        print(f"🎬 Kho video sau khi bổ sung: {len(videos)} video")

    if not videos:
        print("❌ Không có video nào trong thư mục output để lên lịch!")
        return

    # 6. Schedule across Channels & Accounts
    if args.dry_run:
        print("\n⚠️ [DRY RUN] Chế độ mô phỏng - Không gửi dữ liệu lên Planly API")

    for acc_idx, acc in enumerate(target_accounts, 1):
        acc_name = acc.get("name", f"Acc #{acc_idx}")
        channels = acc.get("channels", [])
        if not channels:
            continue

        print(f"\n--- TÀI KHOẢN #{acc_idx}: '{acc_name}' ({len(channels)} kênh) ---")
        client = None if args.dry_run else PlanlyClient(acc["token"], acc["team_id"])

        results = schedule_channel_quota(
            channels=channels,
            quota_per_channel=args.quota,
            schedule_mode=args.mode,
            planly_client=client,
            dry_run=args.dry_run,
            log=print
        )

    print("\n====================================================================")
    print("✅ TIẾN TRÌNH XẾP LỊCH HOÀN TẤT THÀNH CÔNG!")
    print("====================================================================")


if __name__ == "__main__":
    main()
