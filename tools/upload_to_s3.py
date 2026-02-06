"""
upload_to_s3.py — Upload batch videos to S3 for Instagram API access.

Reads .tmp/video_metadata.json, uploads each video to S3 with public-read ACL,
and writes .tmp/video_urls.json mapping video_id → public S3 URL.

Usage:
    python tools/upload_to_s3.py
"""

import json
import mimetypes
import sys
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError

from config import (
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET, AWS_S3_REGION,
    TMP_DIR, VIDEOS_DIR,
)


def get_s3_client():
    """Create and return an S3 client."""
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print("ERROR: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set in .env")
        sys.exit(1)
    if not AWS_S3_BUCKET:
        print("ERROR: AWS_S3_BUCKET must be set in .env")
        sys.exit(1)

    return boto3.client(
        "s3",
        region_name=AWS_S3_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


def file_exists_on_s3(client, key: str) -> bool:
    """Check if a file already exists in the S3 bucket."""
    try:
        client.head_object(Bucket=AWS_S3_BUCKET, Key=key)
        return True
    except ClientError:
        return False


def upload_video(client, file_path, s3_key: str) -> str:
    """Upload a single video to S3 and return the public URL."""
    content_type = mimetypes.guess_type(str(file_path))[0] or "video/mp4"

    client.upload_file(
        str(file_path),
        AWS_S3_BUCKET,
        s3_key,
        ExtraArgs={"ContentType": content_type},
    )

    return f"https://{AWS_S3_BUCKET}.s3.{AWS_S3_REGION}.amazonaws.com/{quote(s3_key)}"


def main():
    # Load video metadata
    metadata_path = TMP_DIR / "video_metadata.json"
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run scan_videos.py first.")
        sys.exit(1)

    with open(metadata_path, "r", encoding="utf-8") as f:
        videos = json.load(f)

    if not videos:
        print("No videos in metadata. Nothing to upload.")
        sys.exit(0)

    # Load existing URLs (for resume/skip)
    urls_path = TMP_DIR / "video_urls.json"
    existing_urls = {}
    if urls_path.exists():
        with open(urls_path, "r", encoding="utf-8") as f:
            existing_urls = json.load(f)

    client = get_s3_client()
    video_urls = dict(existing_urls)
    uploaded = 0
    skipped = 0

    print(f"Uploading {len(videos)} video(s) to S3 bucket '{AWS_S3_BUCKET}'...\n")

    for video in videos:
        vid = video["video_id"]
        file_name = video["file_name"]
        file_path = VIDEOS_DIR / file_name
        s3_key = f"videos/{file_name}"

        if not file_path.exists():
            print(f"  SKIP {file_name} — file not found in videos/")
            continue

        # Skip if already uploaded
        if vid in existing_urls:
            print(f"  SKIP {file_name} — already uploaded")
            skipped += 1
            continue

        # Check S3 too
        if file_exists_on_s3(client, s3_key):
            url = f"https://{AWS_S3_BUCKET}.s3.{AWS_S3_REGION}.amazonaws.com/{s3_key}"
            video_urls[vid] = url
            print(f"  SKIP {file_name} — already on S3")
            skipped += 1
            continue

        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"  Uploading {file_name} ({size_mb:.1f} MB)...", end=" ", flush=True)

        url = upload_video(client, file_path, s3_key)
        video_urls[vid] = url
        uploaded += 1
        print("done")

    # Save URLs
    with open(urls_path, "w", encoding="utf-8") as f:
        json.dump(video_urls, f, indent=2)

    print(f"\nS3 upload complete: {uploaded} uploaded, {skipped} skipped")
    print(f"Video URLs written to {urls_path}")


if __name__ == "__main__":
    main()
