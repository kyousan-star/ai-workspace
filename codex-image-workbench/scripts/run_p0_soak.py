#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import struct
import sys
import tempfile
import time
import zlib
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
DEFAULT_OUTPUT = ROOT / "p0" / "evidence" / "P0-SOAK-2026-07-15.json"
sys.path.insert(0, str(ROOT))

from workbench.core import Workbench
from workbench.util import iso, utcnow


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def make_png(path: Path, width: int = 64, height: int = 64) -> Path:
    row = b"\x00" + bytes((226, 231, 227)) * width
    raw = row * height
    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(raw))
    payload += png_chunk(b"IEND", b"")
    path.write_bytes(payload)
    return path


def contract(index: int, operation: str, parent_asset_id: str | None = None) -> dict:
    prefix = "G" if operation == "generate" else "E"
    return {
        "slot_key": f"SOAK-{prefix}{index:02d}",
        "execution_mode": "codex_auto",
        "operation": operation,
        "parent_asset_id": parent_asset_id,
        "prompt": "P0 state-machine soak fixture; no ImageGen call is required.",
        "invariants": ["square fixture", "single deterministic output"],
        "avoid": ["Registry write"],
        "acceptance": ["technical pass", "manual QC pass"],
        "expected_output": {"format": "png", "aspect_ratio": "1:1"},
        "idempotency_key": f"p0-soak-{operation}-{index:02d}",
        "max_attempts": 3,
        "production": {"requested_route": "concept_only", "exact_product_required": False},
    }


def run_soak(count: int, worker_count: int) -> dict:
    if count < 4 or count % 2:
        raise ValueError("count must be an even number of at least 4")
    if worker_count < 2:
        raise ValueError("worker_count must be at least 2")

    started = time.perf_counter()
    task_times: list[float] = []
    with tempfile.TemporaryDirectory(prefix="codex-image-workbench-soak-") as tmp:
        temp = Path(tmp)
        registry = temp / "asset-registry.json"
        registry.write_text(
            json.dumps({"schema_version": "1.0", "updated_at": "2026-07-15", "assets": []}),
            encoding="utf-8",
        )
        app = Workbench(
            temp / "workbench",
            registry_path=registry,
            registryctl_path=WORKSPACE / "skills" / "asset-curator" / "scripts" / "registryctl.py",
        )
        project = app.create_project(
            {
                "name": "P0 Queue Soak",
                "project_mode": "launch",
                "brand": "VLOGARA",
                "sku": "SOAK-20",
                "marketplace": "US",
            }
        )["project"]
        fixture = make_png(temp / "fixture.png")
        workers = [f"p0-soak-worker-{index + 1}" for index in range(worker_count)]
        parents: list[str] = []

        for index in range(1, count // 2 + 1):
            task_started = time.perf_counter()
            job, _ = app.create_job(project["project_id"], contract(index, "generate"))
            if index == 1:
                first_claim = app.claim_job(workers[0], 60)
                with app.connect() as conn:
                    conn.execute(
                        "UPDATE jobs SET lease_expires_at = ? WHERE job_id = ?",
                        (iso(utcnow() - timedelta(seconds=1)), first_claim["job_id"]),
                    )
                worker = workers[1]
            else:
                worker = workers[(index - 1) % worker_count]
            claimed = app.claim_job(worker, 60)
            if claimed["job_id"] != job["job_id"]:
                raise RuntimeError("queue order changed during soak")
            asset = app.complete_job(job["job_id"], worker, fixture)
            asset = app.evaluate_asset(asset["asset_id"], "passed", "P0 soak fixture", actor=worker)
            parents.append(asset["asset_id"])
            task_times.append(time.perf_counter() - task_started)

        for index in range(1, count // 2 + 1):
            task_started = time.perf_counter()
            worker = workers[(index + count // 2 - 1) % worker_count]
            job, _ = app.create_job(
                project["project_id"],
                contract(index, "edit", parents[index - 1]),
            )
            claimed = app.claim_job(worker, 60)
            if claimed["job_id"] != job["job_id"]:
                raise RuntimeError("queue order changed during edit soak")
            asset = app.complete_job(job["job_id"], worker, fixture)
            app.evaluate_asset(asset["asset_id"], "passed", "P0 soak edit fixture", actor=worker)
            task_times.append(time.perf_counter() - task_started)

        with app.connect() as conn:
            totals = dict(
                conn.execute(
                    "SELECT COUNT(*) AS jobs, "
                    "SUM(execution_status = 'succeeded') AS succeeded, "
                    "SUM(attempts) AS attempts FROM jobs"
                ).fetchone()
            )
            assets = dict(
                conn.execute(
                    "SELECT COUNT(*) AS assets, "
                    "SUM(technical_status = 'passed') AS technical_passed, "
                    "SUM(qc_status = 'passed') AS qc_passed FROM assets"
                ).fetchone()
            )
            expired_leases = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = 'lease.expired'"
            ).fetchone()[0]
            worker_rows = [dict(row) for row in conn.execute("SELECT * FROM worker_sessions ORDER BY worker_id")]

    if totals != {"jobs": count, "succeeded": count, "attempts": count + 1}:
        raise RuntimeError(f"unexpected job totals: {totals}")
    if assets != {"assets": count, "technical_passed": count, "qc_passed": count}:
        raise RuntimeError(f"unexpected asset totals: {assets}")
    if expired_leases != 1:
        raise RuntimeError(f"expected one expired lease, got {expired_leases}")

    elapsed = time.perf_counter() - started
    return {
        "schema_version": "p0-soak.1",
        "result": "PASS",
        "scope": "queue-and-state-machine-only",
        "imagegen_calls": 0,
        "limitations": [
            "Uses deterministic PNG fixtures, not Codex ImageGen.",
            "Does not measure model context capacity or image quality drift.",
        ],
        "jobs": totals,
        "assets": assets,
        "operations": {"generate": count // 2, "edit": count // 2},
        "workers": worker_rows,
        "worker_count": worker_count,
        "expired_lease_recoveries": expired_leases,
        "elapsed_seconds": round(elapsed, 4),
        "median_task_seconds": round(sorted(task_times)[len(task_times) // 2], 4),
        "max_task_seconds": round(max(task_times), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the P0 queue and state-machine soak test")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run_soak(args.count, args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Evidence: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
