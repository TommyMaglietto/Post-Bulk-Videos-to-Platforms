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
# AWS S3
# ---------------------------------------------------------------------------
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "")
AWS_S3_REGION = os.getenv("AWS_S3_REGION", "us-east-1")

# ---------------------------------------------------------------------------
# Instagram (Meta Graph API)
# ---------------------------------------------------------------------------
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

# ---------------------------------------------------------------------------
# Facebook (Meta Graph API)
# ---------------------------------------------------------------------------
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")

# ---------------------------------------------------------------------------
# TikTok (Content Posting API)
# ---------------------------------------------------------------------------
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

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
