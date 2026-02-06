"""
post_facebook.py — Post a Reel to a Facebook Page via the Meta Graph API.

Requires FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN in .env.
Uploads the video file directly (no public URL needed).

Usage (standalone test):
    python tools/post_facebook.py <video_path> "caption text" "#tag1" "#tag2"
"""

import os
import sys
import time

import requests

from config import FACEBOOK_PAGE_ID, FACEBOOK_PAGE_ACCESS_TOKEN

GRAPH_API = "https://graph.facebook.com/v22.0"
RUPLOAD_API = "https://rupload.facebook.com/video-upload/v22.0"
POLL_INTERVAL = 5      # seconds between status checks
POLL_TIMEOUT = 300     # max seconds to wait for processing


def post_reel(video_path: str, caption: str, hashtags: list[str]) -> dict:
    """
    Post a Reel to a Facebook Page.

    Args:
        video_path: Local path to the video file
        caption: The caption text
        hashtags: List of hashtags (without #)

    Returns:
        dict with keys: success, platform, video_id (or error)
    """
    if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
        return {"success": False, "platform": "facebook",
                "error": "FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN must be set in .env"}

    if not os.path.exists(video_path):
        return {"success": False, "platform": "facebook",
                "error": f"Video file not found: {video_path}"}

    file_size = os.path.getsize(video_path)

    # Build full caption with hashtags
    tag_str = " ".join(f"#{t.lstrip('#')}" for t in hashtags)
    full_caption = f"{caption}\n\n{tag_str}".strip()

    # Step 1: Initialize upload
    init_resp = requests.post(
        f"{GRAPH_API}/{FACEBOOK_PAGE_ID}/video_reels",
        params={
            "upload_phase": "start",
            "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
        },
    )

    if init_resp.status_code != 200:
        return {"success": False, "platform": "facebook",
                "error": f"Init failed: {init_resp.text}"}

    video_id = init_resp.json().get("video_id")
    if not video_id:
        return {"success": False, "platform": "facebook",
                "error": f"No video_id returned: {init_resp.json()}"}

    # Step 2: Upload video binary (streamed — avoids loading entire file into RAM)
    with open(video_path, "rb") as f:
        upload_resp = requests.post(
            f"{RUPLOAD_API}/{video_id}",
            headers={
                "Authorization": f"OAuth {FACEBOOK_PAGE_ACCESS_TOKEN}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream",
            },
            data=f,
        )

    if upload_resp.status_code != 200:
        return {"success": False, "platform": "facebook",
                "error": f"Upload failed: {upload_resp.text}"}

    # Step 3: Finish upload and publish
    finish_resp = requests.post(
        f"{GRAPH_API}/{FACEBOOK_PAGE_ID}/video_reels",
        params={
            "upload_phase": "finish",
            "video_id": video_id,
            "description": full_caption,
            "video_state": "PUBLISHED",
            "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
        },
    )

    if finish_resp.status_code != 200:
        return {"success": False, "platform": "facebook",
                "error": f"Finish/publish failed: {finish_resp.text}"}

    # Step 4: Verify status
    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        status_resp = requests.get(
            f"{GRAPH_API}/{video_id}",
            params={
                "fields": "status",
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
            },
        )

        if status_resp.status_code == 200:
            status = status_resp.json().get("status", {})
            publishing_phase = status.get("publishing_phase", {})
            if publishing_phase.get("status") == "complete":
                return {"success": True, "platform": "facebook", "video_id": video_id}
            elif publishing_phase.get("status") == "error":
                return {"success": False, "platform": "facebook",
                        "error": f"Publishing error: {status}"}

        time.sleep(POLL_INTERVAL)

    # If we get here, assume success since finish returned 200
    return {"success": True, "platform": "facebook", "video_id": video_id}


def main():
    if len(sys.argv) < 3:
        print("Usage: python tools/post_facebook.py <video_path> \"caption\" [hashtags...]")
        sys.exit(1)

    video_path = sys.argv[1]
    caption = sys.argv[2]
    hashtags = sys.argv[3:] if len(sys.argv) > 3 else []

    print(f"Posting Reel to Facebook Page...")
    result = post_reel(video_path, caption, hashtags)

    if result["success"]:
        print(f"Success! Video ID: {result['video_id']}")
    else:
        print(f"Failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
