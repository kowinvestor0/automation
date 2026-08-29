"""Hide the console window when the exe was started as the GUI.

AutomationHub.exe is built with console=True on purpose. The control panel
re-launches the very same exe as a subprocess - [sys.executable, "run", ...] and
[sys.executable, "factory", "us", ...] - and reads the child's stdout to show a
live log. A windowed PyInstaller build has no stdout at all: the child's prints
go into a null writer and the parent reads an empty pipe, so the progress view
would stay blank for a twenty-minute render. Console it is.

The cost is a black window behind the GUI, so this hook closes that gap: when no
CLI subcommand was given we are the control panel, and the console gets hidden
straight away. It is hidden, not detached - the process keeps a real stdout, and
children launched later inherit the same invisible console instead of popping
one of their own.

Lives under installer/ because it is packaging machinery: it only ever runs
inside a frozen build, never when the project is run from source.
"""
import sys

# Mirrors the dispatch table in AutomationHub.py. Anything else means the GUI.
_CLI = {"run", "factory", "preflight", "help", "-h", "--help"}


def _hide_console():
    import ctypes

    window = ctypes.windll.kernel32.GetConsoleWindow()
    if not window:
        return
    # The console is ours alone only when no other process is attached to it,
    # which is the double-click case. Started from an existing terminal we would
    # be hiding the user's own window, so leave it alone.
    buffer = (ctypes.c_uint * 2)()
    if ctypes.windll.kernel32.GetConsoleProcessList(buffer, 2) > 1:
        return
    ctypes.windll.user32.ShowWindow(window, 0)   # SW_HIDE


if sys.platform == "win32":
    argument = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if argument not in _CLI:
        try:
            _hide_console()
        except Exception:
            pass      # A missing console is not a reason to refuse to start.
