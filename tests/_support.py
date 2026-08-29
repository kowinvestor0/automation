"""Fixtures shared by the test modules.

The leading underscore keeps `unittest discover` from importing this as a test
module.

Every test that touches settings or state inherits from `IsolatedHome`. The hub
reads HUB_DATA_DIR on every call (hub.paths.data_dir), so pointing it at a
tempdir is enough to guarantee no test can read or write the settings.json and
state.json in the user's real profile.
"""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Anything the hub may read from the environment. A real key or a leftover
# GitHub Actions variable on the developer's machine would otherwise change the
# outcome of a test.
LEAKY_ENV = (
    "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "PEXELS_API_KEY", "PLANLY_API_KEY",
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GITHUB_TOKEN", "WIKI_CONTACT",
    "HUB_WORKSPACE", "GITHUB_STEP_SUMMARY", "GITHUB_RUN_NUMBER", "GITHUB_RUN_ID",
    "GITHUB_REPOSITORY", "GITHUB_SERVER_URL",
)

TZ7 = dt.timezone(dt.timedelta(hours=7))          # the user lives in UTC+7
SIX_TIMES = ["09:00", "12:00", "15:00", "18:00", "21:00", "23:00"]


class IsolatedHome(unittest.TestCase):
    """Gives the test its own data dir, and restores the environment after."""

    def setUp(self):
        self._saved_env = dict(os.environ)
        self.tmp = Path(tempfile.mkdtemp(prefix="hubtest-"))
        for name in LEAKY_ENV:
            os.environ.pop(name, None)
        os.environ["HUB_DATA_DIR"] = str(self.tmp)
        self.addCleanup(self._restore)

    def _restore(self):
        os.environ.clear()
        os.environ.update(self._saved_env)
        shutil.rmtree(self.tmp, ignore_errors=True)


def local(year=2026, month=8, day=29, hour=8, minute=0):
    """A fixed `now` on the user's own wall clock, so tests are deterministic."""
    return dt.datetime(year, month, day, hour, minute, tzinfo=TZ7)


def publish_cfg(**over):
    """The `publish` block of settings.json, with the shipped defaults."""
    cfg = {
        "enabled": True,
        "dry_run": True,
        # Planly's API cannot look a team up, so a run without one is an error
        # path, not the normal case. Tests that want that path clear it.
        "team_id": "team-1",
        "channels": ["all"],
        "mode": "same_time",
        "times": list(SIX_TIMES),
        "gap_minutes": 120,
        "timezone_offset": 7,
        "lead_minutes": 30,
        "distribute": "unique",
        "max_seconds": 60,
        "channel_options": {},
    }
    cfg.update(over)
    return cfg


def channels(*names):
    return [{"id": n, "name": n.upper(), "social_network": "tiktok"} for n in names]


def videos(count, prefix="v"):
    return [{"folder": f"{prefix}{i}", "title": f"Title {i}",
             "description": f"Description {i}", "duration_seconds": 30}
            for i in range(count)]


def make_output(factory_dir, folder, meta, mp4="video.mp4", raw_meta=None):
    """Build one output/<stamp>/ the way a factory leaves it behind.

    `mp4` of None writes no video file; `raw_meta` writes that exact text
    instead of JSON, for the unreadable-metadata case.
    """
    d = Path(factory_dir) / "output" / folder
    d.mkdir(parents=True, exist_ok=True)
    if raw_meta is not None:
        (d / "meta.json").write_text(raw_meta, encoding="utf-8")
    else:
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    if mp4:
        (d / mp4).write_bytes(b"\x00fake mp4")
    return d
