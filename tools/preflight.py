"""Can this machine actually render and publish? Answer before burning minutes.

Each factory ships its own preflight, but a factory only knows about itself.
This one checks what the hub needs: both factories present and complete, the
FFmpeg filters the render graph reaches for, and whether a key is missing badly
enough to change what a run produces.

Two severities, and the split is the whole point of the file. A PROBLEM means a
render cannot work, and this exits 1. A NOTE means the run still makes videos,
just a lesser version of them - no Pexels key means Wikimedia-only visuals. This
runs in CI ahead of every render, so failing the job over an optional key would
teach the user that red means nothing.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hub import settings                                              # noqa: E402
from hub.paths import (CODE, FACTORIES, FACTORY_LABEL, IS_CI,         # noqa: E402
                       IS_FROZEN, factory_code, factory_dir, workspace)

# Every filter the two render graphs use. A distro FFmpeg built without libass
# still runs, it just silently drops the captions, so this is worth checking.
FILTERS = {
    "ass": "burn the captions in",
    "zoompan": "Ken Burns move on stills",
    "gblur": "blurred backdrop behind a photo",
    "gradients": "generated background when there is no photo",
    "loudnorm": "normalise the mix to -14 LUFS",
    "alimiter": "stop the mix clipping",
    "sidechaincompress": "duck the music under the voice",
    "tremolo": "generated music bed",
    "aevalsrc": "sound effects",
    "anoisesrc": "whoosh transition",
}

MODULES = {
    "edge_tts": "the voiceover; there is no fallback for this one",
    "requests": "every HTTP call the pipeline makes",
}

FACTORY_FILES = ("main.py", "config.json", "topics.json")

MIN_PYTHON = (3, 9)
WANT_PYTHON = (3, 12)

_NAME = re.compile(r"^[A-Za-z0-9_]+$")


class Report:
    def __init__(self):
        self.problems = []
        self.notes = []

    def ok(self, line):
        print(f"OK    {line}")

    def problem(self, line):
        print(f"FAIL  {line}")
        self.problems.append(line)

    def note(self, line):
        print(f"note  {line}")
        self.notes.append(line)


def _run(command):
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace")


def check_python(report):
    version = sys.version_info
    shown = f"{version.major}.{version.minor}.{version.micro}"
    if version[:2] < MIN_PYTHON:
        report.problem(f"python {shown} is too old; need "
                       f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer")
    elif version[:2] < WANT_PYTHON:
        report.ok(f"python {shown}")
        report.note(f"python {shown} works, but the project is developed and "
                    f"built on {WANT_PYTHON[0]}.{WANT_PYTHON[1]}")
    else:
        report.ok(f"python {shown}")


def check_ffmpeg(report):
    """Returns True when the binaries are there and the filters can be listed."""
    found = True
    for exe in ("ffmpeg", "ffprobe"):
        try:
            first = _run([exe, "-version"]).stdout.splitlines()[0]
            report.ok(first[:100])
        except (OSError, IndexError):
            report.problem(f"{exe} is not on PATH - nothing can be rendered without it")
            found = False
    if not found:
        return False

    listing = _run(["ffmpeg", "-hide_banner", "-filters"]).stdout
    names = set()
    for line in listing.splitlines():
        parts = line.split()
        if len(parts) > 2 and _NAME.match(parts[1]):
            names.add(parts[1])

    missing = [(n, why) for n, why in FILTERS.items() if n not in names]
    for name, why in missing:
        report.problem(f"FFmpeg has no '{name}' filter ({why})")
    if not missing:
        report.ok(f"ffmpeg filters ({len(FILTERS)} needed, all present)")
    return True


def check_modules(report):
    for name, why in MODULES.items():
        try:
            __import__(name)
            report.ok(f"module {name}")
        except ImportError:
            report.problem(f"python module '{name}' is missing ({why}) - "
                           f"pip install -r requirements.txt")

    # Scripts come from Gemini or Claude over plain HTTP, so the SDK is a bonus,
    # not a requirement. Say so rather than listing it as a failure.
    try:
        import anthropic                                             # noqa: F401
        report.ok("module anthropic (Claude available as a script writer)")
    except ImportError:
        report.note("module anthropic is not installed - Gemini and the local "
                    "topics bank still work")


def check_factories(report):
    for name in FACTORIES:
        label = FACTORY_LABEL.get(name, name)
        shipped = factory_code(name)
        if not shipped.is_dir():
            report.problem(f"factory {name} ({label}) is missing from {shipped}")
            continue

        absent = [f for f in FACTORY_FILES if not (shipped / f).exists()]
        if absent:
            report.problem(f"factory {name} is incomplete, no {', '.join(absent)}")
            continue

        font = shipped / "assets" / "fonts" / "Anton-Regular.ttf"
        if font.exists():
            report.ok(f"factory {name} ({label}) with {font.name}")
        else:
            report.ok(f"factory {name} ({label})")
            report.note(f"factory {name} has no {font.name}; captions fall back "
                        f"to whatever typeface the system offers")

        # An installed copy runs from the workspace, not from the install dir.
        # It gets created on the first run, so its absence is not a failure.
        live = factory_dir(name)
        if live != shipped and not live.is_dir():
            report.note(f"factory {name} has no workspace copy yet at {live}; "
                        f"the first run creates it")


def check_keys(report):
    cfg = settings.load()
    for line in settings.missing_keys(cfg):
        report.note(line)
    present = [n for n in settings.SECRET_NAMES if settings.secret(n, cfg)]
    if present:
        report.ok(f"keys set: {', '.join(present)}")
    else:
        report.note("no keys are set anywhere - scripts come from topics.json, "
                    "visuals from Wikimedia, and nothing gets published")


def main():
    print("Automation Hub preflight")
    print(f"code      {CODE}")
    print(f"workspace {workspace()}")
    print(f"mode      {'frozen exe' if IS_FROZEN else 'source'}"
          f"{', GitHub Actions' if IS_CI else ''}")
    print("")

    report = Report()
    check_python(report)
    check_ffmpeg(report)
    check_modules(report)
    check_factories(report)
    check_keys(report)

    print("")
    if report.problems:
        print(f"{len(report.problems)} problem(s) block a render:")
        for line in report.problems:
            print(f"  - {line}")
        return 1

    if report.notes:
        print(f"Ready. {len(report.notes)} thing(s) worth knowing:")
        for line in report.notes:
            print(f"  - {line}")
    else:
        print("Ready. Everything checked out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
