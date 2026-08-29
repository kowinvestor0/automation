"""Empaqueta el panel de control como un solo .exe.

El ejecutable NO lleva adentro config.json, topics.json ni assets: esos quedan
junto al .exe para que se puedan editar y para que GitHub Actions use los mismos.
Tampoco lleva FFmpeg (son ~100 MB); el panel avisa si no lo encuentra.

    python tools/build_exe.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOMBRE = "FabricaVideosMX"


def main():
    if not (ROOT / "gui.py").exists():
        print("ERROR: no encuentro gui.py", file=sys.stderr)
        return 1

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile",
        "--windowed",                 # sin consola negra al abrir
        "--name", NOMBRE,
        "--distpath", str(ROOT),      # el .exe cae en la raiz del proyecto
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
        # El modo --run importa esto en caliente; PyInstaller no siempre lo ve.
        "--hidden-import", "main",
        "--hidden-import", "pipeline.render",
        "--hidden-import", "pipeline.script_gen",
        "--hidden-import", "pipeline.subtitles",
        "--hidden-import", "pipeline.tts",
        "--hidden-import", "pipeline.visuals",
        "--hidden-import", "pipeline.audio_fx",
        "--hidden-import", "pipeline.util",
        "--hidden-import", "edge_tts",
        "--hidden-import", "requests",
        # Pesan y no se usan.
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "PIL",
        "--exclude-module", "pytest",
        str(ROOT / "gui.py"),
    ]
    print(" ".join(cmd), flush=True)
    if subprocess.run(cmd, cwd=str(ROOT)).returncode != 0:
        return 1

    shutil.rmtree(ROOT / "build", ignore_errors=True)
    exe = ROOT / f"{NOMBRE}.exe"
    if not exe.exists():
        print("ERROR: PyInstaller termino pero no hay .exe", file=sys.stderr)
        return 1
    print(f"\nListo: {exe}  ({exe.stat().st_size / 1048576:.1f} MB)")
    print("Dejalo en esta carpeta: lee config.json y escribe en output/ desde aqui.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
