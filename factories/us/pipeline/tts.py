"""Voiceover via Edge TTS (free) plus word-level timings."""
import asyncio
from pathlib import Path

from .util import ffprobe_duration, log, run

TICKS = 10_000_000  # edge-tts reporta offsets en unidades de 100 ns


async def _synth_one(text, voice, rate, pitch, out_path):
    import edge_tts

    # edge-tts >= 7 defaults to SentenceBoundary; we need it word by word.
    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch,
                                    boundary="WordBoundary")
    except TypeError:
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)

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
    if out_path.stat().st_size == 0:
        raise RuntimeError("Edge TTS returned empty audio (check your connection)")
    return words


def _estimate_words(text, duration):
    """Fallback: split the duration across words by their length."""
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


def synth_scenes(scenes, cfg, workdir):
    """Synthesize each scene separately; returns (final_mp3, timed_scenes)."""
    workdir = Path(workdir)
    voice = cfg.get("voice", "es-MX-JorgeNeural")
    rate = cfg.get("voice_rate", "+0%")
    pitch = cfg.get("voice_pitch", "+0Hz")
    gap = float(cfg.get("scene_gap", 0.12))

    parts = []
    timeline = []
    cursor = 0.0

    for i, sc in enumerate(scenes):
        mp3 = workdir / f"scene_{i:02d}.mp3"
        words = asyncio.run(_synth_one(sc["text"], voice, rate, pitch, mp3))
        dur = ffprobe_duration(mp3)
        if not words:
            words = _estimate_words(sc["text"], dur)
            log(f"scene {i + 1}/{len(scenes)}: {dur:.2f}s, {len(words)} words (estimated)")
        else:
            log(f"scene {i + 1}/{len(scenes)}: {dur:.2f}s, {len(words)} words")

        timeline.append({
            "index": i,
            "text": sc["text"],
            "keywords": sc.get("keywords", []),
            "audio": mp3.name,
            "start": cursor,
            "duration": dur + gap,
            "words": [
                {"text": w["text"], "start": cursor + w["start"], "end": cursor + w["end"]}
                for w in words
            ],
        })
        parts.append(mp3)
        cursor += dur + gap

    voice_mp3 = workdir / "voice.mp3"
    _concat_audio(parts, gap, voice_mp3, workdir)
    log(f"total voiceover: {ffprobe_duration(voice_mp3):.2f}s")
    return voice_mp3, timeline


def _concat_audio(parts, gap, out_path, workdir):
    """Concatenate the mp3s with `gap` seconds of silence between scenes."""
    inputs = []
    filters = []
    for i, p in enumerate(parts):
        inputs += ["-i", p.name]
        filters.append(f"[{i}:a]aresample=44100,apad=pad_dur={gap}[a{i}]")
    chain = ";".join(filters)
    joined = "".join(f"[a{i}]" for i in range(len(parts)))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs,
           "-filter_complex", f"{chain};{joined}concat=n={len(parts)}:v=0:a=1[out]",
           "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "192k", out_path.name]
    run(cmd, cwd=workdir)
