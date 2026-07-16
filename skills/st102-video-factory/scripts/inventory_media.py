#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from _common import VIDEO_EXTENSIONS, load_project, probe_video, read_csv, sha256_file


def iter_videos(path: Path):
    if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
        yield path
    elif path.is_dir():
        for candidate in sorted(path.rglob("*")):
            if candidate.is_file() and candidate.suffix.lower() in VIDEO_EXTENSIONS:
                yield candidate


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory ST102 videos without modifying sources.")
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    root = args.project.expanduser().resolve()
    project = load_project(root)
    source_rows = read_csv(Path(project["source_manifest"]))
    rows = []
    seen = set()
    for source in source_rows:
        source_path = Path(source["path"]).expanduser()
        for video in iter_videos(source_path):
            resolved = video.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            probe = probe_video(resolved)
            rows.append({
                "source_id": source["source_id"],
                "path": str(resolved),
                "filename": resolved.name,
                "bytes": resolved.stat().st_size,
                "sha256": sha256_file(resolved),
                "duration": probe["duration"],
                "width": probe["width"],
                "height": probe["height"],
                "codec": probe["codec"],
                "probe_status": probe["probe_status"],
                "source_kind": source["source_kind"],
                "rights_status": source["rights_status"],
                "disclosure": source["disclosure"],
            })
    output = root / "inventory/media-inventory.csv"
    fields = list(rows[0]) if rows else ["source_id", "path", "filename", "bytes", "sha256", "duration", "width", "height", "codec", "probe_status", "source_kind", "rights_status", "disclosure"]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} videos -> {output}")


if __name__ == "__main__":
    main()
