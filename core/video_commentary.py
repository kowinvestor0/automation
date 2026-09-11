"""Video Commentary Engine: Generates video-specific, high-retention commentary
reacting to the actual footage with natural duration matching and vocal isolation.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yt_dlp

from core.paths import CACHE_DIR, OUTPUT_DIR
from core.tts_engine import ffprobe_duration
from core.config_manager import get_api_key
from core.audio_processor import has_audio_stream

SOURCES_DIR = CACHE_DIR / "sources"
SOURCES_DIR.mkdir(parents=True, exist_ok=True)


def download_or_load_source_video(
    source_input: str,
    target_tier: str = "growth",
    cut_start: float = 0.0,
    cut_duration: Optional[float] = None,
    log=print
) -> Dict[str, Any]:
    source_input = source_input.strip()
    
    # Local file
    local_p = Path(source_input)
    if local_p.exists() and local_p.is_file():
        dur = ffprobe_duration(local_p)
        return {
            "id": local_p.stem,
            "title": local_p.stem,
            "description": "",
            "transcript": "",
            "video_path": str(local_p.resolve()),
            "duration": dur,
            "source_type": "local",
            "url": ""
        }

    # Online URL
    log(f"[VideoCommentary] Extracting video metadata from: {source_input}...")
    ydl_opts = {
        "outtmpl": str(SOURCES_DIR / "%(id)s.%(ext)s"),
        "format": "bestvideo[height<=1920][ext=mp4]+bestaudio[ext=m4a]/best[height<=1920][ext=mp4]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "vi"],
        "subtitlesformat": "vtt",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(source_input, download=True)

    vid_id = info.get("id")
    title = info.get("title", "Viral Clip")
    raw_dur = float(info.get("duration") or 35.0)
    desc = info.get("description", "")
    
    mp4_file = SOURCES_DIR / f"{vid_id}.mp4"
    if not mp4_file.exists():
        for f in SOURCES_DIR.glob(f"{vid_id}.*"):
            if f.suffix in (".mp4", ".mkv", ".webm"):
                mp4_file = f
                break

    actual_dur = ffprobe_duration(mp4_file) if mp4_file.exists() else raw_dur

    transcript = ""
    for sub_file in SOURCES_DIR.glob(f"{vid_id}.*.vtt"):
        try:
            sub_text = sub_file.read_text(encoding="utf-8", errors="ignore")
            cleaned = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*", "", sub_text)
            cleaned = re.sub(r"<[^>]+>", "", cleaned)
            cleaned = re.sub(r"WEBVTT.*", "", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if len(cleaned) > 20:
                transcript = cleaned[:1000]
                break
        except Exception:
            pass

    final_video_path = mp4_file
    final_duration = actual_dur

    if actual_dur > 90.0 and cut_duration and cut_duration > 10.0:
        log(f"[VideoCommentary] Source video is long ({actual_dur:.1f}s), cutting {cut_duration:.1f}s segment from {cut_start:.1f}s...")
        cut_out = SOURCES_DIR / f"{vid_id}_cut_{int(cut_start)}_{int(cut_duration)}.mp4"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", str(cut_start),
            "-i", str(mp4_file),
            "-t", str(cut_duration),
            "-c:v", "libx264", "-c:a", "aac",
            str(cut_out)
        ]
        subprocess.run(cmd, check=False)
        if cut_out.exists():
            final_video_path = cut_out
            final_duration = ffprobe_duration(cut_out)

    return {
        "id": vid_id,
        "title": title,
        "description": desc,
        "transcript": transcript,
        "video_path": str(final_video_path.resolve()),
        "duration": final_duration,
        "source_type": "online",
        "url": source_input
    }


def generate_commentary_script(
    video_info: Dict[str, Any],
    voice_q: str = "en-US-BrianNeural",
    voice_a: str = "en-US-ChristopherNeural",
    language: str = "en"
) -> Dict[str, Any]:
    """Generates an electrifying, 100% video-matched dual-voice commentary (>60s).
    Powered by core.script_synthesizer with 22 specialized domains and Gemini API support.
    """
    from core.script_synthesizer import generate_intelligent_script
    return generate_intelligent_script(
        video_info=video_info,
        voice_q=voice_q,
        voice_a=voice_a,
        language=language
    )


def fetch_viral_batch_sources(count: int = 6, log=print) -> List[Dict[str, Any]]:
    """Fetches a batch of completely distinct viral source clips across diverse categories.
    Ensures that every commentary video has 100% unique primary footage!
    """
    from core.scraper import VideoScraper
    from core.config_manager import load_config
    scraper = VideoScraper()
    cfg = load_config()
    queries = cfg.get("search_queries") or [
        "hydraulic press crushing experiment",
        "crazy science experiment reactions",
        "unbelievable wild animal encounters",
        "extreme engineering mega machines",
        "bizarre mystery phenomena caught on camera",
        "satisfying craftsmanship restoration",
        "deep ocean strange creatures discovery",
        "deadly survival situations explained",
        "unexpected sports physics moments",
        "crazy chemical reaction slow motion"
    ]
    log(f"[VideoCommentary] Searching {count} distinct viral video clips across diverse niches...")
    sources = []
    seen_ids = set()

    for i in range(count):
        q = queries[i % len(queries)]
        log(f"  -> Niche #{i+1}: '{q}'...")
        clips = scraper.search_viral_clips(q, limit=6)
        downloaded_clip = None
        for c in clips:
            if c["id"] in seen_ids:
                continue
            downloaded_clip = scraper.download_clip(c["url"])
            if downloaded_clip and Path(downloaded_clip["video_path"]).exists():
                seen_ids.add(c["id"])
                break

        if downloaded_clip:
            sources.append(downloaded_clip)
            log(f"  -> Acquired clip #{i+1}: {downloaded_clip.get('title', '')[:40]} ({downloaded_clip.get('duration', 0):.1f}s)")
        else:
            log(f"  -> Warning: could not download unique clip for niche '{q}'")

    return sources


def render_hybrid_commentary_video(
    source_video_info: Dict[str, Any],
    out_file: Path,
    cfg: Optional[Dict[str, Any]] = None,
    enable_broll_cutaways: bool = False,
    log=print
) -> Path:
    """Renders a pure, continuous single-video commentary (or optional hybrid with B-roll).
    - Single continuous video footage from beginning to end
    - Center-vocal suppression on original audio
    - Synchronized dual-voice commentary reacting to the action
    - Top Hook Banner & Dynamic ASS Karaoke subtitles
    """
    from core.tts_engine import synthesize_script
    from core.subtitles import build_ass_subtitles
    from core.audio_processor import get_background_music, build_sfx_track
    from core.pexels_client import PexelsClient
    from core.video_engine import _clean_hook_banner
    from core.paths import FONTS_DIR

    cfg = cfg or {}
    workdir = out_file.parent / f"_tmp_{out_file.stem}"
    workdir.mkdir(parents=True, exist_ok=True)

    log(f"[Commentary Engine] Preparing commentary script for '{source_video_info.get('title', '')}'...")
    script = generate_commentary_script(source_video_info)
    scenes = script["scenes"]

    # Voice config
    voice_cfg = {
        "voice_q": script.get("voice_q", "en-US-BrianNeural"),
        "voice_a": script.get("voice_a", "en-US-ChristopherNeural"),
        "voice_rate": cfg.get("voice_rate", "+5%"),
        "font": "Anton",
        "font_size": cfg.get("font_size", 95),
        "highlight_color": script.get("highlight_color", "&H0033E5FF&"),
        "words_per_caption": 3,
    }

    log("[Commentary Engine] 1/4 Synthesizing dual-voice narration & timeline...")
    full_voice_path, timeline = synthesize_script(scenes, voice_cfg, workdir, log=log)
    total_voice_dur = ffprobe_duration(full_voice_path)

    log("[Commentary Engine] 2/4 Building animated ASS karaoke subtitles...")
    ass_path = workdir / "subtitles.ass"
    build_ass_subtitles(timeline, voice_cfg, ass_path, w=1080, h=1920)

    src_video_path = Path(source_video_info["video_path"])
    src_dur = ffprobe_duration(src_video_path)

    if enable_broll_cutaways:
        log("[Commentary Engine] 3/4 Fetching HD Pexels B-roll cutaways...")
        pex = PexelsClient()
        broll_clips = []
        if pex.is_configured:
            topic = source_video_info.get("title", "")
            clean_topic = re.sub(r"[^\w\s]", "", topic)
            keywords = " ".join([w for w in clean_topic.split() if len(w) >= 4][:2]) or "cinematic"
            found = pex.search_videos(keywords, per_page=4)
            for v in found:
                dl = pex.download_video_file(v)
                if dl and dl.exists():
                    broll_clips.append(dl)

        seg_files = []
        concat_list = workdir / "montage_concat.txt"
        concat_lines = []
        for idx, sc in enumerate(timeline):
            sc_dur = float(sc.get("duration", 8.0))
            seg_out = workdir / f"seg_{idx:02d}.mp4"
            use_broll = (idx % 2 == 1) and broll_clips
            if use_broll:
                clip_p = broll_clips[(idx // 2) % len(broll_clips)]
                cut_start = 0.0
            else:
                clip_p = src_video_path
                cut_start = min(max(0.0, (src_dur - sc_dur) * (idx / max(1, len(timeline)))), max(0.0, src_dur - sc_dur))

            vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30"
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-ss", f"{cut_start:.2f}", "-t", f"{sc_dur:.2f}",
                "-i", str(clip_p), "-vf", vf,
                "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-an",
                str(seg_out)
            ]
            subprocess.run(cmd, check=True)
            seg_files.append(seg_out)
            concat_lines.append(f"file '{str(seg_out.resolve()).replace('\\', '/')}'")

        concat_list.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
        stitched_footage = workdir / "stitched_footage.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(stitched_footage)
        ], check=True)
    else:
        log(f"[Commentary Engine] 3/4 Using single continuous video footage ({src_dur:.1f}s)...")
        stitched_footage = src_video_path

    log("[Commentary Engine] 4/4 Mixing audio & final 1080x1920 render...")
    bg_music = get_background_music(total_voice_dur, workdir)
    sfx_path = build_sfx_track(timeline, total_voice_dur, workdir)

    # 1. Master Audio Track (Decoupled to guarantee zero audio cutoff)
    master_audio = workdir / "master_audio.wav"
    audio_inputs = [
        "-i", str(full_voice_path),
        "-i", str(bg_music),
    ]
    input_count = 2  # Track FFmpeg input index explicitly (0=voice, 1=music)
    af_parts = [
        "[0:a]volume=1.25,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,asplit=2[voice_sc][voice];",
        "[1:a]volume=0.12,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[music];",
        "[music][voice_sc]sidechaincompress=threshold=0.12:ratio=4:attack=20:release=350[ducked_music];",
    ]
    mix_ins = ["[ducked_music]", "[voice]"]

    # If src video has audio, mix background wild audio safely
    src_has_audio = has_audio_stream(src_video_path)
    if src_has_audio:
        wild_idx = input_count
        audio_inputs.extend(["-stream_loop", "-1", "-i", str(src_video_path)])
        input_count += 1
        af_parts.append(
            f"[{wild_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
            f"stereotools=mlev=0.12:slev=1.3:mpan=0,volume=0.14,apad=whole_dur={total_voice_dur:.2f}[wild_a];"
        )
        mix_ins.append("[wild_a]")

    if sfx_path and sfx_path.exists():
        sfx_idx = input_count
        audio_inputs.extend(["-i", str(sfx_path)])
        input_count += 1
        af_parts.append(
            f"[{sfx_idx}:a]volume=0.32,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
            f"apad=whole_dur={total_voice_dur:.2f}[sfx];"
        )
        mix_ins.append("[sfx]")

    af_parts.append(
        f"{''.join(mix_ins)}amix=inputs={len(mix_ins)}:duration=longest:normalize=0,loudnorm=I=-14:LRA=7:TP=-1.5,aresample=async=1[a_out]"
    )
    cmd_audio = [
        "ffmpeg", "-y", "-loglevel", "error",
        *audio_inputs,
        "-filter_complex", "".join(af_parts),
        "-map", "[a_out]",
        "-t", f"{total_voice_dur:.2f}",
        str(master_audio)
    ]
    subprocess.run(cmd_audio, check=True)

    # 2. Final Multiplex with Video
    clean_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    font_file = FONTS_DIR / "Anton-Regular.ttf"
    if font_file.exists():
        clean_font = str(font_file.resolve()).replace("\\", "/").replace(":", "\\:")
        font_arg = f":fontfile='{clean_font}'"
    else:
        font_arg = ""
    hook_banner_text = _clean_hook_banner(script.get("hook_banner", "WATCH CAREFULLY"))

    fc_video = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,"
        "eq=saturation=1.08:contrast=1.05:brightness=0.01,"
        "drawbox=x=0:y=110:w=1080:h=170:color=black@0.75:t=fill,"
        f"drawtext=text='{hook_banner_text}'{font_arg}:fontcolor=yellow:fontsize=76:x=(w-text_w)/2:y=155,"
        f"ass='{clean_ass}'[v]"
    )

    cmd_final = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-stream_loop", "-1", "-i", str(stitched_footage),
        "-i", str(master_audio),
        "-filter_complex", fc_video,
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total_voice_dur:.2f}",
        str(out_file)
    ]
    subprocess.run(cmd_final, check=True)

    # Save meta json
    meta_path = out_file.with_suffix(".meta.json")
    meta_data = {
        "title": script.get("title", source_video_info.get("title", "Commentary Video")),
        "description": f"{script.get('title', '')} #shorts #viral #commentary #breakdown",
        "hashtags": script.get("hashtags", ["#shorts", "#viral", "#commentary"]),
        "duration": ffprobe_duration(out_file),
        "monetizable": ffprobe_duration(out_file) >= 60.0,
        "created_at": dt.datetime.now().isoformat(),
        "video_file": out_file.name,
        "hook_banner": script.get("hook_banner", "")
    }
    meta_path.write_text(json.dumps(meta_data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"[Commentary Engine] Rendered hybrid commentary video: {out_file.name} ({meta_data['duration']:.1f}s)")
    try:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)
    except Exception:
        pass
    return out_file


