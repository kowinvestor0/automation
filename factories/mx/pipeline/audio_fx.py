"""Musica de fondo y efectos de sonido, generados con FFmpeg.

Todo se sintetiza aqui mismo: no hay archivos que descargar y no hay
problema de derechos de autor. Si pones tus propios mp3 en assets/music/,
esos ganan sobre la musica generada.
"""
import hashlib
from pathlib import Path

from .util import ROOT, ffprobe_duration, log, run

SFX_CACHE = ROOT / "cache" / "sfx"

# Acordes por ambiente. Frecuencias en Hz: (bajo, y tres voces del acorde).
MOODS = {
    "misterios":   {"bass": 55.00, "notes": [110.00, 164.81, 220.00], "lp": 1100, "pulse": 0.50},
    "curiosidades": {"bass": 65.41, "notes": [130.81, 196.00, 261.63], "lp": 1600, "pulse": 0.75},
    "historia":    {"bass": 61.74, "notes": [123.47, 185.00, 246.94], "lp": 1300, "pulse": 0.60},
    "lugares":     {"bass": 73.42, "notes": [146.83, 220.00, 293.66], "lp": 1800, "pulse": 0.80},
    # Humor: mayor con sexta, brillante y con pulso rapido. Nada de suspenso.
    "humor":       {"bass": 87.31, "notes": [174.61, 220.00, 293.66], "lp": 2600, "pulse": 1.60},
    "commentary":  {"bass": 65.41, "notes": [130.81, 196.00, 261.63], "lp": 1800, "pulse": 1.10},
}


def _cached(name, builder):
    SFX_CACHE.mkdir(parents=True, exist_ok=True)
    path = SFX_CACHE / name
    if not path.exists() or path.stat().st_size < 1024:
        builder(path)
    return path


def make_music(duration, mood, workdir):
    """Colchon ambiental: acorde sostenido + pulso grave, con eco y fades."""
    m = MOODS.get(mood, MOODS["misterios"])
    dur = duration + 2.0
    key = hashlib.md5(f"{mood}:{dur:.1f}".encode()).hexdigest()[:12]

    def build(out):
        n1, n2, n3 = m["notes"]
        inputs = []
        for freq in (n1, n2, n3, m["bass"]):
            inputs += ["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={dur:.2f}"]
        fade_out = max(0.5, duration - 3.0)
        fc = (
            "[0:a]volume=0.30,tremolo=f=0.11:d=0.35[a];"
            "[1:a]volume=0.20,tremolo=f=0.13:d=0.30[b];"
            "[2:a]volume=0.12,vibrato=f=0.3:d=0.4[c];"
            f"[3:a]volume=0.38,tremolo=f={m['pulse']}:d=0.65[d];"
            "[a][b][c][d]amix=inputs=4:normalize=0,"
            f"lowpass=f={m['lp']},aecho=0.8:0.85:180|420:0.35|0.2,"
            f"afade=t=in:d=2,afade=t=out:st={fade_out:.2f}:d=3[out]"
        )
        run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
             "-filter_complex", fc, "-map", "[out]", "-t", f"{duration:.2f}",
             "-c:a", "libmp3lame", "-b:a", "160k", str(out)])

    return _cached(f"music_{key}.mp3", build)


def _whoosh(out):
    run(["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", "anoisesrc=d=0.55:c=pink:a=0.8",
         "-af", "volume='min(1,t*14)*exp(-5.5*t)':eval=frame,"
                "highpass=f=500,lowpass=f=7000,aecho=0.9:0.8:60:0.25,volume=2.2",
         "-ar", "44100", "-ac", "1", str(out)])


def _boom(out):
    run(["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i",
         "aevalsrc='0.9*sin(2*PI*(65*t-22*t*t))*exp(-3.2*t)':d=1.4:s=44100",
         "-af", "lowpass=f=180,volume=1.4",
         "-ar", "44100", "-ac", "1", str(out)])


def _pop(out):
    """Blip ascendente tipo caricatura, para los cortes de humor."""
    run(["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i",
         "aevalsrc='0.7*sin(2*PI*(320*t+1100*t*t))*exp(-11*t)':d=0.35:s=44100",
         "-af", "highpass=f=200,volume=1.5",
         "-ar", "44100", "-ac", "1", str(out)])


def _ding(out):
    """Campanita de remate: dos armonicos que se apagan juntos."""
    run(["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i",
         "aevalsrc='(0.5*sin(2*PI*1568*t)+0.3*sin(2*PI*2349*t))*exp(-5*t)':d=1.0:s=44100",
         "-af", "highpass=f=400,aecho=0.8:0.7:70:0.3,volume=1.2",
         "-ar", "44100", "-ac", "1", str(out)])


def _riser(out):
    run(["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i",
         "aevalsrc='0.45*sin(2*PI*(180*t+260*t*t))*(t/1.6)^1.6':d=1.6:s=44100",
         "-af", "highpass=f=150,aecho=0.8:0.8:90:0.3,volume=1.3",
         "-ar", "44100", "-ac", "1", str(out)])


def build_sfx_track(timeline, total_duration, cfg, workdir):
    """Pista de efectos: golpe en el gancho, whoosh en cada corte, riser antes del cierre.

    Devuelve None si no hay nada que poner.
    """
    if not cfg.get("sfx", True):
        return None

    if cfg.get("niche") == "humor":
        # Comedia: nada de suspenso. Blip en cada corte y campanita en el remate.
        hook = _cached("pop.wav", _pop)
        cut = _cached("pop.wav", _pop)
        end, end_lead, end_gain = _cached("ding.wav", _ding), 0.30, 0.55
    else:
        hook = _cached("boom.wav", _boom)
        cut = _cached("whoosh.wav", _whoosh)
        end, end_lead, end_gain = _cached("riser.wav", _riser), 1.45, 0.7

    # (archivo, segundo en que entra, ganancia)
    events = [(hook, 0.05, 1.0)]
    for sc in timeline[1:]:
        events.append((cut, max(0.0, sc["start"] - 0.18), 0.85))
    if len(timeline) >= 3:
        events.append((end, max(0.0, timeline[-1]["start"] - end_lead), end_gain))

    inputs, filters, labels = [], [], []
    for i, (path, at, gain) in enumerate(events):
        inputs += ["-i", str(path)]
        delay_ms = int(at * 1000)
        filters.append(f"[{i}:a]adelay={delay_ms}|{delay_ms},volume={gain}[e{i}]")
        labels.append(f"[e{i}]")

    out = workdir / "sfx.wav"
    fc = (";".join(filters) + ";" + "".join(labels)
          + f"amix=inputs={len(events)}:normalize=0:duration=longest[mix]")
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
         "-filter_complex", fc, "-map", "[mix]",
         "-t", f"{total_duration:.2f}", "-ar", "44100", "-ac", "1", out.name],
        cwd=workdir)
    log(f"{len(events)} efectos de sonido ({ffprobe_duration(out):.1f}s)")
    return out
