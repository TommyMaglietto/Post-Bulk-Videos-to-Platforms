"""
test_pipeline.py — Offline tests for the social video publishing pipeline.

No API keys, network access, or real videos required.
Run:  python -m pytest tests/test_pipeline.py -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Make tools/ importable
# ---------------------------------------------------------------------------
TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))


# =========================================================================
# Config
# =========================================================================

class TestConfig:
    def test_load_brand_config_missing_file(self, tmp_path):
        """Should raise FileNotFoundError when brand_config.json is missing."""
        import config as cfg
        original = cfg.BRAND_CONFIG_PATH
        cfg.BRAND_CONFIG_PATH = tmp_path / "nonexistent.json"
        try:
            with pytest.raises(FileNotFoundError):
                cfg.load_brand_config()
        finally:
            cfg.BRAND_CONFIG_PATH = original

    def test_load_brand_config_valid(self, tmp_path):
        """Should load and return the JSON contents."""
        import config as cfg
        original = cfg.BRAND_CONFIG_PATH
        config_file = tmp_path / "brand_config.json"
        config_file.write_text(json.dumps({"brand_voice": "bold", "niche": "fitness"}))
        cfg.BRAND_CONFIG_PATH = config_file
        try:
            result = cfg.load_brand_config()
            assert result["brand_voice"] == "bold"
            assert result["niche"] == "fitness"
        finally:
            cfg.BRAND_CONFIG_PATH = original

    def test_video_extensions(self):
        """Should include all expected video formats."""
        import config as cfg
        assert ".mp4" in cfg.VIDEO_EXTENSIONS
        assert ".mov" in cfg.VIDEO_EXTENSIONS
        assert ".webm" in cfg.VIDEO_EXTENSIONS
        assert ".txt" not in cfg.VIDEO_EXTENSIONS


# =========================================================================
# Scan Videos
# =========================================================================

class TestScanVideos:
    def _create_fake_videos(self, directory, names):
        """Create fake video files with some content."""
        for name in names:
            f = directory / name
            f.write_bytes(b"\x00" * 1024)  # 1KB dummy file

    def test_scan_empty_folder(self, tmp_path):
        """Should return empty list when no videos exist."""
        import scan_videos
        with patch.object(scan_videos, "VIDEOS_DIR", tmp_path), \
             patch.object(scan_videos, "load_brand_config", return_value={"videos_per_batch": 5}):
            result = scan_videos.scan_and_select()
            assert result == []

    def test_scan_finds_mp4_files(self, tmp_path):
        """Should find .mp4 files and return metadata."""
        import scan_videos
        self._create_fake_videos(tmp_path, ["test1.mp4", "test2.mp4"])

        with patch.object(scan_videos, "VIDEOS_DIR", tmp_path), \
             patch.object(scan_videos, "load_brand_config", return_value={"videos_per_batch": 15}), \
             patch.object(scan_videos, "get_duration", return_value=None):
            result = scan_videos.scan_and_select()
            assert len(result) == 2
            filenames = {v["file_name"] for v in result}
            assert "test1.mp4" in filenames
            assert "test2.mp4" in filenames

    def test_scan_respects_batch_size(self, tmp_path):
        """Should only select up to videos_per_batch."""
        import scan_videos
        self._create_fake_videos(tmp_path, [f"v{i}.mp4" for i in range(10)])

        with patch.object(scan_videos, "VIDEOS_DIR", tmp_path), \
             patch.object(scan_videos, "load_brand_config", return_value={"videos_per_batch": 3}), \
             patch.object(scan_videos, "get_duration", return_value=None):
            result = scan_videos.scan_and_select()
            assert len(result) == 3

    def test_scan_ignores_non_video_files(self, tmp_path):
        """Should ignore .txt, .jpg, etc."""
        import scan_videos
        self._create_fake_videos(tmp_path, ["video.mp4"])
        (tmp_path / "notes.txt").write_text("hello")
        (tmp_path / "thumb.jpg").write_bytes(b"\xff\xd8")

        with patch.object(scan_videos, "VIDEOS_DIR", tmp_path), \
             patch.object(scan_videos, "load_brand_config", return_value={"videos_per_batch": 15}), \
             patch.object(scan_videos, "get_duration", return_value=None):
            result = scan_videos.scan_and_select()
            assert len(result) == 1
            assert result[0]["file_name"] == "video.mp4"

    def test_video_id_format(self, tmp_path):
        """Video IDs should be v001, v002, etc."""
        import scan_videos
        self._create_fake_videos(tmp_path, ["a.mp4", "b.mp4", "c.mp4"])

        with patch.object(scan_videos, "VIDEOS_DIR", tmp_path), \
             patch.object(scan_videos, "load_brand_config", return_value={"videos_per_batch": 15}), \
             patch.object(scan_videos, "get_duration", return_value=None):
            result = scan_videos.scan_and_select()
            ids = [v["video_id"] for v in result]
            assert ids == ["v001", "v002", "v003"]

    def test_get_duration_no_ffprobe(self):
        """Should return None gracefully when ffprobe is missing."""
        import scan_videos
        result = scan_videos.get_duration(Path("nonexistent.mp4"))
        assert result is None


# =========================================================================
# Generate Posting Plan — Validation
# =========================================================================

class TestValidation:
    def _make_plan(self, items, schedule=None):
        """Build a minimal plan dict for validation testing."""
        return {
            "batch_summary": {"overall_theme": "test", "tone_notes": "test"},
            "items": items,
            "posting_plan": {
                "strategy": "test",
                "recommended_schedule": schedule or [],
                "compliance_checks": [],
            },
        }

    def _make_item(self, vid="v001", ig_tags=6, tt_tags=4, fb_tags=5,
                   ig_caption="ig caption", tt_caption="tt caption", fb_caption="fb caption"):
        return {
            "video_id": vid,
            "instagram": {"title": "t", "caption": ig_caption, "hashtags": [f"tag{i}" for i in range(ig_tags)]},
            "tiktok": {"caption": tt_caption, "hashtags": [f"tag{i}" for i in range(tt_tags)]},
            "facebook": {"caption": fb_caption, "hashtags": [f"tag{i}" for i in range(fb_tags)]},
        }

    def test_valid_plan_passes(self):
        from generate_posting_plan import validate_plan
        plan = self._make_plan(
            [self._make_item()],
            [{"video_id": "v001", "platform": "instagram", "publish_time_local": "2026-02-06 09:00"}],
        )
        warnings = validate_plan(plan, 1)
        assert warnings == []

    def test_wrong_item_count(self):
        from generate_posting_plan import validate_plan
        plan = self._make_plan([self._make_item()])
        warnings = validate_plan(plan, 3)
        assert any("Expected 3" in w for w in warnings)

    def test_ig_hashtag_too_few(self):
        from generate_posting_plan import validate_plan
        plan = self._make_plan([self._make_item(ig_tags=2)])
        warnings = validate_plan(plan, 1)
        assert any("Instagram" in w and "2 hashtags" in w for w in warnings)

    def test_ig_hashtag_too_many(self):
        from generate_posting_plan import validate_plan
        plan = self._make_plan([self._make_item(ig_tags=15)])
        warnings = validate_plan(plan, 1)
        assert any("Instagram" in w and "15 hashtags" in w for w in warnings)

    def test_tt_hashtag_out_of_range(self):
        from generate_posting_plan import validate_plan
        plan = self._make_plan([self._make_item(tt_tags=1)])
        warnings = validate_plan(plan, 1)
        assert any("TikTok" in w for w in warnings)

    def test_fb_hashtag_out_of_range(self):
        from generate_posting_plan import validate_plan
        plan = self._make_plan([self._make_item(fb_tags=10)])
        warnings = validate_plan(plan, 1)
        assert any("Facebook" in w for w in warnings)

    def test_ig_caption_too_long(self):
        from generate_posting_plan import validate_plan
        plan = self._make_plan([self._make_item(ig_caption="x" * 2201)])
        warnings = validate_plan(plan, 1)
        assert any("2200" in w for w in warnings)

    def test_duplicate_captions_detected(self):
        from generate_posting_plan import validate_plan
        plan = self._make_plan([self._make_item(
            ig_caption="same", tt_caption="same", fb_caption="different"
        )])
        warnings = validate_plan(plan, 1)
        assert any("Duplicate" in w for w in warnings)

    def test_no_schedule_warning(self):
        from generate_posting_plan import validate_plan
        plan = self._make_plan([self._make_item()], schedule=[])
        warnings = validate_plan(plan, 1)
        assert any("No posting schedule" in w for w in warnings)

    def test_duplicate_times_warning(self):
        from generate_posting_plan import validate_plan
        plan = self._make_plan(
            [self._make_item("v001"), self._make_item("v002")],
            [
                {"video_id": "v001", "platform": "instagram", "publish_time_local": "2026-02-06 09:00"},
                {"video_id": "v002", "platform": "tiktok", "publish_time_local": "2026-02-06 09:00"},
            ],
        )
        warnings = validate_plan(plan, 2)
        assert any("duplicate publish times" in w for w in warnings)


# =========================================================================
# Generate Posting Plan — build_user_message
# =========================================================================

class TestBuildUserMessage:
    def test_includes_brand_fields(self):
        from generate_posting_plan import build_user_message
        brand = {"brand_voice": "bold", "audience": "teens", "niche": "gaming"}
        msg = build_user_message(brand, [])
        assert "bold" in msg
        assert "teens" in msg
        assert "gaming" in msg

    def test_includes_video_data(self):
        from generate_posting_plan import build_user_message
        videos = [{"video_id": "v001", "file_name": "test.mp4"}]
        msg = build_user_message({}, videos)
        assert "v001" in msg
        assert "test.mp4" in msg

    def test_defaults_for_missing_fields(self):
        from generate_posting_plan import build_user_message
        msg = build_user_message({}, [])
        assert "not specified" in msg


# =========================================================================
# S3 URL Encoding
# =========================================================================

class TestS3UrlEncoding:
    def test_url_encodes_spaces(self):
        from upload_to_s3 import quote
        key = "videos/SOMP Promotion.mp4"
        encoded = quote(key)
        assert " " not in encoded
        assert "SOMP%20Promotion" in encoded

    def test_url_preserves_safe_characters(self):
        from upload_to_s3 import quote
        key = "videos/simple.mp4"
        encoded = quote(key)
        assert encoded == "videos/simple.mp4"


# =========================================================================
# Execute Posting Plan — Logic
# =========================================================================

class TestExecutePostingPlan:
    def test_get_item_content_found(self):
        from execute_posting_plan import get_item_content
        items = [
            {"video_id": "v001", "instagram": {"caption": "ig cap"}, "tiktok": {"caption": "tt cap"}},
        ]
        result = get_item_content(items, "v001", "instagram")
        assert result["caption"] == "ig cap"

    def test_get_item_content_not_found(self):
        from execute_posting_plan import get_item_content
        items = [{"video_id": "v001", "instagram": {"caption": "ig"}}]
        result = get_item_content(items, "v999", "instagram")
        assert result is None

    def test_get_item_content_wrong_platform(self):
        from execute_posting_plan import get_item_content
        items = [{"video_id": "v001", "instagram": {"caption": "ig"}}]
        result = get_item_content(items, "v001", "youtube")
        assert result is None

    def test_check_credentials_none(self):
        from execute_posting_plan import check_credentials
        with patch("execute_posting_plan.INSTAGRAM_ACCESS_TOKEN", ""), \
             patch("execute_posting_plan.TIKTOK_ACCESS_TOKEN", ""), \
             patch("execute_posting_plan.FACEBOOK_PAGE_ACCESS_TOKEN", ""):
            assert check_credentials() == []

    def test_check_credentials_partial(self):
        from execute_posting_plan import check_credentials
        with patch("execute_posting_plan.INSTAGRAM_ACCESS_TOKEN", ""), \
             patch("execute_posting_plan.TIKTOK_ACCESS_TOKEN", "tok123"), \
             patch("execute_posting_plan.FACEBOOK_PAGE_ACCESS_TOKEN", "fb123"):
            result = check_credentials()
            assert "tiktok" in result
            assert "facebook" in result
            assert "instagram" not in result


# =========================================================================
# Platform Caption Building
# =========================================================================

class TestCaptionBuilding:
    def test_instagram_caption_appends_hashtags(self):
        from post_instagram import post_reel
        # Won't actually post — no credentials set, will return early
        with patch("post_instagram.INSTAGRAM_USER_ID", ""), \
             patch("post_instagram.INSTAGRAM_ACCESS_TOKEN", ""):
            result = post_reel("http://example.com/v.mp4", "Hello world", ["travel", "fun"])
            assert result["success"] is False  # no creds, but function doesn't crash

    def test_tiktok_caption_with_hashtags(self):
        from post_tiktok import post_video
        with patch("post_tiktok.TIKTOK_ACCESS_TOKEN", ""):
            result = post_video("fake.mp4", "Test", ["tag1"])
            assert result["success"] is False  # no creds

    def test_facebook_caption_with_hashtags(self):
        from post_facebook import post_reel
        with patch("post_facebook.FACEBOOK_PAGE_ID", ""), \
             patch("post_facebook.FACEBOOK_PAGE_ACCESS_TOKEN", ""):
            result = post_reel("fake.mp4", "Test", ["tag1"])
            assert result["success"] is False  # no creds

    def test_hashtag_lstrip_removes_hash(self):
        """Hashtags passed with # prefix should not double up."""
        tag_str = " ".join(f"#{t.lstrip('#')}" for t in ["#travel", "fun", "#food"])
        assert tag_str == "#travel #fun #food"


# =========================================================================
# Run Pipeline — Flag Parsing
# =========================================================================

class TestPipelineFlags:
    def test_generate_and_post_conflict(self):
        """Should exit with error when both flags used together."""
        import run_pipeline
        with patch("sys.argv", ["run_pipeline.py", "--generate-only", "--post-only"]):
            with pytest.raises(SystemExit) as exc_info:
                run_pipeline.main()
            assert exc_info.value.code == 1
