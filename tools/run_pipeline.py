"""
run_pipeline.py — Single entry point for the social video publishing pipeline.

Runs all steps in order; stops if any step fails.

Usage:
    python tools/run_pipeline.py                # full pipeline (scan → generate → upload → post)
    python tools/run_pipeline.py --generate-only  # steps 1-2 only (review plan before posting)
    python tools/run_pipeline.py --post-only      # steps 3-4 only (after reviewing plan)
    python tools/run_pipeline.py --dry-run        # full pipeline but posting step is dry-run
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

GENERATE_STEPS = [
    {"label": "Scanning videos",           "script": "tools/scan_videos.py"},
    {"label": "Generating posting plan",    "script": "tools/generate_posting_plan.py"},
]

POST_STEPS = [
    {"label": "Uploading videos to S3",     "script": "tools/upload_to_s3.py"},
    {"label": "Executing posting plan",     "script": "tools/execute_posting_plan.py"},
]


def run_steps(steps, extra_args=None):
    """Run a list of pipeline steps sequentially."""
    for i, step in enumerate(steps, start=1):
        print(f"[Step {i}/{len(steps)}] {step['label']}...", flush=True)

        cmd = [sys.executable, "-u", str(PROJECT_ROOT / step["script"])]
        if extra_args:
            cmd.extend(extra_args)

        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        if result.returncode != 0:
            print(f"\nPipeline STOPPED at step {i} ({step['label']}). See error above.", flush=True)
            sys.exit(result.returncode)
        print(flush=True)


def main():
    args = sys.argv[1:]
    generate_only = "--generate-only" in args
    post_only = "--post-only" in args
    dry_run = "--dry-run" in args

    print(f"=== Social Video Publishing Pipeline === {datetime.now().isoformat()}", flush=True)

    if generate_only and post_only:
        print("ERROR: Cannot use --generate-only and --post-only together.", flush=True)
        sys.exit(1)

    if generate_only:
        print("Mode: generate-only (steps 1-2)\n", flush=True)
        run_steps(GENERATE_STEPS)
        print(f"Plan generated: {PROJECT_ROOT / '.tmp' / 'posting_plan.json'}", flush=True)
        print("Review the plan, then run: python tools/run_pipeline.py --post-only", flush=True)
    elif post_only:
        print("Mode: post-only (steps 3-4)\n", flush=True)
        extra = ["--dry-run"] if dry_run else None
        run_steps(POST_STEPS, extra_args=extra)
    else:
        mode = "dry-run" if dry_run else "full"
        print(f"Mode: {mode} (all steps)\n", flush=True)
        run_steps(GENERATE_STEPS)
        extra = ["--dry-run"] if dry_run else None
        run_steps(POST_STEPS, extra_args=extra)

    print(f"\n=== Pipeline complete === {datetime.now().isoformat()}", flush=True)


if __name__ == "__main__":
    main()
