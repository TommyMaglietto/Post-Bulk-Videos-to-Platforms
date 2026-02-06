# Social Video Publishing Workflow

## Objective

Generate platform-tailored titles, captions, hashtags, and a staggered posting schedule for a batch of short-form videos targeting Instagram Reels, TikTok, and Facebook Reels. Output is a JSON posting plan ready for automation or human review.

## Prerequisites

- [ ] `.env` populated with `OPENAI_API_KEY`
- [ ] `brand_config.json` filled in with brand voice, audience, niche, etc.
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Video files dropped into `videos/` folder

## Required Inputs

| Variable | Source | Required |
|---|---|---|
| OPENAI_API_KEY | .env | Yes |
| brand_voice | brand_config.json | Yes |
| audience | brand_config.json | Yes |
| niche | brand_config.json | Yes |
| cta_style | brand_config.json | Recommended |
| hashtag_style | brand_config.json | Recommended |
| banned_list | brand_config.json | Optional |
| videos_per_batch | brand_config.json | Optional (default 15) |
| timezone | brand_config.json | Optional (default America/New_York) |
| posts_per_day | brand_config.json | Optional (default 3) |
| start_date | brand_config.json | Optional (default "auto" = tomorrow) |

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/scan_videos.py` | Scans `videos/` folder, extracts metadata, randomly selects batch |
| `tools/generate_posting_plan.py` | Calls OpenAI GPT-4o to generate captions, hashtags, and schedule |
| `tools/run_pipeline.py` | Runs all steps in order (single entry point) |
| `tools/config.py` | Central configuration, loaded by all tools |

## Execution

```
python tools/run_pipeline.py
```

Pipeline steps (in order, stops on failure):
1. **scan_videos.py** — scans `videos/`, randomly selects up to `videos_per_batch`, writes `.tmp/video_metadata.json`
2. **generate_posting_plan.py** — reads video metadata + brand config, calls GPT-4o, validates output, writes `.tmp/posting_plan.json`

## Output

Final JSON is saved to `.tmp/posting_plan.json` with this structure:
- `batch_summary` — overall theme and tone notes
- `items[]` — per-video content for each platform (Instagram, TikTok, Facebook)
- `posting_plan` — staggered schedule, strategy notes, compliance checks

## Configuration

All brand settings are in `brand_config.json`:

| Setting | Default | Purpose |
|---|---|---|
| brand_voice | (required) | Tone and personality of captions |
| audience | (required) | Target audience description |
| niche | (required) | Content niche/category |
| cta_style | (recommended) | Style of calls-to-action |
| hashtag_style | (recommended) | Hashtag strategy preferences |
| banned_list | (optional) | Words or topics to avoid |
| videos_per_batch | 15 | How many videos per batch |
| timezone | America/New_York | Timezone for schedule |
| posts_per_day | 3 | Max posts per day in schedule |
| start_date | auto | Schedule start (auto = tomorrow) |

## Platform Rules (Enforced by Prompt)

| Platform | Caption Limit | Hashtags |
|---|---|---|
| Instagram Reels | 2200 chars | 5–12 |
| TikTok | Short | 3–6 |
| Facebook Reels | Friendly tone | 3–8 |

## Anti-Spam Rules (Enforced by Prompt + Validation)

- Captions differ across platforms for the same video
- Hashtag sets vary between videos (no copy-paste)
- Hooks and CTAs are varied across the batch
- Publish times are staggered (no same-minute posts)
- Language is natural and human

## Edge Cases

| Scenario | Behavior |
|---|---|
| No videos in folder | Pipeline exits cleanly with message |
| Fewer videos than batch size | Uses all available videos |
| ffprobe not installed | Duration is set to null, everything else works |
| OPENAI_API_KEY missing | Pipeline stops with clear error message |
| brand_config.json missing | Pipeline stops with clear error message |
| GPT returns invalid JSON | Should not happen (JSON mode), but caught by json.loads |
| Hashtag counts out of range | Validation warns but still saves output |
| Duplicate captions detected | Validation warns but still saves output |

## Change Log

| Date | What Changed |
|---|---|
| 2026-02-05 | Initial workflow created |
