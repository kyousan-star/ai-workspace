#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


ALLOWED = {"raw", "candidate", "approved", "published", "validated", "rejected", "retired"}
PROMOTED = {"approved", "published", "validated", "retired"}
LINEAGE_ONLY = {"raw", "rejected"}
REQUIRED = {"asset_id", "kind", "status", "source_path", "sha256"}
TRANSITIONS = {
    "candidate": {"approved", "rejected", "retired"},
    "approved": {"published", "retired"},
    "published": {"validated", "retired"},
    "validated": {"retired"},
    "raw": {"candidate", "rejected", "retired"},
    "rejected": {"candidate", "retired"},
    "retired": set(),
}


class RegistryError(RuntimeError):
    pass


def now_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": "1.0", "updated_at": now_date(), "assets": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot read registry {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError("registry root must be an object")
    return data


def validate(data: dict[str, Any], verify_files: bool = False) -> list[str]:
    assets = data.get("assets")
    if not isinstance(assets, list):
        return ["registry.assets must be a list"]
    errors = []
    seen = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            errors.append(f"assets[{index}] must be an object")
            continue
        missing = sorted(REQUIRED - set(asset))
        if missing:
            errors.append(f"assets[{index}] missing: {', '.join(missing)}")
            continue
        asset_id = asset["asset_id"]
        if asset_id in seen:
            errors.append(f"duplicate asset_id: {asset_id}")
        seen.add(asset_id)
        status = asset["status"]
        if status not in ALLOWED:
            errors.append(f"{asset_id}: invalid status {status}")
        if status in PROMOTED:
            approval = asset.get("approval") or {}
            if not approval.get("approved_by") or not approval.get("approved_at"):
                errors.append(f"{asset_id}: {status} requires approval evidence")
        parent = asset.get("parent_asset_id")
        if parent and parent == asset_id:
            errors.append(f"{asset_id}: parent_asset_id cannot reference itself")
        if verify_files:
            source = Path(str(asset["source_path"])).expanduser()
            if not source.is_file():
                errors.append(f"{asset_id}: source file missing: {source}")
            elif sha256_file(source) != asset["sha256"]:
                errors.append(f"{asset_id}: source hash mismatch")
    return errors


@contextmanager
def registry_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temp_path = Path(handle.name)
    try:
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def register_candidate(path: Path, manifest_path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot read manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise RegistryError("manifest must be an object")
    manifest["status"] = "candidate"
    missing = sorted(REQUIRED - set(manifest))
    if missing:
        raise RegistryError(f"manifest missing: {', '.join(missing)}")
    source = Path(str(manifest["source_path"])).expanduser().resolve()
    if not source.is_file():
        raise RegistryError(f"source file missing: {source}")
    actual_hash = sha256_file(source)
    if actual_hash != manifest["sha256"]:
        raise RegistryError("manifest sha256 does not match source file")
    manifest["source_path"] = str(source)
    manifest["approval_required"] = True
    manifest.pop("approval", None)

    with registry_lock(path):
        data = load_registry(path)
        errors = validate(data)
        if errors:
            raise RegistryError("registry invalid before write: " + "; ".join(errors))
        assets = data["assets"]
        existing = next((asset for asset in assets if asset["asset_id"] == manifest["asset_id"]), None)
        if existing:
            if (
                existing["sha256"] == actual_hash
                and existing["source_path"] == str(source)
                and existing["status"] == "candidate"
            ):
                return {"created": False, "asset": existing}
            raise RegistryError(f"asset_id conflict: {manifest['asset_id']}")
        parent = manifest.get("parent_asset_id")
        if parent and not any(asset["asset_id"] == parent for asset in assets):
            raise RegistryError(f"parent asset is not registered: {parent}")
        assets.append(manifest)
        data["updated_at"] = now_date()
        errors = validate(data)
        if errors:
            raise RegistryError("candidate rejected: " + "; ".join(errors))
        atomic_write(path, data)
    return {"created": True, "asset": manifest}


def register_lineage(path: Path, manifest_path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot read manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise RegistryError("manifest must be an object")
    status = manifest.get("status")
    if status not in LINEAGE_ONLY:
        raise RegistryError(
            "lineage registration status must be one of: " + ", ".join(sorted(LINEAGE_ONLY))
        )
    if status == "rejected" and not str(manifest.get("notes", "")).strip():
        raise RegistryError("rejected lineage assets require notes")
    missing = sorted(REQUIRED - set(manifest))
    if missing:
        raise RegistryError(f"manifest missing: {', '.join(missing)}")
    source = Path(str(manifest["source_path"])).expanduser().resolve()
    if not source.is_file():
        raise RegistryError(f"source file missing: {source}")
    actual_hash = sha256_file(source)
    if actual_hash != manifest["sha256"]:
        raise RegistryError("manifest sha256 does not match source file")
    manifest["source_path"] = str(source)
    manifest["approval_required"] = False
    manifest.pop("approval", None)

    with registry_lock(path):
        data = load_registry(path)
        errors = validate(data)
        if errors:
            raise RegistryError("registry invalid before write: " + "; ".join(errors))
        assets = data["assets"]
        existing = next((asset for asset in assets if asset["asset_id"] == manifest["asset_id"]), None)
        if existing:
            if (
                existing["sha256"] == actual_hash
                and existing["source_path"] == str(source)
                and existing["status"] == status
            ):
                return {"created": False, "asset": existing}
            raise RegistryError(f"asset_id conflict: {manifest['asset_id']}")
        parent = manifest.get("parent_asset_id")
        if parent and not any(asset["asset_id"] == parent for asset in assets):
            raise RegistryError(f"parent asset is not registered: {parent}")
        assets.append(manifest)
        data["updated_at"] = now_date()
        errors = validate(data)
        if errors:
            raise RegistryError("lineage asset rejected: " + "; ".join(errors))
        atomic_write(path, data)
    return {"created": True, "asset": manifest}


def promote(
    path: Path,
    asset_id: str,
    target_status: str,
    approved_by: str,
    approved_at: str,
    decision_ref: str,
) -> dict[str, Any]:
    if target_status not in PROMOTED:
        raise RegistryError(f"promotion target must be one of: {', '.join(sorted(PROMOTED))}")
    if not approved_by or not approved_at or not decision_ref:
        raise RegistryError("approved_by, approved_at, and decision_ref are required")
    with registry_lock(path):
        data = load_registry(path)
        errors = validate(data)
        if errors:
            raise RegistryError("registry invalid before write: " + "; ".join(errors))
        asset = next((item for item in data["assets"] if item["asset_id"] == asset_id), None)
        if not asset:
            raise RegistryError(f"unknown asset: {asset_id}")
        current = asset["status"]
        if target_status not in TRANSITIONS.get(current, set()):
            raise RegistryError(f"invalid transition: {current} -> {target_status}")
        asset["status"] = target_status
        asset["approval_required"] = False
        asset["approval"] = {
            "approved_by": approved_by,
            "approved_at": approved_at,
            "decision_ref": decision_ref,
        }
        data["updated_at"] = now_date()
        errors = validate(data)
        if errors:
            raise RegistryError("promotion rejected: " + "; ".join(errors))
        atomic_write(path, data)
    return {"asset": asset, "from": current, "to": target_status}


def reject(
    path: Path,
    asset_id: str,
    notes: str,
    decided_by: str,
    decided_at: str,
    decision_ref: str,
) -> dict[str, Any]:
    if not notes.strip():
        raise RegistryError("rejection notes are required")
    if not decided_by or not decided_at or not decision_ref:
        raise RegistryError("decided_by, decided_at, and decision_ref are required")
    with registry_lock(path):
        data = load_registry(path)
        errors = validate(data)
        if errors:
            raise RegistryError("registry invalid before write: " + "; ".join(errors))
        asset = next((item for item in data["assets"] if item["asset_id"] == asset_id), None)
        if not asset:
            raise RegistryError(f"unknown asset: {asset_id}")
        current = asset["status"]
        if "rejected" not in TRANSITIONS.get(current, set()):
            raise RegistryError(f"invalid transition: {current} -> rejected")
        asset["status"] = "rejected"
        asset["approval_required"] = False
        asset.pop("approval", None)
        asset["notes"] = notes.strip()
        asset["decision"] = {
            "decided_by": decided_by,
            "decided_at": decided_at,
            "decision_ref": decision_ref,
        }
        data["updated_at"] = now_date()
        errors = validate(data)
        if errors:
            raise RegistryError("rejection failed: " + "; ".join(errors))
        atomic_write(path, data)
    return {"asset": asset, "from": current, "to": "rejected"}


def reconcile(path: Path, sqlite_path: Path) -> dict[str, Any]:
    data = load_registry(path)
    errors = validate(data)
    if errors:
        raise RegistryError("registry invalid: " + "; ".join(errors))
    if not sqlite_path.is_file():
        raise RegistryError(f"SQLite database missing: {sqlite_path}")
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(assets)")}
        required = {"asset_id", "sha256", "source_path", "registry_status"}
        if not required.issubset(columns):
            raise RegistryError("SQLite assets table does not match workbench schema")
        rows = conn.execute(
            "SELECT asset_id, sha256, source_path, registry_status FROM assets"
        ).fetchall()
    finally:
        conn.close()
    registry_assets = {asset["asset_id"]: asset for asset in data["assets"]}
    workbench_assets = {row["asset_id"]: dict(row) for row in rows}
    expected_registry = {
        asset_id: asset
        for asset_id, asset in workbench_assets.items()
        if asset["registry_status"] != "transient"
    }
    missing_registry = sorted(set(expected_registry) - set(registry_assets))
    missing_workbench = sorted(
        asset_id
        for asset_id in registry_assets
        if asset_id.startswith("wb-") and asset_id not in workbench_assets
    )
    hash_mismatches = sorted(
        asset_id
        for asset_id in set(expected_registry) & set(registry_assets)
        if expected_registry[asset_id]["sha256"] != registry_assets[asset_id]["sha256"]
    )
    status_conflicts = [
        {
            "asset_id": asset_id,
            "workbench_status": expected_registry[asset_id]["registry_status"],
            "registry_status": registry_assets[asset_id]["status"],
        }
        for asset_id in sorted(set(expected_registry) & set(registry_assets))
        if expected_registry[asset_id]["registry_status"] != registry_assets[asset_id]["status"]
    ]
    return {
        "ok": not (missing_registry or hash_mismatches or status_conflicts),
        "missing_registry": missing_registry,
        "missing_workbench": missing_workbench,
        "hash_mismatches": hash_mismatches,
        "status_conflicts": status_conflicts,
        "workbench_assets": len(workbench_assets),
        "registry_assets": len(registry_assets),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Atomic visual asset registry control")
    parser.add_argument("--registry", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--verify-files", action="store_true")

    register_parser = subparsers.add_parser("register-candidate")
    register_parser.add_argument("--manifest", type=Path, required=True)

    lineage_parser = subparsers.add_parser("register-lineage")
    lineage_parser.add_argument("--manifest", type=Path, required=True)

    promote_parser = subparsers.add_parser("promote")
    promote_parser.add_argument("--asset-id", required=True)
    promote_parser.add_argument("--status", required=True)
    promote_parser.add_argument("--approved-by", required=True)
    promote_parser.add_argument("--approved-at", required=True)
    promote_parser.add_argument("--decision-ref", required=True)

    reject_parser = subparsers.add_parser("reject")
    reject_parser.add_argument("--asset-id", required=True)
    reject_parser.add_argument("--notes", required=True)
    reject_parser.add_argument("--decided-by", required=True)
    reject_parser.add_argument("--decided-at", required=True)
    reject_parser.add_argument("--decision-ref", required=True)

    reconcile_parser = subparsers.add_parser("reconcile")
    reconcile_parser.add_argument("--sqlite", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry = args.registry.expanduser().resolve()
    try:
        if args.command == "check":
            data = load_registry(registry)
            errors = validate(data, args.verify_files)
            if errors:
                raise RegistryError("; ".join(errors))
            result = {"ok": True, "assets": len(data["assets"]), "registry": str(registry)}
        elif args.command == "register-candidate":
            result = register_candidate(registry, args.manifest.expanduser().resolve())
        elif args.command == "register-lineage":
            result = register_lineage(registry, args.manifest.expanduser().resolve())
        elif args.command == "promote":
            result = promote(
                registry,
                args.asset_id,
                args.status,
                args.approved_by,
                args.approved_at,
                args.decision_ref,
            )
        elif args.command == "reject":
            result = reject(
                registry,
                args.asset_id,
                args.notes,
                args.decided_by,
                args.decided_at,
                args.decision_ref,
            )
        elif args.command == "reconcile":
            result = reconcile(registry, args.sqlite.expanduser().resolve())
        else:
            raise RegistryError(f"unknown command: {args.command}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (RegistryError, OSError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
