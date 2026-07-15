#!/usr/bin/env python3
"""P-1 persistent queue and manual-import spike for Codex Image Workbench."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB = Path(__file__).resolve().parent / "state" / "workbench-p1.sqlite"
ALLOWED_MODES = {"codex_auto", "manual_import"}
ALLOWED_OPERATIONS = {"generate", "edit"}
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


class WorkbenchError(RuntimeError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or utcnow()).isoformat(timespec="milliseconds")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def encode_crockford(value: int, length: int) -> str:
    chars = []
    for _ in range(length):
        chars.append(CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def new_ulid() -> str:
    timestamp_ms = int(time.time() * 1000)
    randomness = int.from_bytes(os.urandom(10), "big")
    return encode_crockford(timestamp_ms, 10) + encode_crockford(randomness, 16)


def slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in cleaned.split("-") if part) or "unknown"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise WorkbenchError(f"database does not exist; run init first: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db(db_path: Path, workspace: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            PRAGMA journal_mode = WAL;
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                execution_mode TEXT NOT NULL CHECK (execution_mode IN ('codex_auto', 'manual_import')),
                operation TEXT NOT NULL CHECK (operation IN ('generate', 'edit')),
                status TEXT NOT NULL CHECK (status IN (
                    'queued', 'leased', 'awaiting_import', 'succeeded',
                    'failed', 'cancelled'
                )),
                asset_id TEXT NOT NULL,
                parent_asset_id TEXT,
                slot TEXT NOT NULL,
                contract_json TEXT NOT NULL,
                input_count INTEGER NOT NULL DEFAULT 0,
                input_bytes INTEGER NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                lease_owner TEXT,
                lease_expires_at TEXT,
                queued_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                output_path TEXT,
                output_sha256 TEXT,
                output_bytes INTEGER,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                event_type TEXT NOT NULL,
                worker_id TEXT,
                at TEXT NOT NULL,
                detail_json TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(job_id)
            );

            CREATE TABLE IF NOT EXISTS worker_sessions (
                worker_id TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                claimed_count INTEGER NOT NULL DEFAULT 0,
                completed_count INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS jobs_status_queue
                ON jobs(status, execution_mode, queued_at);
            CREATE INDEX IF NOT EXISTS events_job_time
                ON events(job_id, at);
            """
        )
        conn.execute(
            "INSERT INTO settings(key, value) VALUES('workspace', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(workspace.resolve()),),
        )
        conn.commit()
    finally:
        conn.close()


def setting(conn: sqlite3.Connection, key: str) -> str:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if not row:
        raise WorkbenchError(f"missing setting: {key}")
    return str(row["value"])


def add_event(
    conn: sqlite3.Connection,
    event_type: str,
    job_id: str | None = None,
    worker_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        "INSERT INTO events(job_id, event_type, worker_id, at, detail_json) VALUES(?, ?, ?, ?, ?)",
        (job_id, event_type, worker_id, iso(), json_dump(detail or {})),
    )


def touch_worker(conn: sqlite3.Connection, worker_id: str, counter: str | None = None) -> None:
    now = iso()
    conn.execute(
        "INSERT INTO worker_sessions(worker_id, first_seen_at, last_seen_at) VALUES(?, ?, ?) "
        "ON CONFLICT(worker_id) DO UPDATE SET last_seen_at = excluded.last_seen_at",
        (worker_id, now, now),
    )
    if counter:
        if counter not in {"claimed_count", "completed_count", "failed_count"}:
            raise WorkbenchError(f"invalid worker counter: {counter}")
        conn.execute(
            f"UPDATE worker_sessions SET {counter} = {counter} + 1, last_seen_at = ? WHERE worker_id = ?",
            (now, worker_id),
        )


def read_contract(path: Path) -> dict[str, Any]:
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkbenchError(f"cannot read contract {path}: {exc}") from exc
    required = {"project_id", "brand", "sku", "kind", "slot", "operation", "prompt"}
    missing = sorted(required - set(contract))
    if missing:
        raise WorkbenchError(f"contract missing fields: {', '.join(missing)}")
    if contract["operation"] not in ALLOWED_OPERATIONS:
        raise WorkbenchError(f"invalid operation: {contract['operation']}")
    if not isinstance(contract.get("references", []), list):
        raise WorkbenchError("contract.references must be a list")
    return contract


def reference_stats(contract: dict[str, Any]) -> tuple[int, int]:
    count = 0
    total = 0
    for reference in contract.get("references", []):
        raw_path = reference.get("path") if isinstance(reference, dict) else reference
        if not raw_path:
            continue
        path = Path(str(raw_path)).expanduser()
        count += 1
        if path.is_file():
            total += path.stat().st_size
    return count, total


def create_job(
    conn: sqlite3.Connection,
    contract: dict[str, Any],
    mode: str,
    idempotency_key: str | None,
    max_attempts: int,
) -> tuple[sqlite3.Row, bool]:
    if mode not in ALLOWED_MODES:
        raise WorkbenchError(f"invalid execution mode: {mode}")
    if max_attempts < 1:
        raise WorkbenchError("max_attempts must be at least 1")
    canonical = json_dump(contract)
    key = idempotency_key or hashlib.sha256(f"{mode}:{canonical}".encode()).hexdigest()
    existing = conn.execute("SELECT * FROM jobs WHERE idempotency_key = ?", (key,)).fetchone()
    if existing:
        return existing, False

    job_id = f"job_{new_ulid()}"
    asset_id = contract.get("asset_id") or (
        f"wb-{slug(str(contract['brand']))}-{slug(str(contract['sku']))}-"
        f"{slug(str(contract['kind']))}-{new_ulid()}"
    )
    status = "queued" if mode == "codex_auto" else "awaiting_import"
    input_count, input_bytes = reference_stats(contract)
    conn.execute(
        """
        INSERT INTO jobs(
            job_id, idempotency_key, project_id, execution_mode, operation,
            status, asset_id, parent_asset_id, slot, contract_json,
            input_count, input_bytes, max_attempts, queued_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            key,
            contract["project_id"],
            mode,
            contract["operation"],
            status,
            asset_id,
            contract.get("parent_asset_id"),
            contract["slot"],
            canonical,
            input_count,
            input_bytes,
            max_attempts,
            iso(),
        ),
    )
    add_event(conn, "job.created", job_id, detail={"mode": mode, "status": status})
    conn.commit()
    return conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone(), True


def reclaim_expired(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        "SELECT job_id, lease_owner FROM jobs "
        "WHERE status = 'leased' AND lease_expires_at <= ?",
        (iso(),),
    ).fetchall()
    for row in rows:
        conn.execute(
            "UPDATE jobs SET status = 'queued', lease_owner = NULL, lease_expires_at = NULL "
            "WHERE job_id = ? AND status = 'leased'",
            (row["job_id"],),
        )
        add_event(
            conn,
            "lease.expired",
            row["job_id"],
            row["lease_owner"],
            {"requeued": True},
        )
    return len(rows)


def claim_job(conn: sqlite3.Connection, worker: str, lease_seconds: int) -> sqlite3.Row | None:
    if lease_seconds < 1:
        raise WorkbenchError("lease_seconds must be at least 1")
    conn.execute("BEGIN IMMEDIATE")
    reclaim_expired(conn)
    row = conn.execute(
        "SELECT * FROM jobs WHERE status = 'queued' AND execution_mode = 'codex_auto' "
        "AND attempts < max_attempts ORDER BY queued_at, job_id LIMIT 1"
    ).fetchone()
    if not row:
        conn.commit()
        return None
    expiry = iso(utcnow() + timedelta(seconds=lease_seconds))
    cursor = conn.execute(
        "UPDATE jobs SET status = 'leased', lease_owner = ?, lease_expires_at = ?, "
        "attempts = attempts + 1, started_at = COALESCE(started_at, ?), error = NULL "
        "WHERE job_id = ? AND status = 'queued'",
        (worker, expiry, iso(), row["job_id"]),
    )
    if cursor.rowcount != 1:
        conn.rollback()
        raise WorkbenchError("job was claimed concurrently")
    touch_worker(conn, worker, "claimed_count")
    add_event(conn, "lease.claimed", row["job_id"], worker, {"expires_at": expiry})
    conn.commit()
    return conn.execute("SELECT * FROM jobs WHERE job_id = ?", (row["job_id"],)).fetchone()


def heartbeat(conn: sqlite3.Connection, job_id: str, worker: str, lease_seconds: int) -> sqlite3.Row:
    row = get_job(conn, job_id)
    if row["status"] != "leased" or row["lease_owner"] != worker:
        raise WorkbenchError("heartbeat rejected: worker does not hold this lease")
    expiry = iso(utcnow() + timedelta(seconds=lease_seconds))
    conn.execute("UPDATE jobs SET lease_expires_at = ? WHERE job_id = ?", (expiry, job_id))
    touch_worker(conn, worker)
    add_event(conn, "lease.heartbeat", job_id, worker, {"expires_at": expiry})
    conn.commit()
    return get_job(conn, job_id)


def get_job(conn: sqlite3.Connection, job_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    if not row:
        raise WorkbenchError(f"unknown job: {job_id}")
    return row


def result_destination(conn: sqlite3.Connection, row: sqlite3.Row, source: Path) -> Path:
    workspace = Path(setting(conn, "workspace"))
    suffix = source.suffix.lower() or ".bin"
    directory = workspace / "artifacts" / "results" / slug(row["project_id"])
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{row['asset_id']}-{row['job_id']}{suffix}"


def persist_result(conn: sqlite3.Connection, row: sqlite3.Row, source: Path) -> tuple[Path, str, int]:
    if not source.is_file():
        raise WorkbenchError(f"result file does not exist: {source}")
    source_hash = sha256_file(source)
    destination = result_destination(conn, row, source)
    if destination.exists():
        existing_hash = sha256_file(destination)
        if existing_hash != source_hash:
            raise WorkbenchError(f"refusing to overwrite different result: {destination}")
    elif source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return destination, source_hash, destination.stat().st_size


def complete_job(
    conn: sqlite3.Connection,
    job_id: str,
    worker: str,
    output: Path,
) -> sqlite3.Row:
    row = get_job(conn, job_id)
    if row["status"] == "succeeded":
        if row["output_sha256"] == sha256_file(output):
            return row
        raise WorkbenchError("job already succeeded with a different output")
    if row["status"] != "leased" or row["lease_owner"] != worker:
        raise WorkbenchError("completion rejected: worker does not hold this lease")
    destination, digest, size = persist_result(conn, row, output)
    conn.execute(
        "UPDATE jobs SET status = 'succeeded', finished_at = ?, output_path = ?, "
        "output_sha256 = ?, output_bytes = ?, lease_expires_at = NULL, error = NULL "
        "WHERE job_id = ?",
        (iso(), str(destination), digest, size, job_id),
    )
    touch_worker(conn, worker, "completed_count")
    add_event(
        conn,
        "job.completed",
        job_id,
        worker,
        {"output_path": str(destination), "sha256": digest, "bytes": size},
    )
    conn.commit()
    return get_job(conn, job_id)


def fail_job(
    conn: sqlite3.Connection,
    job_id: str,
    worker: str,
    error: str,
    retry: bool,
) -> sqlite3.Row:
    row = get_job(conn, job_id)
    if row["status"] != "leased" or row["lease_owner"] != worker:
        raise WorkbenchError("failure rejected: worker does not hold this lease")
    can_retry = retry and row["attempts"] < row["max_attempts"]
    status = "queued" if can_retry else "failed"
    finished_at = None if can_retry else iso()
    conn.execute(
        "UPDATE jobs SET status = ?, finished_at = ?, error = ?, lease_owner = NULL, "
        "lease_expires_at = NULL WHERE job_id = ?",
        (status, finished_at, error, job_id),
    )
    touch_worker(conn, worker, "failed_count")
    add_event(conn, "job.retry" if can_retry else "job.failed", job_id, worker, {"error": error})
    conn.commit()
    return get_job(conn, job_id)


def export_package(conn: sqlite3.Connection, job_id: str, output_root: Path) -> Path:
    row = get_job(conn, job_id)
    contract = json.loads(row["contract_json"])
    package = output_root / job_id
    package.mkdir(parents=True, exist_ok=True)
    packaged_references = []
    for index, reference in enumerate(contract.get("references", []), start=1):
        raw_path = reference.get("path") if isinstance(reference, dict) else reference
        role = reference.get("role", "reference") if isinstance(reference, dict) else "reference"
        source = Path(str(raw_path)).expanduser() if raw_path else None
        record = {"index": index, "role": role, "source_path": str(raw_path or "")}
        if source and source.is_file():
            reference_dir = package / "references"
            reference_dir.mkdir(parents=True, exist_ok=True)
            destination = reference_dir / f"{index:02d}-{slug(str(role))}-{source.name}"
            if not destination.exists():
                shutil.copy2(source, destination)
            record.update(
                {
                    "package_path": str(destination.relative_to(package)),
                    "sha256": sha256_file(destination),
                    "bytes": destination.stat().st_size,
                }
            )
        else:
            record["missing"] = True
        packaged_references.append(record)
    manifest = {
        "schema_version": "p1.1",
        "job_id": row["job_id"],
        "asset_id": row["asset_id"],
        "parent_asset_id": row["parent_asset_id"],
        "project_id": row["project_id"],
        "slot": row["slot"],
        "execution_mode": row["execution_mode"],
        "contract": contract,
        "packaged_references": packaged_references,
    }
    (package / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    prompt_lines = [
        f"# Generation Package {job_id}",
        "",
        f"Asset ID: {row['asset_id']}",
        f"Project: {row['project_id']}",
        f"Slot: {row['slot']}",
        "",
        "## Prompt",
        "",
        str(contract["prompt"]),
        "",
        "## Invariants",
        "",
    ]
    prompt_lines.extend(f"- {item}" for item in contract.get("invariants", []))
    prompt_lines.extend(["", "## Avoid", ""])
    prompt_lines.extend(f"- {item}" for item in contract.get("avoid", []))
    prompt_lines.extend(["", "## Acceptance", ""])
    prompt_lines.extend(f"- {item}" for item in contract.get("acceptance", []))
    (package / "PROMPT.md").write_text("\n".join(prompt_lines) + "\n", encoding="utf-8")
    add_event(conn, "package.exported", job_id, detail={"path": str(package)})
    conn.commit()
    return package


def import_result(conn: sqlite3.Connection, job_id: str, source: Path) -> sqlite3.Row:
    row = get_job(conn, job_id)
    if row["execution_mode"] != "manual_import":
        raise WorkbenchError("import-result is only valid for manual_import jobs")
    if row["status"] == "succeeded":
        if row["output_sha256"] == sha256_file(source):
            return row
        raise WorkbenchError("job already succeeded with a different output")
    if row["status"] != "awaiting_import":
        raise WorkbenchError(f"manual job is not awaiting import: {row['status']}")
    destination, digest, size = persist_result(conn, row, source)
    conn.execute(
        "UPDATE jobs SET status = 'succeeded', started_at = COALESCE(started_at, queued_at), "
        "finished_at = ?, output_path = ?, output_sha256 = ?, output_bytes = ?, error = NULL "
        "WHERE job_id = ?",
        (iso(), str(destination), digest, size, job_id),
    )
    add_event(
        conn,
        "result.imported",
        job_id,
        detail={"output_path": str(destination), "sha256": digest, "bytes": size},
    )
    conn.commit()
    return get_job(conn, job_id)


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    if "contract_json" in value:
        value["contract"] = json.loads(value.pop("contract_json"))
    if "detail_json" in value:
        value["detail"] = json.loads(value.pop("detail_json"))
    return value


def throughput_report(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute("SELECT * FROM jobs ORDER BY queued_at, job_id").fetchall()
    durations = []
    queue_delays = []
    for row in rows:
        if row["started_at"] and row["finished_at"]:
            durations.append((parse_time(row["finished_at"]) - parse_time(row["started_at"])).total_seconds())
        if row["started_at"]:
            queue_delays.append((parse_time(row["started_at"]) - parse_time(row["queued_at"])).total_seconds())
    workers = [row_to_dict(row) for row in conn.execute(
        "SELECT * FROM worker_sessions ORDER BY first_seen_at"
    ).fetchall()]
    statuses = {
        row["status"]: row["count"]
        for row in conn.execute("SELECT status, COUNT(*) AS count FROM jobs GROUP BY status")
    }
    return {
        "generated_at": iso(),
        "total_jobs": len(rows),
        "statuses": statuses,
        "successful_auto_jobs": sum(
            1 for row in rows if row["execution_mode"] == "codex_auto" and row["status"] == "succeeded"
        ),
        "successful_manual_jobs": sum(
            1 for row in rows if row["execution_mode"] == "manual_import" and row["status"] == "succeeded"
        ),
        "duration_seconds": {
            "count": len(durations),
            "median": statistics.median(durations) if durations else None,
            "max": max(durations) if durations else None,
        },
        "queue_delay_seconds": {
            "count": len(queue_delays),
            "median": statistics.median(queue_delays) if queue_delays else None,
            "max": max(queue_delays) if queue_delays else None,
        },
        "workers": workers,
    }


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent)

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--contract", type=Path, required=True)
    create_parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), required=True)
    create_parser.add_argument("--idempotency-key")
    create_parser.add_argument("--max-attempts", type=int, default=3)

    claim_parser = subparsers.add_parser("claim")
    claim_parser.add_argument("--worker", required=True)
    claim_parser.add_argument("--lease-seconds", type=int, default=900)

    heartbeat_parser = subparsers.add_parser("heartbeat")
    heartbeat_parser.add_argument("--job", required=True)
    heartbeat_parser.add_argument("--worker", required=True)
    heartbeat_parser.add_argument("--lease-seconds", type=int, default=900)

    complete_parser = subparsers.add_parser("complete")
    complete_parser.add_argument("--job", required=True)
    complete_parser.add_argument("--worker", required=True)
    complete_parser.add_argument("--output", type=Path, required=True)

    fail_parser = subparsers.add_parser("fail")
    fail_parser.add_argument("--job", required=True)
    fail_parser.add_argument("--worker", required=True)
    fail_parser.add_argument("--error", required=True)
    fail_parser.add_argument("--retry", action="store_true")

    subparsers.add_parser("recover-expired")

    export_parser = subparsers.add_parser("export-package")
    export_parser.add_argument("--job", required=True)
    export_parser.add_argument("--out", type=Path, required=True)

    import_parser = subparsers.add_parser("import-result")
    import_parser.add_argument("--job", required=True)
    import_parser.add_argument("--file", type=Path, required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--status")

    events_parser = subparsers.add_parser("events")
    events_parser.add_argument("--job")
    events_parser.add_argument("--limit", type=int, default=100)

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--out", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db_path = args.db.expanduser().resolve()
    try:
        if args.command == "init":
            init_db(db_path, args.workspace.expanduser().resolve())
            print_json({"ok": True, "database": str(db_path), "workspace": str(args.workspace.resolve())})
            return 0

        conn = connect(db_path)
        try:
            if args.command == "create":
                row, created = create_job(
                    conn,
                    read_contract(args.contract),
                    args.mode,
                    args.idempotency_key,
                    args.max_attempts,
                )
                value = row_to_dict(row)
                value["created"] = created
                print_json(value)
            elif args.command == "claim":
                row = claim_job(conn, args.worker, args.lease_seconds)
                print_json(row_to_dict(row) if row else {"job": None})
            elif args.command == "heartbeat":
                print_json(row_to_dict(heartbeat(conn, args.job, args.worker, args.lease_seconds)))
            elif args.command == "complete":
                print_json(row_to_dict(complete_job(conn, args.job, args.worker, args.output.resolve())))
            elif args.command == "fail":
                print_json(row_to_dict(fail_job(conn, args.job, args.worker, args.error, args.retry)))
            elif args.command == "recover-expired":
                conn.execute("BEGIN IMMEDIATE")
                count = reclaim_expired(conn)
                conn.commit()
                print_json({"recovered": count})
            elif args.command == "export-package":
                package = export_package(conn, args.job, args.out.resolve())
                print_json({"job_id": args.job, "package": str(package)})
            elif args.command == "import-result":
                print_json(row_to_dict(import_result(conn, args.job, args.file.resolve())))
            elif args.command == "list":
                if args.status:
                    rows = conn.execute(
                        "SELECT * FROM jobs WHERE status = ? ORDER BY queued_at, job_id", (args.status,)
                    ).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM jobs ORDER BY queued_at, job_id").fetchall()
                print_json([row_to_dict(row) for row in rows])
            elif args.command == "events":
                if args.job:
                    rows = conn.execute(
                        "SELECT * FROM events WHERE job_id = ? ORDER BY event_id DESC LIMIT ?",
                        (args.job, args.limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM events ORDER BY event_id DESC LIMIT ?", (args.limit,)
                    ).fetchall()
                print_json([row_to_dict(row) for row in rows])
            elif args.command == "report":
                report = throughput_report(conn)
                if args.out:
                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    args.out.write_text(
                        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                    )
                print_json(report)
            else:
                raise WorkbenchError(f"unknown command: {args.command}")
        finally:
            conn.close()
    except (WorkbenchError, sqlite3.Error, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
