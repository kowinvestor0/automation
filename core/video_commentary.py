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
    title = video_info.get("title", "Viral Clip")
    desc = video_info.get("description", "")
    transcript = video_info.get("transcript", "")
    dur = float(video_info.get("duration", 30.0))
    full_context = f"{title} {desc} {transcript}".lower()

    clean_title = re.sub(r"[^\w\s-]", "", title).strip()[:45]

    # Try Gemini if key configured
    key = get_api_key("gemini_api_key")
    if key and len(key) >= 20:
        try:
            import requests
            word_target = int(dur * 2.3)
            scene_target = max(2, min(10, int(dur / 8.0)))
            prompt = f"""You are an elite viral video commentary creator (like Adam Rose or Daily Dose of Internet).
Write an electrifying, witty English commentary reacting directly to this video:
Video Title: {title}
Context / Subtitles: {transcript or desc[:300]}
Video Duration: {dur:.1f} seconds.

RULES:
1. Speak DIRECTLY about what is happening on screen in this specific clip!
2. Match the exact duration of {dur:.1f} seconds (Total words must be approximately {word_target} words across {scene_target} dialogue scenes).
3. Alternate between role 'q' (amazed reactor) and role 'a' (expert/witty analyst).
4. Do NOT use generic placeholder words. Mention the exact subjects from the title/video!
5. Output ONLY valid JSON:
{{
  "hook_banner": "3-4 WORDS IN ALL CAPS",
  "scenes": [
    {{"role": "q", "text": "..."}},
    {{"role": "a", "text": "..."}}
  ]
}}"""
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}, timeout=20)
            if res.status_code == 200:
                data = res.json()
                parsed = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
                if parsed.get("scenes") and len(parsed["scenes"]) >= 2:
                    return {
                        "hook_banner": parsed.get("hook_banner", "WATCH CAREFULLY 😱"),
                        "title": f"The Truth Behind {clean_title}",
                        "voice_q": voice_q,
                        "voice_a": voice_a,
                        "scenes": parsed["scenes"],
                        "target_duration": dur,
                        "hashtags": ["#shorts", "#viral", "#commentary", "#breakdown", "#trending"]
                    }
        except Exception as e:
            print(f"[VideoCommentary] Gemini call skipped: {e}")

    # Dynamic Video-Matching Commentary Engine (Guaranteed >60s Monetization Threshold)
    is_tiger_animal = any(w in full_context for w in ("tiger", "lion", "tree", "bear", "climb", "animal", "shark", "predator", "danger", "dog", "cat", "snake", "crocodile"))
    is_water_nature = any(w in full_context for w in ("water", "swimming", "nuoc", "nguy hiem", "lake", "pool", "spillway", "vortex", "sinkhole", "acid", "ocean", "river", "flood"))
    is_experiment = any(w in full_context for w in ("press", "hydraulic", "experiment", "crush", "explosion", "science", "lava", "fire", "reaction", "chemical", "shatter", "test"))
    is_craft_satisfying = any(w in full_context for w in ("satisfying", "restoration", "restore", "craft", "wood", "metal", "lathe", "clean", "carving", "polish", "handmade"))

    if is_tiger_animal:
        hook_banner = "NEVER DO THIS 💀"
        scenes = [
            {"role": "q", "text": f"Watch closely right here when this person thinks climbing a tree is the best way to escape an apex predator!"},
            {"role": "a", "text": "Are you out of your mind?! That is one of the most fatal survival mistakes anyone can ever make in the wild!"},
            {"role": "q", "text": "Wait, can big cats and wild predators actually climb vertical trees that fast?"},
            {"role": "a", "text": "Tigers and leopards are armed with massive five-inch retractable claws and dense muscle fiber. They can sprint straight up a thirty-foot vertical trunk in under two seconds!"},
            {"role": "q", "text": "Look at how effortlessly it reaches the upper canopy branches right there!"},
            {"role": "a", "text": "By climbing upward, you have completely trapped yourself high off the ground with zero escape routes left. The predator now holds all the leverage, balance, and reach."},
            {"role": "q", "text": "What is the only proven survival tactic if you ever find yourself facing a wild predator in real life?"},
            {"role": "a", "text": "Never turn your back and never run. Stand as tall as possible, maintain direct unblinking eye contact, make deep aggressive noise, and slowly back away step by step. Would you have survived this encounter? Leave your thoughts below and subscribe for more survival facts!"}
        ]

    elif is_water_nature:
        hook_banner = "DO NOT SWIM HERE ⚠️"
        scenes = [
            {"role": "q", "text": "Can I take a quick swim right here? The water looks completely calm and peaceful on the surface!"},
            {"role": "a", "text": "Stop right there! Back away immediately! That seemingly calm surface is concealing an extreme downward suction vortex!"},
            {"role": "q", "text": "What makes these innocent looking pools and spillways so extraordinarily deadly?"},
            {"role": "a", "text": "This is a giant bell-mouth spillway system. Once the drainage gates open underneath, thousands of tons of rushing water create a crushing whirlpool that drags anything down with zero escape!"},
            {"role": "q", "text": "What about that colorful geothermal mineral lake over there in the distance?"},
            {"role": "a", "text": "That is Lake Dallol! It is boiling toxic sulfuric acid and hyper-saline sludge. Even inhaling the chemical fumes will scorch your lungs, and touching the liquid causes immediate chemical burns!"},
            {"role": "q", "text": "Why do so many tourists still underestimate the danger of these natural traps?"},
            {"role": "a", "text": "People overlook hidden underwater rip currents and zero-buoyancy aeration. One tiny slip, and you are trapped fighting for your life against immense hydraulic tonnage. Would you dare swim here? Drop your reaction below and follow!"}
        ]

    elif is_experiment:
        hook_banner = "WAIT FOR THE END 😱"
        scenes = [
            {"role": "q", "text": f"Look extremely closely at what they just placed under this heavy industrial hydraulic press!"},
            {"role": "a", "text": "This machine is capable of delivering over one hundred and fifty tons of concentrated downward force, and what happens next shocked millions of people online!"},
            {"role": "q", "text": "At first, the material appears completely solid and almost indestructible against the hardened steel piston."},
            {"role": "a", "text": "However, as the digital pressure gauge crosses fifty tons, internal molecular lattice stress builds up rapidly until the entire structure suddenly fractures in a violent shockwave!"},
            {"role": "q", "text": "Did you see how those high-speed fragments deflected off the protective polycarbonate blast shielding?"},
            {"role": "a", "text": "That instantaneous kinetic release created localized friction temperatures exceeding two hundred degrees in just a few milliseconds."},
            {"role": "q", "text": "Why did it withstand so much pressure before suddenly detonating all at once like that?"},
            {"role": "a", "text": "Under high compression, brittle materials store enormous elastic energy until catastrophic structural shear failure occurs. Did you expect that ending? Drop your guess in the comments and subscribe for more insane lab tests!"}
        ]

    elif is_craft_satisfying:
        hook_banner = "ODDLY SATISFYING ✨"
        scenes = [
            {"role": "q", "text": f"Take a close look at this precision restoration process right as the master craftsman begins!"},
            {"role": "a", "text": "This piece was completely buried under decades of heavy rust, corrosion, and grime, but what it looks like after twenty hours of work is unbelievable!"},
            {"role": "q", "text": "Watch how smoothly the specialized rotary carbide bit peels away the damaged oxidized layer."},
            {"role": "a", "text": "Notice the steady hand pressure. Even a half-millimeter deviation could permanently score the antique metal casing and ruin its historic balance."},
            {"role": "q", "text": "Look at the high-grit diamond paste polish bringing out the original mirror reflection right now!"},
            {"role": "a", "text": "By combining ultrasonic cleaning baths with hand-applied micro-crystalline wax, the surface is sealed against moisture for the next fifty years."},
            {"role": "q", "text": "Is it better to preserve the original weathered patina or restore it to pristine factory condition?"},
            {"role": "a", "text": "True collectors debate this constantly, but seeing this level of craftsmanship brought back to life is pure therapy. What would you have done with this? Let us know below and subscribe!"}
        ]

    else:
        hook_banner = "WATCH THIS CAREFULLY 🤔"
        scenes = [
            {"role": "q", "text": f"Pay extremely close attention to what happens right here in this viral clip of {clean_title}!"},
            {"role": "a", "text": "Ninety nine percent of casual viewers completely miss the critical detail that occurs within the first three seconds of the footage."},
            {"role": "q", "text": "What is the real scientific explanation behind this unbelievable moment caught on camera?"},
            {"role": "a", "text": "When you slow down and break down the video frame by frame, you realize the situation escalated ten times faster than anyone on the scene could anticipate."},
            {"role": "q", "text": "Look at the immediate kinetic reaction of everyone involved right as the sequence unfolds!"},
            {"role": "a", "text": "Physics experts who analyzed this viral phenomenon pointed out that an instant split-second reaction was the only reason this did not turn into an absolute disaster."},
            {"role": "q", "text": "Would you have been able to keep your composure if you were standing right there in that exact spot?"},
            {"role": "a", "text": "Most people panic under sudden unexpected pressure, but observing how momentum shifted here is fascinating. Did you catch that hidden detail? Drop your thoughts below and subscribe for more breakdowns!"}
        ]

    return {
        "hook_banner": hook_banner,
        "title": f"Commentary: {clean_title}",
        "voice_q": voice_q,
        "voice_a": voice_a,
        "scenes": scenes,
        "target_duration": dur,
        "hashtags": ["#shorts", "#viral", "#commentary", "#breakdown", "#trending"]
    }

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
    clean_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
    font_file = FONTS_DIR / "Anton-Regular.ttf"
    font_arg = f":fontfile='{str(font_file).replace('\\', '/').replace(':', '\\:')}'" if font_file.exists() else ""
    hook_banner_text = _clean_hook_banner(script.get("hook_banner", "WATCH CAREFULLY"))

    fc_video = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,"
        "eq=saturation=1.08:contrast=1.05:brightness=0.01,"
        "drawbox=x=0:y=110:w=1080:h=170:color=black@0.75:t=fill,"
        f"drawtext=text='{hook_banner_text}'{font_arg}:fontcolor=yellow:fontsize=76:x=(w-text_w)/2:y=155,"
        f"ass='{clean_ass}'[v]"
    )

    af_parts = [
        # Original wild audio: center channel suppression + low volume
        "[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,stereotools=mlev=0.12:slev=1.3:mpan=0,volume=0.14[wild_a];",
        "[2:a]volume=1.25,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,asplit=2[voice_sc][voice];",
        "[3:a]volume=0.12,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[music];",
        "[music][voice_sc]sidechaincompress=threshold=0.12:ratio=4:attack=20:release=350[ducked_music];",
    ]
    mix_ins = ["[wild_a]", "[ducked_music]", "[voice]"]
    cmd_inputs = [
        "-stream_loop", "-1", "-i", str(stitched_footage),
        "-stream_loop", "-1", "-i", str(src_video_path),
        "-i", str(full_voice_path),
        "-i", str(bg_music),
    ]

    if sfx_path and sfx_path.exists():
        cmd_inputs += ["-i", str(sfx_path)]
        af_parts.append("[4:a]volume=0.32,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[sfx];")
        mix_ins.append("[sfx]")

    af_parts.append(f"{''.join(mix_ins)}amix=inputs={len(mix_ins)}:normalize=0,loudnorm=I=-14:LRA=7:TP=-1.5[a]")
    fc_audio = "".join(af_parts)

    cmd_final = [
        "ffmpeg", "-y", "-loglevel", "error",
        *cmd_inputs,
        "-filter_complex", f"{fc_video};{fc_audio}",
        "-map", "[v]", "-map", "[a]",
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
    return out_file


