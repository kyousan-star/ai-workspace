#!/usr/bin/env python3
"""Send one compact VLOGARA growth brief to Feishu per ET calendar day."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
WEBHOOK_FILE = ROOT / "config" / "feishu_growth_webhook.txt"
SENT_DIR = ROOT / "output" / "feishu-sent"
ET = ZoneInfo("America/New_York")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message-file", required=True, type=Path)
    parser.add_argument("--date", help="ET report date in YYYY-MM-DD format")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_date = args.date or datetime.now(ET).date().isoformat()
    marker = SENT_DIR / f"{report_date}.json"

    if marker.exists():
        print(f"SKIP_ALREADY_SENT date={report_date}")
        return 0

    message = args.message_file.read_text(encoding="utf-8").strip()
    if not message:
        raise SystemExit("message file is empty")

    if args.dry_run:
        print(f"DRY_RUN_OK date={report_date} chars={len(message)}")
        return 0

    webhook = WEBHOOK_FILE.read_text(encoding="utf-8").strip()
    if not webhook.startswith("https://open.feishu.cn/open-apis/bot/v2/hook/"):
        raise SystemExit("invalid Feishu webhook configuration")

    payload = json.dumps(
        {"msg_type": "text", "content": {"text": message}},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"SEND_FAILED date={report_date} error={type(exc).__name__}", file=sys.stderr)
        return 1

    if body.get("code") != 0:
        print(
            f"SEND_FAILED date={report_date} code={body.get('code')}",
            file=sys.stderr,
        )
        return 1

    SENT_DIR.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "report_date_et": report_date,
                "sent_at_et": datetime.now(ET).isoformat(timespec="seconds"),
                "status": "success",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"SEND_OK date={report_date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
