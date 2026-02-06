"""
scan_videos.py — Scan the videos/ folder, extract metadata, randomly select a batch.

Writes .tmp/video_metadata.json with the selected videos.

Usage:
    python tools/scan_videos.py
"""

import json
import random
import subprocess
import sys
from pathlib import Path

from config import VIDEOS_DIR, TMP_DIR, VIDEO_EXTENSIONS, load_brand_config


def get_duration(file_path: Path) -> float | None:
    """Try to get video duration in seconds via ffprobe. Returns None if unavailable."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return round(float(data["format"]["duration"]), 1)
    except (FileNotFoundError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired):
        pass
    return None


def scan_and_select() -> list[dict]:
    """Scan videos/ folder and randomly select a batch."""
    brand = load_brand_config()
    batch_size = brand.get("videos_per_batch", 15)

    # Find all video files
    all_videos = [
        f for f in VIDEOS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
    ]

    if not all_videos:
        print(f"No videos found in {VIDEOS_DIR}/")
        print(f"Drop .mp4/.mov/.avi/.mkv/.webm files there and re-run.")
        return []

    print(f"Found {len(all_videos)} video(s) in {VIDEOS_DIR}/")

    # Randomly select up to batch_size
    selected = random.sample(all_videos, min(batch_size, len(all_videos)))
    print(f"Selected {len(selected)} video(s) for this batch.")

    # Build metadata
    metadata = []
    for i, vf in enumerate(selected, start=1):
        size_mb = round(vf.stat().st_size / (1024 * 1024), 1)
        duration = get_duration(vf)

        metadata.append({
            "video_id": f"v{i:03d}",
            "file_name": vf.name,
            "file_size_mb": size_mb,
            "duration_seconds": duration,
            "topic": "",
            "transcript_optional": "",
            "notes_optional": "",
        })

        dur_str = f"{duration}s" if duration else "unknown duration"
        print(f"  {vf.name} ({size_mb} MB, {dur_str})")

    return metadata


def main():
    metadata = scan_and_select()
    if not metadata:
        sys.exit(1)

    out_path = TMP_DIR / "video_metadata.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nVideo metadata written to {out_path}")


if __name__ == "__main__":
    main()
