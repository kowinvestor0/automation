
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hub import settings, publish, state as hub_state


def parse_args():
    parser = argparse.ArgumentParser(description="Direct Local Video Folder Publisher")
    parser.add_argument("--dir", "-d", default=r"D:\video\Alan Medina", help="Path to video folder")
    parser.add_argument("--count", "-c", type=int, default=15, help="Number of videos to schedule")
    parser.add_argument("--live", action="store_true", help="Post live to Planly (default: dry run)")
    parser.add_argument("--route", "-r", default="us", help="Route/market to post to")
    return parser.parse_args()


def main():
    args = parse_args()
    folder = Path(args.dir)
    if not folder.exists() or not folder.is_dir():
        print(f"Folder not found: {folder}")
        return 1

    vids = sorted(list(folder.glob("*.mp4")))
    if not vids:
        print(f"No .mp4 videos found in {folder}")
        return 1

    seen = hub_state.seen_videos()
    available = [f for f in vids if f.name not in seen and f"{folder.name}{f.name}" not in seen]
    if not available:
        print(f"Recycling video pool for {folder.name}...")
        available = vids

    chosen = available[:args.count]
    print("=" * 60)
    print("DIRECT LOCAL VIDEO FOLDER PUBLISHER")
    print(f"Source: {folder} ({len(vids)} total, {len(available)} fresh)")
    print(f"Selected: {len(chosen)} video(s) for scheduling")
    mode_str = 'LIVE POSTING' if args.live else 'DRY RUN (Simulation)'
    print(f"Mode: {mode_str}")
    print("=" * 60)

    cfg = settings.load()
    pub_cfg = dict(cfg.get("publish", {}))
    pub_cfg["dry_run"] = not args.live
    pub_cfg["enabled"] = True
    pub_cfg["route"] = args.route

    key = settings.secret("PLANLY_API_KEY", cfg) or os.environ.get("PLANLY_API_KEY", "")
    if not key:
        print("PLANLY_API_KEY is not configured.")
        return 1

    items = []
    for f in chosen:
        clean_title = re.sub(r"^\d{8}\s*-\s*", "", f.stem)
        clean_title = re.sub(r"#\S+", "", clean_title).strip()
        items.append({
            "title": clean_title or f.stem,
            "description": f.stem,
            "folder": f"{folder.name}/{f.name}",
            "path": f,
            "duration_seconds": 30,
        })

    res = publish.publish(items, pub_cfg, key, log=print, factory=args.route)
    print("\n" + "=" * 60)
    print(f"Result: {res.scheduled} video(s) scheduled across Planly channels.")
    if res.errors:
        print("Errors encountered:", res.errors)
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
