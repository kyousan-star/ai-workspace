#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from _common import find_binary, load_project, read_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Check ST102 video-factory dependencies and source availability.")
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    root = args.project.expanduser().resolve()
    project = load_project(root)
    manifest_path = Path(project["source_manifest"])
    source_rows = read_csv(manifest_path) if manifest_path.exists() else []
    report = {
        "project": str(root),
        "ffmpeg": find_binary("ffmpeg"),
        "ffprobe": find_binary("ffprobe"),
        "faster_whisper": bool(importlib.util.find_spec("faster_whisper")),
        "sources": [{"path": row.get("path", ""), "exists": Path(row.get("path", "")).exists()} for row in source_rows],
    }
    report["planning_ready"] = all(item["exists"] for item in report["sources"])
    report["metadata_ready"] = bool(report["ffprobe"] or report["ffmpeg"])
    report["render_ready"] = bool(report["ffmpeg"] and report["planning_ready"])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["planning_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
