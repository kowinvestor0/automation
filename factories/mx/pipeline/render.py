"""Ensambla el video final con FFmpeg (1080x1920).

Los clips se generan sueltos y todo lo demas -transiciones, subtitulos y mezcla
de audio- ocurre en UN solo filter_complex, o sea una sola codificacion.
"""
import random
from pathlib import Path

from .audio_fx import build_sfx_track, make_music
from .util import ROOT, log, run

MUSIC_DIR = ROOT / "assets" / "music"
FONTS_DIR = ROOT / "assets" / "fonts"
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".ogg"}
AFMT = "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"

# Como se ve y como corta cada nicho.
STYLES = {
    "misterios": {
        "transitions": ["fadeblack", "dissolve", "fadegrays", "wipeleft"],
        "vignette": 0.85, "grain": 3, "saturation": 1.02, "brightness": -0.05,
    },
    "humor": {
        "transitions": ["slideleft", "circleopen", "squeezeh", "slideup"],
        "vignette": 0.0, "grain": 0, "saturation": 1.18, "brightness": 0.02,
    },
    "curiosidades": {
        "transitions": ["dissolve", "smoothleft", "circleopen", "wipeup"],
        "vignette": 0.3, "grain": 0, "saturation": 1.12, "brightness": 0.0,
    },
    "historia": {
        "transitions": ["fadegrays", "dissolve", "wipeleft", "fadeblack"],
        "vignette": 0.7, "grain": 2, "saturation": 0.95, "brightness": -0.03,
    },
    "lugares": {
        "transitions": ["smoothleft", "circleopen", "dissolve", "wipeup"],
        "vignette": 0.25, "grain": 0, "saturation": 1.15, "brightness": 0.01,
    },
}


def _style(cfg):
    base = dict(STYLES.get(cfg.get("niche", "misterios"), STYLES["misterios"]))
    base.update(cfg.get("style_override") or {})
    return base


# Presets de calidad. El bitrate es un techo, no un objetivo: sin el, el grano
# temporal sobre un degradado liso dispara un video de 40 segundos a cientos de
# megas.
QUALITY = {
    "fast": {"crf": 22, "preset": "veryfast", "maxrate": "6M", "bufsize": "12M"},
    "high": {"crf": 19, "preset": "medium", "maxrate": "14M", "bufsize": "28M"},
    "max": {"crf": 16, "preset": "slow", "maxrate": "24M", "bufsize": "48M"},
}

# Tamanos verticales de salida. 1080x1920 es lo que TikTok, Reels y Shorts
# sirven de verdad; cualquier cosa mas grande la recodifican al subirla, o sea
# que solo cuesta tiempo de render salvo que el material vaya a otro lado.
RESOLUTIONS = {"1080p": (1080, 1920), "1440p": (1440, 2560), "4k": (2160, 3840)}


def _quality(cfg):
    q = dict(QUALITY.get(cfg.get("quality", "high"), QUALITY["high"]))
    # Un crf/preset puesto a mano en el config sigue mandando, para quien afina.
    for key, cfg_key in (("crf", "crf"), ("preset", "preset"),
                         ("maxrate", "max_bitrate"), ("bufsize", "bufsize")):
        if cfg.get(cfg_key) is not None and cfg.get("quality") is None:
            q[key] = cfg[cfg_key]
    return q


def _dims(cfg):
    """Tamano de salida. `resolution` manda; width/height quedan de escape manual."""
    name = cfg.get("resolution")
    if name in RESOLUTIONS:
        w, h = RESOLUTIONS[name]
    else:
        w, h = int(cfg.get("width", 1080)), int(cfg.get("height", 1920))
    return w, h, int(cfg.get("fps", 30))


# Topes de H.264 por level: (macrobloques por cuadro, macrobloques por segundo).
# Los dos importan: 4K a 30 fps cabe en 5.1 y a 60 fps ya no.
LEVELS = (
    ("4.2", 8704, 522240),
    ("5.0", 22080, 589824),
    ("5.1", 36864, 983040),
    ("5.2", 36864, 2073600),
    ("6.0", 139264, 4177920),
)


def _level(w, h, fps=30):
    """El level de H.264 que de verdad aguanta ese cuadro a esa velocidad.

    El level va por macrobloques, no por pixeles: 1080x1920 son 8160 y caben en
    4.2, pero 1440p son 14400 y 4K son 32400. Dejar "4.1" escrito a mano hacia
    que el archivo saliera etiquetado fuera de norma en cuanto alguien tocaba
    `resolution`, y ahi los decodificadores por hardware se rinden.
    """
    per_frame = ((w + 15) // 16) * ((h + 15) // 16)
    per_second = per_frame * max(1, int(fps))
    for level, max_frame, max_rate in LEVELS:
        if per_frame <= max_frame and per_second <= max_rate:
            return level
    return "6.2"


def _venc(cfg):
    q = _quality(cfg)
    return [
        "-c:v", "libx264", "-preset", str(q["preset"]), "-crf", str(q["crf"]),
        "-maxrate", str(q["maxrate"]), "-bufsize", str(q["bufsize"]),
    ]


# Tope de grano. El grano temporal cuesta bitrate de forma no lineal: medido a
# 1080x1920/30fps, alls=6 da 5.8 Mbps y alls=3 da 0.8 Mbps, para una diferencia
# que no se distingue en pantalla de telefono. Arriba de esto no vale la pena.
GRAIN_MAX = 3

# Las fotos se decodifican en rango completo (yuvj420p). Pasarle eso a un
# reproductor que espera rango limitado apachurra los negros y quema las luces,
# asi que cada clip se convierte una sola vez, de entrada, y el archivo final
# sale etiquetado bt709/limitado.
RANGE_FIX = "scale=in_range=auto:out_range=tv,format=yuv420p"
COLOR_TAGS = ["-color_range", "tv", "-colorspace", "bt709",
              "-color_primaries", "bt709", "-color_trc", "bt709"]


def _look(st):
    """Cola de filtros de acabado que comparten todos los clips."""
    chain = [f"eq=saturation={st['saturation']}:brightness={st['brightness']}"]
    if st["vignette"] > 0:
        chain.append(f"vignette=angle=PI/4:mode=forward,eq=gamma={1 + st['vignette'] * 0.12:.3f}")
    if st["grain"] > 0:
        chain.append(f"noise=alls={min(st['grain'], GRAIN_MAX)}:allf=t")
    chain += ["setsar=1", RANGE_FIX]
    return ",".join(chain)


def _shake(w, h):
    """Sacudida de camara que se apaga sola: da un golpe al arranque del gancho."""
    over = 1.06
    return (f"scale={int(w * over)}:{int(h * over)},"
            f"crop={w}:{h}:"
            f"'(iw-ow)/2+11*sin(2*PI*t*13)*exp(-2.6*t)':"
            f"'(ih-oh)/2+9*cos(2*PI*t*10)*exp(-2.6*t)'")


def _clip_video(src, dur, out, cfg, workdir, shake=False):
    w, h, fps = _dims(cfg)
    chain = [f"scale={w}:{h}:force_original_aspect_ratio=increase", f"crop={w}:{h}",
             f"fps={fps}"]
    if shake:
        chain.append(_shake(w, h))
    chain.append(_look(_style(cfg)))
    run(["ffmpeg", "-y", "-loglevel", "error",
         "-stream_loop", "-1", "-i", str(src), "-t", f"{dur:.3f}",
         "-an", "-vf", ",".join(chain),
         *_venc(cfg), "-r", str(fps), out], cwd=workdir)


def _clip_image(src, dur, out, cfg, workdir, shake=False):
    """Foto -> clip con fondo desenfocado + Ken Burns.

    Casi ninguna foto real viene en 9:16. Recortarla a la brava se come la mitad
    del encuadre, asi que la foto se ajusta entera al centro y el hueco lo llena
    una version borrosa de ella misma.
    """
    w, h, fps = _dims(cfg)
    cw, ch = int(w * 1.5), int(h * 1.5)  # margen para el zoom
    post = (_shake(w, h) + "," if shake else "") + _look(_style(cfg))
    fc = (
        # fondo: llenar, desenfocar barato (bajar, borrar, subir) y oscurecer
        f"[0:v]scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch},"
        f"scale=160:284,gblur=sigma=14,scale={cw}:{ch},"
        f"eq=brightness=-0.18:saturation=0.65[bg];"
        # frente: la foto completa, sin recortar
        f"[0:v]scale={cw}:{ch}:force_original_aspect_ratio=decrease[fg];"
        # Ken Burns: d=1 hace que `zoom` se acumule cuadro a cuadro -> zoom suave
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        f"zoompan=z='min(zoom+0.0009,1.22)':d=1:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},"
        f"{post}[v]"
    )
    run(["ffmpeg", "-y", "-loglevel", "error",
         "-framerate", str(fps), "-loop", "1", "-t", f"{dur:.3f}", "-i", str(src),
         "-an", "-filter_complex", fc, "-map", "[v]",
         *_venc(cfg), "-r", str(fps), out], cwd=workdir)


def _clip_gradient(dur, out, cfg, workdir, seed, shake=False):
    w, h, fps = _dims(cfg)
    palettes = [
        ("0x1b1035", "0x0d1b2a"), ("0x2b1055", "0x141e30"),
        ("0x0f2027", "0x203a43"), ("0x3a1c71", "0x0f0c29"),
    ]
    c0, c1 = palettes[seed % len(palettes)]
    src = f"gradients=s={w}x{h}:c0={c0}:c1={c1}:speed=0.02:type=radial"
    chain = [f"fps={fps}"]
    if shake:
        chain.append(_shake(w, h))
    chain.append(_look(_style(cfg)))
    run(["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-t", f"{dur:.3f}", "-i", src,
         "-vf", ",".join(chain),
         *_venc(cfg), "-r", str(fps), out], cwd=workdir)


def _pick_music(duration, cfg, workdir):
    """Tu musica de assets/music/ gana; si no hay, se genera una."""
    if cfg.get("music", "auto") == "off":
        return None, False
    if MUSIC_DIR.exists():
        tracks = [p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in AUDIO_EXT]
        if tracks:
            pick = random.choice(tracks)
            log(f"musica: {pick.name} (assets/music)")
            return pick, True  # hay que repetirla en bucle por si es corta
    track = make_music(duration, cfg.get("niche", "misterios"), workdir)
    log(f"musica: generada ({cfg.get('niche', 'misterios')})")
    return track, False


def _fontsdir(workdir):
    """Ruta relativa: un `D:` absoluto rompe el parser de filtros por los dos puntos."""
    import os
    return Path(os.path.relpath(FONTS_DIR, workdir)).as_posix()


def _video_graph(n, durations, cfg, ass_name, fontsdir):
    """Encadena los clips y quema los subtitulos. Devuelve (filtros, etiqueta)."""
    trans_dur = float(cfg.get("transition_duration", 0.4))
    style = _style(cfg)
    parts = []

    if n == 1 or not cfg.get("transitions", True) or trans_dur <= 0:
        if n == 1:
            cur = "[0:v]"
        else:
            parts.append("".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vcat]")
            cur = "[vcat]"
    else:
        # Cada clip se genero `trans_dur` mas largo, asi que el corte cae justo
        # en la frontera de la escena: offset = suma de duraciones previas.
        names = style["transitions"]
        cur = "[0:v]"
        offset = 0.0
        for i in range(1, n):
            offset += durations[i - 1]
            nxt = f"[x{i}]"
            parts.append(f"{cur}[{i}:v]xfade=transition={names[(i - 1) % len(names)]}"
                         f":duration={trans_dur}:offset={offset:.3f}{nxt}")
            cur = nxt
        log(f"{n - 1} transiciones ({', '.join(dict.fromkeys(names))})")

    # fontsdir apunta a la fuente incluida en el repo: asi el video se ve igual
    # en Windows y en Linux (GitHub Actions, Colab, VPS), sin instalar nada.
    parts.append(f"{cur}ass={ass_name}:fontsdir={fontsdir}[v]")
    return parts


def _audio_graph(cfg, base, has_music, has_sfx):
    """Mezcla voz + musica (con ducking) + efectos. `base` = indice de la voz."""
    voice_v = cfg.get("voice_volume", 1.0)
    music_v = cfg.get("music_volume", 0.18)
    sfx_v = cfg.get("sfx_volume", 0.35)
    # TikTok/Reels normalizan a ~-14 LUFS. Subir aqui evita que la plataforma
    # lo haga por su cuenta y deje el audio apagado frente a los demas videos.
    norm = f"loudnorm=I={cfg.get('loudness_lufs', -14)}:TP=-1.5:LRA=11"

    if not has_music and not has_sfx:
        return [f"[{base}:a]volume={voice_v},{AFMT},{norm}[a]"]

    parts, mix_in = [], []
    duck = has_music and cfg.get("music_duck", True)
    if duck:
        parts.append(f"[{base}:a]volume={voice_v},{AFMT},asplit=2[vo][vosc]")
    else:
        parts.append(f"[{base}:a]volume={voice_v},{AFMT}[vo]")
    mix_in.append("[vo]")

    idx = base + 1
    if has_music:
        parts.append(f"[{idx}:a]volume={music_v},{AFMT}[mus]")
        if duck:
            # La musica se agacha sola cuando entra la voz.
            parts.append("[mus][vosc]sidechaincompress="
                         "threshold=0.03:ratio=8:attack=15:release=350[musd]")
            mix_in.append("[musd]")
        else:
            mix_in.append("[mus]")
        idx += 1
    if has_sfx:
        parts.append(f"[{idx}:a]volume={sfx_v},{AFMT}[fx]")
        mix_in.append("[fx]")

    parts.append("".join(mix_in)
                 + f"amix=inputs={len(mix_in)}:duration=first:normalize=0,"
                 + f"{norm},alimiter=limit=0.95[a]")
    return parts


def render(timeline, assets, voice_mp3, ass_path, cfg, workdir):
    workdir = Path(workdir)
    n = len(timeline)
    trans_dur = float(cfg.get("transition_duration", 0.4))
    use_trans = cfg.get("transitions", True) and trans_dur > 0 and n > 1
    shake_on = cfg.get("camera_shake", True)

    clips, durations = [], []
    for sc, asset in zip(timeline, assets):
        name = f"clip_{sc['index']:02d}.mp4"
        dur = max(0.5, sc["duration"])
        durations.append(dur)
        # Con transiciones cada clip se alarga para que el cruce no coma escena.
        clip_len = dur + (trans_dur if use_trans else 0.0)
        shake = shake_on and sc["index"] == 0  # solo el gancho

        if asset["kind"] == "video":
            _clip_video(asset["path"], clip_len, name, cfg, workdir, shake)
        elif asset["kind"] == "image":
            _clip_image(asset["path"], clip_len, name, cfg, workdir, shake)
        else:
            _clip_gradient(clip_len, name, cfg, workdir, sc["index"], shake)
        clips.append(name)
        log(f"clip {sc['index'] + 1}/{n} listo ({dur:.2f}s)")

    total = timeline[-1]["start"] + timeline[-1]["duration"]
    music, loop_music = _pick_music(total, cfg, workdir)
    sfx = build_sfx_track(timeline, total, cfg, workdir)

    inputs = []
    for c in clips:
        inputs += ["-i", c]
    inputs += ["-i", voice_mp3.name]
    voice_idx = n
    if music:
        if loop_music:
            inputs += ["-stream_loop", "-1"]
        inputs += ["-i", str(music)]
    if sfx:
        inputs += ["-i", sfx.name]

    fc = (_video_graph(n, durations, cfg, ass_path.name, _fontsdir(workdir))
          + _audio_graph(cfg, voice_idx, bool(music), bool(sfx)))

    out = "video.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
         "-filter_complex", ";".join(fc),
         "-map", "[v]", "-map", "[a]", "-shortest",
         *_venc(cfg), *COLOR_TAGS, "-pix_fmt", "yuv420p",
         "-profile:v", "high", "-level", _level(*_dims(cfg)),
         "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
         "-movflags", "+faststart", out], cwd=workdir)

    for name in clips + [sc["audio"] for sc in timeline]:
        (workdir / name).unlink(missing_ok=True)
    if sfx:
        sfx.unlink(missing_ok=True)

    return workdir / out
