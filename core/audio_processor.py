"""Advanced audio processor: Vocal suppression, ambient SFX preservation, ducking & mastering."""
from __future__ import annotations

import os
import random
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.paths import MUSIC_DIR, SFX_DIR


def has_audio_stream(video_path: Path) -> bool:
    """Check if video has an audio stream."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(video_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return bool(res.stdout.strip())
    except Exception:
        return False


def build_vocal_suppression_filter(input_label: str, volume: float = 0.15) -> str:
    """FFmpeg filter to suppress human speech (center mono vocal cancel)

    while preserving wide environmental sound effects (SFX) and ambient noise.
    Uses stereo center-channel subtraction + bandpass texture.
    """
    return (
        f"[{input_label}]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
        f"stereotools=mlev=0.15:slev=1.2:mpan=0,"
        f"volume={volume:.2f}[ambient_sfx]"
    )


def get_background_music(target_duration: float, workdir: Path) -> Path:
    """Pick a high-retention background music track or synthesize one."""
    music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
    if music_files:
        chosen = random.choice(music_files)
        # Loop or trim to target duration
        looped = workdir / "bg_music.mp3"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-stream_loop", "-1",
            "-i", str(chosen),
            "-t", f"{target_duration:.2f}",
            "-af", f"afade=t=in:d=1,afade=t=out:st={max(0, target_duration - 2.5):.2f}:d=2.5",
            "-c:a", "libmp3lame", "-b:a", "192k",
            str(looped)
        ]
        subprocess.run(cmd, check=True)
        return looped

    # Fallback: synthesize ambient cinematic pulse with FFmpeg
    synth = workdir / "bg_music_synth.mp3"
    fc = (
        f"sine=frequency=65.41:duration={target_duration:.2f}[b];"
        f"sine=frequency=130.81:duration={target_duration:.2f}[n1];"
        f"sine=frequency=196.00:duration={target_duration:.2f}[n2];"
        f"[b]volume=0.35,tremolo=f=1.2:d=0.6[bass];"
        f"[n1]volume=0.18,tremolo=f=0.2:d=0.4[lead];"
        f"[n2]volume=0.12,vibrato=f=0.4:d=0.3[pad];"
        f"[bass][lead][pad]amix=inputs=3:normalize=0,"
        f"lowpass=f=1800,aecho=0.8:0.85:180|420:0.35|0.2,"
        f"afade=t=in:d=1.5,afade=t=out:st={max(0, target_duration - 2.5):.2f}:d=2.5[out]"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"sine=frequency=65.41:duration={target_duration:.2f}",
        "-f", "lavfi", "-i", f"sine=frequency=130.81:duration={target_duration:.2f}",
        "-f", "lavfi", "-i", f"sine=frequency=196.00:duration={target_duration:.2f}",
        "-filter_complex",
        "[0:a]volume=0.35,tremolo=f=1.2:d=0.6[bass];"
        "[1:a]volume=0.18,tremolo=f=0.2:d=0.4[lead];"
        "[2:a]volume=0.12,vibrato=f=0.4:d=0.3[pad];"
        "[bass][lead][pad]amix=inputs=3:normalize=0,lowpass=f=1800[out]",
        "-map", "[out]", "-t", f"{target_duration:.2f}",
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(synth)
    ]
    subprocess.run(cmd, check=True)
    return synth


def build_sfx_track(timeline: List[Dict[str, Any]], total_duration: float, workdir: Path) -> Optional[Path]:
    """Generates an aligned SFX track (Whooshes at cuts, Booms/Risers at climax)."""
    whoosh = SFX_DIR / "whoosh.wav"
    boom = SFX_DIR / "vineboom.mp3" if (SFX_DIR / "vineboom.mp3").exists() else (SFX_DIR / "boom.wav")
    riser = SFX_DIR / "dramaticdundundun.mp3" if (SFX_DIR / "dramaticdundundun.mp3").exists() else (SFX_DIR / "riser.wav")
    scratch = SFX_DIR / "recordscratch.mp3"

    sfx_events = []
    for sc in timeline:
        start = float(sc.get("start", 0.0))
        idx = int(sc.get("index", 0))
        if idx == 0 and boom.exists():
            sfx_events.append((boom, max(0.0, start)))
        elif idx == max(0, len(timeline) - 2) and riser.exists():
            sfx_events.append((riser, max(0.0, start)))
        elif idx == 3 and scratch.exists():
            sfx_events.append((scratch, max(0.0, start)))
        elif whoosh.exists() and start > 1.0:
            sfx_events.append((whoosh, start))

    if not sfx_events:
        return None

    inputs = []
    filters = []
    for i, (fpath, offset) in enumerate(sfx_events):
        inputs += ["-i", str(fpath)]
        delay_ms = int(offset * 1000)
        filters.append(f"[{i}:a]adelay={delay_ms}|{delay_ms},volume=0.25[sfx{i}]")

    joined = "".join(f"[sfx{i}]" for i in range(len(sfx_events)))
    fc = f"{';'.join(filters)};{joined}amix=inputs={len(sfx_events)}:normalize=0[sfx_out]"

    out_sfx = workdir / "sfx_mix.wav"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        *inputs,
        "-filter_complex", fc,
        "-map", "[sfx_out]",
        "-t", f"{total_duration:.2f}",
        str(out_sfx)
    ]
    subprocess.run(cmd, check=True)
    return out_sfx
