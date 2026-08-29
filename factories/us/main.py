"""Automated short-video factory for a US audience (9:16, US English).

Uso:
    python main.py                      # one video
    python main.py --count 5            # five in a row
    python main.py --topic "roanoke colony"
    python main.py --voice en-US-AvaMultilingualNeural
    python main.py --bank               # force the local bank (no API)
"""
import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from pipeline.render import render
from pipeline.script_gen import build_script
from pipeline.subtitles import build_ass
from pipeline.tts import synth_scenes
from pipeline.util import (ROOT, ffprobe_duration, load_json, log, require_binaries,
                           save_json, slugify, step)
from pipeline.visuals import fetch_for_timeline

OUT = ROOT / "output"


def publish_to_planly(video, meta, cfg):
    """Hand the finished file to Planly, if the user turned that on.

    Never fatal: a scheduling problem should not throw away a video that already
    rendered. The file is on disk either way.
    """
    # When the hub drives the run it owns publishing, so the factory must not
    # also schedule - that is how a video ends up on the calendar twice.
    if os.environ.get("FACTORY_SKIP_PLANLY") == "1":
        return None

    pl = dict(cfg.get("planly") or {})
    if not pl.get("enabled"):
        return None

    key = os.environ.get("PLANLY_API_KEY", "").strip()
    if not key:
        log("planly.enabled is on but PLANLY_API_KEY is not set - skipping")
        return None

    step("6/6  Planly")
    try:
        from pipeline.planly import publish
        return publish(video, meta, pl, key)
    except Exception as e:
        log(f"Planly failed ({type(e).__name__}: {str(e)[:160]})")
        return {"error": f"{type(e).__name__}: {e}"}


def make_one(cfg, topic=None, force_bank=False):
    t0 = time.time()

    step("1/5  Script")
    script = build_script(cfg, topic=topic, force_bank=force_bank)
    log(f"[{script['source']}] {script['title']}")
    log(f"{len(script['scenes'])} scenes")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    workdir = OUT / f"{stamp}_{slugify(script['id'], 40)}"
    workdir.mkdir(parents=True, exist_ok=True)
    save_json(workdir / "script.json", script)

    step("2/5  Voiceover (Edge TTS)")
    voice_mp3, timeline = synth_scenes(script["scenes"], cfg, workdir)

    step("3/5  Captions")
    ass_path = build_ass(timeline, cfg, workdir / "subs.ass")
    log(f"{sum(len(s['words']) for s in timeline)} words synced")

    step("4/5  Visuals")
    assets = fetch_for_timeline(timeline, cfg, subject=script.get("subject"))

    step("5/5  Render (music + SFX + video)")
    video = render(timeline, assets, voice_mp3, ass_path, cfg, workdir)

    meta = {
        "title": script["title"],
        "description": (script.get("description", "") + "\n\n"
                        + " ".join(script.get("hashtags", []))).strip(),
        "hashtags": script.get("hashtags", []),
        "duration_seconds": round(ffprobe_duration(video), 2),
        "voice": cfg.get("voice"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": script["source"],
        "file": video.name,
        "attributions": [a["attribution"] for a in assets if a.get("attribution")],
    }
    if meta["attributions"]:
        # Most of Wikimedia Commons is CC-BY or CC-BY-SA, so credit is required.
        creditos = [f"{a['title']} - {a['author']} ({a['license']}) {a['url']}"
                    for a in meta["attributions"]]
        (workdir / "credits.txt").write_text("\n".join(creditos) + "\n", encoding="utf-8")
    schedule = publish_to_planly(video, meta, cfg)
    if schedule:
        meta["planly"] = schedule

    save_json(workdir / "meta.json", meta)
    save_json(workdir / "timeline.json", timeline)

    print(f"\nDONE in {time.time() - t0:.1f}s  ({meta['duration_seconds']}s of video)")
    print(f"   {video}")
    print(f"   title: {meta['title']}")
    print(f"   tags:  {' '.join(meta['hashtags'])}")
    return video


def main():
    ap = argparse.ArgumentParser(description="Automated short-form video generator (US)")
    ap.add_argument("--count", type=int, default=1, help="how many videos to make")
    ap.add_argument("--topic", help="force a topic (or a topics.json id in bank mode)")
    ap.add_argument("--niche", choices=["mysteries", "truecrime", "facts", "history", "money", "humor"])
    ap.add_argument("--voice", help="Edge TTS voice, e.g. en-US-AvaMultilingualNeural")
    ap.add_argument("--seconds", type=int, help="target length in seconds")
    ap.add_argument("--bank", action="store_true", help="use topics.json only, skip Claude")
    args = ap.parse_args()

    require_binaries()

    cfg = load_json(ROOT / "config.json")
    if cfg is None:
        print("ERROR: config.json is missing", file=sys.stderr)
        sys.exit(1)
    if args.niche:
        cfg["niche"] = args.niche
    # Each niche has its own pace: humor runs fast with no pauses, mystery
    # breathes. Applied before --voice so the flag still wins.
    preset = (cfg.get("niche_voice") or {}).get(cfg.get("niche"), {})
    cfg.update(preset)
    if args.voice:
        cfg["voice"] = args.voice
    if args.seconds:
        cfg["target_seconds"] = args.seconds

    OUT.mkdir(parents=True, exist_ok=True)

    made = []
    for i in range(args.count):
        if args.count > 1:
            print(f"\n{'=' * 60}\nVIDEO {i + 1} / {args.count}\n{'=' * 60}")
        try:
            made.append(make_one(cfg, topic=args.topic, force_bank=args.bank))
        except Exception as e:
            print(f"\nFAILED video {i + 1}: {type(e).__name__}: {e}", file=sys.stderr)

    if args.count > 1:
        print(f"\n{len(made)}/{args.count} videos written to {OUT}")
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())
