# -*- mode: python ; coding: utf-8 -*-
"""One-folder build of AutomationHub.exe.

Two decisions in here are worth explaining, because both look wrong at a glance.

console=True on a desktop app. The control panel runs a render by launching the
same exe again - [sys.executable, "run", ...] - and reads the child's stdout to
show progress. A windowed PyInstaller build has no stdout, so the child's output
would vanish and the log pane would sit empty for twenty minutes. The build is
therefore a console build, and installer/runtime_hook_console.py hides the
window the moment the GUI path starts. See that file for the details.

The factories ship as DATA, not as code. Both of them contain a package called
`pipeline`, so PyInstaller cannot import them into one archive without one
shadowing the other - which is also why a run launches them as subprocesses.
They get extracted as plain .py files and imported off sys.path at run time.
The consequence: nothing the factories import is visible to the analysis below,
so their third-party and less common stdlib imports are listed by hand.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve()

# Mirrors hub.workspace.SKIP_DIRS: these are outputs and scratch, never program.
SKIP_DIRS = {"__pycache__", "output", "cache", ".git", ".claude", "build", "dist",
             ".pytest_cache", ".mypy_cache"}
# Per-factory dev leftovers. Each factory used to build its own exe; the hub
# builds them now, so those scripts would only confuse whoever opens the folder.
SKIP_FILES = {"build_exe.py", "VideoFactory.spec", ".env.example", ".gitignore"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".log", ".spec.bak"}


def tree(source, prefix):
    """(file, destination-folder) pairs for everything worth shipping under
    `source`. PyInstaller's own Tree() has no way to skip output/ and cache/,
    which on a used checkout are the two biggest folders on disk."""
    source = Path(source)
    items = []
    if not source.is_dir():
        return items
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if SKIP_DIRS.intersection(relative.parts[:-1]):
            continue
        if path.name in SKIP_FILES or path.suffix in SKIP_SUFFIXES:
            continue
        items.append((str(path), str(Path(prefix) / relative.parent)))
    return items


datas = []
for name in ("us", "mx"):
    # Includes each factory's assets/fonts, which is where Anton-Regular.ttf
    # lives - without it every caption falls back to a system typeface.
    datas += tree(ROOT / "factories" / name, f"factories/{name}")
datas += tree(ROOT / "assets", "assets")

binaries = []
hiddenimports = [
    "requests",
    # The hub and the desktop app are reached through late imports in
    # AutomationHub.py; collecting them by name survives a refactor of that
    # dispatch, and lets this spec build before desktop/ has been written.
    *collect_submodules("hub"),
    *collect_submodules("tools"),
    # tkinter is not referenced anywhere the analysis can see it until the
    # control panel exists, and an exe without tcl/tk cannot open a window.
    "tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.filedialog",
    "tkinter.scrolledtext", "tkinter.font",
    "queue", "threading", "webbrowser",
    # Imported by the factories, which are data files - see the module docstring.
    "asyncio", "hashlib", "random", "unicodedata", "urllib.parse",
]

if (ROOT / "desktop").is_dir():
    hiddenimports += collect_submodules("desktop")

# edge-tts and certifi both carry data files (the CA bundle, the voice list)
# that an import scan alone does not pick up.
for package in ("edge_tts", "certifi"):
    found = collect_all(package)
    datas += found[0]
    binaries += found[1]
    hiddenimports += found[2]

# Claude is one of three ways to get a script, and the other two need no SDK.
# The build must not depend on the wheel being installed.
# "pip" and "wheel" are deliberately absent: setuptools' PyInstaller hook
# aliases its vendored copies of them, and excluding either aborts the build.
excludes = ["numpy", "pandas", "matplotlib", "scipy", "PIL", "IPython",
            "notebook", "pytest", "_pytest",
            "pydoc_data", "lib2to3", "tkinter.test", "test", "tests"]
try:
    found = collect_all("anthropic")
    datas += found[0]
    binaries += found[1]
    hiddenimports += found[2]
except Exception:
    excludes.append("anthropic")


a = Analysis(
    [str(ROOT / "AutomationHub.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "installer" / "runtime_hook_console.py")],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AutomationHub",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX shaves a few MB and has a long history of tripping antivirus and of
    # mangling the Python DLL. Not worth it for a tool that runs unattended.
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icon.ico") if (ROOT / "assets" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AutomationHub",
)
