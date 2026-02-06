"""
post_tiktok.py — Post a video to TikTok via the Content Posting API.

Requires TIKTOK_ACCESS_TOKEN in .env.
Uploads the video file directly (FILE_UPLOAD mode).

Note: Unaudited apps can only post as PRIVATE. After TikTok audit approval,
posts will be PUBLIC_TO_EVERYONE.

Usage (standalone test):
    python tools/post_tiktok.py <video_path> "caption text"
"""

import os
import sys
import time

import requests

from config import TIKTOK_ACCESS_TOKEN

TIKTOK_API = "https://open.tiktokapis.com/v2"
POLL_INTERVAL = 5      # seconds between status checks
POLL_TIMEOUT = 300     # max seconds to wait for processing


def post_video(video_path: str, caption: str, hashtags: list[str]) -> dict:
    """
    Post a video to TikTok.

    Args:
        video_path: Local path to the video file
        caption: The caption text
        hashtags: List of hashtags (without #)

    Returns:
        dict with keys: success, platform, publish_id (or error)
    """
    if not TIKTOK_ACCESS_TOKEN:
        return {"success": False, "platform": "tiktok",
                "error": "TIKTOK_ACCESS_TOKEN must be set in .env"}

    if not os.path.exists(video_path):
        return {"success": False, "platform": "tiktok",
                "error": f"Video file not found: {video_path}"}

    file_size = os.path.getsize(video_path)

    # Build full caption with hashtags
    tag_str = " ".join(f"#{t.lstrip('#')}" for t in hashtags)
    full_caption = f"{caption} {tag_str}".strip()

    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    # Step 1: Initialize upload
    init_body = {
        "post_info": {
            "title": full_caption,
            "privacy_level": "PUBLIC_TO_EVERYONE",
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": file_size,
            "total_chunk_count": 1,
        },
    }

    init_resp = requests.post(
        f"{TIKTOK_API}/post/publish/video/init/",
        headers=headers,
        json=init_body,
    )

    if init_resp.status_code != 200:
        return {"success": False, "platform": "tiktok",
                "error": f"Init failed ({init_resp.status_code}): {init_resp.text}"}

    init_data = init_resp.json()
    if init_data.get("error", {}).get("code") != "ok":
        return {"success": False, "platform": "tiktok",
                "error": f"Init error: {init_data}"}

    publish_id = init_data["data"]["publish_id"]
    upload_url = init_data["data"]["upload_url"]

    # Step 2: Upload video file (streamed — avoids loading entire file into RAM)
    upload_headers = {
        "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
        "Content-Type": "video/mp4",
        "Content-Length": str(file_size),
    }

    with open(video_path, "rb") as f:
        upload_resp = requests.put(upload_url, headers=upload_headers, data=f)

    if upload_resp.status_code not in (200, 201):
        return {"success": False, "platform": "tiktok",
                "error": f"Upload failed ({upload_resp.status_code}): {upload_resp.text}"}

    # Step 3: Poll for completion
    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        status_resp = requests.post(
            f"{TIKTOK_API}/post/publish/status/fetch/",
            headers=headers,
            json={"publish_id": publish_id},
        )

        if status_resp.status_code == 200:
            status_data = status_resp.json()
            status = status_data.get("data", {}).get("status", "")

            if status == "PUBLISH_COMPLETE":
                return {"success": True, "platform": "tiktok", "publish_id": publish_id}
            elif status in ("FAILED", "PUBLISH_FAILED"):
                fail_reason = status_data.get("data", {}).get("fail_reason", "unknown")
                return {"success": False, "platform": "tiktok",
                        "error": f"Publish failed: {fail_reason}"}

        time.sleep(POLL_INTERVAL)

    return {"success": False, "platform": "tiktok",
            "error": f"Publish timed out after {POLL_TIMEOUT}s"}


def main():
    if len(sys.argv) < 3:
        print("Usage: python tools/post_tiktok.py <video_path> \"caption\"")
        sys.exit(1)

    video_path = sys.argv[1]
    caption = sys.argv[2]
    hashtags = sys.argv[3:] if len(sys.argv) > 3 else []

    print(f"Posting video to TikTok...")
    result = post_video(video_path, caption, hashtags)

    if result["success"]:
        print(f"Success! Publish ID: {result['publish_id']}")
    else:
        print(f"Failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
