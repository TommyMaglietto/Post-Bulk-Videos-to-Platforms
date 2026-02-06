"""
generate_posting_plan.py — Generate platform-tailored captions, hashtags, and a posting schedule.

Reads .tmp/video_metadata.json and brand_config.json, calls OpenAI GPT-4o,
and writes the final posting plan to .tmp/posting_plan.json.

Usage:
    python tools/generate_posting_plan.py
"""

import json
import sys

from openai import OpenAI

from config import OPENAI_API_KEY, TMP_DIR, load_brand_config

SYSTEM_PROMPT = """\
You are a social video publishing assistant.

Goal
Create platform tailored titles, captions, and hashtags for a batch of short form videos, then produce a safe posting plan that my automation can execute through official platform APIs (Instagram, TikTok, Facebook).

Important constraints
1) Output must be valid JSON only. No extra text.
2) Never claim you posted anything. You only generate copy and a posting plan.
3) Follow platform rules and avoid spam patterns:
   A) Do not reuse the exact same caption across platforms.
   B) Vary hooks and calls to action across videos.
   C) Avoid repetitive hashtag sets. Keep hashtags relevant.
   D) Respect reasonable volume: stagger publish times, do not schedule many posts at the exact same minute.
   E) Keep language natural and human.
4) If info is missing, make conservative assumptions and keep captions generic rather than inventing specifics.
5) Avoid prohibited content, harassment, misleading claims, or anything that could violate community guidelines.

Platform rules to follow
Instagram Reels: caption up to 2200 chars, suggest 5 to 12 hashtags
TikTok: short caption, suggest 3 to 6 hashtags
Facebook Reels: friendly caption, suggest 3 to 8 hashtags

Required JSON output schema
{
  "batch_summary": {
    "overall_theme": "",
    "tone_notes": ""
  },
  "items": [
    {
      "video_id": "",
      "instagram": {
        "title": "",
        "caption": "",
        "hashtags": ["", ""]
      },
      "tiktok": {
        "caption": "",
        "hashtags": ["", ""]
      },
      "facebook": {
        "caption": "",
        "hashtags": ["", ""]
      }
    }
  ],
  "posting_plan": {
    "strategy": "Upload via official APIs, schedule staggered publish times, and include a final human approval step before publish.",
    "recommended_schedule": [
      {
        "video_id": "",
        "platform": "instagram|tiktok|facebook",
        "publish_time_local": "YYYY-MM-DD HH:MM",
        "notes": ""
      }
    ],
    "compliance_checks": [
      "Confirm account is authorized via official API and permissions are valid",
      "Confirm rate limits are respected",
      "Confirm captions and hashtags are not duplicated in bulk",
      "Confirm final approval is recorded before publish"
    ]
  }
}

Now generate the JSON."""


def build_user_message(brand: dict, videos: list[dict]) -> str:
    """Build the user message with brand config and video metadata filled in."""
    lines = [
        "Inputs",
        f"Brand voice: {brand.get('brand_voice', 'not specified')}",
        f"Audience: {brand.get('audience', 'not specified')}",
        f"Niche: {brand.get('niche', 'not specified')}",
        f"Call to action style: {brand.get('cta_style', 'not specified')}",
        f"Hashtag style: {brand.get('hashtag_style', 'not specified')}",
        f"Banned words or topics: {brand.get('banned_list', 'none')}",
        "",
        f"Videos (batch of {len(videos)}):",
        json.dumps(videos, indent=2),
        "",
        f"Timezone for scheduling: {brand.get('timezone', 'America/New_York')}",
        f"Posts per day: {brand.get('posts_per_day', 3)}",
        f"Start date: {brand.get('start_date', 'auto')}",
        "",
        "Now generate the JSON.",
    ]
    return "\n".join(lines)


def call_openai(system: str, user: str) -> dict:
    """Call OpenAI GPT-4o with JSON mode and return parsed dict."""
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set in .env")
        print("Add your key: OPENAI_API_KEY=sk-...")
        sys.exit(1)

    client = OpenAI(api_key=OPENAI_API_KEY)

    print("Calling OpenAI GPT-4o...")
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content
    tokens = response.usage
    print(f"Tokens used — prompt: {tokens.prompt_tokens}, completion: {tokens.completion_tokens}")

    return json.loads(content)


def validate_plan(plan: dict, video_count: int) -> list[str]:
    """Run basic validation on the generated plan. Returns list of warnings."""
    warnings = []

    items = plan.get("items", [])
    if len(items) != video_count:
        warnings.append(f"Expected {video_count} items, got {len(items)}")

    for item in items:
        vid = item.get("video_id", "?")

        # Check Instagram hashtag count
        ig_tags = item.get("instagram", {}).get("hashtags", [])
        if len(ig_tags) < 5 or len(ig_tags) > 12:
            warnings.append(f"{vid}: Instagram has {len(ig_tags)} hashtags (expected 5-12)")

        # Check TikTok hashtag count
        tt_tags = item.get("tiktok", {}).get("hashtags", [])
        if len(tt_tags) < 3 or len(tt_tags) > 6:
            warnings.append(f"{vid}: TikTok has {len(tt_tags)} hashtags (expected 3-6)")

        # Check Facebook hashtag count
        fb_tags = item.get("facebook", {}).get("hashtags", [])
        if len(fb_tags) < 3 or len(fb_tags) > 8:
            warnings.append(f"{vid}: Facebook has {len(fb_tags)} hashtags (expected 3-8)")

        # Check Instagram caption length
        ig_caption = item.get("instagram", {}).get("caption", "")
        if len(ig_caption) > 2200:
            warnings.append(f"{vid}: Instagram caption is {len(ig_caption)} chars (max 2200)")

        # Check captions are different across platforms
        captions = [
            item.get("instagram", {}).get("caption", ""),
            item.get("tiktok", {}).get("caption", ""),
            item.get("facebook", {}).get("caption", ""),
        ]
        if len(set(captions)) < 3:
            warnings.append(f"{vid}: Duplicate captions detected across platforms")

    # Check schedule exists
    schedule = plan.get("posting_plan", {}).get("recommended_schedule", [])
    if not schedule:
        warnings.append("No posting schedule generated")

    # Check for same-minute posts
    times = [entry.get("publish_time_local", "") for entry in schedule]
    if len(times) != len(set(times)):
        warnings.append("Schedule has duplicate publish times")

    return warnings


def main():
    # Load video metadata
    metadata_path = TMP_DIR / "video_metadata.json"
    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found. Run scan_videos.py first.")
        sys.exit(1)

    with open(metadata_path, "r", encoding="utf-8") as f:
        videos = json.load(f)

    if not videos:
        print("No videos in metadata. Nothing to generate.")
        sys.exit(0)

    # Load brand config
    brand = load_brand_config()

    # Build prompt and call API
    user_msg = build_user_message(brand, videos)
    plan = call_openai(SYSTEM_PROMPT, user_msg)

    # Validate
    warnings = validate_plan(plan, len(videos))
    if warnings:
        print(f"\nValidation warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("Validation passed — all checks OK.")

    # Save output
    out_path = TMP_DIR / "posting_plan.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    print(f"\nPosting plan written to {out_path}")
    print(f"Videos: {len(plan.get('items', []))}")
    schedule = plan.get("posting_plan", {}).get("recommended_schedule", [])
    if schedule:
        first = schedule[0].get("publish_time_local", "?")
        last = schedule[-1].get("publish_time_local", "?")
        print(f"Schedule: {first} → {last} ({len(schedule)} posts)")


if __name__ == "__main__":
    main()
