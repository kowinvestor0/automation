"""True Crime & Real Mystery Storytelling Video Engine.
Produces 100% video-matched, documentary-style portrait 9:16 videos (>60s).
Combines:
- Authentic Wikipedia / Wikimedia Commons historical archive photos
- Cinematic 9:16 B-roll stock footage from Pexels
- Zero camera shake / zero jitter (Smooth slow Ken Burns pan only)
- Deep, suspenseful American voice narration (Edge TTS)
- High-retention ASS Karaoke subtitles
- Suspenseful dark ambient background music + Myinstants SFX cues
"""
from __future__ import annotations

import datetime as dt
import json
import os
import random
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.paths import CACHE_DIR, FONTS_DIR, OUTPUT_DIR, SFX_DIR, MUSIC_DIR
from core.tts_engine import ffprobe_duration, synthesize_script
from core.subtitles import build_ass_subtitles
from core.audio_processor import get_background_music
from core.wikimedia_client import WikimediaClient
from core.pexels_client import PexelsClient
from core.myinstants_client import MyInstantsClient


def _clean_banner_text(text: str) -> str:
    """Sanitizes hook banner string for FFmpeg drawtext."""
    raw = re.sub(r"[^\w\s!?¿¡-]", "", text).strip()
    if not raw:
        raw = "UNSOLVED MYSTERY"
    return raw.replace("'", "").replace(":", "\\:").replace("%", "%%")


def _render_image_to_video_segment(
    image_path: Path,
    duration: float,
    output_path: Path,
    pan_direction: str = "right"
) -> bool:
    """Renders an authentic archive photo into a butter-smooth 9:16 portrait video segment.
    Uses blurred backdrop + centered authentic photo + smooth cinematic slow Ken Burns motion.
    ABSOLUTELY ZERO CAMERA SHAKE / ZERO JITTER.
    """
    try:
        dur_str = f"{duration:.2f}"
        if pan_direction == "right":
            x_expr = f"(in_w-out_w)*(t/{dur_str})"
            y_expr = "(in_h-out_h)/2"
            scale_expr = "scale=1160:2060"
        elif pan_direction == "left":
            x_expr = f"(in_w-out_w)*(1-t/{dur_str})"
            y_expr = "(in_h-out_h)/2"
            scale_expr = "scale=1160:2060"
        elif pan_direction == "zoom_in":
            x_expr = "(in_w-out_w)/2"
            y_expr = "(in_h-out_h)/2"
            # Subtle zoom in (1.00 -> 1.06)
            scale_expr = f"scale='1080*(1+0.06*t/{dur_str})':'1920*(1+0.06*t/{dur_str})':eval=frame"
        elif pan_direction == "zoom_out":
            x_expr = "(in_w-out_w)/2"
            y_expr = "(in_h-out_h)/2"
            # Subtle zoom out (1.06 -> 1.00)
            scale_expr = f"scale='1080*(1.06-0.06*t/{dur_str})':'1920*(1.06-0.06*t/{dur_str})':eval=frame"
        else:
            x_expr = "(in_w-out_w)/2"
            y_expr = "(in_h-out_h)/2"
            scale_expr = "scale=1080:1920"

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-framerate", "30",
            "-loop", "1",
            "-t", dur_str,
            "-i", str(image_path),
            "-filter_complex",
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:2,eq=brightness=-0.35[bg];"
            f"[0:v]scale=980:1380:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[composite];"
            f"[composite]{scale_expr},crop=1080:1920:x='{x_expr}':y='{y_expr}',setsar=1,fps=30[v]",
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p", "-an",
            str(output_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 2000
    except Exception as e:
        print(f"[StoryEngine] Image render failed: {e}")
        return False



def _render_video_broll_segment(
    broll_path: Path,
    duration: float,
    output_path: Path,
    start_offset: float = 0.0
) -> bool:
    """Trims and scales Pexels B-roll to 1080x1920 9:16 portrait segment."""
    try:
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{start_offset:.2f}",
            "-t", f"{duration:.2f}",
            "-i", str(broll_path),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p", "-an",
            str(output_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 2000
    except Exception as e:
        print(f"[StoryEngine] B-roll segment render failed: {e}")
        return False


def render_crime_story_video(
    story: Dict[str, Any],
    out_file: Path,
    cfg: Optional[Dict[str, Any]] = None,
    log=print
) -> Path:
    """Renders a complete, high-retention True Crime storytelling video (>60s)."""
    workdir = out_file.parent / f"_tmp_story_{out_file.stem}"
    workdir.mkdir(parents=True, exist_ok=True)

    case_name = story.get("case_name", "True Crime Documentary")
    hook_banner = story.get("hook_banner", "UNSOLVED MYSTERY 😱")
    scenes_data = story.get("scenes", [])
    wiki_query = story.get("wiki_query", case_name)
    broll_queries = story.get("broll_queries", ["detective investigation night", "police flashing lights night"])

    # 0. Generate 100% unique script via Gemini API to prevent duplicate / unoriginal content
    channel_tag = story.get("channel_name", "")
    try:
        from core.gemini_script import generate_unique_crime_script
        ai_script = generate_unique_crime_script(
            case_name=case_name,
            wiki_query=wiki_query,
            base_scenes=scenes_data,
            channel_name=channel_tag,
            log=log
        )
        if ai_script and ai_script.get("scenes"):
            scenes_data = ai_script["scenes"]
            if ai_script.get("hook_banner"):
                hook_banner = ai_script["hook_banner"]
            if ai_script.get("hashtags"):
                story["hashtags"] = ai_script["hashtags"]
            log(f"[StoryEngine] Ap dung kich ban doc ban (100% unique) tu Gemini API cho kenh '{channel_tag}' ({len(scenes_data)} scenes)")
    except Exception as e:
        log(f"[StoryEngine] Gemini enhancement skipped ({e}), using base database.")

    log(f"[StoryEngine] Starting production for True Crime case: '{case_name}'...")

    # 1. Synthesize Voiceover (Deep, dramatic American narrator)
    # 1. Synthesize Voiceover (High-energy, fast-paced dramatic American narrator)
    log("[StoryEngine] 1/5 Synthesizing high-energy narrator voiceover (+15% fast pace for TikTok)...")
    voice_cfg = {
        "voice": cfg.get("voice", "en-US-ChristopherNeural") if cfg else "en-US-ChristopherNeural",
        "voice_rate": "+15%",  # Fast-paced, intense, energetic pacing to maximize retention and prevent sleepiness
        "font": "Anton",
        "font_size": 66,
        "highlight_color": "&H0033E5FF&",
        "words_per_caption": 2
    }
    tts_scenes = [{"role": "narrator", "text": sc["text"]} for sc in scenes_data]
    voice_path, timeline = synthesize_script(tts_scenes, voice_cfg, workdir, log=log)
    total_voice_dur = ffprobe_duration(voice_path)
    log(f"[StoryEngine] Generated fast-paced voiceover: {total_voice_dur:.1f}s across {len(timeline)} scenes")

    # 2. Build Animated ASS Subtitles (TikTok Safe Zone Compliant)
    log("[StoryEngine] 2/5 Generating safe-zone ASS karaoke subtitles...")
    ass_path = workdir / "subtitles.ass"
    sub_cfg = {
        "font": "Anton",
        "font_size": 66,
        "highlight_color": "&H0033E5FF&",
        "words_per_caption": 2
    }
    build_ass_subtitles(
        timeline=timeline,
        cfg=sub_cfg,
        out_path=ass_path
    )

    # 3. Gather Visual Media (100% Authentic Archival Photos from Wikimedia)
    log(f"[StoryEngine] 3/5 Downloading authentic archive photos for '{wiki_query}'...")
    wiki_client = WikimediaClient()
    wiki_photos = wiki_client.get_case_visuals(wiki_query, count=12)
    if not wiki_photos and wiki_query != case_name:
        wiki_photos = wiki_client.get_case_visuals(case_name, count=12)
    log(f"   [Wikimedia] Retrieved {len(wiki_photos)} authentic historical archive photo(s)")

    # 4. Assemble Scene Montage (1 authentic photo per scene with smooth Ken Burns motion)
    log(f"[StoryEngine] 4/5 Rendering smooth cinematic visual montage for {len(timeline)} scenes...")
    montage_segments = []
    concat_file = workdir / "montage_concat.txt"
    concat_lines = []
    motions = ["right", "zoom_in", "left", "zoom_out", "center"]

    for s_idx, sc_info in enumerate(timeline):
        sc_dur = float(sc_info.get("duration", 7.0))
        seg_dest = workdir / f"scene_seg_{s_idx:02d}.mp4"
        direction = motions[s_idx % len(motions)]

        success = False
        if wiki_photos:
            photo_p = wiki_photos[s_idx % len(wiki_photos)]
            success = _render_image_to_video_segment(photo_p, sc_dur, seg_dest, pan_direction=direction)

        if not success:
            # Fallback dark ambient background
            bg_cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", f"color=c=0x0a0c14:s=1080x1920:d={sc_dur:.2f}",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an",
                str(seg_dest)
            ]
            subprocess.run(bg_cmd, check=False)

        if seg_dest.exists() and seg_dest.stat().st_size > 1000:
            montage_segments.append(seg_dest)
            p_str = str(seg_dest.resolve()).replace("\\", "/")
            concat_lines.append(f"file '{p_str}'")

    concat_file.write_text("\n".join(concat_lines), encoding="utf-8")
    raw_montage_video = workdir / "raw_montage.mp4"
    concat_cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(raw_montage_video)
    ]
    subprocess.run(concat_cmd, check=True)

    # 5. Background Music Ducking & Mastering
    log("[StoryEngine] 5/5 Mixing dark suspense music & mastering audio...")
    bg_music = get_background_music(total_voice_dur, workdir)

    # Render master audio track FIRST (decoupled from video to guarantee zero audio cutoff)
    master_audio = workdir / "master_audio.wav"
    audio_filter = (
        "[0:a]volume=1.35,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,asplit=2[voice_sc][voice];"
        "[1:a]volume=0.10,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[music];"
        "[music][voice_sc]sidechaincompress=threshold=0.10:ratio=4:attack=20:release=350[ducked_music];"
        "[ducked_music][voice]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:LRA=7:TP=-1.5,aresample=async=1[a_out]"
    )
    cmd_audio = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(voice_path),
        "-i", str(bg_music),
        "-filter_complex", audio_filter,
        "-map", "[a_out]",
        "-t", f"{total_voice_dur:.2f}",
        str(master_audio)
    ]
    subprocess.run(cmd_audio, check=True)
    master_dur = ffprobe_duration(master_audio)
    log(f"[StoryEngine] Master audio track ready: {master_dur:.2f}s (voice: {total_voice_dur:.2f}s)")

    # Build video filter complex
    clean_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    font_file = FONTS_DIR / "Anton-Regular.ttf"
    if font_file.exists():
        clean_font = str(font_file.resolve()).replace("\\", "/").replace(":", "\\:")
        font_arg = f":fontfile='{clean_font}'"
    else:
        font_arg = ""
    clean_banner = _clean_banner_text(hook_banner)

    # Top Hook Banner styling: bold yellow text in dark banner box + ASS karaoke (safe 54pt font)
    video_filter = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,"
        "eq=saturation=1.05:contrast=1.04:brightness=0.01,"
        "drawbox=x=0:y=110:w=1080:h=150:color=black@0.80:t=fill,"
        f"drawtext=text='{clean_banner}'{font_arg}:fontcolor=yellow:fontsize=54:x=(w-text_w)/2:y=155,"
        f"ass='{clean_ass}'[v_out]"
    )

    final_cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(raw_montage_video),
        "-i", str(master_audio),
        "-filter_complex", video_filter,
        "-map", "[v_out]",
        "-map", "1:a",
        "-t", f"{total_voice_dur:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(out_file)
    ]
    subprocess.run(final_cmd, check=True)
    actual_dur = ffprobe_duration(out_file)
    log(f"[StoryEngine] Successfully rendered True Crime story video: {out_file.name} (Audio & Video: {actual_dur:.1f}s)")


    # Save metadata
    meta_path = out_file.with_suffix(".meta.json")
    meta_data = {
        "title": f"The Story of {case_name}",
        "hook_banner": hook_banner,
        "duration": total_voice_dur,
        "monetizable": total_voice_dur >= 60.0,
        "case_name": case_name,
        "hashtags": story.get("hashtags", ["#truecrime", "#mystery", "#fbi", "#unsolved", "#history", "#crimetok"]),
        "created_at": dt.datetime.now().isoformat(),
        "video_file": out_file.name
    }
    meta_path.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")

    # Cleanup temp workdir
    try:
        shutil.rmtree(workdir)
    except Exception:
        pass

    return out_file
