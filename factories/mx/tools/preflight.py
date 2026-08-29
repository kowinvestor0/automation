"""Revisa que la maquina pueda correr el pipeline antes de gastar minutos en render.

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
            problems.append(f"falta {exe} en el PATH")

    if not problems:
        available = _run(["ffmpeg", "-hide_banner", "-filters"]).stdout
        # Las lineas son "  T.. nombre  entradas->salidas  descripcion"
        names = {line.split()[1] for line in available.splitlines()
                 if len(line.split()) > 2 and not line.startswith("Filters:")}
        for name, why in FILTERS.items():
            if name in names:
                print(f"OK  filtro {name}")
            else:
                problems.append(f"FFmpeg sin el filtro '{name}' ({why})")

    font = ROOT / "assets" / "fonts" / "Anton-Regular.ttf"
    if font.exists():
        print(f"OK  fuente {font.name} ({font.stat().st_size // 1024} KB)")
    else:
        problems.append(f"falta la fuente {font} (los subtitulos saldrian con otra tipografia)")

    for mod in ("edge_tts", "requests"):
        try:
            __import__(mod)
            print(f"OK  modulo {mod}")
        except ImportError:
            problems.append(f"falta el modulo de Python '{mod}' (pip install -r requirements.txt)")

    if problems:
        print("\nPROBLEMAS:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("\nTodo listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
