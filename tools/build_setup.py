"""Compile installer/AutomationHub.iss into dist/setup/AutomationHub_Setup_*.exe.

    python tools/build_setup.py

Run tools/build_exe.py first - this only wraps what is already in
dist/AutomationHub. Inno Setup is Windows-only, so this refuses to pretend
anywhere else rather than failing halfway through.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "installer" / "AutomationHub.iss"
PAYLOAD = ROOT / "dist" / "AutomationHub"
OUTPUT = ROOT / "dist" / "setup"


def version():
    sys.path.insert(0, str(ROOT))
    try:
        from hub import __version__
        return __version__
    except Exception:
        return "0.0.0"


def candidates():
    """Where ISCC.exe might be, best guess first. The env var comes first so a
    non-standard install can be pointed at without editing anything."""
    found = []
    override = os.environ.get("ISCC_PATH", "").strip().strip('"')
    if override:
        found.append(Path(override))
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        found.append(Path(local) / "Programs" / "Inno Setup 6" / "ISCC.exe")
    found += [
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
    ]
    return found


def find_iscc():
    looked = []
    for path in candidates():
        looked.append(path)
        if path.is_file():
            return path, looked
    # Last resort: chocolatey and scoop both put ISCC on PATH.
    on_path = shutil.which("ISCC") or shutil.which("iscc")
    if on_path:
        return Path(on_path), looked
    looked.append(Path("ISCC.exe on PATH"))
    return None, looked


def main():
    parser = argparse.ArgumentParser(description="Compile the Windows installer.")
    parser.add_argument("--version", default=None,
                        help="version stamped into the setup exe (default: hub.__version__)")
    parser.add_argument("--source", default=str(PAYLOAD),
                        help="the built one-folder app to wrap")
    args = parser.parse_args()

    if sys.platform != "win32":
        print("ERROR: Inno Setup only runs on Windows. Build the installer on a "
              "Windows machine or on the windows-latest runner.", file=sys.stderr)
        return 1

    if not SCRIPT.exists():
        print(f"ERROR: {SCRIPT} is missing", file=sys.stderr)
        return 1

    source = Path(args.source).resolve()
    if not (source / "AutomationHub.exe").is_file():
        print(f"ERROR: nothing to package - there is no AutomationHub.exe in "
              f"{source}.\nRun:  python tools/build_exe.py", file=sys.stderr)
        return 1

    iscc, looked = find_iscc()
    if iscc is None:
        print("ERROR: could not find the Inno Setup 6 compiler (ISCC.exe).",
              file=sys.stderr)
        print("Looked in:", file=sys.stderr)
        for path in looked:
            print(f"  - {path}", file=sys.stderr)
        print("Install Inno Setup 6 from https://jrsoftware.org/isdl.php, or set "
              "ISCC_PATH to its ISCC.exe.", file=sys.stderr)
        return 1

    app_version = args.version or version()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    command = [
        str(iscc),
        f"/DAppVersion={app_version}",
        f"/DSourceDir={source}",
        f"/DOutDir={OUTPUT}",
        str(SCRIPT),
    ]
    print(f"compiler {iscc}")
    print(f"payload  {source}")
    print(f"version  {app_version}")
    result = subprocess.run(command, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\nERROR: ISCC exited {result.returncode}", file=sys.stderr)
        return result.returncode

    setup = OUTPUT / f"AutomationHub_Setup_{app_version}.exe"
    if not setup.exists():
        print(f"\nERROR: ISCC reported success but {setup} is not there",
              file=sys.stderr)
        return 1

    print(f"\nInstaller: {setup}  ({setup.stat().st_size / (1 << 20):.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
