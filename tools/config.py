"""
config.py — Central configuration for the social video publishing system.

Loads .env and brand_config.json, exposes all settings as module-level constants.
Every other tool imports from here.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TMP_DIR = BASE_DIR / ".tmp"
TMP_DIR.mkdir(exist_ok=True)

VIDEOS_DIR = BASE_DIR / "videos"
VIDEOS_DIR.mkdir(exist_ok=True)

BRAND_CONFIG_PATH = BASE_DIR / "brand_config.json"

# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ---------------------------------------------------------------------------
# Brand Config
# ---------------------------------------------------------------------------

def load_brand_config() -> dict:
    """Load brand_config.json. Returns empty-ish defaults if file is missing."""
    if not BRAND_CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"brand_config.json not found at {BRAND_CONFIG_PATH}. "
            "Copy the template and fill in your brand details."
        )
    with open(BRAND_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Video file extensions to scan
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
