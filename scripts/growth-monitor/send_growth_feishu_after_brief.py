#!/usr/bin/env python3
"""Wait for the daily growth brief, then send it via the local Feishu webhook."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
SENT_DIR = OUTPUT_DIR / "feishu-sent"
SENDER = ROOT / "scripts" / "send_growth_feishu.py"
ET = ZoneInfo("America/New_York")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="ET report date in YYYY-MM-DD format")
    parser.add_argument(
        "--brief-file",
        type=Path,
        help="Override brief file path; defaults to output/daily-growth-brief-YYYY-MM-DD.txt",
    )
    parser.add_argument(
        "--wait-minutes",
        type=int,
        default=120,
        help="Maximum time to wait for the brief file before giving up",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=120,
        help="Polling interval while waiting for the brief file",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def infer_report_date(raw_date: str | None) -> str:
    return raw_date or datetime.now(ET).date().isoformat()


def infer_brief_file(report_date: str, override: Path | None) -> Path:
    return override or OUTPUT_DIR / f"daily-growth-brief-{report_date}.txt"


def marker_path(report_date: str) -> Path:
    return SENT_DIR / f"{report_date}.json"


def wait_for_brief(path: Path, wait_minutes: int, poll_seconds: int) -> bool:
    deadline = time.monotonic() + max(wait_minutes, 0) * 60
    poll_seconds = max(poll_seconds, 1)

    while True:
        if path.exists():
            try:
                if path.read_text(encoding="utf-8").strip():
                    return True
            except OSError:
                pass

        if time.monotonic() >= deadline:
            return False

        print(f"WAITING_FOR_BRIEF path={path} next_check_in={poll_seconds}s")
        time.sleep(poll_seconds)


def main() -> int:
    args = parse_args()
    report_date = infer_report_date(args.date)
    brief_file = infer_brief_file(report_date, args.brief_file)
    marker = marker_path(report_date)

    if marker.exists():
        print(f"SKIP_ALREADY_SENT date={report_date}")
        return 0

    if not wait_for_brief(brief_file, args.wait_minutes, args.poll_seconds):
        print(f"WAIT_TIMEOUT date={report_date} path={brief_file}", file=sys.stderr)
        return 1

    command = [
        sys.executable,
        str(SENDER),
        "--message-file",
        str(brief_file),
        "--date",
        report_date,
    ]
    if args.dry_run:
        command.append("--dry-run")

    result = subprocess.run(command, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
