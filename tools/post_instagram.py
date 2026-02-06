"""
post_instagram.py — Post a Reel to Instagram via the Meta Graph API.

Requires INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN in .env.
The video must be hosted at a public URL (use upload_to_s3.py first).

Usage (standalone test):
    python tools/post_instagram.py <video_url> "caption text" "#tag1" "#tag2"
"""

import sys
import time

import requests

from config import INSTAGRAM_USER_ID, INSTAGRAM_ACCESS_TOKEN

GRAPH_API = "https://graph.instagram.com"
POLL_INTERVAL = 5      # seconds between status checks
POLL_TIMEOUT = 300     # max seconds to wait for processing


def post_reel(video_url: str, caption: str, hashtags: list[str]) -> dict:
    """
    Post a Reel to Instagram.

    Args:
        video_url: Public URL of the video (e.g. S3 URL)
        caption: The caption text
        hashtags: List of hashtags (without #)

    Returns:
        dict with keys: success, platform, media_id (or error)
    """
    if not INSTAGRAM_USER_ID or not INSTAGRAM_ACCESS_TOKEN:
        return {"success": False, "platform": "instagram",
                "error": "INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN must be set in .env"}

    # Build full caption with hashtags
    tag_str = " ".join(f"#{t.lstrip('#')}" for t in hashtags)
    full_caption = f"{caption}\n\n{tag_str}".strip()

    # Step 1: Create media container
    resp = requests.post(
        f"{GRAPH_API}/{INSTAGRAM_USER_ID}/media",
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": full_caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
    )

    if resp.status_code != 200:
        return {"success": False, "platform": "instagram",
                "error": f"Container creation failed: {resp.text}"}

    container_id = resp.json().get("id")
    if not container_id:
        return {"success": False, "platform": "instagram",
                "error": f"No container ID returned: {resp.json()}"}

    # Step 2: Poll until container is ready
    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        status_resp = requests.get(
            f"{GRAPH_API}/{container_id}",
            params={
                "fields": "status_code",
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            },
        )
        status = status_resp.json().get("status_code", "")

        if status == "FINISHED":
            break
        elif status == "ERROR":
            return {"success": False, "platform": "instagram",
                    "error": f"Container processing failed: {status_resp.json()}"}

        time.sleep(POLL_INTERVAL)
    else:
        return {"success": False, "platform": "instagram",
                "error": f"Container processing timed out after {POLL_TIMEOUT}s"}

    # Step 3: Publish
    pub_resp = requests.post(
        f"{GRAPH_API}/{INSTAGRAM_USER_ID}/media_publish",
        params={
            "creation_id": container_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
    )

    if pub_resp.status_code != 200:
        return {"success": False, "platform": "instagram",
                "error": f"Publish failed: {pub_resp.text}"}

    media_id = pub_resp.json().get("id")
    return {"success": True, "platform": "instagram", "media_id": media_id}


def main():
    if len(sys.argv) < 3:
        print("Usage: python tools/post_instagram.py <video_url> \"caption\" [hashtags...]")
        sys.exit(1)

    video_url = sys.argv[1]
    caption = sys.argv[2]
    hashtags = sys.argv[3:] if len(sys.argv) > 3 else []

    print(f"Posting Reel to Instagram...")
    result = post_reel(video_url, caption, hashtags)

    if result["success"]:
        print(f"Success! Media ID: {result['media_id']}")
    else:
        print(f"Failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
