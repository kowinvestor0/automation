"""Single entry point for everything the hub does.

    AutomationHub.py                      open the control panel
    AutomationHub.py run --factory us     render + schedule, no window
    AutomationHub.py factory us --count 3 run one factory directly
    AutomationHub.py preflight            check this machine can render

One entry point matters more than it looks: PyInstaller produces one exe, and
the exe has to be able to re-launch itself to run a factory as a subprocess.
`sys.executable` on a frozen build is the exe, not python, so a build with two
separate entry scripts could not do that.
"""
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def _utf8_console():
    """Windows consoles default to cp1252 and raise on Vietnamese or on the
    status badges. Losing a whole run to a print is not acceptable."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    _utf8_console()
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv[0] if argv else ""

    if command == "run":
        from tools import run_factory
        sys.argv = ["run_factory"] + argv[1:]
        return run_factory.main()

    if command == "factory":
        # The subprocess side of a render. Only one factory is ever loaded per
        # process, which is the whole point: both factories ship a package
        # called `pipeline` and they would shadow each other.
        if len(argv) < 2:
            print("usage: AutomationHub factory <us|mx> [factory flags]", file=sys.stderr)
            return 2
        from hub.paths import factory_dir
        directory = factory_dir(argv[1])
        entry = directory / "main.py"
        if not entry.exists():
            print(f"no factory at {entry}", file=sys.stderr)
            return 127
        sys.path.insert(0, str(directory))
        os.chdir(directory)
        sys.argv = ["main.py"] + argv[2:]
        runpy.run_path(str(entry), run_name="__main__")
        return 0

    if command == "preflight":
        from tools import preflight
        sys.argv = ["preflight"] + argv[1:]
        return preflight.main()

    if command in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    from desktop.app import main as gui
    return gui()


if __name__ == "__main__":
    sys.exit(main())
