# Post-Bulk-Videos-to-Platforms

An automated pipeline that selects random videos from a folder, generates platform-specific titles, captions, and hashtags using AI, then posts them to Instagram Reels, TikTok, and Facebook Reels via official APIs — all with a single command.

## How It Works

```
videos/ folder          .tmp/video_metadata.json     .tmp/posting_plan.json
  15 random videos  -->   file names, sizes,     -->   captions, hashtags,
  selected from pool      durations extracted          schedule generated
                                                       by GPT-4o
                                                            |
                                                            v
.tmp/posting_results.json   <--  post to each    <--  .tmp/video_urls.json
  success/failure log            platform via          videos uploaded
  per post                       official APIs         to S3
```

**Step 1 — Scan:** Finds all video files in `videos/`, randomly picks a batch (default 15), extracts metadata.

**Step 2 — Generate:** Sends video metadata + your brand config to OpenAI GPT-4o. Returns platform-tailored captions, hashtags, and a staggered posting schedule — all as validated JSON.

**Step 3 — Upload to S3:** Uploads the batch to AWS S3 so Instagram's API can access them (Instagram requires a public URL; TikTok and Facebook accept direct file uploads).

**Step 4 — Post:** Iterates through the schedule and posts each video to the correct platform with 30-second delays between posts. Logs every result. Supports resume if interrupted.

## Quick Start

### 1. Install dependencies
```
pip install -r requirements.txt
```

### 2. Configure credentials

Copy your API keys into `.env`:
```env
OPENAI_API_KEY=sk-...

AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=your-bucket-name
AWS_S3_REGION=us-east-1

INSTAGRAM_USER_ID=17841...
INSTAGRAM_ACCESS_TOKEN=EAAx...

FACEBOOK_PAGE_ID=123456...
FACEBOOK_PAGE_ACCESS_TOKEN=EAAx...

TIKTOK_CLIENT_KEY=aw...
TIKTOK_CLIENT_SECRET=...
TIKTOK_ACCESS_TOKEN=act...
```

### 3. Configure your brand

Edit `brand_config.json` with your brand details:
```json
{
  "brand_voice": "inspirational, grounded, relatable",
  "audience": "young adults interested in personal growth",
  "niche": "faith and motivation",
  "cta_style": "soft — invite, don't push",
  "hashtag_style": "mix of broad and niche tags",
  "banned_list": "profanity, political topics",
  "videos_per_batch": 15,
  "timezone": "America/New_York",
  "posts_per_day": 3,
  "start_date": "auto"
}
```

### 4. Add videos

Drop `.mp4`, `.mov`, `.avi`, `.mkv`, or `.webm` files into the `videos/` folder.

### 5. Run

```bash
# Full pipeline — generate captions and post everything
python tools/run_pipeline.py

# Or split into two steps (recommended — review before posting)
python tools/run_pipeline.py --generate-only    # scan + generate plan
# Review .tmp/posting_plan.json
python tools/run_pipeline.py --post-only         # upload + post

# Preview what would be posted without actually posting
python tools/run_pipeline.py --dry-run
```

## Project Structure

```
AllPlatFormPosting/
├── .env                             # API keys (gitignored)
├── brand_config.json                # Brand voice, audience, niche, CTA style
├── requirements.txt                 # Python dependencies
├── videos/                          # Drop video files here (gitignored)
│   └── .gitkeep
├── .tmp/                            # Pipeline intermediate files (gitignored)
│   ├── video_metadata.json          # Scanned video info
│   ├── posting_plan.json            # AI-generated captions + schedule
│   ├── video_urls.json              # S3 public URLs
│   └── posting_results.json         # Post success/failure log
├── tools/
│   ├── config.py                    # Central config — loads .env + brand_config.json
│   ├── scan_videos.py               # Scans videos/, picks random batch
│   ├── generate_posting_plan.py     # Calls GPT-4o for captions/hashtags/schedule
│   ├── upload_to_s3.py              # Uploads videos to AWS S3
│   ├── post_instagram.py            # Posts Reels via Meta Graph API
│   ├── post_tiktok.py               # Posts videos via TikTok Content Posting API
│   ├── post_facebook.py             # Posts Reels via Meta Graph API
│   ├── execute_posting_plan.py      # Reads plan, posts to each platform
│   └── run_pipeline.py              # Single entry point — orchestrates everything
├── workflows/
│   └── social_video_publishing.md   # Full SOP with setup guides
└── CLAUDE.md                        # AI agent instructions (WAT framework)
```

## Pipeline Modes

| Command | What it does |
|---|---|
| `python tools/run_pipeline.py` | Full pipeline: scan, generate, upload, post |
| `python tools/run_pipeline.py --generate-only` | Steps 1-2 only: scan + generate captions |
| `python tools/run_pipeline.py --post-only` | Steps 3-4 only: upload to S3 + post |
| `python tools/run_pipeline.py --dry-run` | Full pipeline but prints posts without sending |

## Platform Details

| Platform | API | Upload Method | Rate Limit |
|---|---|---|---|
| Instagram Reels | Meta Graph API | Public URL (via S3) | 100 posts/24hrs |
| TikTok | Content Posting API | Direct file upload | 15 posts/24hrs |
| Facebook Reels | Meta Graph API | Direct file upload | 25 posts/day |

## Content Generation Rules

The AI follows these constraints when generating captions:
- Captions differ across platforms for the same video
- Hashtag sets vary between videos (no repetitive copy-paste)
- Hooks and calls-to-action are varied across the batch
- Publish times are staggered (no same-minute posts)
- Instagram: up to 2200 chars, 5-12 hashtags
- TikTok: short caption, 3-6 hashtags
- Facebook: friendly caption, 3-8 hashtags

## Platform Setup

Each platform requires its own developer account and API credentials. Full step-by-step setup instructions are in [`workflows/social_video_publishing.md`](workflows/social_video_publishing.md), covering:

- **AWS S3** — Creating a bucket with public read access for video hosting
- **Instagram** — Meta developer app, Business account, content publishing permissions
- **Facebook** — Page access token, post management permissions
- **TikTok** — Developer app, Content Posting API access, audit process for public posting

## Safety Features

- **Dry run mode** — Preview every post before sending
- **Two-step workflow** — Generate plan first, review it, then post
- **Resume on failure** — If the pipeline crashes mid-posting, re-run picks up where it left off
- **Validation** — Checks hashtag counts, caption lengths, and duplicate captions before posting
- **Rate limit awareness** — 30-second delay between posts, per-platform limits documented
- **Videos gitignored** — Video files never get pushed to remote repos

## Architecture

Built on the **WAT framework** (Workflows, Agents, Tools):
- **Workflows** — Markdown SOPs defining what to do and how
- **Agents** — AI handles reasoning, orchestration, and content generation
- **Tools** — Deterministic Python scripts handle API calls and file operations

This separation keeps AI focused on creative decisions while execution stays reliable and testable.
