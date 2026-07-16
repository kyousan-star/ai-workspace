#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

from _common import dump_json

DEFAULT_PROJECT = Path("/Users/lihuan/Documents/跨境业务/美国亚马逊业务运营/品类cell phone tripod/ST102/video-factory")
SOURCE_ROWS = [
    {
        "source_id": "st102-owned-raw",
        "path": "/Users/lihuan/Documents/跨境业务/美国亚马逊业务运营/品类cell phone tripod/ST102/内容创作",
        "source_kind": "owned_raw",
        "rights_status": "approved_internal",
        "disclosure": "",
        "notes": "Self-shot ST102 source clips; preserve originals.",
    },
    {
        "source_id": "st102-sponsored-creator",
        "path": "/Users/lihuan/Documents/跨境业务/美国亚马逊业务运营/品类cell phone tripod/ST102/ST102 亚马逊买家秀",
        "source_kind": "sponsored_creator",
        "rights_status": "needs_confirmation",
        "disclosure": "Sponsored Product Demo",
        "notes": "Plan and timestamp freely; render externally only after cross-channel rights are confirmed.",
    },
    {
        "source_id": "st102-how-to-master",
        "path": "/Users/lihuan/Documents/Codex/2026-07-10/new-chat/outputs/ST102_How_To_Quick_Setup.mp4",
        "source_kind": "owned_master",
        "rights_status": "approved_internal",
        "disclosure": "",
        "notes": "28.467-second How-to master.",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the ST102 video-factory project without touching source videos.")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    args = parser.parse_args()
    root = args.project.expanduser().resolve()
    directories = [
        "inventory/transcripts",
        "campaigns",
        "approved-library",
        "publish-log",
    ]
    for relative in directories:
        (root / relative).mkdir(parents=True, exist_ok=True)

    config = root / "project.yaml"
    if not config.exists():
        dump_json(config, {
            "project_name": "ST102 Video Factory",
            "sku": "ST102",
            "created": date.today().isoformat(),
            "project_root": str(root),
            "default_scene_ratio": 0.70,
            "default_support_ratio": 0.30,
            "fact_sources": [
                "/Users/lihuan/Documents/跨境业务/美国亚马逊业务运营/Vlogara logo&站外&shopify/codex/shopify-deploy/st102-fact-fix-20260714/README.md",
                "/Users/lihuan/Documents/跨境业务/美国亚马逊业务运营/Vlogara logo&站外&shopify/codex/VLOGARA-当前状态.md",
            ],
            "source_manifest": str(root / "inventory/source-manifest.csv"),
        })

    manifest = root / "inventory/source-manifest.csv"
    if not manifest.exists():
        with manifest.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(SOURCE_ROWS[0]))
            writer.writeheader()
            writer.writerows(SOURCE_ROWS)

    publish_log = root / "publish-log/content-log.csv"
    if not publish_log.exists():
        with publish_log.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "content_id", "platform", "url", "pillar", "duration", "views", "likes", "comments", "shares", "profile_visits", "bio_clicks", "notes"])
    print(root)


if __name__ == "__main__":
    main()
