#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from _common import load_project


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a non-destructive ST102 video campaign workspace.")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--campaign", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", args.campaign):
        raise SystemExit("Campaign id must use lowercase letters, digits, and hyphens.")
    root = args.project.expanduser().resolve()
    load_project(root)
    campaign = root / "campaigns" / args.campaign
    for relative in ["scripts", "cut-manifests", "transcripts", "previews", "finals", "covers", "captions", "qa"]:
        (campaign / relative).mkdir(parents=True, exist_ok=True)
    brief = campaign / "brief.md"
    if not brief.exists():
        brief.write_text(
            "# Campaign Brief\n\n"
            "- Goal:\n- Audience:\n- Channels: TikTok, Reels, Shorts\n"
            "- Planned mix: 70% scenes / 30% How-to and FAQ\n"
            "- Approval gate: planning pending\n- Final publish approval: required\n",
            encoding="utf-8",
        )
    shot_list = campaign / "shot-list.md"
    if not shot_list.exists():
        shot_list.write_text("# Shot List\n\n| shot_id | scene | framing | action | existing/missing | notes |\n|---|---|---|---|---|---|\n", encoding="utf-8")
    plan = campaign / "content-plan.csv"
    if not plan.exists():
        with plan.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["content_id", "pillar", "hook", "audience", "story", "source_assets", "missing_shots", "caption", "disclosure", "channels", "status"])
    print(campaign)


if __name__ == "__main__":
    main()
