#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ALLOWED = {"raw", "candidate", "approved", "published", "validated", "rejected", "retired"}
PROMOTED = {"approved", "published", "validated", "retired"}
REQUIRED = {"asset_id", "kind", "status", "source_path", "sha256"}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_asset_registry.py <registry.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    assets = data.get("assets")
    if not isinstance(assets, list):
        print("registry.assets must be a list", file=sys.stderr)
        return 1
    seen = set()
    errors = []
    for index, asset in enumerate(assets):
        missing = sorted(REQUIRED - set(asset))
        if missing:
            errors.append(f"assets[{index}] missing: {', '.join(missing)}")
            continue
        asset_id = asset["asset_id"]
        if asset_id in seen:
            errors.append(f"duplicate asset_id: {asset_id}")
        seen.add(asset_id)
        if asset["status"] not in ALLOWED:
            errors.append(f"{asset_id}: invalid status {asset['status']}")
        if asset["status"] in PROMOTED:
            approval = asset.get("approval") or {}
            if not approval.get("approved_by") or not approval.get("approved_at"):
                errors.append(f"{asset_id}: {asset['status']} requires approval evidence")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"ok: {len(assets)} assets; statuses and approval gates valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
