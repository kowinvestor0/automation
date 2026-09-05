"""Viral Shorts Commentary Bot CLI.

Automates the entire pipeline:
1. Scrapes viral clips from YouTube Shorts (or downloads from URL)
2. Uses Gemini AI to write a high-retention commentary script (>60s)
3. Renders a transformative 9:16 vertical video (Hook Banner, ASS Karaoke, Ducked Audio, SFX)

Usage:
    python tools/viral_bot.py --count 1
    python tools/viral_bot.py --query "crazy science experiment shorts" --count 2
    python tools/viral_bot.py --url "https://www.youtube.com/shorts/..."
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hub.scraper import ViralScraper
from hub.commentary import generate_commentary_script, render_commentary_video
from hub.paths import CODE


def parse_args():
    parser = argparse.ArgumentParser(description="Viral Shorts Commentary Bot")
    parser.add_argument("--query", "-q", default="", help="Search query for viral shorts")
    parser.add_argument("--file", "-f", default="", help="Direct path to a local video file (.mp4)")
    parser.add_argument("--folder", "-d", default="", help="Directory of local videos (.mp4) to process in batch")
    parser.add_argument("--url", "-u", default="", help="Direct URL of a YouTube Short or clip")
    parser.add_argument("--count", "-c", type=int, default=1, help="Number of videos to generate")
    parser.add_argument("--lang", "-l", choices=["us", "mx"], default="us", help="Target language/market")
    parser.add_argument("--out", "-o", default="", help="Output directory (default: output/commentary)")
    parser.add_argument("--skip-render", action="store_true", help="Only scrape and generate scripts")
    return parser.parse_args()


def _utf8_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main():
    _utf8_console()
    args = parse_args()
    print("=" * 60)
    print("VIRAL SHORTS COMMENTARY BOT")
    print(f"Target market: {args.lang.upper()} | Goal: {args.count} video(s)")
    print("=" * 60)

    scraper = ViralScraper()
    clips = []

    if args.folder:
        folder_path = Path(args.folder)
        if not folder_path.is_dir():
            print(f"❌ Folder not found: {args.folder}")
            return 1
        from factories.us.pipeline.util import ffprobe_duration, slugify
        import re
        all_vids = sorted(list(folder_path.glob("*.mp4")))
        if not all_vids:
            print(f"❌ No .mp4 files found in {args.folder}")
            return 1
        target_vids = all_vids[:args.count]
        print(f"\n[1/3] Found {len(all_vids)} videos in '{folder_path.name}'. Processing first {len(target_vids)} video(s)...")
        for f in target_vids:
            dur = round(ffprobe_duration(f), 2)
            title_clean = re.sub(r"^\d{8}\s*-\s*", "", f.stem)
            clips.append({
                "id": slugify(title_clean, 30) or f.stem[:30],
                "title": title_clean,
                "video_path": str(f),
                "duration": dur,
                "url": str(f),
                "uploader": folder_path.name,
                "view_count": 0,
            })
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {args.file}")
            return 1
        from factories.us.pipeline.util import ffprobe_duration, slugify
        dur = round(ffprobe_duration(file_path), 2)
        title_clean = file_path.stem
        # Clean leading dates like '20260117 - '
        import re
        title_clean = re.sub(r"^\d{8}\s*-\s*", "", title_clean)
        meta = {
            "id": slugify(title_clean, 30) or "local_video",
            "title": title_clean,
            "video_path": str(file_path),
            "duration": dur,
            "url": str(file_path),
            "uploader": "Local Video",
            "view_count": 0,
        }
        print(f"\n[1/3] Using local video: {file_path.name}")
        clips.append(meta)
    elif args.url:
        print(f"\n[1/3] Downloading direct clip: {args.url}")
        meta = scraper.download_clip(args.url)
        if meta:
            clips.append(meta)
        else:
            print("❌ Failed to download clip from URL.")
            return 1
    else:
        print(f"\n[1/3] Searching and downloading {args.count} viral clip(s)...")
        clips = scraper.fetch_batch(count=args.count, query=args.query or None, language=args.lang)

    if not clips:
        print("❌ No clips found or downloaded.")
        return 1

    out_dir = Path(args.out) if args.out else (CODE / "output" / "commentary")
    out_dir.mkdir(parents=True, exist_ok=True)

    rendered = []
    for idx, clip in enumerate(clips, 1):
        print(f"\n[{idx}/{len(clips)}] Processing: {clip['title'][:60]}...")
        print("  -> Writing transformative commentary script...")
        script = generate_commentary_script(clip, language=args.lang)

        print(f"  -> Hook Banner: '{script.get('hook_banner')}'")
        print(f"  -> Title: '{script.get('title')}'")
        print(f"  -> Scenes: {len(script.get('scenes', []))} scenes planned (~65-75s)")

        if args.skip_render:
            print("  -> [skip-render] Script generated, skipping video compilation.")
            continue

        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = out_dir / f"commentary_{stamp}_{clip['id']}.mp4"

        print(f"  -> Rendering final video with FFmpeg to {out_file.name}...")
        try:
            final_path = render_commentary_video(clip, script, out_file, language=args.lang)
            rendered.append(final_path)
            print(f"  ✅ DONE: {final_path.resolve()}")
        except Exception as e:
            print(f"  ❌ Render failed: {e}")

    print("\n" + "=" * 60)
    print(f"🎉 Completed! {len(rendered)}/{len(clips)} video(s) rendered successfully.")
    if rendered:
        print(f"📁 Output folder: {out_dir.resolve()}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
