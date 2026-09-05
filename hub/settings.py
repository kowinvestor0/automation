"""One settings file for the whole hub, plus the env-first rule for secrets.

Secrets are read from the environment first and settings.json second. That is
what lets the same code run in two places without a flag: on GitHub Actions the
keys arrive as repository secrets, on the user's PC they come from the file the
app writes. Nothing has to know which world it is in.

The file is written with restrictive permissions where the OS supports it - it
holds API keys.
"""
import json
import os
import copy
from pathlib import Path

from hub.paths import CODE, IS_CI, IS_FROZEN, data_dir, default_workspace

FILENAME = "settings.json"                  # local, holds the keys, gitignored
PUBLIC_FILENAME = "settings.public.json"    # committed, no keys in it

SECRET_NAMES = (
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
    "PEXELS_API_KEY",
    "PLANLY_API_KEY",
    "PLANLY_TEAM_ID",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "GITHUB_TOKEN",
    "WIKI_CONTACT",
)

# Placeholder text people leave behind when they half-fill a template.
_PLACEHOLDERS = {"...", "xxx", "your-key-here", "changeme", "none", "null"}

DEFAULTS = {
    "workspace": "",
    "keys": {name: "" for name in SECRET_NAMES},
    "github": {
        "repo": "",              # "owner/name"
        "run_workflow": "videos.yml",
        "build_workflow": "build.yml",
    },
    "publish": {
        "enabled": False,
        "dry_run": True,
        "team_id": "",
        "channels": ["all"],
        # same_time: every channel posts at the exact times below, together.
        # spread:    the first time is a start point and posts walk forward by
        #            gap_minutes.
        "mode": "same_time",
        "times": ["09:00", "12:00", "15:00", "18:00", "21:00", "23:00"],
        "gap_minutes": 120,
        "timezone_offset": 7,
        "lead_minutes": 30,
        # unique: split the batch so no two channels get the same video.
        # mirror: every channel gets every video.
        "distribute": "unique",
        # "now" hands the video to Planly to publish immediately; "slots" puts
        # it on the calendar at the times above.
        "when": "now",
        "max_seconds": 90,
        # Hold back a video whose topic already went out this recently.
        # The local bank recycles in under two days at full volume, and
        # the same clip on two accounts is what gets a network flagged.
        "repeat_days": 14,
        # TikTok rejects a video longer than about a minute while Duet or
        # Stitch are on, so "auto" switches them off past the limit.
        "post_options": {
            "duet": "auto",
            "stitch": "auto",
            "comment": "keep",
            "privacy_level": "default",
            "auto_disable_over_seconds": 60,
        },
        # Folder holding one sub-folder per account, for videos the user made
        # themselves. Empty means <repo>/video.
        "library_root": "",
        # Which stream of videos goes to which accounts. Keys are "us", "mx",
        # or "us:humor" for one niche; the value is a list of Planly channel
        # ids. Anything with no route falls back to `channels` above.
        "routes": {},
        "channel_options": {},
    },
    "run": {
        "us": {"count": 3, "niche": "", "enabled": True},
        "mx": {"count": 3, "niche": "", "enabled": True},
    },
    "notify": {"telegram": True, "on_success": True, "on_failure": True},
}


def path():
    return data_dir() / FILENAME


def public_path():
    """The committed half of the settings - everything except the keys.

    Without this, a run on GitHub Actions would find no settings file at all
    (settings.json is gitignored, and rightly so) and fall back to DEFAULTS,
    which have publishing switched off. The user would configure their posting
    times in the app and the background runs would quietly ignore every one of
    them. So the schedule, the channels and the run counts live in a file that
    is safe to commit, and only the keys stay behind.
    """
    override = os.environ.get("HUB_PUBLIC_SETTINGS", "").strip()
    if override:
        return Path(override)
    # Tests and scratch runs point HUB_DATA_DIR at a temp folder. When they do,
    # this file has to come from there too, or a real committed one would leak
    # into them and they would stop testing the defaults they think they test.
    if os.environ.get("HUB_DATA_DIR", "").strip():
        return data_dir() / PUBLIC_FILENAME
    return CODE / PUBLIC_FILENAME


def _merge(base, override):
    """Deep-merge, so a settings file written by an older version still loads."""
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _read(p):
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load():
    """DEFAULTS, then the committed file, then the local one. Keys last."""
    cfg = _merge(DEFAULTS, _read(public_path()))
    cfg = _merge(cfg, _read(path()))
    if not cfg.get("workspace"):
        cfg["workspace"] = str(default_workspace())
    return cfg


def public_view(cfg):
    """`cfg` minus anything that should not be in a repository, ready to commit."""
    out = copy.deepcopy(cfg)
    out.pop("keys", None)
    # The workspace is one machine's folder layout; it means nothing on a runner.
    out.pop("workspace", None)
    # The team id is not a credential - it is useless without the token - but it
    # names the account, and this file can end up in a public repo. CI gets it
    # from the PLANLY_TEAM_ID secret instead.
    if isinstance(out.get("publish"), dict):
        out["publish"]["team_id"] = ""
    return out


def save_public(cfg):
    """Write the committable half. Returns the path, or None when frozen.

    An installed copy has no repo to write into - the file it would touch is
    inside Program Files - so this is a no-op there and the app tells the user
    to export it instead.
    """
    p = public_path()
    if not p.parent.exists() or (IS_FROZEN and not IS_CI):
        return None
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(public_view(cfg), indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    tmp.replace(p)
    return p


def save(cfg):
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass          # Windows without the POSIX bits; the file is under the user profile anyway.
    return p


def secret(name, cfg=None):
    """Environment wins, settings.json is the fallback. Placeholders count as empty."""
    value = (os.environ.get(name) or "").strip()
    if value and value.lower() not in _PLACEHOLDERS:
        return value
    cfg = cfg if cfg is not None else load()
    value = ((cfg.get("keys") or {}).get(name) or "").strip()
    return "" if value.lower() in _PLACEHOLDERS else value


def export_env(cfg=None):
    """Push stored keys into os.environ so the factory subprocess inherits them."""
    cfg = cfg if cfg is not None else load()
    exported = []
    names = list(SECRET_NAMES)
    for k in (cfg.get("keys") or {}).keys():
        if k.startswith("PLANLY_") and k not in names:
            names.append(k)
    for name in names:
        value = secret(name, cfg)
        if value:
            os.environ[name] = value
            exported.append(name)
    return exported


def missing_keys(cfg=None):
    """Which keys block which feature. Used by the GUI and by preflight."""
    cfg = cfg if cfg is not None else load()
    problems = []
    if not (secret("GEMINI_API_KEY", cfg) or secret("ANTHROPIC_API_KEY", cfg)):
        problems.append("No GEMINI_API_KEY or ANTHROPIC_API_KEY - scripts fall back "
                        "to the local topics.json bank.")
    if not secret("PEXELS_API_KEY", cfg):
        problems.append("No PEXELS_API_KEY - visuals come from Wikimedia only.")
    if (cfg.get("publish") or {}).get("enabled") and not secret("PLANLY_API_KEY", cfg):
        problems.append("Publishing is on but PLANLY_API_KEY is empty.")
    return problems
