"""Checks the machine can run the pipeline before burning minutes on a render.

Util sobre todo en Linux (GitHub Actions, Colab, VPS), donde el FFmpeg del sistema
puede venir sin libass o sin algun filtro.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILTERS = {
    "ass": "quemar los subtitulos",
    "zoompan": "efecto Ken Burns en las fotos",
    "gblur": "fondo desenfocado",
    "gradients": "fondo generado cuando no hay foto",
    "loudnorm": "normalizar a -14 LUFS",
    "alimiter": "evitar saturacion en la mezcla",
    "sidechaincompress": "bajar la musica cuando habla la voz",
    "tremolo": "musica generada",
    "aevalsrc": "efectos de sonido",
    "anoisesrc": "whoosh",
}


def _run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace")


def main():
    problems = []

    for exe in ("ffmpeg", "ffprobe"):
        try:
            out = _run([exe, "-version"]).stdout.splitlines()[0]
            print(f"OK  {out}")
        except FileNotFoundError:
            problems.append(f"{exe} is not on PATH")

    if not problems:
        available = _run(["ffmpeg", "-hide_banner", "-filters"]).stdout
        # Las lineas son "  T.. nombre  entradas->salidas  descripcion"
        names = {line.split()[1] for line in available.splitlines()
                 if len(line.split()) > 2 and not line.startswith("Filters:")}
        for name, why in FILTERS.items():
            if name in names:
                print(f"OK  filter {name}")
            else:
                problems.append(f"FFmpeg is missing the '{name}' filter ({why})")

    font = ROOT / "assets" / "fonts" / "Anton-Regular.ttf"
    if font.exists():
        print(f"OK  font {font.name} ({font.stat().st_size // 1024} KB)")
    else:
        problems.append(f"font {font} is missing (captions would fall back to another typeface)")

    for mod in ("edge_tts", "requests"):
        try:
            __import__(mod)
            print(f"OK  module {mod}")
        except ImportError:
            problems.append(f"Python module '{mod}' is missing (pip install -r requirements.txt)")

    if problems:
        print("\nPROBLEMAS:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("\nAll good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
