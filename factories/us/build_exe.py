"""Package the app into dist/VideoFactory.exe with PyInstaller.

    python build_exe.py                 lean build (Gemini + offline bank)
    python build_exe.py --with-claude   also bundle the Anthropic SDK
    python build_exe.py --with-ffmpeg   copy ffmpeg/ffprobe into the exe

Without --with-ffmpeg the exe expects FFmpeg on PATH, which keeps it around
30 MB instead of 150 MB. The app says so on startup if it cannot find it.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "VideoFactory"
SEP = ";" if sys.platform == "win32" else ":"


def data_args(with_ffmpeg):
    items = [("config.json", "."), ("topics.json", "."),
             ("assets/fonts", "assets/fonts")]
    args = []
    for src, dst in items:
        path = ROOT / src
        if not path.exists():
            print(f"  ! missing {src}, skipping")
            continue
        args += ["--add-data", f"{path}{SEP}{dst}"]

    if with_ffmpeg:
        staged = ROOT / "build_ffmpeg"
        staged.mkdir(exist_ok=True)
        found = 0
        for exe in ("ffmpeg", "ffprobe"):
            which = shutil.which(exe)
            if not which:
                print(f"  ! {exe} not on PATH, cannot bundle it")
                continue
            shutil.copy2(which, staged / Path(which).name)
            found += 1
        if found:
            args += ["--add-data", f"{staged}{SEP}ffmpeg"]
            print(f"  bundling {found} FFmpeg binaries "
                  f"({sum(f.stat().st_size for f in staged.iterdir()) // (1 << 20)} MB)")
    return args


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-claude", action="store_true",
                    help="bundle the Anthropic SDK too (adds ~40 MB)")
    ap.add_argument("--with-ffmpeg", action="store_true",
                    help="copy ffmpeg/ffprobe inside the exe (adds ~120 MB)")
    ap.add_argument("--console", action="store_true",
                    help="keep a console window, useful for debugging")
    # Windows will not let PyInstaller overwrite an exe that is currently open.
    ap.add_argument("--out", default="dist",
                    help="output folder (use another one if the app is running)")
    args = ap.parse_args()

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is missing. Run:  pip install pyinstaller")
        return 1

    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onefile", "--name", NAME, "--distpath", str(ROOT / args.out),
        "--console" if args.console else "--windowed",
        # edge-tts and certifi carry data files that a plain import scan misses.
        "--collect-all", "edge_tts",
        "--collect-all", "certifi",
        "--hidden-import", "requests",
        # Imported lazily inside functions, so PyInstaller cannot see them.
        "--hidden-import", "pipeline.gemini",
        "--hidden-import", "pipeline.render",
        "--hidden-import", "pipeline.visuals",
        "--hidden-import", "pipeline.audio_fx",
    ]
    if args.with_claude:
        cmd += ["--collect-all", "anthropic"]
    else:
        # Keeps the build lean; the app degrades to Gemini or the local bank.
        cmd += ["--exclude-module", "anthropic"]

    cmd += data_args(args.with_ffmpeg)
    cmd.append(str(ROOT / "app.py"))

    print("Building...\n  " + " ".join(cmd[:6]) + " ...")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode

    shutil.rmtree(ROOT / "build_ffmpeg", ignore_errors=True)
    exe = ROOT / args.out / (NAME + (".exe" if sys.platform == "win32" else ""))
    if exe.exists():
        print(f"\nDone: {exe}  ({exe.stat().st_size / (1 << 20):.1f} MB)")
        print("Copy the exe anywhere. On first run it writes config.json,")
        print("topics.json and assets/ next to itself so you can edit them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
