# Social Video Publishing Workflow

## Objective

Generate platform-tailored titles, captions, hashtags, and a staggered posting schedule for a batch of short-form videos, then upload and post them to Instagram Reels, TikTok, and Facebook Reels via official APIs.

## Prerequisites

- [ ] `.env` populated with `OPENAI_API_KEY`
- [ ] `.env` populated with AWS S3 credentials
- [ ] `.env` populated with platform credentials (Instagram, TikTok, Facebook)
- [ ] `brand_config.json` filled in with brand voice, audience, niche, etc.
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Video files dropped into `videos/` folder
- [ ] Platform developer apps created and approved (see Platform Setup below)

## Required Inputs

| Variable | Source | Required |
|---|---|---|
| OPENAI_API_KEY | .env | Yes |
| AWS_ACCESS_KEY_ID | .env | Yes (for Instagram) |
| AWS_SECRET_ACCESS_KEY | .env | Yes (for Instagram) |
| AWS_S3_BUCKET | .env | Yes (for Instagram) |
| INSTAGRAM_USER_ID | .env | For Instagram posting |
| INSTAGRAM_ACCESS_TOKEN | .env | For Instagram posting |
| FACEBOOK_PAGE_ID | .env | For Facebook posting |
| FACEBOOK_PAGE_ACCESS_TOKEN | .env | For Facebook posting |
| TIKTOK_CLIENT_KEY | .env | For TikTok posting |
| TIKTOK_ACCESS_TOKEN | .env | For TikTok posting |
| brand_voice | brand_config.json | Yes |
| audience | brand_config.json | Yes |
| niche | brand_config.json | Yes |

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/config.py` | Central configuration, loaded by all tools |
| `tools/scan_videos.py` | Scans `videos/`, extracts metadata, randomly selects batch |
| `tools/generate_posting_plan.py` | Calls GPT-4o to generate captions, hashtags, and schedule |
| `tools/upload_to_s3.py` | Uploads batch videos to S3 (needed for Instagram API) |
| `tools/post_instagram.py` | Posts a Reel to Instagram via Meta Graph API |
| `tools/post_tiktok.py` | Posts a video to TikTok via Content Posting API |
| `tools/post_facebook.py` | Posts a Reel to Facebook Page via Meta Graph API |
| `tools/execute_posting_plan.py` | Reads plan JSON, posts each entry to correct platform |
| `tools/run_pipeline.py` | Orchestrates all steps (single entry point) |

## Execution

### Full pipeline (generate + post)
```
python tools/run_pipeline.py
```

### Two-step workflow (recommended — review before posting)
```
python tools/run_pipeline.py --generate-only    # Step 1: scan + generate plan
# Review .tmp/posting_plan.json
python tools/run_pipeline.py --post-only         # Step 2: upload + post
```

### Dry run (preview what would be posted)
```
python tools/run_pipeline.py --dry-run
```

### Pipeline steps
1. **scan_videos.py** — scans `videos/`, randomly selects batch, writes `.tmp/video_metadata.json`
2. **generate_posting_plan.py** — calls GPT-4o, validates output, writes `.tmp/posting_plan.json`
3. **upload_to_s3.py** — uploads videos to S3, writes `.tmp/video_urls.json`
4. **execute_posting_plan.py** — posts to each platform with 30s delays, writes `.tmp/posting_results.json`

## Output Files

| File | Contents |
|---|---|
| `.tmp/video_metadata.json` | Scanned video metadata |
| `.tmp/posting_plan.json` | Generated captions, hashtags, schedule |
| `.tmp/video_urls.json` | S3 public URLs per video |
| `.tmp/posting_results.json` | Success/failure log per post |

## Platform Rate Limits

| Platform | Limit | Notes |
|---|---|---|
| Instagram | 100 posts/24hrs | Includes Reels + Feed + Stories combined |
| TikTok | 15 posts/24hrs | Unaudited apps: private posts only |
| Facebook | 25 posts/day | 200 API calls/hour |

## Platform Setup Guide

### AWS S3 (required for Instagram)

1. Create an AWS account at https://aws.amazon.com
2. Go to S3 console → Create bucket
   - Name: something like `your-brand-videos`
   - Region: `us-east-1` (or closest)
   - Uncheck "Block all public access" (needed for Instagram to fetch videos)
   - Add bucket policy for public read:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [{
         "Sid": "PublicRead",
         "Effect": "Allow",
         "Principal": "*",
         "Action": "s3:GetObject",
         "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/videos/*"
       }]
     }
     ```
3. Go to IAM → Create user → Attach `AmazonS3FullAccess` policy
4. Create access key → Copy to `.env`:
   ```
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=...
   AWS_S3_BUCKET=your-brand-videos
   AWS_S3_REGION=us-east-1
   ```

### Instagram (Meta Graph API)

1. Convert Instagram account to **Business** or **Creator** account
2. Link it to a Facebook Page
3. Go to https://developers.facebook.com → Create App → Business type
4. Add "Instagram Graph API" product
5. Request permissions: `instagram_basic`, `instagram_content_publish`
6. Submit for App Review (required for production use)
7. Generate a long-lived User Access Token via Graph API Explorer
8. Get your Instagram User ID: `GET /me?fields=id&access_token={token}`
9. Copy to `.env`:
   ```
   INSTAGRAM_USER_ID=17841...
   INSTAGRAM_ACCESS_TOKEN=EAAx...
   ```

**Token refresh:** Long-lived tokens expire in ~60 days. Refresh before expiry:
```
GET /oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}&client_secret={app_secret}&fb_exchange_token={old_token}
```

### Facebook (Meta Graph API)

1. Same Meta developer app as Instagram (step 3 above)
2. Add "Facebook Login" product
3. Request permissions: `pages_manage_posts`, `pages_read_engagement`
4. Get Page Access Token: `GET /{page-id}?fields=access_token&access_token={user_token}`
5. Exchange for long-lived token (same endpoint as Instagram)
6. Copy to `.env`:
   ```
   FACEBOOK_PAGE_ID=123456...
   FACEBOOK_PAGE_ACCESS_TOKEN=EAAx...
   ```

### TikTok (Content Posting API)

1. Go to https://developers.tiktok.com → Create App
2. Select "Content Posting API" product
3. Add scope: `video.upload`
4. **Sandbox mode (immediate):** Posts are PRIVATE only, max 5 users
5. **Audit for production:** Submit app for review with:
   - Demo video showing your integration
   - Privacy Policy and Terms of Service links on your website
   - After approval: posts can be PUBLIC
6. Implement OAuth 2.0 flow to get user access token
7. Copy to `.env`:
   ```
   TIKTOK_CLIENT_KEY=aw...
   TIKTOK_CLIENT_SECRET=...
   TIKTOK_ACCESS_TOKEN=act...
   ```

**Note:** TikTok tokens need periodic refresh via OAuth refresh flow.

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

| Platform | Caption Limit | Hashtags | Video Duration |
|---|---|---|---|
| Instagram Reels | 2200 chars | 5–12 | 3–90 seconds |
| TikTok | Short | 3–6 | Up to 60 minutes |
| Facebook Reels | Friendly tone | 3–8 | 3–90 seconds |

## Anti-Spam Rules (Enforced by Prompt + Validation)

- Captions differ across platforms for the same video
- Hashtag sets vary between videos (no copy-paste)
- Hooks and CTAs are varied across the batch
- Publish times are staggered (no same-minute posts)
- Language is natural and human
- 30-second delay between API posts

## Edge Cases

| Scenario | Behavior |
|---|---|
| No videos in folder | Pipeline exits cleanly with message |
| Fewer videos than batch size | Uses all available videos |
| ffprobe not installed | Duration set to null, everything else works |
| OPENAI_API_KEY missing | Pipeline stops with clear error |
| brand_config.json missing | Pipeline stops with clear error |
| S3 credentials missing | Upload step stops with clear error |
| Platform token missing | That platform is skipped, others still post |
| Platform API error | Logged to posting_results.json, pipeline continues |
| Pipeline crashes mid-posting | Re-run resumes from where it left off (skips already-posted) |
| Video already on S3 | Upload step skips it (no re-upload) |
| Rate limit hit | Logged as failure; re-run after cooldown |
| TikTok unaudited app | Posts go to PRIVATE; user must manually change or get audit approval |

## Change Log

| Date | What Changed |
|---|---|
| 2026-02-05 | Initial workflow created |
| 2026-02-05 | Added posting tools (S3 upload, Instagram, TikTok, Facebook), auth setup guide, pipeline flags |
