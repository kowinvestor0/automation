"""High-retention Video Engine: Multi-clip concatenation, 9:16 vertical render,
Hook Banner, ASS Karaoke, Vocal suppression & ducked audio mixing.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import random
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from core.paths import CACHE_DIR, FONTS_DIR, OUTPUT_DIR
from core.tts_engine import ffprobe_duration, synthesize_script
from core.subtitles import build_ass_subtitles
from core.audio_processor import (
    has_audio_stream,
    build_vocal_suppression_filter,
    get_background_music,
    build_sfx_track,
)


def _clean_hook_banner(text: str) -> str:
    """Sanitize hook banner for FFmpeg drawtext."""
    raw = re.sub(r"[^\w\s!?¿¡-]", "", text).strip()
    if not raw:
        raw = "WAIT FOR THE END"
    return raw.replace("'", "").replace(":", "\\:").replace("%", "%%")


def assemble_dynamic_scene_montage(
    clip_paths: List[Path],
    timeline: List[Dict[str, Any]],
    target_duration: float,
    workdir: Path,
    log=print
) -> Path:
    """Assembles a high-retention multi-clip 9:16 portrait video montage where
    the visual footage cuts and changes dynamically at each scene transition!
    """
    workdir.mkdir(parents=True, exist_ok=True)
    if not clip_paths:
        bg_clip = workdir / "motion_bg.mp4"
        dur = max(30.0, target_duration + 5.0)
        gen_cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c=0x0a0f1d:s=1080x1920:d={dur}",
            "-vf", "noise=c1s=8:c0f=u",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(bg_clip)
        ]
        subprocess.run(gen_cmd, check=False)
        return bg_clip

    # Single clip provided covering entire duration (e.g. commentary source)
    if len(clip_paths) == 1:
        dur = ffprobe_duration(clip_paths[0])
        if dur >= target_duration:
            return clip_paths[0]
        # Loop single clip cleanly to target duration
        looped_clip = workdir / "looped_source.mp4"
        cmd_loop = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-stream_loop", "-1",
            "-i", str(clip_paths[0]),
            "-t", f"{target_duration:.2f}",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            str(looped_clip)
        ]
        res_l = subprocess.run(cmd_loop, capture_output=True, text=True)
        if res_l.returncode == 0 and looped_clip.exists() and looped_clip.stat().st_size > 5000:
            return looped_clip

    log(f"[VideoEngine] Assembling {len(timeline)} scene visual cuts using {len(clip_paths)} distinct clip(s)...")
    seg_files = []
    concat_list = workdir / "scene_montage_concat.txt"
    concat_lines = []

    for idx, sc in enumerate(timeline):
        clip_p = clip_paths[idx % len(clip_paths)]
        sc_dur = float(sc.get("duration", 8.0))
        clip_dur = ffprobe_duration(clip_p)

        # Pick safe start offset within clip
        start_offset = 0.0
        if clip_dur > sc_dur + 1.5:
            start_offset = random.uniform(0.0, min(5.0, clip_dur - sc_dur))

        seg_out = workdir / f"montage_seg_{idx:02d}.mp4"
        loop_in = ["-stream_loop", "-1"] if (clip_dur < sc_dur) else []

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            *loop_in,
            "-i", str(clip_p),
            "-ss", f"{start_offset:.2f}",
            "-t", f"{sc_dur:.2f}",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p", "-an",
            str(seg_out)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and seg_out.exists() and seg_out.stat().st_size > 1000:
            seg_files.append(seg_out)
            p_str = str(seg_out.resolve()).replace("\\", "/")
            concat_lines.append(f"file '{p_str}'")

    if not concat_lines:
        return clip_paths[0]

    concat_list.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    stitched_out = workdir / "stitched_footage.mp4"

    cmd_concat = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(stitched_out)
    ]
    res_concat = subprocess.run(cmd_concat, capture_output=True, text=True)
    if res_concat.returncode == 0 and stitched_out.exists() and stitched_out.stat().st_size > 5000:
        actual_dur = ffprobe_duration(stitched_out)
        log(f"[VideoEngine] Multi-clip scene montage ready ({actual_dur:.1f}s across {len(seg_files)} scene cuts)")
        return stitched_out

    return clip_paths[0]



def stitch_clips_to_target_duration(
    clip_paths: List[Path],
    target_duration: float,
    workdir: Path,
    log=print
) -> Path:
    """Backwards compatible wrapper for multi-clip stitching."""
    timeline = [{"duration": target_duration / max(1, len(clip_paths))} for _ in range(len(clip_paths))]
    return assemble_dynamic_scene_montage(clip_paths, timeline, target_duration, workdir, log=log)


def render_monetizable_video(
    source_clips: List[Dict[str, Any]],
    script: Dict[str, Any],
    out_file: Path,
    cfg: Optional[Dict[str, Any]] = None,
    session_used_ids: Optional[Set[int]] = None,
    log=print
) -> Path:
    """Renders high-retention 9:16 vertical video (>60s) with:
    - Multi-clip seamless footage with dynamic cuts on scene transitions
    - Suppressed original vocals (keeping environmental sound)
    - High-energy AI narration (Edge TTS)
    - Ducked background music & synced SFX
    - Top Hook Banner & Dynamic ASS Karaoke subtitles
    """
    cfg = cfg or {}
    temp_dir = out_file.parent / f"_tmp_{out_file.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Generate Voiceover narration from Script
        log("[VideoEngine] 1/5 Synthesizing AI narration scenes...")
        voice_cfg = {
            "voice": script.get("voice_a") or cfg.get("voice", "en-US-ChristopherNeural"),
            "voice_q": script.get("voice_q") or cfg.get("voice_q", "en-US-BrianNeural"),
            "voice_a": script.get("voice_a") or cfg.get("voice_a", "en-US-ChristopherNeural"),
            "voice_rate": cfg.get("voice_rate", "+10%"),
            "font": "Anton",
            "font_size": cfg.get("font_size", 95),
            "highlight_color": script.get("highlight_color") or cfg.get("highlight_color", "&H0033E5FF&"),
            "words_per_caption": 3,
        }
        full_voice_path, timeline = synthesize_script(script["scenes"], voice_cfg, temp_dir, log=log)
        voice_duration = ffprobe_duration(full_voice_path)
        log(f"[VideoEngine] Voiceover total duration: {voice_duration:.2f}s (Monetizable: {'YES' if voice_duration >= 60 else 'UNDER 60S'})")

        # 2. Build ASS Karaoke subtitles
        log("[VideoEngine] 2/5 Building animated ASS karaoke subtitles...")
        ass_path = temp_dir / "subtitles.ass"
        build_ass_subtitles(timeline, voice_cfg, ass_path, w=1080, h=1920)

        # 3. Prepare visual footage
        log("[VideoEngine] 3/5 Preparing visual footage (dynamic scene montage)...")
        clip_files = [Path(c["video_path"]) for c in (source_clips or []) if Path(c.get("video_path", "")).exists()]
        if not clip_files:
            log("[VideoEngine] Fetching scene-specific 9:16 portrait stock footage from Pexels API (Zero repetition)...")
            from core.pexels_client import PexelsClient
            pex = PexelsClient()
            scenes_data = script.get("scenes") or [{"text": script.get("topic", "viral news")}]
            clip_files = pex.download_scene_clips(
                scenes=scenes_data,
                default_topic=script.get("topic") or "breaking news",
                session_used_ids=session_used_ids,
                log=log
            )
            if not clip_files:
                broll = pex.download_broll(script.get("topic") or "dramatic news event")
                if broll:
                    clip_files = [broll]

        source_video = assemble_dynamic_scene_montage(
            clip_paths=clip_files,
            timeline=timeline,
            target_duration=voice_duration,
            workdir=temp_dir,
            log=log
        )
        source_dur = ffprobe_duration(source_video)

        # Loop video stream if slightly shorter than audio
        loop_args = ["-stream_loop", "-1"] if (voice_duration > source_dur + 1.0) else []

        # 4. Audio Processing: BGM, SFX & Vocal Suppression
        log("[VideoEngine] 4/5 Processing audio: Background music ducking, SFX and vocal suppression...")
        bg_music_path = get_background_music(voice_duration, temp_dir)
        sfx_path = build_sfx_track(timeline, voice_duration, temp_dir)
        has_orig_audio = has_audio_stream(source_video)

        # 5. FFmpeg Video Filter Complex
        font_file = FONTS_DIR / "Anton-Regular.ttf"
        clean_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
        font_arg = f":fontfile='{str(font_file).replace('\\', '/').replace(':', '\\:')}'" if font_file.exists() else ""
        hook_banner_text = _clean_hook_banner(script.get("hook_banner", "WAIT FOR THE END"))

        # Anti-fingerprint video mutation (defeats TikTok/YouTube duplicate detection)
        zoom_factor = random.uniform(1.02, 1.05)
        crop_w = int(1080 * zoom_factor)
        crop_h = int(1920 * zoom_factor)
        sat = random.uniform(1.08, 1.14)
        contrast = random.uniform(1.04, 1.08)
        brightness = random.uniform(0.005, 0.018)
        salt_id = uuid.uuid4().hex[:12]

        # 9:16 Scale and crop, dynamic contrast/saturation pop, top hook banner, ASS subtitles
        fc_video = (
            f"[0:v]scale={crop_w}:{crop_h}:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            f"eq=saturation={sat:.2f}:contrast={contrast:.2f}:brightness={brightness:.3f},"
            "drawbox=x=0:y=110:w=1080:h=170:color=black@0.75:t=fill,"
            f"drawtext=text='{hook_banner_text}'{font_arg}:fontcolor=yellow:fontsize=76:x=(w-text_w)/2:y=155,"
            f"ass='{clean_ass}'[v]"
        )

        # Audio inputs
        input_files = [source_video, full_voice_path, bg_music_path]
        cmd_inputs = [
            *loop_args, "-i", str(source_video),
            "-i", str(full_voice_path),
            "-i", str(bg_music_path),
        ]

        # Audio mix parts
        tts_vol = cfg.get("tts_volume", 1.25)
        music_vol = cfg.get("music_volume", 0.12)
        orig_vol = cfg.get("original_audio_volume", 0.14)
        vocal_suppress = cfg.get("vocal_suppression", True)

        af_parts = [
            f"[1:a]volume={tts_vol:.2f},aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,asplit=2[voice_sc][voice];",
            f"[2:a]volume={music_vol:.2f},aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[music];",
            # Sidechain compressor: ducks music when voice speaks
            "[music][voice_sc]sidechaincompress=threshold=0.12:ratio=4:attack=20:release=350[ducked_music];",
        ]
        mix_sources = ["[ducked_music]", "[voice]"]

        # If source has audio, process original audio and pad with silence so it never truncates mix
        if has_orig_audio:
            if vocal_suppress:
                af_parts.insert(0, f"[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,stereotools=mlev=0.15:slev=1.2:mpan=0,volume={orig_vol:.2f},apad=whole_dur={voice_duration:.2f}[orig_a];")
            else:
                af_parts.insert(0, f"[0:a]volume={orig_vol:.2f},aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,apad=whole_dur={voice_duration:.2f}[orig_a];")
            mix_sources.insert(0, "[orig_a]")

        if sfx_path and sfx_path.exists():
            sfx_idx = len(input_files)
            input_files.append(sfx_path)
            cmd_inputs += ["-i", str(sfx_path)]
            af_parts.append(f"[{sfx_idx}:a]volume=0.30,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,apad=whole_dur={voice_duration:.2f}[sfx];")
            mix_sources.append("[sfx]")

        # Combine all audio streams, duration=longest ensures voice never cuts off
        af_parts.append(f"{''.join(mix_sources)}amix=inputs={len(mix_sources)}:duration=longest:normalize=0,loudnorm=I=-14:LRA=7:TP=-1.5,aresample=async=1[a]")
        fc_audio = "".join(af_parts)


        # 6. Render Final Output with FFmpeg
        log(f"[VideoEngine] 5/5 Final render to {out_file.name} (1080x1920 30fps)...")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            *cmd_inputs,
            "-filter_complex", f"{fc_video};{fc_audio}",
            "-map", "[v]", "-map", "[a]",
            "-t", f"{voice_duration:.2f}",
            "-metadata", f"title={script.get('title', 'Video')}",
            "-metadata", f"comment=salt_{salt_id}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "21", "-threads", "0",
            "-c:a", "aac", "-b:a", "192k",
            str(out_file)
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg rendering failed: {res.stderr[:400]}")

        # Write metadata JSON for scheduler / publishing
        meta_json = out_file.with_suffix(".meta.json")
        meta_data = {
            "title": script.get("title", ""),
            "description": script.get("description", ""),
            "hashtags": script.get("hashtags", []),
            "duration": voice_duration,
            "monetizable": voice_duration >= 60.0,
            "created_at": dt.datetime.now().isoformat(),
            "video_file": out_file.name,
            "source_clips": [c.get("url", "") for c in source_clips],
        }
        meta_json.write_text(json.dumps(meta_data, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"[VideoEngine] Successfully rendered: {out_file.name} ({voice_duration:.1f}s)")
        return out_file

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def remake_and_mask_video(
    source_video: Path,
    out_file: Path,
    hook_banner: str = "NHỮNG VÙNG NƯỚC NGUY HIỂM NHẤT THẾ GIỚI",
    mask_caption: bool = True,
    mask_caption_box: tuple = (40, 1410, 1000, 190),
    mask_watermark: bool = True,
    mask_watermark_box: tuple = (290, 105, 500, 100),
    remove_voice: bool = True,
    bg_music_track: Optional[Path] = None,
    add_sfx: bool = True,
    cfg: Optional[Dict[str, Any]] = None,
    log=print
) -> Path:
    """Repurposes an existing video:
    - Removes original speech dialogue
    - Adds/loops dramatic background music
    - Blurs and masks old burned-in captions
    - Blurs old channel watermarks and overlays a high-CTR hook banner
    - Injects viral MyInstants SFX
    """
    cfg = cfg or {}
    temp_dir = out_file.parent / f"_tmp_{out_file.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        duration = ffprobe_duration(source_video)
        log(f"[RemakeEngine] Source video duration: {duration:.2f}s")

        from core.paths import MUSIC_DIR, SFX_DIR
        if bg_music_track and Path(bg_music_track).exists():
            chosen_music = Path(bg_music_track)
        else:
            music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
            chosen_music = music_files[0] if music_files else None

        temp_music = temp_dir / "looped_bgm.mp3"
        if chosen_music and chosen_music.exists():
            fade_out_start = max(0.0, duration - 3.0)
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-stream_loop", "-1", "-i", str(chosen_music),
                "-t", f"{duration:.2f}",
                "-af", f"afade=t=in:d=1.5,afade=t=out:st={fade_out_start:.2f}:d=3.0,volume=0.95",
                "-c:a", "libmp3lame", "-b:a", "192k",
                str(temp_music)
            ], check=True)
            log("[RemakeEngine] Background music prepared.")
        else:
            temp_music = get_background_music(duration, temp_dir)

        sfx_inputs = []
        sfx_filters = []
        boom = SFX_DIR / "vineboom.mp3"
        dramatic = SFX_DIR / "dramaticdundundun.mp3"
        
        sfx_count = 0
        if add_sfx and boom.exists():
            sfx_inputs += ["-i", str(boom)]
            sfx_filters.append(f"[{sfx_count + 2}:a]adelay=500|500,volume=0.35[sfx{sfx_count}]")
            sfx_count += 1
        if add_sfx and dramatic.exists() and duration > 30:
            delay_ms = int(min(65.0, duration * 0.5) * 1000)
            sfx_inputs += ["-i", str(dramatic)]
            sfx_filters.append(f"[{sfx_count + 2}:a]adelay={delay_ms}|{delay_ms},volume=0.40[sfx{sfx_count}]")
            sfx_count += 1

        vf_steps = [
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "eq=saturation=1.08:contrast=1.05"
        ]

        current_v = "[v_graded]"
        vf_chain = f"{','.join(vf_steps)}{current_v};"

        if mask_caption:
            cx, cy, cw, ch = mask_caption_box
            vf_chain += (
                f"{current_v}split=2[vb1][vc1];"
                f"[vc1]crop=w={cw}:h={ch}:x={cx}:y={cy},boxblur=25:enable=1[vblur1];"
                f"[vb1][vblur1]overlay=x={cx}:y={cy}[vm1];"
                f"[vm1]drawbox=x={cx}:y={cy}:w={cw}:h={ch}:color=black@0.65:t=fill[v_masked_cap];"
            )
            current_v = "[v_masked_cap]"

        if mask_watermark:
            wx, wy, ww, wh = mask_watermark_box
            vf_chain += (
                f"{current_v}split=2[vb2][vc2];"
                f"[vc2]crop=w={ww}:h={wh}:x={wx}:y={wy},boxblur=20:enable=1[vblur2];"
                f"[vb2][vblur2]overlay=x={wx}:y={wy}[vm2];"
                f"[vm2]drawbox=x=0:y=95:w=1080:h=120:color=black@0.80:t=fill[v_banner_bg];"
            )
            current_v = "[v_banner_bg]"

        if hook_banner:
            clean_text = hook_banner.replace("'", "").replace(":", "\\:")
            vf_chain += (
                f"{current_v}drawtext=text='{clean_text}':"
                f"fontfile='C\\:/Windows/Fonts/arialbd.ttf':fontcolor=yellow:fontsize=46:"
                f"x=(w-text_w)/2:y=132[outv];"
            )
        else:
            vf_chain += f"{current_v}null[outv];"

        if sfx_count > 0:
            joined_sfx = "".join(f"[sfx{i}]" for i in range(sfx_count))
            fc_audio = (
                f"{';'.join(sfx_filters)};"
                f"[1:a]{joined_sfx}amix=inputs={sfx_count + 1}:normalize=0,loudnorm=I=-14:LRA=7:TP=-1.5[outa]"
            )
        else:
            fc_audio = "[1:a]loudnorm=I=-14:LRA=7:TP=-1.5[outa]"

        out_file.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(source_video),
            "-i", str(temp_music),
            *sfx_inputs,
            "-filter_complex", f"{vf_chain}{fc_audio}",
            "-map", "[outv]", "-map", "[outa]",
            "-t", f"{duration:.2f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-threads", "0",
            "-c:a", "aac", "-b:a", "192k",
            str(out_file)
        ]

        log(f"[RemakeEngine] Rendering remade video to {out_file.name}...")
        subprocess.run(cmd, check=True)

        meta_json = out_file.with_suffix(".meta.json")
        meta_data = {
            "title": hook_banner,
            "description": f"{hook_banner} #shorts #nature #khampha #viral",
            "hashtags": ["#shorts", "#nature", "#khampha", "#viral", "#danger"],
            "duration": duration,
            "monetizable": duration >= 60.0,
            "created_at": dt.datetime.now().isoformat(),
            "video_file": out_file.name,
            "source_clip": str(source_video),
            "repurposed": True,
        }
        meta_json.write_text(json.dumps(meta_data, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"[RemakeEngine] Done: {out_file.name}")
        return out_file

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
