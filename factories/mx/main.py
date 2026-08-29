"""Fabrica de videos automaticos para audiencia mexicana (9:16, espanol de Mexico).

Uso:
    python main.py                      # 1 video
    python main.py --count 5            # 5 videos seguidos
    python main.py --topic "el chupacabras"
    python main.py --voice es-MX-DaliaNeural
    python main.py --bank               # fuerza el banco local (sin API)
"""
import argparse
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


def make_one(cfg, topic=None, force_bank=False):
    t0 = time.time()

    step("1/5  Guion")
    script = build_script(cfg, topic=topic, force_bank=force_bank)
    log(f"[{script['source']}] {script['title']}")
    log(f"{len(script['scenes'])} escenas")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    workdir = OUT / f"{stamp}_{slugify(script['id'], 40)}"
    workdir.mkdir(parents=True, exist_ok=True)
    save_json(workdir / "script.json", script)

    step("2/5  Voz en off (Edge TTS)")
    voice_mp3, timeline = synth_scenes(script["scenes"], cfg, workdir)

    step("3/5  Subtitulos")
    ass_path = build_ass(timeline, cfg, workdir / "subs.ass")
    log(f"{sum(len(s['words']) for s in timeline)} palabras sincronizadas")

    step("4/5  Imagenes y video")
    assets = fetch_for_timeline(timeline, cfg, subject=script.get("subject"))

    step("5/5  Render (musica + efectos + video)")
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
        # Casi todo Wikimedia Commons es CC-BY o CC-BY-SA: hay que dar credito.
        creditos = [f"{a['title']} - {a['author']} ({a['license']}) {a['url']}"
                    for a in meta["attributions"]]
        (workdir / "creditos.txt").write_text("\n".join(creditos) + "\n", encoding="utf-8")
    save_json(workdir / "meta.json", meta)
    save_json(workdir / "timeline.json", timeline)

    print(f"\nLISTO en {time.time() - t0:.1f}s  ({meta['duration_seconds']}s de video)")
    print(f"   {video}")
    print(f"   titulo: {meta['title']}")
    print(f"   tags:   {' '.join(meta['hashtags'])}")
    return video


def main():
    ap = argparse.ArgumentParser(description="Generador automatico de videos cortos (MX)")
    ap.add_argument("--count", type=int, default=1, help="cuantos videos generar")
    ap.add_argument("--topic", help="tema forzado (o id de topics.json en modo banco)")
    ap.add_argument("--niche", choices=["misterios", "humor", "curiosidades", "historia", "lugares"])
    ap.add_argument("--voice", help="voz de Edge TTS, ej. es-MX-DaliaNeural")
    ap.add_argument("--seconds", type=int, help="duracion objetivo en segundos")
    ap.add_argument("--bank", action="store_true", help="usar solo topics.json, sin Claude")
    args = ap.parse_args()

    require_binaries()

    cfg = load_json(ROOT / "config.json")
    if cfg is None:
        print("ERROR: falta config.json", file=sys.stderr)
        sys.exit(1)
    if args.niche:
        cfg["niche"] = args.niche
    # Cada nicho tiene su ritmo: el humor va rapido y sin pausas, el misterio
    # respira. Se aplica antes de --voice para que la bandera siga mandando.
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
            print(f"\nFALLO el video {i + 1}: {type(e).__name__}: {e}", file=sys.stderr)

    if args.count > 1:
        print(f"\n{len(made)}/{args.count} videos generados en {OUT}")
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())
