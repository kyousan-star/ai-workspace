#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from render_short import render


def main() -> None:
    parser = argparse.ArgumentParser(description="Render all JSON cut manifests in a directory.")
    parser.add_argument("manifest_dir", type=Path)
    parser.add_argument("--mode", choices=["preview", "final"], default="preview")
    args = parser.parse_args()
    manifests = sorted(args.manifest_dir.expanduser().resolve().glob("*.json"))
    if not manifests:
        raise SystemExit(f"No JSON manifests found in {args.manifest_dir}")
    results = []
    failed = False
    for manifest in manifests:
        try:
            output = render(manifest, args.mode)
            results.append({"manifest": str(manifest), "status": "ok", "output": str(output)})
        except (SystemExit, Exception) as exc:
            failed = True
            results.append({"manifest": str(manifest), "status": "failed", "error": str(exc)})
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
