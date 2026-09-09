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
    """Renders a still photo into a butter-smooth 9:16 portrait video segment.
    Uses blurred background + centered authentic photo + smooth slow pan.
    ABSOLUTELY ZERO CAMERA SHAKE / ZERO JITTER.
    """
    try:
        dur_str = f"{duration:.2f}"
        # Pan horizontally across slightly oversized frame
        if pan_direction == "right":
            x_expr = f"(in_w-out_w)*(t/{dur_str})"
        elif pan_direction == "left":
            x_expr = f"(in_w-out_w)*(1-t/{dur_str})"
        else:
            x_expr = "(in_w-out_w)/2"

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
            f"[composite]scale=1160:2060,crop=1080:1920:x='{x_expr}':y='(in_h-out_h)/2',setsar=1,fps=30[v]",
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

    log(f"[StoryEngine] Starting production for True Crime case: '{case_name}'...")

    # 1. Synthesize Voiceover (Deep, dramatic American narrator)
    log("[StoryEngine] 1/5 Synthesizing dramatic narrator voiceover (Edge TTS)...")
    voice_cfg = {
        "voice": "en-US-ChristopherNeural",
        "voice_rate": "-2%",  # Slightly slower for intense suspenseful pacing
        "font": "Anton",
        "font_size": 90,
        "highlight_color": "&H0033E5FF&",
        "words_per_caption": 3
    }
    tts_scenes = [{"role": "narrator", "text": sc["text"]} for sc in scenes_data]
    voice_path, timeline = synthesize_script(tts_scenes, voice_cfg, workdir, log=log)
    total_voice_dur = ffprobe_duration(voice_path)
    log(f"[StoryEngine] Generated voiceover duration: {total_voice_dur:.1f}s across {len(timeline)} scenes")

    # 2. Build Animated ASS Subtitles
    log("[StoryEngine] 2/5 Generating dynamic ASS karaoke subtitles...")
    ass_path = workdir / "subtitles.ass"
    sub_cfg = {
        "font": "Anton",
        "font_size": 90,
        "highlight_color": "&H0033E5FF&",
        "words_per_caption": 3
    }
    build_ass_subtitles(
        timeline=timeline,
        cfg=sub_cfg,
        out_path=ass_path
    )

    # 3. Gather Visual Media (Wikimedia Archival Photos + Pexels B-Roll)
    log(f"[StoryEngine] 3/5 Downloading authentic archive photos & cinematic B-roll...")
    wiki_client = WikimediaClient()
    wiki_photos = wiki_client.get_case_visuals(wiki_query, count=4)
    log(f"   [Wikimedia] Retrieved {len(wiki_photos)} authentic archive photo(s)")

    pexels_client = PexelsClient()
    broll_clips = []
    if pexels_client.is_configured:
        for bq in broll_queries:
            results = pexels_client.search_videos(bq, per_page=4)
            for vdata in results:
                dl = pexels_client.download_video_file(vdata)
                if dl and dl.exists():
                    broll_clips.append(dl)
                    break
    log(f"   [Pexels] Retrieved {len(broll_clips)} cinematic B-roll clip(s)")

    # 4. Assemble Scene Montage (1 visual per scene transition, NO SHAKE)
    log(f"[StoryEngine] 4/5 Rendering smooth cinematic visual montage for {len(timeline)} scenes...")
    montage_segments = []
    concat_file = workdir / "montage_concat.txt"
    concat_lines = []

    wiki_idx = 0
    broll_idx = 0

    for s_idx, sc_info in enumerate(timeline):
        sc_dur = float(sc_info.get("duration", 7.0))
        seg_dest = workdir / f"scene_seg_{s_idx:02d}.mp4"
        orig_scene = scenes_data[s_idx] if s_idx < len(scenes_data) else {}
        visual_hint = orig_scene.get("visual_hint", "wiki" if (s_idx % 2 == 1) else "broll")

        success = False
        if visual_hint == "wiki" and wiki_photos:
            photo_p = wiki_photos[wiki_idx % len(wiki_photos)]
            wiki_idx += 1
            direction = "right" if (s_idx % 2 == 0) else "left"
            success = _render_image_to_video_segment(photo_p, sc_dur, seg_dest, pan_direction=direction)

        if not success and broll_clips:
            clip_p = broll_clips[broll_idx % len(broll_clips)]
            broll_idx += 1
            clip_dur = ffprobe_duration(clip_p)
            start_off = random.uniform(0.0, max(0.0, clip_dur - sc_dur - 1.0)) if (clip_dur > sc_dur + 1.0) else 0.0
            success = _render_video_broll_segment(clip_p, sc_dur, seg_dest, start_offset=start_off)

        if not success and wiki_photos:
            photo_p = wiki_photos[0]
            success = _render_image_to_video_segment(photo_p, sc_dur, seg_dest, pan_direction="center")

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

    # 5. Sound Effects & Audio Mixing
    log("[StoryEngine] 5/5 Mixing dark suspense music, SFX & mastering audio...")
    bg_music = get_background_music(total_voice_dur, workdir)

    myinstants = MyInstantsClient()
    sfx_inputs = []
    sfx_filter_chains = []

    # Map SFX cues from scenes
    sfx_count = 0
    for s_idx, sc_info in enumerate(timeline):
        orig_sc = scenes_data[s_idx] if s_idx < len(scenes_data) else {}
        sfx_cue = orig_sc.get("sfx")
        if sfx_cue:
            start_t = float(sc_info.get("start", 0.0))
            sfx_file = myinstants.download_sound(sfx_cue)
            if sfx_file and sfx_file.exists():
                delay_ms = int(start_t * 1000)
                sfx_inputs.extend(["-i", str(sfx_file)])
                sfx_idx = 3 + sfx_count
                sfx_filter_chains.append(f"[{sfx_idx}:a]adelay={delay_ms}|{delay_ms},volume=0.35[sfx_{sfx_count}];")
                sfx_count += 1
            if sfx_count >= 5:
                break

    # Build audio & video filter complex
    clean_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
    font_file = FONTS_DIR / "Anton-Regular.ttf"
    font_arg = f":fontfile='{str(font_file).replace('\\', '/').replace(':', '\\:')}'" if font_file.exists() else ""
    clean_banner = _clean_banner_text(hook_banner)

    # Top Hook Banner styling: bold yellow text in dark banner box + ASS karaoke
    video_filter = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,"
        "drawbox=x=0:y=110:w=1080:h=170:color=black@0.75:t=fill,"
        f"drawtext=text='{clean_banner}'{font_arg}:fontcolor=yellow:fontsize=76:x=(w-text_w)/2:y=155,"
        f"ass='{clean_ass}'[v_out]"
    )

    af_parts = [
        "[1:a]volume=1.25,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,asplit=2[voice_sc][voice];",
        "[2:a]volume=0.12,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[music];",
        "[music][voice_sc]sidechaincompress=threshold=0.12:ratio=4:attack=20:release=350[ducked_music];",
    ]
    mix_ins = ["[ducked_music]", "[voice]"]

    for i in range(sfx_count):
        af_parts.append(f"{sfx_filter_chains[i]}")
        mix_ins.append(f"[sfx_{i}]")

    af_parts.append(f"{''.join(mix_ins)}amix=inputs={len(mix_ins)}:normalize=0,loudnorm=I=-14:LRA=7:TP=-1.5[a_out]")
    audio_filter = "".join(af_parts)

    final_cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(raw_montage_video),
        "-i", str(voice_path),
        "-i", str(bg_music),
        *sfx_inputs,
        "-filter_complex", f"{video_filter};{audio_filter}",
        "-map", "[v_out]",
        "-map", "[a_out]",
        "-t", f"{total_voice_dur:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(out_file)
    ]
    subprocess.run(final_cmd, check=True)
    log(f"[StoryEngine] Successfully rendered True Crime story video: {out_file.name} ({total_voice_dur:.1f}s)")

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
