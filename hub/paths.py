"""Where everything lives, in both the source tree and the installed exe.

Three roots, and they are genuinely different things:

  CODE   - the read-only program. In a PyInstaller build this is the temp
           folder that gets deleted on exit, so nothing writable may go here.
  DATA   - settings and run state. %APPDATA%/AutomationHub on Windows.
  WORK   - the workspace: a materialised copy of the factories plus their
           output/, cache/ and state.json. The user picks the drive at install
           time, so this is read from settings, not hard-coded.

In CI there is no installer and no %APPDATA%, so all three collapse onto the
checkout and everything keeps working unchanged.
"""
import os
import sys
from pathlib import Path


def _code_root():
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


CODE = _code_root()
IS_FROZEN = bool(getattr(sys, "frozen", False))
IS_CI = os.environ.get("GITHUB_ACTIONS") == "true"


def data_dir():
    """Settings + run state. Never inside Program Files."""
    override = os.environ.get("HUB_DATA_DIR", "").strip()
    if override:
        return Path(override)
    if IS_CI or not IS_FROZEN:
        return CODE
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / "AutomationHub"
    return Path.home() / ".automation-hub"


def default_workspace():
    if IS_CI or not IS_FROZEN:
        return CODE
    docs = Path.home() / "Documents"
    return (docs if docs.is_dir() else Path.home()) / "AutomationHub"


def workspace():
    """Where factories actually run. Overridable per install and per run."""
    override = os.environ.get("HUB_WORKSPACE", "").strip()
    if override:
        return Path(override)
    try:
        from hub.settings import load
        configured = (load().get("workspace") or "").strip()
    except Exception:
        configured = ""
    return Path(configured) if configured else default_workspace()


def factory_code(name):
    """The pristine, read-only copy that ships with the program."""
    return CODE / "factories" / name


def factory_dir(name):
    """The writable copy a run actually executes in."""
    if IS_CI or not IS_FROZEN:
        return factory_code(name)
    return workspace() / "factories" / name


FACTORIES = ("us", "mx")

FACTORY_LABEL = {
    "us": "US / English",
    "mx": "Mexico / Espanol",
}


def ensure_dirs():
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "logs").mkdir(parents=True, exist_ok=True)
    return d
