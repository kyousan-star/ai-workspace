#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from _common import dump_json, load_json, probe_video

FORBIDDEN = (
    "zero wobble",
    "no wobble",
    "1-second release",
    "1 second release",
    "works on uneven ground",
    "heavy duty",
    "windproof",
    "universal for all devices",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="QA one rendered ST102 video against its cut manifest.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    payload = load_json(args.manifest)
    failures = []
    warnings = []
    if not args.video.exists():
        failures.append(f"Missing rendered video: {args.video}")
        probe = {"probe_status": "missing", "duration": "", "width": "", "height": "", "codec": ""}
    else:
        probe = probe_video(args.video)
        if probe["probe_status"].startswith("ok"):
            if (probe["width"], probe["height"]) not in {(720, 1280), (1080, 1920)}:
                failures.append(f"Unexpected dimensions: {probe['width']}x{probe['height']}")
            if probe["duration"] and not 12 <= float(probe["duration"]) <= 25:
                warnings.append(f"Duration outside default 12–25s range: {probe['duration']}s")
        else:
            warnings.append(f"Metadata not verified: {probe['probe_status']}")
    text_parts = [payload.get("title", ""), payload.get("disclosure", ""), *payload.get("claims", [])]
    captions = payload.get("captions_srt")
    if captions and Path(captions).exists():
        text_parts.append(Path(captions).read_text(encoding="utf-8", errors="replace"))
    combined = " ".join(text_parts).lower()
    for claim in FORBIDDEN:
        if claim in combined:
            failures.append(f"Forbidden claim: {claim}")
    if payload.get("source_kind") == "sponsored_creator":
        if payload.get("rights_status") != "approved_cross_channel":
            failures.append("Cross-channel creator rights not approved.")
        if not payload.get("disclosure"):
            failures.append("Sponsored creator disclosure missing.")
    report = {
        "content_id": payload.get("content_id", ""),
        "manifest": str(args.manifest.resolve()),
        "video": str(args.video.resolve()),
        "probe": probe,
        "failures": failures,
        "warnings": warnings,
        "status": "fail" if failures else "pass_with_warnings" if warnings else "pass",
    }
    dump_json(args.report, report)
    print(args.report)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
