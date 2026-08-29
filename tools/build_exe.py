"""Build dist/AutomationHub/ with PyInstaller.

    python tools/build_exe.py

Runs the same way on this machine and on the windows-latest runner: it only
needs python, pip and the spec. The result is a folder, not a single file - a
one-file build would unpack ~150 MB into a temp directory on every launch, and
the app launches itself again for every render.
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "AutomationHub.spec"
NAME = "AutomationHub"


def version():
    sys.path.insert(0, str(ROOT))
    try:
        from hub import __version__
        return __version__
    except Exception:
        return "0.0.0"


def folder_size(path):
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def megabytes(size):
    return f"{size / (1 << 20):.1f} MB"


def clean(dist):
    """Wipe the previous build. dist/setup is left alone on purpose: it holds
    the installer from an earlier compile, and throwing that away because the
    exe was rebuilt would be a nasty surprise on a slow machine."""
    for path in (ROOT / "build", dist / NAME):
        if not path.exists():
            continue
        try:
            shutil.rmtree(path)
            print(f"removed {path}")
        except OSError as e:
            # Windows refuses to delete an exe that is currently running.
            print(f"ERROR: cannot remove {path}: {e}", file=sys.stderr)
            print("Close AutomationHub.exe if it is open and run this again.",
                  file=sys.stderr)
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Build the AutomationHub exe.")
    parser.add_argument("--distpath", default=str(ROOT / "dist"),
                        help="where the built folder goes (default: dist)")
    args = parser.parse_args()

    if not SPEC.exists():
        print(f"ERROR: {SPEC} is missing", file=sys.stderr)
        return 1
    try:
        import PyInstaller                                            # noqa: F401
    except ImportError:
        print("ERROR: PyInstaller is not installed. Run:  pip install pyinstaller",
              file=sys.stderr)
        return 1

    dist = Path(args.distpath).resolve()
    if not clean(dist):
        return 1

    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
               "--distpath", str(dist), "--workpath", str(ROOT / "build"),
               str(SPEC)]
    print(f"building {NAME} {version()}")
    print("  " + " ".join(command))
    started = time.time()
    result = subprocess.run(command, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\nERROR: PyInstaller exited {result.returncode}", file=sys.stderr)
        return result.returncode

    out = dist / NAME
    exe = out / (NAME + (".exe" if sys.platform == "win32" else ""))
    if not exe.exists():
        print(f"\nERROR: PyInstaller reported success but {exe} is not there",
              file=sys.stderr)
        return 1

    files = sum(1 for f in out.rglob("*") if f.is_file())
    print(f"\nBuilt in {time.time() - started:.0f}s")
    print(f"  folder {out}  ({megabytes(folder_size(out))}, {files} files)")
    print(f"  exe    {exe.name}  ({megabytes(exe.stat().st_size)})")
    print(f"  check  {exe} preflight")
    return 0


if __name__ == "__main__":
    sys.exit(main())
