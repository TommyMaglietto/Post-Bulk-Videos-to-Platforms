"""
execute_posting_plan.py — Read the posting plan and post each entry to the correct platform.

Reads .tmp/posting_plan.json, .tmp/video_urls.json, and .tmp/video_metadata.json,
then posts each scheduled entry to Instagram, TikTok, or Facebook.

Supports --dry-run to preview without posting, and resumes after partial failure
by skipping entries already in .tmp/posting_results.json.

Usage:
    python tools/execute_posting_plan.py              # post everything
    python tools/execute_posting_plan.py --dry-run    # preview only
"""

import json
import sys
import time
from datetime import datetime

from config import (
    TMP_DIR, VIDEOS_DIR,
    INSTAGRAM_ACCESS_TOKEN, FACEBOOK_PAGE_ACCESS_TOKEN, TIKTOK_ACCESS_TOKEN,
)
from post_instagram import post_reel as ig_post_reel
from post_tiktok import post_video as tt_post_video
from post_facebook import post_reel as fb_post_reel

POST_DELAY = 30  # seconds between posts


def load_json(path):
    """Load a JSON file or exit with an error."""
    if not path.exists():
        print(f"ERROR: {path} not found.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_item_content(items: list, video_id: str, platform: str) -> dict | None:
    """Look up the caption/hashtags for a video_id + platform combo."""
    for item in items:
        if item["video_id"] == video_id:
            return item.get(platform)
    return None


def check_credentials() -> list[str]:
    """Check which platforms have credentials configured."""
    available = []
    if INSTAGRAM_ACCESS_TOKEN:
        available.append("instagram")
    if TIKTOK_ACCESS_TOKEN:
        available.append("tiktok")
    if FACEBOOK_PAGE_ACCESS_TOKEN:
        available.append("facebook")
    return available


def main():
    dry_run = "--dry-run" in sys.argv

    # Load all data
    plan = load_json(TMP_DIR / "posting_plan.json")
    video_metadata = load_json(TMP_DIR / "video_metadata.json")

    # video_urls.json is optional (only needed for Instagram; may not exist in dry-run)
    urls_path = TMP_DIR / "video_urls.json"
    video_urls = {}
    if urls_path.exists():
        with open(urls_path, "r", encoding="utf-8") as f:
            video_urls = json.load(f)

    items = plan.get("items", [])
    schedule = plan.get("posting_plan", {}).get("recommended_schedule", [])

    if not schedule:
        print("No entries in posting schedule. Nothing to do.")
        sys.exit(0)

    # Load existing results (for resume)
    results_path = TMP_DIR / "posting_results.json"
    existing_results = []
    if results_path.exists():
        with open(results_path, "r", encoding="utf-8") as f:
            existing_results = json.load(f)

    # Build set of already-posted entries for skip logic
    posted_keys = {
        (r["video_id"], r["platform"])
        for r in existing_results
        if r.get("success")
    }

    # Check which platforms are configured
    available_platforms = check_credentials()
    if not dry_run and not available_platforms:
        print("ERROR: No platform credentials configured in .env")
        print("Set at least one of: INSTAGRAM_ACCESS_TOKEN, TIKTOK_ACCESS_TOKEN, FACEBOOK_PAGE_ACCESS_TOKEN")
        sys.exit(1)

    # Build file_name lookup
    file_lookup = {v["video_id"]: v["file_name"] for v in video_metadata}

    if dry_run:
        print("=== DRY RUN — no posts will be made ===\n")
    else:
        print(f"Platforms configured: {', '.join(available_platforms)}\n")

    results = list(existing_results)
    succeeded = 0
    failed = 0
    skipped = 0

    for i, entry in enumerate(schedule):
        vid = entry["video_id"]
        platform = entry["platform"]
        pub_time = entry.get("publish_time_local", "")

        # Skip already posted
        if (vid, platform) in posted_keys:
            print(f"  [{i+1}/{len(schedule)}] SKIP {vid} → {platform} (already posted)")
            skipped += 1
            continue

        # Get content
        content = get_item_content(items, vid, platform)
        if not content:
            print(f"  [{i+1}/{len(schedule)}] SKIP {vid} → {platform} (no content found)")
            skipped += 1
            continue

        caption = content.get("caption", "")
        hashtags = content.get("hashtags", [])
        file_name = file_lookup.get(vid, "")
        video_path = str(VIDEOS_DIR / file_name) if file_name else ""
        s3_url = video_urls.get(vid, "")

        if dry_run:
            print(f"  [{i+1}/{len(schedule)}] {vid} → {platform} @ {pub_time}")
            print(f"    File: {file_name}")
            print(f"    Caption: {caption[:80]}{'...' if len(caption) > 80 else ''}")
            print(f"    Hashtags: {', '.join(hashtags[:5])}")
            print()
            continue

        # Skip if platform not configured
        if platform not in available_platforms:
            print(f"  [{i+1}/{len(schedule)}] SKIP {vid} → {platform} (not configured)")
            skipped += 1
            continue

        print(f"  [{i+1}/{len(schedule)}] Posting {vid} → {platform}...", end=" ", flush=True)

        # Post to the correct platform
        result = None
        if platform == "instagram":
            if not s3_url:
                result = {"success": False, "platform": "instagram",
                          "error": "No S3 URL — run upload_to_s3.py first"}
            else:
                result = ig_post_reel(s3_url, caption, hashtags)
        elif platform == "tiktok":
            if not video_path:
                result = {"success": False, "platform": "tiktok",
                          "error": "No video file path"}
            else:
                result = tt_post_video(video_path, caption, hashtags)
        elif platform == "facebook":
            if not video_path:
                result = {"success": False, "platform": "facebook",
                          "error": "No video file path"}
            else:
                result = fb_post_reel(video_path, caption, hashtags)

        # Log result
        result_entry = {
            "video_id": vid,
            "platform": platform,
            "success": result["success"],
            "posted_at": datetime.now().isoformat(),
            "error": result.get("error"),
        }
        # Copy platform-specific IDs
        if "media_id" in result:
            result_entry["media_id"] = result["media_id"]
        if "publish_id" in result:
            result_entry["publish_id"] = result["publish_id"]
        if platform == "facebook" and "video_id" in result:
            result_entry["fb_video_id"] = result["video_id"]

        results.append(result_entry)

        if result["success"]:
            print("OK")
            succeeded += 1
        else:
            print(f"FAILED: {result['error']}")
            failed += 1

        # Save after each post (so progress is preserved on crash)
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        # Delay between posts
        if i < len(schedule) - 1:
            time.sleep(POST_DELAY)

    # Final summary
    print(f"\n{'=== DRY RUN COMPLETE ===' if dry_run else '=== Posting complete ==='}")
    if not dry_run:
        print(f"  Succeeded: {succeeded}")
        print(f"  Failed: {failed}")
        print(f"  Skipped: {skipped}")
        print(f"  Results: {results_path}")

        if failed > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
