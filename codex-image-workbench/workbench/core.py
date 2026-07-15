from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterator

from . import db
from .util import WorkbenchError, iso, json_dump, new_ulid, sha256_file, slug, technical_check, utcnow


ALLOWED_MODES = {"codex_auto", "manual_import"}
ALLOWED_OPERATIONS = {"generate", "edit"}
QC_STATUSES = {"needs_review", "passed", "failed"}


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    value = dict(row)
    for field in ("contract_json", "technical_checks_json", "evidence_json", "detail_json"):
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
