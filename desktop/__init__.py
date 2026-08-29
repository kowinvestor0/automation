"""The Tkinter control panel.

Everything the hub does can run headless - GitHub Actions never opens a window.
This package is the other half: the screen the user opens on their own PC to
fill in keys, pick channels and see what the unattended runs have been doing.

Kept to the standard library on purpose. The desktop build is one PyInstaller
exe, and tkinter is the only GUI toolkit that survives freezing without extra
wheels, native DLLs or a runtime install step.
"""
__all__ = ["main"]


def main(*args, **kwargs):
    """Late import so `import desktop` stays cheap for the CLI paths."""
    from desktop.app import main as _main
    return _main(*args, **kwargs)
