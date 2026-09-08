"""Configuration manager with automatic detection and safe local storage."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from core.paths import CONFIG_FILE, ROOT_DIR

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_keys": {
        "gemini_api_key": "",
        "pexels_api_key": "",
        "anthropic_api_key": "",
    },
    "generation": {
        "target_duration_min": 60,       # Minimum 60s for TikTok monetization
        "target_duration_max": 85,       # Sweet spot 65-85s
        "language": "en",                # "en" (US) or "vi" or "es"
        "voice": "en-US-ChristopherNeural",
        "voice_rate": "+10%",
        "auto_stitch_multi_clips": True, # If single clip < 60s, stitch multiple clips
        "vocal_suppression": True,       # Suppress original speech, keep SFX/ambient
        "original_audio_volume": 0.15,   # Low ambient SFX level
        "music_volume": 0.12,            # Background music level
        "tts_volume": 1.25,              # Clear loud narrator
        "font_size": 95,
        "highlight_color": "&H0033E5FF&",# Yellow/Cyan karaoke highlight
    },
    "publishing": {
        "videos_per_channel_per_day": 3, # 3 or 6 videos/channel/day
        "mode": "same_time",             # "same_time" (Đăng cùng lúc) or "scheduled" (Lên lịch giờ vàng)
        "schedule_times": [
            "09:00", "12:00", "15:00", "18:00", "21:00", "23:00"
        ],
        "timezone_offset": 7,            # UTC+7 for Vietnam / customizable
        "dry_run": False,                # Set false for real upload
    },
    "search_queries": [
        "unexpected caught on camera shorts",
        "crazy science experiment shorts",
        "wild animals unexpected encounters shorts",
        "incredible human skill shorts",
        "bizarre mystery phenomena shorts",
        "us breaking events viral moments",
    ]
}


def _auto_import_from_legacy() -> Dict[str, Any]:
    """Scan machine for legacy config from D:\\automation\\settings.json."""
    cfg = dict(DEFAULT_CONFIG)
    legacy_file = Path(r"D:\automation\settings.json")
    if legacy_file.exists():
        try:
            legacy = json.loads(legacy_file.read_text(encoding="utf-8"))
            keys = legacy.get("keys", {})
            if keys.get("GEMINI_API_KEY"):
                cfg["api_keys"]["gemini_api_key"] = keys["GEMINI_API_KEY"]
            if keys.get("ANTHROPIC_API_KEY"):
                cfg["api_keys"]["anthropic_api_key"] = keys["ANTHROPIC_API_KEY"]
            if keys.get("PEXELS_API_KEY"):
                cfg["api_keys"]["pexels_api_key"] = keys["PEXELS_API_KEY"]
        except Exception:
            pass
    return cfg


def load_config() -> Dict[str, Any]:
    """Load config from local config.json, auto-creating if missing."""
    if not CONFIG_FILE.exists():
        cfg = _auto_import_from_legacy()
        save_config(cfg)
        return cfg

    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        # Merge defaults for any missing keys
        merged = dict(DEFAULT_CONFIG)
        for k, v in data.items():
            if isinstance(v, dict) and k in merged:
                merged[k].update(v)
            else:
                merged[k] = v
        return merged
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg: Dict[str, Any]) -> None:
    """Save configuration to config.json."""
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def get_api_key(name: str) -> str:
    """Get specific API key from config or environment variable."""
    cfg = load_config()
    key = cfg.get("api_keys", {}).get(name.lower(), "")
    if not key:
        key = os.environ.get(name.upper(), "")
    return key.strip()
