"""Canonical paths for the Auto Make Money application."""
from __future__ import annotations

import sys
from pathlib import Path

# Root of the auto make money workspace
ROOT_DIR = Path(__file__).resolve().parent.parent

CORE_DIR = ROOT_DIR / "core"
ASSETS_DIR = ROOT_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
SFX_DIR = ASSETS_DIR / "sfx"
MUSIC_DIR = ASSETS_DIR / "music"

DATA_DIR = ROOT_DIR / "data"
CACHE_DIR = ROOT_DIR / "cache"
OUTPUT_DIR = ROOT_DIR / "output"
UI_DIR = ROOT_DIR / "ui"

CONFIG_FILE = ROOT_DIR / "config.json"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"

# Ensure essential runtime folders exist
for p in (DATA_DIR, CACHE_DIR, OUTPUT_DIR, SFX_DIR, MUSIC_DIR, FONTS_DIR):
    p.mkdir(parents=True, exist_ok=True)
