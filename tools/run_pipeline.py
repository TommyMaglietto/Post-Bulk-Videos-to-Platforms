"""
run_pipeline.py — Single entry point for the social video publishing pipeline.

Runs all steps in order; stops if any step fails.

Usage:
    python tools/run_pipeline.py
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

STEPS = [
    {"label": "Scanning videos",           "script": "tools/scan_videos.py"},
    {"label": "Generating posting plan",    "script": "tools/generate_posting_plan.py"},
]


def main():
    print(f"=== Social Video Publishing Pipeline === {datetime.now().isoformat()}\n", flush=True)

    for i, step in enumerate(STEPS, start=1):
        print(f"[Step {i}/{len(STEPS)}] {step['label']}...", flush=True)
        result = subprocess.run(
            [sys.executable, "-u", str(PROJECT_ROOT / step["script"])],
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            print(f"\nPipeline STOPPED at step {i} ({step['label']}). See error above.", flush=True)
            sys.exit(result.returncode)
        print(flush=True)

    print(f"=== Pipeline complete === {datetime.now().isoformat()}", flush=True)
    print(f"Output: {PROJECT_ROOT / '.tmp' / 'posting_plan.json'}", flush=True)


if __name__ == "__main__":
    main()
