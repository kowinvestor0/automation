"""Viral commentary generator and video renderer.

Takes a scraped viral clip, uses Gemini AI (or template fallback) to write a
transformative commentary script (>60s), generates natural neural TTS + Karaoke
subtitles, and renders a monetizable 9:16 vertical video using FFmpeg.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from hub.paths import CODE, factory_dir
from hub import settings

COMMENTARY_SCHEMA = {
    "type": "object",
    "properties": {
        "hook_banner": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "keywords"],
                "additionalProperties": False,
            },
        },
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["hook_banner", "title", "description", "scenes", "hashtags"],
    "additionalProperties": False,
}

PROMPT_SYSTEM_EN = """You write commentary scripts for viral short-form video (TikTok, Shorts, Reels)
based on real viral clips.
The goal is HIGH RETENTION and FAIR USE MONETIZATION:
- You are not just re-posting; you are providing TRANSFORMATIVE COMMENTARY (analysis, breakdown, explanation, context).
- Structure (11 scenes, ~180 words, ~65-75 seconds):
  - hook_banner: 3-5 words in ALL CAPS (e.g. "WAIT FOR THE END 😱", "IS THIS EVEN REAL? 🤔", "HOW DID HE SURVIVE THIS?").
  - Scene 1 (The Hook): Grab attention in 2 seconds. Point to the strangest detail immediately ("Look closely at the corner of the frame", "Nobody expected what happened three seconds in").
  - Scenes 2-4: Breakdown of the situation as it unfolds.
  - Scenes 5-8: The "WHY" and backstory: Explain the science, physics, history, or investigation behind the clip. This is the crucial transformative element that qualifies the video for YouTube monetization under Fair Use!
  - Scenes 9-11: Twist/Resolution, witty takeaway, and engaging call-to-action ("Would you have reacted differently? Follow for more insane breakdowns").
- Voice: Conversational, energetic, fast-paced second-person ("You", "Watch this").
- No emoji or quotes in scene text. Spell numbers out in words (twenty feet, five hundred dollars).
"""

PROMPT_SYSTEM_ES = """Escribes guiones de comentario y análisis para videos virales (TikTok, Shorts, Reels)
diseñados para monetización y alta retención:
- Estructura (11 escenas, ~180 palabras, ~65-75 segundos):
  - hook_banner: 3-5 palabras en MAYÚSCULAS con emoji (ej. "MIRA HASTA EL FINAL 😱", "¿ESTO ES REAL? 🤔").
  - Escena 1: Gancho en 2 segundos directo al detalle ("Mira con atención la esquina de la pantalla").
  - Escenas 2-4: Narración de lo que está sucediendo en el clip.
  - Escenas 5-8: Explicación del PORQUÉ: ciencia, física, historia o investigación detrás del suceso (Transformative Content / Fair Use).
  - Escenas 9-11: Remate, reflexión y llamado a seguir la cuenta.
- Voz: Tono conversacional, directo, de tú a tú. Números escritos con letra.
"""


def _get_gemini_key() -> str:
    cfg = settings.load()
    return settings.secret("GEMINI_API_KEY", cfg) or os.environ.get("GEMINI_API_KEY", "")


def generate_commentary_script(clip_meta: Dict[str, Any], language: str = "us") -> Dict[str, Any]:
    """Generates an 11-scene commentary script based on clip metadata."""
    key = _get_gemini_key()
    title = clip_meta.get("title", "Viral Clip")
    desc = (clip_meta.get("description") or "")[:400]

    if key and len(key) >= 20:
        try:
            from factories.us.pipeline import gemini
            system = PROMPT_SYSTEM_EN if language == "us" else PROMPT_SYSTEM_ES
            brief = (
                f"Clip Title: {title}\n"
                f"Clip Details: {desc}\n"
                f"Duration of original clip: {clip_meta.get('duration', 30)} seconds.\n\n"
                f"Write an exciting 11-scene commentary breakdown explaining this event."
            )
            data = gemini.generate_json(key, system, brief, COMMENTARY_SCHEMA, model="gemini-2.5-flash")
            return data
        except Exception as e:
            print(f"[commentary] Gemini API error ({e}), falling back to template")

    # High-retention template fallback (tuned to ~175 words, ~65 seconds audio)
    if language == "us":
        return {
            "hook_banner": "WAIT FOR THE END 😱",
            "title": f"The Truth Behind {title[:50]}",
            "description": f"Breaking down what really happened in this viral moment. #shorts #viral #breakdown",
            "scenes": [
                {"text": "Look extremely closely at this moment, because ninety nine percent of people completely miss what actually happened.", "keywords": ["shocked reaction"]},
                {"text": f"This incredible clip recently took over the entire internet, with millions of viewers questioning whether it was real or completely staged.", "keywords": ["crowd watching"]},
                {"text": "At first glance, everything appears to be totally ordinary and peaceful as the scene begins.", "keywords": ["normal daily life"]},
                {"text": "However, as the seconds tick by, the tension escalates rapidly and catches everyone completely off guard.", "keywords": ["fast motion"]},
                {"text": "Here is the exact step by step breakdown of the mysterious circumstances behind this event.", "keywords": ["laboratory experiment"]},
                {"text": "Forensic specialists who reviewed this footage pointed out an astonishing detail hidden in the background that changes everything.", "keywords": ["magnifying glass research"]},
                {"text": "The rare chain reaction you are witnessing can only occur under extremely precise environmental conditions.", "keywords": ["science reaction"]},
                {"text": "In fact, verified occurrences like this have only been documented a handful of times across modern records.", "keywords": ["archive footage"]},
                {"text": "Once you uncover the full backstory, the entire mystery finally connects and makes total sense.", "keywords": ["light bulb moment"]},
                {"text": "It turns out the genuine explanation behind this moment is even crazier than what anyone online originally imagined.", "keywords": ["laughing reaction"]},
                {"text": "Would you have caught that hidden detail on the first watch? Subscribe right now and let me know your thoughts in the comments.", "keywords": ["subscribe icon"]},
            ],
            "hashtags": ["#shorts", "#viral", "#breakdown", "#didyouknow", "#mystery", "#reaction"],
        }
    else:
        return {
            "hook_banner": "MIRA HASTA EL FINAL 😱",
            "title": f"La verdad detrás de {title[:50]}",
            "description": f"Explicando qué fue lo que pasó en este video viral. #shorts #viral #curiosidades",
            "scenes": [
                {"text": "Fíjate con muchísima atención en este momento, porque el noventa y nueve por ciento de la gente no nota lo que pasó de verdad.", "keywords": ["reaccion sorpresa"]},
                {"text": f"Este video se hizo completamente viral en redes sociales y millones de personas se preguntaban si era real o actuado.", "keywords": ["gente mirando"]},
                {"text": "Al principio todo parece completamente normal y tranquilo como cualquier otro día ordinario.", "keywords": ["vida diaria"]},
                {"text": "Pero en cuestión de segundos, la tensión aumenta de golpe y deja a todos los presentes con la boca abierta.", "keywords": ["movimiento rapido"]},
                {"text": "Aquí está la explicación científica y detallada de por qué ocurrió semejante suceso.", "keywords": ["laboratorio ciencia"]},
                {"text": "Los especialistas que analizaron la grabación descubrieron un detalle oculto al fondo que lo cambia absolutamente todo.", "keywords": ["investigacion"]},
                {"text": "Este curioso fenómeno solo puede manifestarse bajo condiciones climáticas y físicas verdaderamente excepcionales.", "keywords": ["experimento cientifico"]},
                {"text": "De hecho, registros certificados de este tipo se han documentado muy pocas veces a lo largo de la historia moderna.", "keywords": ["documento antiguo"]},
                {"text": "Cuando entiendes el contexto completo y las razones detrás, todo el misterio cobra un sentido absoluto.", "keywords": ["descubrimiento"]},
                {"text": "Al final, la verdad detrás de esta historia resultó ser muchísimo más loca de lo que todos en internet pensaban.", "keywords": ["sonrisa"]},
                {"text": "¿Tú te habías dado cuenta de lo que iba a pasar? Suscríbete ahora mismo y déjame tu opinión en los comentarios.", "keywords": ["campana suscripcion"]},
            ],
            "hashtags": ["#shorts", "#viral", "#curiosidades", "#asombroso", "#tendencia"],
        }


def render_commentary_video(
    clip_meta: Dict[str, Any],
    script: Dict[str, Any],
    out_file: Path,
    language: str = "us",
    workdir: Optional[Path] = None,
) -> Path:
    """Renders the final 9:16 commentary video with looped/scaled clip, TTS, ASS captions, and SFX."""
    source_video = Path(clip_meta["video_path"])
    if not source_video.exists():
        raise FileNotFoundError(f"Source video not found at {source_video}")

    temp_dir = workdir or (out_file.parent / f"_temp_{source_video.stem}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Synthesize audio scenes via factory pipeline
    from factories.us.pipeline import tts, subtitles, audio_fx
    cfg_voice = {
        "voice": "en-US-AndrewMultilingualNeural" if language == "us" else "es-MX-JorgeNeural",
        "voice_rate": "+12%",
        "voice_pitch": "+0Hz",
        "scene_gap": 0.12,
        "font": "Anton",
        "font_size": 95,
        "highlight_color": "&H0033E5FF&",
        "words_per_caption": 3,
        "width": 1080,
        "height": 1920,
        "fps": 30,
    }

    full_voice_path, timeline = tts.synth_scenes(script["scenes"], cfg_voice, temp_dir)
    voice_duration = audio_fx.ffprobe_duration(full_voice_path)

    # 2. Build ASS karaoke subtitles
    ass_path = temp_dir / "subtitles.ass"
    subtitles.build_ass(timeline, cfg_voice, ass_path)

    # 3. Build background music and SFX
    music_path = audio_fx.make_music(voice_duration, "commentary", temp_dir)
    cfg_sfx = {"sfx": True, "niche": "commentary"}
    sfx_path = audio_fx.build_sfx_track(timeline, voice_duration, cfg_sfx, temp_dir)

    # 4. Escape paths and text for FFmpeg
    raw_hook = script.get("hook_banner") or "WAIT FOR THE END"
    import re
    clean_hook = re.sub(r"[^A-Za-z0-9 !?]", "", raw_hook).strip() or "WAIT FOR IT"
    clean_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")

    # Font path
    font_file = CODE / "factories" / "us" / "assets" / "fonts" / "Anton-Regular.ttf"
    font_arg = f":fontfile='{str(font_file).replace('\\', '/').replace(':', '\\:')}'" if font_file.exists() else ""

    # 5. Build FFmpeg Filter Complex:
    fc_video = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "eq=saturation=1.12:contrast=1.04:brightness=0.01,"
        "drawbox=x=0:y=110:w=1080:h=170:color=black@0.75:t=fill,"
        f"drawtext=text='{clean_hook}'{font_arg}:fontcolor=yellow:fontsize=76:x=(w-text_w)/2:y=155,"
        f"ass='{clean_ass}'[v]"
    )

    # Audio inputs and mixing
    input_files = [source_video, full_voice_path, music_path]
    cmd_inputs = [
        "-stream_loop", "-1", "-i", str(source_video),
        "-i", str(full_voice_path),
        "-i", str(music_path),
    ]
    af_parts = [
        "[0:a]volume=0.12,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[orig_a];",
        "[1:a]volume=1.0,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[voice];",
        "[2:a]volume=0.20,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[music];",
    ]
    mix_sources = ["[orig_a]", "[ducked_music]", "[voice]"]

    if sfx_path and sfx_path.exists():
        sfx_idx = len(input_files)
        input_files.append(sfx_path)
        cmd_inputs += ["-i", str(sfx_path)]
        af_parts.append(f"[{sfx_idx}:a]volume=0.35,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[sfx];")
        mix_sources.append("[sfx]")

    af_parts.append("[music][voice]sidechaincompress=threshold=0.12:ratio=4:attack=20:release=350[ducked_music];")
    af_parts.append(f"{''.join(mix_sources)}amix=inputs={len(mix_sources)}:normalize=0,loudnorm=I=-14:LRA=7:TP=-1.5[a]")
    fc_audio = "".join(af_parts)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        *cmd_inputs,
        "-filter_complex", f"{fc_video};{fc_audio}",
        "-map", "[v]", "-map", "[a]",
        "-t", f"{voice_duration:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        str(out_file)
    ]

    out_file.parent.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed: {res.stderr[:400]}")

    # Write companion metadata for publishing
    meta_json = out_file.with_suffix(".meta.json")
    meta_json.write_text(json.dumps({
        "title": script.get("title", ""),
        "description": script.get("description", ""),
        "hashtags": script.get("hashtags", []),
        "source_clip": clip_meta.get("url", ""),
        "duration": voice_duration,
        "rendered_at": str(out_file),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    # Clean up temp
    shutil.rmtree(temp_dir, ignore_errors=True)
    return out_file
