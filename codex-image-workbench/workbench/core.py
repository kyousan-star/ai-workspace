from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from . import db
from .p1 import build_coverage, normalize_intake, validate_contracts, validate_sequence, validate_strategy
from .p2 import (
    build_optimization_readiness,
    normalize_interference_event,
    normalize_observation,
    normalize_optimization_intake,
    validate_diagnosis,
    validate_evaluation,
    validate_optimization_contracts,
)
from .util import WorkbenchError, iso, json_dump, new_ulid, sha256_file, slug, technical_check, utcnow


ALLOWED_MODES = {"codex_auto", "manual_import"}
ALLOWED_OPERATIONS = {"generate", "edit"}
QC_STATUSES = {"needs_review", "passed", "failed"}


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    value = dict(row)
    for field in (
        "contract_json",
        "technical_checks_json",
        "evidence_json",
        "detail_json",
        "metrics_json",
        "release_json",
    ):
        if field in value:
            decoded_name = field.removesuffix("_json")
            value[decoded_name] = json.loads(value.pop(field))
    return value


class Workbench:
    def __init__(
        self,
        root: Path,
        db_path: Path | None = None,
        registry_path: Path | None = None,
        registryctl_path: Path | None = None,
    ) -> None:
        self.root = root.resolve()
        self.runtime = self.root / "runtime"
        self.db_path = (db_path or self.runtime / "workbench.sqlite").resolve()
        workspace_root = self.root.parent
        self.registry_path = (
            registry_path or workspace_root / "visual-lab" / "asset-registry.json"
        ).resolve()
        self.registryctl_path = (
            registryctl_path
            or workspace_root / "skills" / "asset-curator" / "scripts" / "registryctl.py"
        ).resolve()
        db.initialize(self.db_path, self.root)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = db.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def event(
        self,
        conn: sqlite3.Connection,
        entity_type: str,
        entity_id: str,
        event_type: str,
        actor: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            "INSERT INTO events(entity_type, entity_id, event_type, actor, detail_json, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (entity_type, entity_id, event_type, actor, json_dump(detail or {}), iso()),
        )

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = {"name", "project_mode", "brand", "sku", "marketplace"}
        missing = sorted(field for field in required if not str(payload.get(field, "")).strip())
        if missing:
            raise WorkbenchError(f"missing project fields: {', '.join(missing)}")
        if payload["project_mode"] not in {"launch", "optimize"}:
            raise WorkbenchError("project_mode must be launch or optimize")
        project_id = f"prj_{new_ulid()}"
        now = iso()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO projects(project_id, name, project_mode, brand, sku, marketplace, created_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    project_id,
                    str(payload["name"]).strip(),
                    payload["project_mode"],
                    str(payload["brand"]).strip(),
                    str(payload["sku"]).strip(),
                    str(payload["marketplace"]).strip(),
                    now,
                    now,
                ),
            )
            self.event(conn, "project", project_id, "project.created", detail=payload)
        return self.get_project(project_id)

    def list_projects(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT p.*,
                    (SELECT COUNT(*) FROM jobs j WHERE j.project_id = p.project_id) AS job_count,
                    (SELECT COUNT(*) FROM assets a WHERE a.project_id = p.project_id) AS asset_count,
                    (SELECT COUNT(*) FROM jobs j WHERE j.project_id = p.project_id
                        AND j.execution_status IN ('queued', 'leased', 'awaiting_import')) AS open_job_count
                FROM projects p ORDER BY p.updated_at DESC
                """
            ).fetchall()
        return [row_dict(row) for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            project = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
            if not project:
                raise WorkbenchError(f"unknown project: {project_id}")
            slots = conn.execute(
                "SELECT * FROM image_slots WHERE project_id = ? ORDER BY position, slot_key", (project_id,)
            ).fetchall()
            jobs = conn.execute(
                """
                SELECT j.*, s.slot_key, s.title AS slot_title
                FROM jobs j JOIN image_slots s ON s.slot_id = j.slot_id
                WHERE j.project_id = ? ORDER BY j.queued_at DESC
                """,
                (project_id,),
            ).fetchall()
            assets = conn.execute(
                """
                SELECT a.*, s.slot_key, s.title AS slot_title
                FROM assets a JOIN image_slots s ON s.slot_id = a.slot_id
                WHERE a.project_id = ? ORDER BY a.created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return {
            "project": row_dict(project),
            "slots": [row_dict(row) for row in slots],
            "jobs": [row_dict(row) for row in jobs],
            "assets": [row_dict(row) for row in assets],
        }

    def dashboard(self) -> dict[str, Any]:
        with self.connect() as conn:
            counts = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM projects WHERE status = 'active') AS active_projects,
                    (SELECT COUNT(*) FROM jobs WHERE execution_status = 'queued') AS queued_jobs,
                    (SELECT COUNT(*) FROM jobs WHERE execution_status = 'awaiting_import') AS awaiting_import,
                    (SELECT COUNT(*) FROM assets WHERE qc_status = 'needs_review' OR qc_status = 'not_run') AS needs_qc,
                    (SELECT COUNT(*) FROM assets WHERE registry_status = 'candidate') AS candidates
                """
            ).fetchone()
        return {"counts": row_dict(counts), "projects": self.list_projects()}

    def ensure_slot(
        self,
        conn: sqlite3.Connection,
        project_id: str,
        slot_key: str,
        title: str | None = None,
    ) -> sqlite3.Row:
        row = conn.execute(
            "SELECT * FROM image_slots WHERE project_id = ? AND slot_key = ?",
            (project_id, slot_key),
        ).fetchone()
        if row:
            return row
        position = conn.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM image_slots WHERE project_id = ?",
            (project_id,),
        ).fetchone()[0]
        slot_id = f"slot_{new_ulid()}"
        conn.execute(
            "INSERT INTO image_slots(slot_id, project_id, slot_key, title, position, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (slot_id, project_id, slot_key, title or slot_key, position, iso()),
        )
        return conn.execute("SELECT * FROM image_slots WHERE slot_id = ?", (slot_id,)).fetchone()

    def create_job(self, project_id: str, payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        mode = payload.get("execution_mode")
        operation = payload.get("operation", "generate")
        slot_key = str(payload.get("slot_key", "")).strip()
        prompt = str(payload.get("prompt", "")).strip()
        if mode not in ALLOWED_MODES:
            raise WorkbenchError("execution_mode must be codex_auto or manual_import")
        if operation not in ALLOWED_OPERATIONS:
            raise WorkbenchError("operation must be generate or edit")
        if not slot_key or not prompt:
            raise WorkbenchError("slot_key and prompt are required")
        max_attempts = int(payload.get("max_attempts", 3))
        if max_attempts < 1 or max_attempts > 5:
            raise WorkbenchError("max_attempts must be between 1 and 5")

        with self.connect() as conn:
            project = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
            if not project:
                raise WorkbenchError(f"unknown project: {project_id}")
            parent_asset_id = payload.get("parent_asset_id") or None
            if operation == "edit" and not parent_asset_id:
                raise WorkbenchError("edit jobs require parent_asset_id")
            if parent_asset_id:
                parent = conn.execute(
                    "SELECT asset_id FROM assets WHERE asset_id = ? AND project_id = ?",
                    (parent_asset_id, project_id),
                ).fetchone()
                if not parent:
                    raise WorkbenchError(f"unknown parent asset: {parent_asset_id}")

            slot = self.ensure_slot(conn, project_id, slot_key, payload.get("slot_title"))
            contract = {
                "project_id": project_id,
                "brand": project["brand"],
                "sku": project["sku"],
                "kind": payload.get("kind", "listing-image"),
                "slot": slot_key,
                "operation": operation,
                "prompt": prompt,
                "references": payload.get("references", []),
                "invariants": payload.get("invariants", []),
                "avoid": payload.get("avoid", []),
                "acceptance": payload.get("acceptance", []),
                "expected_output": payload.get(
                    "expected_output", {"format": "png", "aspect_ratio": "1:1"}
                ),
            }
            for field in (
                "claim_ids",
                "claims",
                "product_invariants",
                "brand_invariants",
                "change_only",
                "contract_id",
                "optimization_contract_id",
                "issue_id",
                "challenge_key",
                "target_metrics",
                "observation_days",
            ):
                if field in payload:
                    contract[field] = payload[field]
            if parent_asset_id:
                contract["parent_asset_id"] = parent_asset_id
            canonical = json_dump(contract)
            key = payload.get("idempotency_key") or hashlib.sha256(
                f"{mode}:{canonical}".encode()
            ).hexdigest()
            existing = conn.execute(
                "SELECT * FROM jobs WHERE idempotency_key = ?", (key,)
            ).fetchone()
            if existing:
                return row_dict(existing), False

            job_id = f"job_{new_ulid()}"
            target_asset_id = (
                payload.get("target_asset_id")
                or f"wb-{slug(project['brand'])}-{slug(project['sku'])}-{slug(contract['kind'])}-{new_ulid()}"
            )
            status = "queued" if mode == "codex_auto" else "awaiting_import"
            conn.execute(
                """
                INSERT INTO jobs(
                    job_id, idempotency_key, project_id, slot_id, execution_mode,
                    operation, execution_status, target_asset_id, parent_asset_id,
                    contract_json, max_attempts, queued_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    key,
                    project_id,
                    slot["slot_id"],
                    mode,
                    operation,
                    status,
                    target_asset_id,
                    parent_asset_id,
                    canonical,
                    max_attempts,
                    iso(),
                ),
            )
            conn.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?", (iso(), project_id))
            self.event(
                conn,
                "job",
                job_id,
                "job.created",
                detail={"execution_mode": mode, "execution_status": status},
            )
            created = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return row_dict(created), True

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT j.*, s.slot_key, s.title AS slot_title
                FROM jobs j JOIN image_slots s ON s.slot_id = j.slot_id
                WHERE j.job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if not row:
            raise WorkbenchError(f"unknown job: {job_id}")
        return row_dict(row)

    def list_jobs(self, project_id: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE project_id = ? ORDER BY queued_at DESC", (project_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM jobs ORDER BY queued_at DESC").fetchall()
        return [row_dict(row) for row in rows]

    def _touch_worker(self, conn: sqlite3.Connection, worker: str, counter: str | None = None) -> None:
        now = iso()
        conn.execute(
            "INSERT INTO worker_sessions(worker_id, first_seen_at, last_seen_at) VALUES(?, ?, ?) "
            "ON CONFLICT(worker_id) DO UPDATE SET last_seen_at = excluded.last_seen_at",
            (worker, now, now),
        )
        if counter:
            if counter not in {"claimed_count", "completed_count", "failed_count"}:
                raise WorkbenchError("invalid worker counter")
            conn.execute(
                f"UPDATE worker_sessions SET {counter} = {counter} + 1 WHERE worker_id = ?",
                (worker,),
            )

    def _reclaim_expired(self, conn: sqlite3.Connection) -> int:
        rows = conn.execute(
            "SELECT job_id, lease_owner FROM jobs WHERE execution_status = 'leased' "
            "AND lease_expires_at <= ?",
            (iso(),),
        ).fetchall()
        for row in rows:
            conn.execute(
                "UPDATE jobs SET execution_status = 'queued', lease_owner = NULL, lease_expires_at = NULL "
                "WHERE job_id = ?",
                (row["job_id"],),
            )
            self.event(
                conn,
                "job",
                row["job_id"],
                "lease.expired",
                row["lease_owner"],
                {"requeued": True},
            )
        return len(rows)

    def claim_job(self, worker: str, lease_seconds: int = 900) -> dict[str, Any] | None:
        if not worker:
            raise WorkbenchError("worker is required")
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._reclaim_expired(conn)
            row = conn.execute(
                "SELECT * FROM jobs WHERE execution_status = 'queued' "
                "AND execution_mode = 'codex_auto' AND attempts < max_attempts "
                "ORDER BY queued_at, job_id LIMIT 1"
            ).fetchone()
            if not row:
                return None
            expiry = iso(utcnow() + timedelta(seconds=lease_seconds))
            conn.execute(
                "UPDATE jobs SET execution_status = 'leased', lease_owner = ?, lease_expires_at = ?, "
                "attempts = attempts + 1, started_at = COALESCE(started_at, ?) WHERE job_id = ?",
                (worker, expiry, iso(), row["job_id"]),
            )
            self._touch_worker(conn, worker, "claimed_count")
            self.event(conn, "job", row["job_id"], "lease.claimed", worker, {"expires_at": expiry})
        return self.get_job(row["job_id"])

    def heartbeat(self, job_id: str, worker: str, lease_seconds: int = 900) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if not row or row["execution_status"] != "leased" or row["lease_owner"] != worker:
                raise WorkbenchError("worker does not hold this lease")
            expiry = iso(utcnow() + timedelta(seconds=lease_seconds))
            conn.execute("UPDATE jobs SET lease_expires_at = ? WHERE job_id = ?", (expiry, job_id))
            self._touch_worker(conn, worker)
            self.event(conn, "job", job_id, "lease.heartbeat", worker, {"expires_at": expiry})
        return self.get_job(job_id)

    def _persist_result(self, job: sqlite3.Row, source: Path) -> tuple[Path, str, int]:
        if not source.is_file():
            raise WorkbenchError(f"result file does not exist: {source}")
        digest = sha256_file(source)
        directory = self.runtime / "projects" / slug(job["project_id"]) / "assets"
        directory.mkdir(parents=True, exist_ok=True)
        suffix = source.suffix.lower() or ".bin"
        destination = directory / f"{job['target_asset_id']}{suffix}"
        if destination.exists():
            if sha256_file(destination) != digest:
                raise WorkbenchError(f"refusing to overwrite different result: {destination}")
        elif source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        return destination, digest, destination.stat().st_size

    def _finish_job(self, job_id: str, source: Path, worker: str | None) -> dict[str, Any]:
        with self.connect() as conn:
            job = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if not job:
                raise WorkbenchError(f"unknown job: {job_id}")
            if job["execution_status"] == "succeeded":
                asset = conn.execute("SELECT * FROM assets WHERE job_id = ?", (job_id,)).fetchone()
                if asset and asset["sha256"] == sha256_file(source):
                    return row_dict(asset)
                raise WorkbenchError("job already succeeded with a different result")
            if job["execution_mode"] == "codex_auto":
                if job["execution_status"] != "leased" or job["lease_owner"] != worker:
                    raise WorkbenchError("worker does not hold this lease")
            elif job["execution_status"] != "awaiting_import":
                raise WorkbenchError("manual job is not awaiting import")

            destination, digest, _ = self._persist_result(job, source)
            contract = json.loads(job["contract_json"])
            technical = technical_check(destination, contract)
            metadata = technical["metadata"]
            now = iso()
            conn.execute(
                """
                INSERT INTO assets(
                    asset_id, project_id, slot_id, job_id, parent_asset_id, source_type,
                    source_path, sha256, file_format, width, height, technical_status,
                    technical_checks_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["target_asset_id"],
                    job["project_id"],
                    job["slot_id"],
                    job_id,
                    job["parent_asset_id"],
                    job["execution_mode"],
                    str(destination),
                    digest,
                    metadata.get("format"),
                    metadata.get("width"),
                    metadata.get("height"),
                    technical["status"],
                    json_dump(technical),
                    now,
                ),
            )
            conn.execute(
                "UPDATE jobs SET execution_status = 'succeeded', finished_at = ?, "
                "lease_expires_at = NULL, error = NULL WHERE job_id = ?",
                (now, job_id),
            )
            if worker:
                self._touch_worker(conn, worker, "completed_count")
            self.event(
                conn,
                "asset",
                job["target_asset_id"],
                "asset.ingested",
                worker,
                {"technical_status": technical["status"], "sha256": digest},
            )
            conn.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?", (now, job["project_id"]))
            asset = conn.execute("SELECT * FROM assets WHERE job_id = ?", (job_id,)).fetchone()
        return row_dict(asset)

    def complete_job(self, job_id: str, worker: str, source: Path) -> dict[str, Any]:
        return self._finish_job(job_id, source.resolve(), worker)

    def import_result(self, job_id: str, source: Path) -> dict[str, Any]:
        return self._finish_job(job_id, source.resolve(), None)

    def fail_job(self, job_id: str, worker: str, error: str, retry: bool) -> dict[str, Any]:
        with self.connect() as conn:
            job = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if not job or job["execution_status"] != "leased" or job["lease_owner"] != worker:
                raise WorkbenchError("worker does not hold this lease")
            can_retry = retry and job["attempts"] < job["max_attempts"]
            status = "queued" if can_retry else "failed"
            conn.execute(
                "UPDATE jobs SET execution_status = ?, error = ?, finished_at = ?, "
                "lease_owner = NULL, lease_expires_at = NULL WHERE job_id = ?",
                (status, error, None if can_retry else iso(), job_id),
            )
            self._touch_worker(conn, worker, "failed_count")
            self.event(conn, "job", job_id, "job.retry" if can_retry else "job.failed", worker, {"error": error})
        return self.get_job(job_id)

    def export_package(self, job_id: str) -> Path:
        with self.connect() as conn:
            job = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if not job:
                raise WorkbenchError(f"unknown job: {job_id}")
            contract = json.loads(job["contract_json"])
        package = self.runtime / "exports" / job_id
        package.mkdir(parents=True, exist_ok=True)
        references = []
        for index, reference in enumerate(contract.get("references", []), start=1):
            raw_path = reference.get("path") if isinstance(reference, dict) else reference
            role = reference.get("role", "reference") if isinstance(reference, dict) else "reference"
            source = Path(str(raw_path)).expanduser() if raw_path else None
            record = {"index": index, "role": role, "source_path": str(raw_path or "")}
            if source and source.is_file():
                ref_dir = package / "references"
                ref_dir.mkdir(parents=True, exist_ok=True)
                destination = ref_dir / f"{index:02d}-{slug(str(role))}-{source.name}"
                if not destination.exists():
                    shutil.copy2(source, destination)
                record.update(
                    {
                        "package_path": str(destination.relative_to(package)),
                        "sha256": sha256_file(destination),
                    }
                )
            else:
                record["missing"] = True
            references.append(record)
        manifest = {
            "schema_version": "p0.1",
            "job_id": job["job_id"],
            "asset_id": job["target_asset_id"],
            "parent_asset_id": job["parent_asset_id"],
            "project_id": job["project_id"],
            "execution_mode": job["execution_mode"],
            "contract": contract,
            "packaged_references": references,
        }
        (package / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        prompt = [
            f"# {contract['slot']} Generation Contract",
            "",
            contract["prompt"],
            "",
            "## Preserve",
            *(f"- {item}" for item in contract.get("invariants", [])),
            "",
            "## Avoid",
            *(f"- {item}" for item in contract.get("avoid", [])),
            "",
            "## Acceptance",
            *(f"- {item}" for item in contract.get("acceptance", [])),
        ]
        (package / "PROMPT.md").write_text("\n".join(prompt) + "\n", encoding="utf-8")
        return package

    def get_asset(self, asset_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT a.*, s.slot_key, s.title AS slot_title, j.contract_json
                FROM assets a
                JOIN image_slots s ON s.slot_id = a.slot_id
                JOIN jobs j ON j.job_id = a.job_id
                WHERE a.asset_id = ?
                """,
                (asset_id,),
            ).fetchone()
        if not row:
            raise WorkbenchError(f"unknown asset: {asset_id}")
        return row_dict(row)

    def evaluate_asset(
        self,
        asset_id: str,
        status: str,
        notes: str,
        evidence: dict[str, Any] | None = None,
        actor: str = "user",
    ) -> dict[str, Any]:
        if status not in QC_STATUSES:
            raise WorkbenchError("invalid QC status")
        with self.connect() as conn:
            asset = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
            if not asset:
                raise WorkbenchError(f"unknown asset: {asset_id}")
            if status == "passed" and asset["technical_status"] != "passed":
                raise WorkbenchError("technical checks must pass before QC can pass")
            evaluation_id = f"eval_{new_ulid()}"
            conn.execute(
                "INSERT INTO evaluations(evaluation_id, asset_id, status, notes, evidence_json, created_at) "
                "VALUES(?, ?, ?, ?, ?, ?)",
                (evaluation_id, asset_id, status, notes.strip(), json_dump(evidence or {}), iso()),
            )
            conn.execute("UPDATE assets SET qc_status = ? WHERE asset_id = ?", (status, asset_id))
            self.event(conn, "asset", asset_id, "asset.qc_updated", actor, {"status": status, "notes": notes})
        return self.get_asset(asset_id)

    def nominate_candidate(self, asset_id: str, actor: str = "user") -> dict[str, Any]:
        asset = self.get_asset(asset_id)
        if asset["technical_status"] != "passed" or asset["qc_status"] != "passed":
            raise WorkbenchError("technical and QC checks must pass before candidate registration")
        contract = asset["contract"]
        manifest = {
            "asset_id": asset["asset_id"],
            "kind": contract.get("kind", "listing-image"),
            "status": "candidate",
            "source_path": asset["source_path"],
            "sha256": asset["sha256"],
            "brand": contract.get("brand"),
            "sku": contract.get("sku"),
            "parent_asset_id": asset.get("parent_asset_id"),
            "dimensions": f"{asset['width']}x{asset['height']}",
            "approval_required": True,
            "notes": "Registered by Codex Image Workbench after technical and manual QC pass.",
        }
        if not self.registryctl_path.is_file():
            raise WorkbenchError(f"registryctl not found: {self.registryctl_path}")
        self.runtime.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", dir=self.runtime, encoding="utf-8", delete=False
        ) as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            manifest_path = Path(handle.name)
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(self.registryctl_path),
                    "--registry",
                    str(self.registry_path),
                    "register-candidate",
                    "--manifest",
                    str(manifest_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            manifest_path.unlink(missing_ok=True)
        if completed.returncode != 0:
            raise WorkbenchError(completed.stderr.strip() or completed.stdout.strip())
        with self.connect() as conn:
            conn.execute("UPDATE assets SET registry_status = 'candidate' WHERE asset_id = ?", (asset_id,))
            self.event(conn, "asset", asset_id, "asset.candidate_registered", actor, {"registry": str(self.registry_path)})
        return self.get_asset(asset_id)

    def promote_registry_asset(
        self,
        asset_id: str,
        status: str,
        approved_by: str,
        approved_at: str,
        decision_ref: str,
        actor: str = "user",
    ) -> dict[str, Any]:
        if status not in {"approved", "published", "validated", "retired"}:
            raise WorkbenchError("promotion status must be approved, published, validated, or retired")
        if not approved_by.strip() or not approved_at.strip() or not decision_ref.strip():
            raise WorkbenchError("approved_by, approved_at, and decision_ref are required")
        asset = self.get_asset(asset_id)
        if asset["registry_status"] == status:
            return asset
        completed = subprocess.run(
            [
                sys.executable,
                str(self.registryctl_path),
                "--registry",
                str(self.registry_path),
                "promote",
                "--asset-id",
                asset_id,
                "--status",
                status,
                "--approved-by",
                approved_by.strip(),
                "--approved-at",
                approved_at.strip(),
                "--decision-ref",
                decision_ref.strip(),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise WorkbenchError(completed.stderr.strip() or completed.stdout.strip())
        with self.connect() as conn:
            conn.execute("UPDATE assets SET registry_status = ? WHERE asset_id = ?", (status, asset_id))
            self.event(
                conn,
                "asset",
                asset_id,
                "asset.registry_promoted",
                actor,
                {
                    "status": status,
                    "approved_by": approved_by.strip(),
                    "approved_at": approved_at.strip(),
                    "decision_ref": decision_ref.strip(),
                },
            )
        return self.get_asset(asset_id)

    def reject_registry_asset(
        self,
        asset_id: str,
        notes: str,
        decided_by: str,
        decided_at: str,
        decision_ref: str,
        actor: str = "user",
    ) -> dict[str, Any]:
        if not notes.strip():
            raise WorkbenchError("rejection notes are required")
        asset = self.get_asset(asset_id)
        if asset["registry_status"] == "rejected":
            return asset
        if asset["registry_status"] == "transient":
            return self.register_lineage_asset(asset_id, "rejected", notes, actor)
        completed = subprocess.run(
            [
                sys.executable,
                str(self.registryctl_path),
                "--registry",
                str(self.registry_path),
                "reject",
                "--asset-id",
                asset_id,
                "--notes",
                notes.strip(),
                "--decided-by",
                decided_by.strip(),
                "--decided-at",
                decided_at.strip(),
                "--decision-ref",
                decision_ref.strip(),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise WorkbenchError(completed.stderr.strip() or completed.stdout.strip())
        with self.connect() as conn:
            conn.execute("UPDATE assets SET registry_status = 'rejected' WHERE asset_id = ?", (asset_id,))
            self.event(
                conn,
                "asset",
                asset_id,
                "asset.registry_rejected",
                actor,
                {
                    "notes": notes.strip(),
                    "decided_by": decided_by.strip(),
                    "decided_at": decided_at.strip(),
                    "decision_ref": decision_ref.strip(),
                },
            )
        return self.get_asset(asset_id)

    def register_lineage_asset(
        self,
        asset_id: str,
        status: str,
        notes: str,
        actor: str = "user",
    ) -> dict[str, Any]:
        if status not in {"raw", "rejected"}:
            raise WorkbenchError("lineage status must be raw or rejected")
        if status == "rejected" and not notes.strip():
            raise WorkbenchError("rejected lineage assets require notes")
        asset = self.get_asset(asset_id)
        if asset["registry_status"] != "transient":
            if asset["registry_status"] == status:
                return asset
            raise WorkbenchError(
                f"asset already has registry status: {asset['registry_status']}"
            )
        contract = asset["contract"]
        manifest = {
            "asset_id": asset["asset_id"],
            "kind": contract.get("kind", "listing-image"),
            "status": status,
            "source_path": asset["source_path"],
            "sha256": asset["sha256"],
            "brand": contract.get("brand"),
            "sku": contract.get("sku"),
            "parent_asset_id": asset.get("parent_asset_id"),
            "dimensions": f"{asset['width']}x{asset['height']}",
            "approval_required": False,
            "notes": notes.strip(),
        }
        if not self.registryctl_path.is_file():
            raise WorkbenchError(f"registryctl not found: {self.registryctl_path}")
        self.runtime.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", dir=self.runtime, encoding="utf-8", delete=False
        ) as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            manifest_path = Path(handle.name)
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(self.registryctl_path),
                    "--registry",
                    str(self.registry_path),
                    "register-lineage",
                    "--manifest",
                    str(manifest_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            manifest_path.unlink(missing_ok=True)
        if completed.returncode != 0:
            raise WorkbenchError(completed.stderr.strip() or completed.stdout.strip())
        with self.connect() as conn:
            conn.execute("UPDATE assets SET registry_status = ? WHERE asset_id = ?", (status, asset_id))
            self.event(
                conn,
                "asset",
                asset_id,
                "asset.lineage_registered",
                actor,
                {"registry": str(self.registry_path), "status": status, "notes": notes.strip()},
            )
        return self.get_asset(asset_id)

    def registry_check(self) -> dict[str, Any]:
        completed = subprocess.run(
            [
                sys.executable,
                str(self.registryctl_path),
                "--registry",
                str(self.registry_path),
                "check",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }

    def _require_launch_project(self, conn: sqlite3.Connection, project_id: str) -> sqlite3.Row:
        project = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        if not project:
            raise WorkbenchError(f"unknown project: {project_id}")
        if project["project_mode"] != "launch":
            raise WorkbenchError("P1 launch workflow is only available for launch projects")
        return project

    def _cancel_pending_contract_jobs(
        self,
        conn: sqlite3.Connection,
        project_id: str,
        now: str,
        reason: str,
    ) -> None:
        leased = conn.execute(
            "SELECT j.job_id FROM jobs j JOIN image_contracts c ON c.job_id = j.job_id "
            "WHERE c.project_id = ? AND c.status != 'superseded' AND j.execution_status = 'leased'",
            (project_id,),
        ).fetchall()
        if leased:
            raise WorkbenchError(
                "cannot revise launch inputs while contract jobs are leased: "
                + ", ".join(row["job_id"] for row in leased)
            )
        pending = conn.execute(
            "SELECT j.job_id FROM jobs j JOIN image_contracts c ON c.job_id = j.job_id "
            "WHERE c.project_id = ? AND c.status != 'superseded' "
            "AND j.execution_status IN ('queued', 'awaiting_import')",
            (project_id,),
        ).fetchall()
        for row in pending:
            conn.execute(
                "UPDATE jobs SET execution_status = 'cancelled', finished_at = ?, error = ?, "
                "lease_owner = NULL, lease_expires_at = NULL WHERE job_id = ?",
                (now, reason, row["job_id"]),
            )
            self.event(conn, "job", row["job_id"], "job.cancelled", "system", {"reason": reason})

    def _supersede_launch_outputs(
        self,
        conn: sqlite3.Connection,
        project_id: str,
        now: str,
        reason: str,
        include_strategy: bool,
        include_sequence: bool,
    ) -> None:
        self._cancel_pending_contract_jobs(conn, project_id, now, reason)
        conn.execute(
            "UPDATE image_contracts SET status = 'superseded', updated_at = ? "
            "WHERE project_id = ? AND status != 'superseded'",
            (now, project_id),
        )
        if include_sequence:
            conn.execute(
                "UPDATE image_sequences SET status = 'superseded', updated_at = ? "
                "WHERE project_id = ? AND status != 'superseded'",
                (now, project_id),
            )
        if include_strategy:
            conn.execute(
                "UPDATE project_strategies SET status = 'superseded', updated_at = ? "
                "WHERE project_id = ? AND status != 'superseded'",
                (now, project_id),
            )

    def import_launch_intake(
        self,
        project_id: str,
        payload: dict[str, Any],
        source_type: str = "codex_normalized",
        actor: str = "codex",
    ) -> dict[str, Any]:
        intake = normalize_intake(payload)
        coverage = build_coverage(intake)
        now = iso()
        report_id = f"coverage_{new_ulid()}"
        with self.connect() as conn:
            self._require_launch_project(conn, project_id)
            self._supersede_launch_outputs(
                conn,
                project_id,
                now,
                "P1 intake was replaced",
                include_strategy=True,
                include_sequence=True,
            )
            conn.execute(
                "INSERT INTO project_intakes(project_id, schema_version, source_type, intake_json, imported_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?, ?) ON CONFLICT(project_id) DO UPDATE SET "
                "schema_version = excluded.schema_version, source_type = excluded.source_type, "
                "intake_json = excluded.intake_json, imported_at = excluded.imported_at, updated_at = excluded.updated_at",
                (project_id, intake["schema_version"], source_type, json_dump(intake), now, now),
            )
            conn.execute(
                "INSERT INTO coverage_reports(report_id, project_id, status, report_json, created_at) "
                "VALUES(?, ?, ?, ?, ?)",
                (report_id, project_id, coverage["status"], json_dump(coverage), now),
            )
            for gate_key in ("gate1", "gate2"):
                conn.execute(
                    "INSERT INTO project_gates(project_id, gate_key, status, decision_json, updated_at) "
                    "VALUES(?, ?, 'pending', '{}', ?) ON CONFLICT(project_id, gate_key) DO UPDATE SET "
                    "status = 'pending', decision_json = '{}', decided_by = NULL, decided_at = NULL, updated_at = excluded.updated_at",
                    (project_id, gate_key, now),
                )
            conn.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?", (now, project_id))
            self.event(
                conn,
                "project",
                project_id,
                "launch.intake_imported",
                actor,
                {"report_id": report_id, "coverage_status": coverage["status"]},
            )
        return self.get_launch_workspace(project_id)

    def get_launch_workspace(self, project_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            self._require_launch_project(conn, project_id)
            intake_row = conn.execute(
                "SELECT * FROM project_intakes WHERE project_id = ?", (project_id,)
            ).fetchone()
            coverage_row = conn.execute(
                "SELECT * FROM coverage_reports WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            strategy_row = conn.execute(
                "SELECT * FROM project_strategies WHERE project_id = ? AND status != 'superseded' "
                "ORDER BY version DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            sequence_row = conn.execute(
                "SELECT * FROM image_sequences WHERE project_id = ? AND status != 'superseded' "
                "ORDER BY version DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            gate_rows = conn.execute(
                "SELECT * FROM project_gates WHERE project_id = ? ORDER BY gate_key", (project_id,)
            ).fetchall()
            if sequence_row:
                contract_rows = conn.execute(
                    "SELECT * FROM image_contracts WHERE project_id = ? AND sequence_id = ? "
                    "AND status != 'superseded' ORDER BY slot_key",
                    (project_id, sequence_row["sequence_id"]),
                ).fetchall()
            else:
                contract_rows = []

        intake = json.loads(intake_row["intake_json"]) if intake_row else None
        coverage = json.loads(coverage_row["report_json"]) if coverage_row else None
        strategy = row_dict(strategy_row)
        if strategy:
            strategy["strategy"] = json.loads(strategy.pop("strategy_json"))
        sequence = row_dict(sequence_row)
        if sequence:
            sequence["sequence"] = json.loads(sequence.pop("sequence_json"))
        gates = {}
        for row in gate_rows:
            gate = row_dict(row)
            gate["decision"] = json.loads(gate.pop("decision_json"))
            gates[gate["gate_key"]] = gate
        contracts = []
        for row in contract_rows:
            contract = row_dict(row)
            contracts.append(contract)
        intake_meta = row_dict(intake_row)
        if intake_meta:
            intake_meta.pop("intake_json", None)
        return {
            "project_id": project_id,
            "intake": intake,
            "intake_meta": intake_meta,
            "coverage": coverage,
            "strategy": strategy,
            "gates": gates,
            "sequence": sequence,
            "contracts": contracts,
        }

    def save_launch_strategy(
        self,
        project_id: str,
        payload: dict[str, Any],
        actor: str = "codex",
    ) -> dict[str, Any]:
        workspace = self.get_launch_workspace(project_id)
        if not workspace["intake"] or not workspace["coverage"]:
            raise WorkbenchError("import P1 intake before saving strategy")
        strategy = validate_strategy(workspace["intake"], payload)
        status = "awaiting_gate1" if workspace["coverage"]["strategy_status"] == "passed" else "draft"
        now = iso()
        with self.connect() as conn:
            self._require_launch_project(conn, project_id)
            self._supersede_launch_outputs(
                conn,
                project_id,
                now,
                "P1 strategy was replaced",
                include_strategy=False,
                include_sequence=True,
            )
            version = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM project_strategies WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]
            conn.execute(
                "UPDATE project_strategies SET status = 'superseded', updated_at = ? "
                "WHERE project_id = ? AND status != 'superseded'",
                (now, project_id),
            )
            strategy_id = f"strategy_{new_ulid()}"
            conn.execute(
                "INSERT INTO project_strategies(strategy_id, project_id, version, status, strategy_json, created_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?)",
                (strategy_id, project_id, version, status, json_dump(strategy), now, now),
            )
            gate_status = "awaiting" if status == "awaiting_gate1" else "pending"
            conn.execute(
                "INSERT INTO project_gates(project_id, gate_key, status, decision_json, updated_at) "
                "VALUES(?, 'gate1', ?, '{}', ?) ON CONFLICT(project_id, gate_key) DO UPDATE SET "
                "status = excluded.status, decision_json = '{}', decided_by = NULL, decided_at = NULL, updated_at = excluded.updated_at",
                (project_id, gate_status, now),
            )
            conn.execute(
                "INSERT INTO project_gates(project_id, gate_key, status, decision_json, updated_at) "
                "VALUES(?, 'gate2', 'pending', '{}', ?) ON CONFLICT(project_id, gate_key) DO UPDATE SET "
                "status = 'pending', decision_json = '{}', decided_by = NULL, decided_at = NULL, updated_at = excluded.updated_at",
                (project_id, now),
            )
            self.event(conn, "strategy", strategy_id, "launch.strategy_saved", actor, {"status": status})
        return self.get_launch_workspace(project_id)

    def decide_launch_gate(
        self,
        project_id: str,
        gate_key: str,
        status: str,
        decision: dict[str, Any] | None = None,
        actor: str = "user",
    ) -> dict[str, Any]:
        if gate_key not in {"gate1", "gate2"}:
            raise WorkbenchError("gate_key must be gate1 or gate2")
        if status not in {"approved", "changes_requested"}:
            raise WorkbenchError("gate status must be approved or changes_requested")
        workspace = self.get_launch_workspace(project_id)
        now = iso()
        if gate_key == "gate1":
            if not workspace["strategy"]:
                raise WorkbenchError("save strategy before Gate 1")
            if status == "approved" and workspace["coverage"]["strategy_status"] != "passed":
                raise WorkbenchError("strategy blockers must be resolved before Gate 1 approval")
            entity_table = "project_strategies"
            entity_id = workspace["strategy"]["strategy_id"]
            entity_field = "strategy_id"
        else:
            if workspace["gates"].get("gate1", {}).get("status") != "approved":
                raise WorkbenchError("Gate 1 must be approved before Gate 2")
            if not workspace["sequence"]:
                raise WorkbenchError("save image sequence before Gate 2")
            entity_table = "image_sequences"
            entity_id = workspace["sequence"]["sequence_id"]
            entity_field = "sequence_id"
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO project_gates(project_id, gate_key, status, decision_json, decided_by, decided_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?) ON CONFLICT(project_id, gate_key) DO UPDATE SET "
                "status = excluded.status, decision_json = excluded.decision_json, decided_by = excluded.decided_by, "
                "decided_at = excluded.decided_at, updated_at = excluded.updated_at",
                (project_id, gate_key, status, json_dump(decision or {}), actor, now, now),
            )
            conn.execute(
                f"UPDATE {entity_table} SET status = ?, updated_at = ? WHERE {entity_field} = ?",
                (status, now, entity_id),
            )
            self.event(conn, "project", project_id, f"launch.{gate_key}_{status}", actor, decision or {})
        return self.get_launch_workspace(project_id)

    def save_launch_sequence(
        self,
        project_id: str,
        payload: dict[str, Any],
        actor: str = "codex",
    ) -> dict[str, Any]:
        workspace = self.get_launch_workspace(project_id)
        if workspace["gates"].get("gate1", {}).get("status") != "approved":
            raise WorkbenchError("Gate 1 must be approved before saving image sequence")
        sequence = validate_sequence(workspace["strategy"]["strategy"], payload)
        now = iso()
        with self.connect() as conn:
            self._cancel_pending_contract_jobs(conn, project_id, now, "P1 image sequence was replaced")
            version = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM image_sequences WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]
            conn.execute(
                "UPDATE image_sequences SET status = 'superseded', updated_at = ? "
                "WHERE project_id = ? AND status != 'superseded'",
                (now, project_id),
            )
            conn.execute(
                "UPDATE image_contracts SET status = 'superseded', updated_at = ? "
                "WHERE project_id = ? AND status != 'superseded'",
                (now, project_id),
            )
            sequence_id = f"sequence_{new_ulid()}"
            conn.execute(
                "INSERT INTO image_sequences(sequence_id, project_id, version, status, sequence_json, created_at, updated_at) "
                "VALUES(?, ?, ?, 'awaiting_gate2', ?, ?, ?)",
                (sequence_id, project_id, version, json_dump(sequence), now, now),
            )
            conn.execute(
                "INSERT INTO project_gates(project_id, gate_key, status, decision_json, updated_at) "
                "VALUES(?, 'gate2', 'awaiting', '{}', ?) ON CONFLICT(project_id, gate_key) DO UPDATE SET "
                "status = 'awaiting', decision_json = '{}', decided_by = NULL, decided_at = NULL, updated_at = excluded.updated_at",
                (project_id, now),
            )
            self.event(conn, "sequence", sequence_id, "launch.sequence_saved", actor, {"version": version})
        return self.get_launch_workspace(project_id)

    def save_image_contracts(
        self,
        project_id: str,
        payload: dict[str, Any],
        actor: str = "codex",
    ) -> dict[str, Any]:
        workspace = self.get_launch_workspace(project_id)
        if workspace["gates"].get("gate2", {}).get("status") != "approved":
            raise WorkbenchError("Gate 2 must be approved before saving image contracts")
        contracts = validate_contracts(workspace["intake"], workspace["sequence"]["sequence"], payload)
        sequence_id = workspace["sequence"]["sequence_id"]
        version = workspace["sequence"]["version"]
        now = iso()
        with self.connect() as conn:
            self._cancel_pending_contract_jobs(conn, project_id, now, "P1 image contracts were replaced")
            conn.execute(
                "UPDATE image_contracts SET status = 'superseded', updated_at = ? "
                "WHERE project_id = ? AND status != 'superseded'",
                (now, project_id),
            )
            for contract in contracts:
                contract_id = f"contract_{new_ulid()}"
                status = contract.pop("readiness")
                conn.execute(
                    "INSERT INTO image_contracts(contract_id, project_id, sequence_id, slot_key, version, status, contract_json, created_at, updated_at) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (contract_id, project_id, sequence_id, contract["slot_key"], version, status, json_dump(contract), now, now),
                )
                self.event(conn, "contract", contract_id, "launch.contract_saved", actor, {"status": status})
        return self.get_launch_workspace(project_id)

    def queue_image_contracts(self, project_id: str, actor: str = "user") -> dict[str, Any]:
        workspace = self.get_launch_workspace(project_id)
        if workspace["coverage"]["generation_status"] != "passed":
            raise WorkbenchError("generation coverage blockers must be resolved before queueing")
        if workspace["gates"].get("gate2", {}).get("status") != "approved":
            raise WorkbenchError("Gate 2 must be approved before queueing")
        if not workspace["contracts"]:
            raise WorkbenchError("save image contracts before queueing")
        blocked = [item for item in workspace["contracts"] if item["status"] == "blocked"]
        if blocked:
            reasons = [f"{item['slot_key']}: {', '.join(item['contract']['blocked_reasons'])}" for item in blocked]
            raise WorkbenchError("blocked image contracts: " + "; ".join(reasons))

        references = {item["reference_id"]: item for item in workspace["intake"]["references"]}
        claims = {item["claim_id"]: item for item in workspace["intake"]["claims"]}
        jobs = []
        for item in workspace["contracts"]:
            if item["job_id"]:
                jobs.append(self.get_job(item["job_id"]))
                continue
            contract = item["contract"]
            payload = {
                "slot_key": contract["slot_key"],
                "slot_title": contract.get("title") or contract["slot_key"],
                "execution_mode": contract["execution_mode"],
                "operation": contract["operation"],
                "parent_asset_id": contract.get("parent_asset_id"),
                "prompt": contract["prompt"],
                "references": [
                    {
                        "reference_id": reference_id,
                        "path": references[reference_id]["path"],
                        "role": references[reference_id]["role"],
                        "view": references[reference_id]["view"],
                    }
                    for reference_id in contract["reference_ids"]
                ],
                "invariants": contract["product_invariants"] + contract["brand_invariants"],
                "product_invariants": contract["product_invariants"],
                "brand_invariants": contract["brand_invariants"],
                "change_only": contract["change_only"],
                "avoid": contract["avoid"],
                "acceptance": contract["acceptance"],
                "expected_output": contract["expected_output"],
                "claim_ids": contract["claim_ids"],
                "claims": [claims[claim_id] for claim_id in contract["claim_ids"]],
                "contract_id": item["contract_id"],
                "idempotency_key": f"p1-{item['contract_id']}",
            }
            job, _ = self.create_job(project_id, payload)
            with self.connect() as conn:
                conn.execute(
                    "UPDATE image_contracts SET status = 'queued', job_id = ?, updated_at = ? WHERE contract_id = ?",
                    (job["job_id"], iso(), item["contract_id"]),
                )
                self.event(conn, "contract", item["contract_id"], "launch.contract_queued", actor, {"job_id": job["job_id"]})
            jobs.append(job)
        result = self.get_launch_workspace(project_id)
        result["queued_jobs"] = jobs
        return result

    def _require_optimize_project(self, conn: sqlite3.Connection, project_id: str) -> sqlite3.Row:
        project = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        if not project:
            raise WorkbenchError(f"unknown project: {project_id}")
        if project["project_mode"] != "optimize":
            raise WorkbenchError("P2 optimization workflow is only available for optimize projects")
        return project

    def _cancel_pending_optimization_jobs(
        self,
        conn: sqlite3.Connection,
        project_id: str,
        now: str,
        reason: str,
    ) -> None:
        leased = conn.execute(
            "SELECT j.job_id FROM jobs j JOIN optimization_contracts c ON c.job_id = j.job_id "
            "WHERE c.project_id = ? AND c.status != 'superseded' AND j.execution_status = 'leased'",
            (project_id,),
        ).fetchall()
        if leased:
            raise WorkbenchError(
                "cannot revise optimization inputs while challenge jobs are leased: "
                + ", ".join(row["job_id"] for row in leased)
            )
        pending = conn.execute(
            "SELECT j.job_id FROM jobs j JOIN optimization_contracts c ON c.job_id = j.job_id "
            "WHERE c.project_id = ? AND c.status != 'superseded' "
            "AND j.execution_status IN ('queued', 'awaiting_import')",
            (project_id,),
        ).fetchall()
        for row in pending:
            conn.execute(
                "UPDATE jobs SET execution_status = 'cancelled', finished_at = ?, error = ?, "
                "lease_owner = NULL, lease_expires_at = NULL WHERE job_id = ?",
                (now, reason, row["job_id"]),
            )
            self.event(conn, "job", row["job_id"], "job.cancelled", "system", {"reason": reason})

    def _supersede_optimization_outputs(
        self,
        conn: sqlite3.Connection,
        project_id: str,
        now: str,
        reason: str,
        include_diagnosis: bool,
    ) -> None:
        self._cancel_pending_optimization_jobs(conn, project_id, now, reason)
        conn.execute(
            "UPDATE optimization_contracts SET status = 'superseded', updated_at = ? "
            "WHERE project_id = ? AND status != 'superseded'",
            (now, project_id),
        )
        if include_diagnosis:
            conn.execute(
                "UPDATE optimization_diagnostics SET status = 'superseded', updated_at = ? "
                "WHERE project_id = ? AND status != 'superseded'",
                (now, project_id),
            )

    def import_optimization_intake(
        self,
        project_id: str,
        payload: dict[str, Any],
        source_type: str = "codex_normalized",
        actor: str = "codex",
    ) -> dict[str, Any]:
        intake = normalize_optimization_intake(payload)
        readiness = build_optimization_readiness(intake)
        now = iso()
        with self.connect() as conn:
            self._require_optimize_project(conn, project_id)
            self._supersede_optimization_outputs(
                conn,
                project_id,
                now,
                "P2 Listing snapshot was replaced",
                include_diagnosis=True,
            )
            version = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM listing_versions WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]
            conn.execute(
                "UPDATE listing_versions SET status = 'superseded', updated_at = ? "
                "WHERE project_id = ? AND status = 'current'",
                (now, project_id),
            )
            listing_version_id = f"listing_{new_ulid()}"
            conn.execute(
                "INSERT INTO listing_versions(listing_version_id, project_id, version, status, schema_version, "
                "source_type, captured_at, intake_json, readiness_json, created_at, updated_at) "
                "VALUES(?, ?, ?, 'current', ?, ?, ?, ?, ?, ?, ?)",
                (
                    listing_version_id,
                    project_id,
                    version,
                    intake["schema_version"],
                    source_type,
                    intake["listing"]["captured_at"],
                    json_dump(intake),
                    json_dump(readiness),
                    now,
                    now,
                ),
            )
            conn.execute(
                "INSERT INTO optimization_gates(project_id, status, decision_json, updated_at) "
                "VALUES(?, 'pending', '{}', ?) ON CONFLICT(project_id) DO UPDATE SET "
                "status = 'pending', decision_json = '{}', decided_by = NULL, decided_at = NULL, updated_at = excluded.updated_at",
                (project_id, now),
            )
            for observation in intake["baseline"]["observations"]:
                conn.execute(
                    "INSERT INTO performance_observations(observation_id, project_id, listing_version_id, release_id, "
                    "phase, period_start, period_end, source, source_class, metrics_json, note, created_at) "
                    "VALUES(?, ?, ?, NULL, 'before', ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"obs_{new_ulid()}",
                        project_id,
                        listing_version_id,
                        observation["period_start"],
                        observation["period_end"],
                        observation["source"],
                        observation["source_class"],
                        json_dump(observation["metrics"]),
                        observation["note"],
                        now,
                    ),
                )
            for event in intake["baseline"]["events"]:
                conn.execute(
                    "INSERT INTO interference_events(interference_event_id, project_id, release_id, event_type, status, "
                    "started_at, ended_at, description, source, created_at, updated_at) "
                    "VALUES(?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"interference_{new_ulid()}",
                        project_id,
                        event["event_type"],
                        event["status"],
                        event["started_at"],
                        event["ended_at"] or None,
                        event["description"],
                        event["source"],
                        now,
                        now,
                    ),
                )
            conn.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?", (now, project_id))
            self.event(
                conn,
                "listing_version",
                listing_version_id,
                "optimization.intake_imported",
                actor,
                {"version": version, "readiness_status": readiness["status"]},
            )
        return self.get_optimization_workspace(project_id)

    def get_optimization_workspace(self, project_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            self._require_optimize_project(conn, project_id)
            listing_row = conn.execute(
                "SELECT * FROM listing_versions WHERE project_id = ? AND status = 'current' "
                "ORDER BY version DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            diagnostic_row = conn.execute(
                "SELECT * FROM optimization_diagnostics WHERE project_id = ? AND status != 'superseded' "
                "ORDER BY version DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            gate_row = conn.execute(
                "SELECT * FROM optimization_gates WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            contract_rows = conn.execute(
                "SELECT * FROM optimization_contracts WHERE project_id = ? AND status != 'superseded' "
                "ORDER BY slot_key, challenge_key",
                (project_id,),
            ).fetchall()
            release_rows = conn.execute(
                "SELECT * FROM release_records WHERE project_id = ? ORDER BY published_at DESC",
                (project_id,),
            ).fetchall()
            observation_rows = conn.execute(
                "SELECT * FROM performance_observations WHERE project_id = ? ORDER BY period_end DESC, created_at DESC",
                (project_id,),
            ).fetchall()
            interference_rows = conn.execute(
                "SELECT * FROM interference_events WHERE project_id = ? ORDER BY started_at DESC",
                (project_id,),
            ).fetchall()
            evaluation_rows = conn.execute(
                "SELECT * FROM optimization_evaluations WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()

        listing = row_dict(listing_row)
        intake = readiness = None
        if listing:
            intake = json.loads(listing.pop("intake_json"))
            readiness = json.loads(listing.pop("readiness_json"))
        diagnostic = row_dict(diagnostic_row)
        if diagnostic:
            diagnostic["diagnostic"] = json.loads(diagnostic.pop("diagnostic_json"))
        gate = row_dict(gate_row)
        if gate:
            gate["decision"] = json.loads(gate.pop("decision_json"))
        contracts = [row_dict(row) for row in contract_rows]
        releases = [row_dict(row) for row in release_rows]
        observations = [row_dict(row) for row in observation_rows]
        interference_events = [row_dict(row) for row in interference_rows]
        evaluations = [row_dict(row) for row in evaluation_rows]
        return {
            "project_id": project_id,
            "listing_version": listing,
            "intake": intake,
            "readiness": readiness,
            "diagnostic": diagnostic,
            "gate": gate,
            "contracts": contracts,
            "releases": releases,
            "observations": observations,
            "interference_events": interference_events,
            "evaluations": evaluations,
        }

    def get_optimization_listing_image_path(self, project_id: str, slot_key: str) -> Path:
        workspace = self.get_optimization_workspace(project_id)
        if not workspace["intake"]:
            raise WorkbenchError("optimization Listing snapshot has not been imported")
        normalized_slot = str(slot_key).strip().upper()
        image = next(
            (
                item for item in workspace["intake"]["listing"]["images"]
                if item["slot_key"] == normalized_slot
            ),
            None,
        )
        if not image or not image["exists"] or not image["readable_image"]:
            raise WorkbenchError(f"current Listing image is not available locally: {normalized_slot}")
        return Path(image["path"])

    def save_optimization_diagnosis(
        self,
        project_id: str,
        payload: dict[str, Any],
        actor: str = "codex",
    ) -> dict[str, Any]:
        workspace = self.get_optimization_workspace(project_id)
        if not workspace["intake"] or not workspace["readiness"]:
            raise WorkbenchError("import a P2 Listing snapshot before saving diagnosis")
        diagnostic = validate_diagnosis(workspace["intake"], payload)
        status = "awaiting_gate" if workspace["readiness"]["diagnosis_status"] == "passed" else "draft"
        now = iso()
        with self.connect() as conn:
            self._require_optimize_project(conn, project_id)
            self._supersede_optimization_outputs(
                conn,
                project_id,
                now,
                "P2 diagnosis was replaced",
                include_diagnosis=False,
            )
            version = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM optimization_diagnostics WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]
            conn.execute(
                "UPDATE optimization_diagnostics SET status = 'superseded', updated_at = ? "
                "WHERE project_id = ? AND status != 'superseded'",
                (now, project_id),
            )
            diagnostic_id = f"diagnostic_{new_ulid()}"
            conn.execute(
                "INSERT INTO optimization_diagnostics(diagnostic_id, project_id, listing_version_id, version, status, "
                "diagnostic_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    diagnostic_id,
                    project_id,
                    workspace["listing_version"]["listing_version_id"],
                    version,
                    status,
                    json_dump(diagnostic),
                    now,
                    now,
                ),
            )
            gate_status = "awaiting" if status == "awaiting_gate" else "pending"
            conn.execute(
                "INSERT INTO optimization_gates(project_id, status, decision_json, updated_at) "
                "VALUES(?, ?, '{}', ?) ON CONFLICT(project_id) DO UPDATE SET status = excluded.status, "
                "decision_json = '{}', decided_by = NULL, decided_at = NULL, updated_at = excluded.updated_at",
                (project_id, gate_status, now),
            )
            self.event(conn, "diagnostic", diagnostic_id, "optimization.diagnosis_saved", actor, {"status": status})
        return self.get_optimization_workspace(project_id)

    def decide_optimization_gate(
        self,
        project_id: str,
        status: str,
        decision: dict[str, Any] | None = None,
        actor: str = "user",
    ) -> dict[str, Any]:
        if status not in {"approved", "changes_requested"}:
            raise WorkbenchError("optimization Gate status must be approved or changes_requested")
        workspace = self.get_optimization_workspace(project_id)
        if not workspace["diagnostic"]:
            raise WorkbenchError("save diagnosis before deciding the optimization Gate")
        if status == "approved" and workspace["readiness"]["diagnosis_status"] != "passed":
            raise WorkbenchError("diagnosis blockers must be resolved before approval")
        now = iso()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO optimization_gates(project_id, status, decision_json, decided_by, decided_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?, ?) ON CONFLICT(project_id) DO UPDATE SET status = excluded.status, "
                "decision_json = excluded.decision_json, decided_by = excluded.decided_by, "
                "decided_at = excluded.decided_at, updated_at = excluded.updated_at",
                (project_id, status, json_dump(decision or {}), actor, now, now),
            )
            conn.execute(
                "UPDATE optimization_diagnostics SET status = ?, updated_at = ? WHERE diagnostic_id = ?",
                (status, now, workspace["diagnostic"]["diagnostic_id"]),
            )
            self.event(conn, "project", project_id, f"optimization.gate_{status}", actor, decision or {})
        return self.get_optimization_workspace(project_id)

    def save_optimization_contracts(
        self,
        project_id: str,
        payload: dict[str, Any],
        actor: str = "codex",
    ) -> dict[str, Any]:
        workspace = self.get_optimization_workspace(project_id)
        if (workspace.get("gate") or {}).get("status") != "approved":
            raise WorkbenchError("approve the optimization diagnosis before saving challenge contracts")
        contracts = validate_optimization_contracts(
            workspace["intake"],
            workspace["diagnostic"]["diagnostic"],
            workspace["readiness"],
            payload,
        )
        now = iso()
        with self.connect() as conn:
            self._cancel_pending_optimization_jobs(conn, project_id, now, "P2 challenge contracts were replaced")
            version = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM optimization_contracts WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]
            conn.execute(
                "UPDATE optimization_contracts SET status = 'superseded', updated_at = ? "
                "WHERE project_id = ? AND status != 'superseded'",
                (now, project_id),
            )
            for contract in contracts:
                optimization_contract_id = f"optcontract_{new_ulid()}"
                status = contract.pop("readiness")
                conn.execute(
                    "INSERT INTO optimization_contracts(optimization_contract_id, project_id, diagnostic_id, "
                    "challenge_key, slot_key, version, status, contract_json, created_at, updated_at) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        optimization_contract_id,
                        project_id,
                        workspace["diagnostic"]["diagnostic_id"],
                        contract["challenge_key"],
                        contract["slot_key"],
                        version,
                        status,
                        json_dump(contract),
                        now,
                        now,
                    ),
                )
                self.event(conn, "optimization_contract", optimization_contract_id, "optimization.contract_saved", actor, {"status": status})
        return self.get_optimization_workspace(project_id)

    def queue_optimization_contracts(self, project_id: str, actor: str = "user") -> dict[str, Any]:
        workspace = self.get_optimization_workspace(project_id)
        if workspace["readiness"]["generation_status"] != "passed":
            raise WorkbenchError("optimization generation blockers must be resolved before queueing")
        if (workspace.get("gate") or {}).get("status") != "approved":
            raise WorkbenchError("approve the optimization diagnosis before queueing")
        if not workspace["contracts"]:
            raise WorkbenchError("save optimization contracts before queueing")
        blocked = [item for item in workspace["contracts"] if item["status"] == "blocked"]
        if blocked:
            reasons = [f"{item['challenge_key']}: {', '.join(item['contract']['blocked_reasons'])}" for item in blocked]
            raise WorkbenchError("blocked optimization contracts: " + "; ".join(reasons))

        current_images = {f"listing:{image['slot_key']}": image for image in workspace["intake"]["listing"]["images"]}
        product_refs = {reference["reference_id"]: reference for reference in workspace["intake"]["references"]}
        references = {**current_images, **product_refs}
        claims = {claim["claim_id"]: claim for claim in workspace["intake"]["claims"]}
        jobs = []
        for item in workspace["contracts"]:
            if item["job_id"]:
                jobs.append(self.get_job(item["job_id"]))
                continue
            contract = item["contract"]
            payload = {
                "slot_key": contract["slot_key"],
                "slot_title": f"{contract['slot_key']} · {contract['challenge_key']}",
                "execution_mode": contract["execution_mode"],
                "operation": contract["operation"],
                "parent_asset_id": contract.get("parent_asset_id"),
                "prompt": contract["prompt"],
                "references": [
                    {
                        "reference_id": reference_id,
                        "path": references[reference_id]["path"],
                        "role": references[reference_id].get("role", "current-listing"),
                        "view": references[reference_id].get("view", "listing"),
                    }
                    for reference_id in contract["reference_ids"]
                ],
                "invariants": contract["product_invariants"],
                "product_invariants": contract["product_invariants"],
                "change_only": contract["change_only"],
                "avoid": contract["avoid"],
                "acceptance": contract["acceptance"],
                "expected_output": contract["expected_output"],
                "claim_ids": contract["claim_ids"],
                "claims": [claims[claim_id] for claim_id in contract["claim_ids"]],
                "optimization_contract_id": item["optimization_contract_id"],
                "issue_id": contract["issue_id"],
                "challenge_key": contract["challenge_key"],
                "target_metrics": contract["target_metrics"],
                "observation_days": contract["observation_days"],
                "idempotency_key": f"p2-{item['optimization_contract_id']}",
            }
            job, _ = self.create_job(project_id, payload)
            with self.connect() as conn:
                conn.execute(
                    "UPDATE optimization_contracts SET status = 'queued', job_id = ?, updated_at = ? "
                    "WHERE optimization_contract_id = ?",
                    (job["job_id"], iso(), item["optimization_contract_id"]),
                )
                self.event(conn, "optimization_contract", item["optimization_contract_id"], "optimization.contract_queued", actor, {"job_id": job["job_id"]})
            jobs.append(job)
        result = self.get_optimization_workspace(project_id)
        result["queued_jobs"] = jobs
        return result

    def get_optimization_release_preflight(
        self,
        project_id: str,
        contract_id: str,
        asset_id: str,
    ) -> dict[str, Any]:
        with self.connect() as conn:
            self._require_optimize_project(conn, project_id)
            contract = conn.execute(
                "SELECT * FROM optimization_contracts WHERE optimization_contract_id = ? AND project_id = ?",
                (contract_id, project_id),
            ).fetchone()
            if not contract:
                raise WorkbenchError(f"unknown optimization contract: {contract_id}")
            asset = conn.execute(
                "SELECT * FROM assets WHERE asset_id = ? AND project_id = ?",
                (asset_id, project_id),
            ).fetchone()
            if not asset:
                raise WorkbenchError(f"unknown optimization asset: {asset_id}")
            listing = conn.execute(
                "SELECT * FROM listing_versions WHERE project_id = ? AND status = 'current'",
                (project_id,),
            ).fetchone()
            if not listing:
                raise WorkbenchError("current ListingVersion is required before release")
            listing_intake = json.loads(listing["intake_json"])
            rollback_image = next(
                (
                    item
                    for item in listing_intake.get("listing", {}).get("images", [])
                    if item.get("slot_key") == contract["slot_key"]
                ),
                None,
            )
            checks = [
                {
                    "key": "contract_current",
                    "passed": contract["status"] != "superseded",
                    "actual": contract["status"],
                },
                {
                    "key": "contract_asset_match",
                    "passed": contract["job_id"] == asset["job_id"],
                    "actual": asset["job_id"],
                },
                {
                    "key": "technical_qc",
                    "passed": asset["technical_status"] == "passed"
                    and asset["qc_status"] == "passed",
                    "actual": f"{asset['technical_status']}/{asset['qc_status']}",
                },
                {
                    "key": "registry_approved",
                    "passed": asset["registry_status"] in {"approved", "published", "validated"},
                    "actual": asset["registry_status"],
                },
                {
                    "key": "rollback_target",
                    "passed": bool(
                        rollback_image
                        and rollback_image.get("path")
                        and Path(str(rollback_image["path"])).is_file()
                        and rollback_image.get("sha256")
                    ),
                    "actual": rollback_image.get("path") if rollback_image else None,
                },
            ]
        return {
            "ready": all(item["passed"] for item in checks),
            "project_id": project_id,
            "optimization_contract_id": contract_id,
            "asset_id": asset_id,
            "slot_key": contract["slot_key"],
            "checks": checks,
            "rollback_target": rollback_image,
            "required_release_fields": ["published_at", "published_by"],
        }

    def record_optimization_release(
        self,
        project_id: str,
        payload: dict[str, Any],
        actor: str = "user",
    ) -> dict[str, Any]:
        contract_id = str(payload.get("optimization_contract_id", "")).strip()
        asset_id = str(payload.get("asset_id", "")).strip()
        published_at = str(payload.get("published_at", "")).strip()
        if not contract_id or not asset_id or not published_at:
            raise WorkbenchError("optimization_contract_id, asset_id, and published_at are required")
        try:
            published_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise WorkbenchError("published_at must be a valid ISO 8601 timestamp") from exc
        if published_time.tzinfo is None or published_time.utcoffset() is None:
            raise WorkbenchError("published_at must include an explicit timezone offset")
        now = iso()
        with self.connect() as conn:
            self._require_optimize_project(conn, project_id)
            contract = conn.execute(
                "SELECT * FROM optimization_contracts WHERE optimization_contract_id = ? AND project_id = ?",
                (contract_id, project_id),
            ).fetchone()
            if not contract:
                raise WorkbenchError(f"unknown optimization contract: {contract_id}")
            if contract["status"] == "superseded":
                raise WorkbenchError("cannot release a superseded optimization contract")
            asset = conn.execute(
                "SELECT * FROM assets WHERE asset_id = ? AND project_id = ?",
                (asset_id, project_id),
            ).fetchone()
            if not asset:
                raise WorkbenchError(f"unknown optimization asset: {asset_id}")
            if contract["job_id"] != asset["job_id"]:
                raise WorkbenchError("release asset must be the result of the selected optimization contract")
            if asset["technical_status"] != "passed" or asset["qc_status"] != "passed":
                raise WorkbenchError("release asset must pass technical checks and manual QC")
            if asset["registry_status"] not in {"approved", "published", "validated"}:
                raise WorkbenchError("release asset must be approved in the central Registry")
            asset_created_at = datetime.fromisoformat(asset["created_at"].replace("Z", "+00:00"))
            if published_time < asset_created_at - timedelta(minutes=5):
                raise WorkbenchError("published_at cannot predate the release asset")
            release_id = f"release_{new_ulid()}"
            conn.execute(
                "UPDATE release_records SET status = 'superseded', updated_at = ? "
                "WHERE project_id = ? AND slot_key = ? AND status = 'active'",
                (now, project_id, contract["slot_key"]),
            )
            release_detail = {
                "note": str(payload.get("note", "")).strip(),
                "published_by": str(payload.get("published_by", actor)).strip(),
            }
            conn.execute(
                "INSERT INTO release_records(release_id, project_id, optimization_contract_id, asset_id, slot_key, "
                "status, published_at, release_json, created_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)",
                (release_id, project_id, contract_id, asset_id, contract["slot_key"], published_at, json_dump(release_detail), now, now),
            )
            self.event(conn, "release", release_id, "optimization.release_recorded", actor, {"published_at": published_at})
        return self.get_optimization_workspace(project_id)

    def add_optimization_observation(
        self,
        project_id: str,
        release_id: str,
        payload: dict[str, Any],
        actor: str = "codex",
    ) -> dict[str, Any]:
        observation = normalize_observation(payload, "after")
        now = iso()
        with self.connect() as conn:
            self._require_optimize_project(conn, project_id)
            release = conn.execute(
                "SELECT release_id FROM release_records WHERE release_id = ? AND project_id = ?",
                (release_id, project_id),
            ).fetchone()
            if not release:
                raise WorkbenchError(f"unknown release: {release_id}")
            observation_id = f"obs_{new_ulid()}"
            conn.execute(
                "INSERT INTO performance_observations(observation_id, project_id, listing_version_id, release_id, "
                "phase, period_start, period_end, source, source_class, metrics_json, note, created_at) "
                "VALUES(?, ?, NULL, ?, 'after', ?, ?, ?, ?, ?, ?, ?)",
                (
                    observation_id,
                    project_id,
                    release_id,
                    observation["period_start"],
                    observation["period_end"],
                    observation["source"],
                    observation["source_class"],
                    json_dump(observation["metrics"]),
                    observation["note"],
                    now,
                ),
            )
            self.event(conn, "observation", observation_id, "optimization.observation_added", actor, {"release_id": release_id})
        return self.get_optimization_workspace(project_id)

    def add_optimization_interference_event(
        self,
        project_id: str,
        payload: dict[str, Any],
        actor: str = "user",
    ) -> dict[str, Any]:
        event = normalize_interference_event(payload)
        release_id = str(payload.get("release_id", "")).strip() or None
        now = iso()
        with self.connect() as conn:
            self._require_optimize_project(conn, project_id)
            if release_id:
                release = conn.execute(
                    "SELECT release_id FROM release_records WHERE release_id = ? AND project_id = ?",
                    (release_id, project_id),
                ).fetchone()
                if not release:
                    raise WorkbenchError(f"unknown release: {release_id}")
            event_id = f"interference_{new_ulid()}"
            conn.execute(
                "INSERT INTO interference_events(interference_event_id, project_id, release_id, event_type, status, "
                "started_at, ended_at, description, source, created_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    project_id,
                    release_id,
                    event["event_type"],
                    event["status"],
                    event["started_at"],
                    event["ended_at"] or None,
                    event["description"],
                    event["source"],
                    now,
                    now,
                ),
            )
            self.event(conn, "interference_event", event_id, "optimization.interference_added", actor, {"release_id": release_id})
        return self.get_optimization_workspace(project_id)

    def resolve_optimization_interference_event(
        self,
        project_id: str,
        interference_event_id: str,
        ended_at: str,
        actor: str = "user",
    ) -> dict[str, Any]:
        ended_at = str(ended_at).strip()
        if not ended_at:
            raise WorkbenchError("ended_at is required when resolving an interference event")
        now = iso()
        with self.connect() as conn:
            self._require_optimize_project(conn, project_id)
            event = conn.execute(
                "SELECT * FROM interference_events WHERE interference_event_id = ? AND project_id = ?",
                (interference_event_id, project_id),
            ).fetchone()
            if not event:
                raise WorkbenchError(f"unknown interference event: {interference_event_id}")
            if ended_at < event["started_at"]:
                raise WorkbenchError("interference event ended_at cannot precede started_at")
            conn.execute(
                "UPDATE interference_events SET status = 'resolved', ended_at = ?, updated_at = ? "
                "WHERE interference_event_id = ?",
                (ended_at, now, interference_event_id),
            )
            self.event(
                conn,
                "interference_event",
                interference_event_id,
                "optimization.interference_resolved",
                actor,
                {"ended_at": ended_at},
            )
        return self.get_optimization_workspace(project_id)

    def evaluate_optimization_release(
        self,
        project_id: str,
        release_id: str,
        payload: dict[str, Any],
        actor: str = "user",
    ) -> dict[str, Any]:
        evaluation = validate_evaluation(payload)
        workspace = self.get_optimization_workspace(project_id)
        release = next((item for item in workspace["releases"] if item["release_id"] == release_id), None)
        if not release:
            raise WorkbenchError(f"unknown release: {release_id}")
        before = [item for item in workspace["observations"] if item["phase"] == "before"]
        after = [item for item in workspace["observations"] if item["phase"] == "after" and item["release_id"] == release_id]
        if not before or not after:
            if evaluation["decision"] != "inconclusive":
                raise WorkbenchError("keep or rollback requires both before and after observations")
        comparable: list[dict[str, Any]] = []
        for after_item in after:
            matches = [
                item for item in before
                if item["source"] == after_item["source"] and item["source_class"] == after_item["source_class"]
                and item["period_end"] <= release["published_at"][:10]
            ]
            if not matches:
                continue
            before_item = max(matches, key=lambda item: (item["period_end"], item["created_at"]))
            shared = sorted(
                key for key in set(before_item["metrics"]) & set(after_item["metrics"])
                if before_item["metrics"][key] is not None and after_item["metrics"][key] is not None
            )
            for key in shared:
                old = before_item["metrics"][key]
                new = after_item["metrics"][key]
                comparable.append(
                    {
                        "metric": key,
                        "source": after_item["source"],
                        "before_observation_id": before_item["observation_id"],
                        "after_observation_id": after_item["observation_id"],
                        "before": old,
                        "after": new,
                        "delta": new - old,
                        "delta_percent": ((new - old) / old * 100) if old else None,
                    }
                )
        open_events = [
            item for item in workspace["interference_events"]
            if item["status"] == "open" and (item["release_id"] in {None, release_id})
        ]
        if evaluation["decision"] in {"keep", "rollback"}:
            if not comparable:
                raise WorkbenchError("keep or rollback requires at least one comparable metric from the same source")
            if open_events:
                raise WorkbenchError("resolve or explicitly close interference events before keep or rollback")
        evidence = {
            "comparable_metrics": comparable,
            "open_interference_event_ids": [item["interference_event_id"] for item in open_events],
            "before_observation_ids": [item["observation_id"] for item in before],
            "after_observation_ids": [item["observation_id"] for item in after],
            "actor": actor,
        }
        now = iso()
        with self.connect() as conn:
            evaluation_id = f"opteval_{new_ulid()}"
            conn.execute(
                "INSERT INTO optimization_evaluations(optimization_evaluation_id, project_id, release_id, decision, "
                "rationale, evidence_json, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (evaluation_id, project_id, release_id, evaluation["decision"], evaluation["rationale"], json_dump(evidence), now),
            )
            if evaluation["decision"] in {"keep", "rollback"}:
                release_status = "kept" if evaluation["decision"] == "keep" else "rolled_back"
                conn.execute(
                    "UPDATE release_records SET status = ?, updated_at = ? WHERE release_id = ?",
                    (release_status, now, release_id),
                )
            self.event(conn, "release", release_id, f"optimization.{evaluation['decision']}", actor, evidence)
        return self.get_optimization_workspace(project_id)
