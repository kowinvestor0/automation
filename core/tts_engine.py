"""Natural AI Voiceover synthesis using edge-tts with precise word boundaries."""
from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

TICKS = 10_000_000  # edge-tts reports 100ns units


def ffprobe_duration(media_path: Path) -> float:
    """Accurately probe media duration using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(media_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 0.0


async def _synth_scene(text: str, voice: str, rate: str, pitch: str, out_path: Path) -> List[Dict[str, Any]]:
    import edge_tts

    candidates = [voice]
    for b in ("en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-BrianMultilingualNeural"):
        if b not in candidates:
            candidates.append(b)

    last_err = None
    for v in candidates:
        try:
            try:
                comm = edge_tts.Communicate(text, v, rate=rate, pitch=pitch, boundary="WordBoundary")
            except TypeError:
                comm = edge_tts.Communicate(text, v, rate=rate, pitch=pitch)

            words = []
            with open(out_path, "wb") as f:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        words.append({
                            "text": chunk["text"],
                            "start": chunk["offset"] / TICKS,
                            "end": (chunk["offset"] + chunk["duration"]) / TICKS,
                        })
            if out_path.exists() and out_path.stat().st_size > 0:
                return words
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Edge TTS failed for text: {text[:40]}... ({last_err})")


def _estimate_words(text: str, duration: float) -> List[Dict[str, Any]]:
    tokens = [t for t in text.split() if t.strip()]
    if not tokens:
        return []
    weights = [len(t) + 1 for t in tokens]
    total = sum(weights)
    out, cursor = [], 0.0
    for tok, weight in zip(tokens, weights):
        span = duration * weight / total
        out.append({"text": tok, "start": cursor, "end": cursor + span * 0.92})
        cursor += span
    return out


def synthesize_script(
    scenes: List[Dict[str, Any]],
    voice_cfg: Dict[str, Any],
    workdir: Path,
    log=print
) -> Tuple[Path, List[Dict[str, Any]]]:
    """Synthesizes all scenes and returns (full_voice_mp3, timeline_with_word_timings)."""
    workdir.mkdir(parents=True, exist_ok=True)
    voice = voice_cfg.get("voice", "en-US-ChristopherNeural")
    rate = voice_cfg.get("voice_rate", "+10%")
    pitch = voice_cfg.get("voice_pitch", "+0Hz")
    gap = float(voice_cfg.get("scene_gap", 0.12))

    parts = []
    timeline = []
    cursor = 0.0

    for i, sc in enumerate(scenes):
        sc_text = sc.get("text", "").strip()
        if not sc_text:
            continue
        
        # Dual-speaker role selection: role 'q' uses voice_q, role 'a' uses voice_a
        role = sc.get("role", "q")
        scene_voice = sc.get("voice") or (voice_cfg.get("voice_a") if role == "a" else voice_cfg.get("voice_q")) or voice
        
        mp3 = workdir / f"scene_{i:02d}.mp3"
        words = asyncio.run(_synth_scene(sc_text, scene_voice, rate, pitch, mp3))
        dur = ffprobe_duration(mp3)

        if not words:
            words = _estimate_words(sc_text, dur)

        timeline.append({
            "index": i,
            "text": sc_text,
            "audio": str(mp3),
            "start": cursor,
            "duration": dur + gap,
            "words": [
                {"text": w["text"], "start": cursor + w["start"], "end": cursor + w["end"]}
                for w in words
            ],
        })
        parts.append(mp3)
        cursor += dur + gap

    full_voice = workdir / "full_narration.mp3"
    inputs = []
    filters = []
    for i, p in enumerate(parts):
        inputs += ["-i", str(p)]
        filters.append(f"[{i}:a]aresample=44100,apad=pad_dur={gap}[a{i}]")
    chain = ";".join(filters)
    joined = "".join(f"[a{i}]" for i in range(len(parts)))

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        *inputs,
        "-filter_complex", f"{chain};{joined}concat=n={len(parts)}:v=0:a=1[out]",
        "-map", "[out]",
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(full_voice)
    ]
    subprocess.run(cmd, check=True)
    total_dur = ffprobe_duration(full_voice)
    log(f"[TTS] Generated full voiceover: {total_dur:.1f}s ({len(scenes)} scenes)")
    return full_voice, timeline
