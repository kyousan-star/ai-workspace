from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = 4


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def initialize(path: Path, workspace: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.executescript(
            """
            PRAGMA journal_mode = WAL;

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                project_mode TEXT NOT NULL CHECK(project_mode IN ('launch', 'optimize')),
                brand TEXT NOT NULL,
                sku TEXT NOT NULL,
                marketplace TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS image_slots (
                slot_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                slot_key TEXT NOT NULL,
                title TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(project_id, slot_key),
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                slot_id TEXT NOT NULL,
                execution_mode TEXT NOT NULL CHECK(execution_mode IN ('codex_auto', 'manual_import')),
                operation TEXT NOT NULL CHECK(operation IN ('generate', 'edit')),
                execution_status TEXT NOT NULL CHECK(execution_status IN (
                    'queued', 'leased', 'awaiting_import', 'succeeded', 'failed', 'cancelled'
                )),
                target_asset_id TEXT NOT NULL UNIQUE,
                parent_asset_id TEXT,
                contract_json TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                lease_owner TEXT,
                lease_expires_at TEXT,
                queued_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                error TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(slot_id) REFERENCES image_slots(slot_id)
            );

            CREATE TABLE IF NOT EXISTS assets (
                asset_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                slot_id TEXT NOT NULL,
                job_id TEXT NOT NULL UNIQUE,
                parent_asset_id TEXT,
                source_type TEXT NOT NULL CHECK(source_type IN ('codex_auto', 'manual_import')),
                source_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                file_format TEXT,
                width INTEGER,
                height INTEGER,
                technical_status TEXT NOT NULL CHECK(technical_status IN ('passed', 'failed')),
                technical_checks_json TEXT NOT NULL,
                qc_status TEXT NOT NULL DEFAULT 'not_run' CHECK(qc_status IN (
                    'not_run', 'needs_review', 'passed', 'failed'
                )),
                registry_status TEXT NOT NULL DEFAULT 'transient' CHECK(registry_status IN (
                    'transient', 'candidate', 'approved', 'published', 'validated', 'retired', 'rejected'
                )),
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(slot_id) REFERENCES image_slots(slot_id),
                FOREIGN KEY(job_id) REFERENCES jobs(job_id)
            );

            CREATE TABLE IF NOT EXISTS evaluations (
                evaluation_id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('needs_review', 'passed', 'failed')),
                notes TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(asset_id) REFERENCES assets(asset_id)
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT,
                detail_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS worker_sessions (
                worker_id TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                claimed_count INTEGER NOT NULL DEFAULT 0,
                completed_count INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS project_intakes (
                project_id TEXT PRIMARY KEY,
                schema_version TEXT NOT NULL,
                source_type TEXT NOT NULL,
                intake_json TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS coverage_reports (
                report_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('passed', 'warning', 'blocked')),
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS project_strategies (
                strategy_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN (
                    'draft', 'awaiting_gate1', 'approved', 'changes_requested', 'superseded'
                )),
                strategy_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, version),
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS project_gates (
                project_id TEXT NOT NULL,
                gate_key TEXT NOT NULL CHECK(gate_key IN ('gate1', 'gate2')),
                status TEXT NOT NULL CHECK(status IN ('pending', 'awaiting', 'approved', 'changes_requested')),
                decision_json TEXT NOT NULL,
                decided_by TEXT,
                decided_at TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(project_id, gate_key),
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS image_sequences (
                sequence_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN (
                    'awaiting_gate2', 'approved', 'changes_requested', 'superseded'
                )),
                sequence_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, version),
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS image_contracts (
                contract_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                sequence_id TEXT NOT NULL,
                slot_key TEXT NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('blocked', 'ready', 'queued', 'superseded')),
                contract_json TEXT NOT NULL,
                job_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, slot_key, version),
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(sequence_id) REFERENCES image_sequences(sequence_id),
                FOREIGN KEY(job_id) REFERENCES jobs(job_id)
            );

            CREATE TABLE IF NOT EXISTS listing_versions (
                listing_version_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('current', 'superseded')),
                schema_version TEXT NOT NULL,
                source_type TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                intake_json TEXT NOT NULL,
                readiness_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, version),
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS optimization_diagnostics (
                diagnostic_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                listing_version_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN (
                    'draft', 'awaiting_gate', 'approved', 'changes_requested', 'superseded'
                )),
                diagnostic_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, version),
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(listing_version_id) REFERENCES listing_versions(listing_version_id)
            );

            CREATE TABLE IF NOT EXISTS optimization_gates (
                project_id TEXT PRIMARY KEY,
                status TEXT NOT NULL CHECK(status IN ('pending', 'awaiting', 'approved', 'changes_requested')),
                decision_json TEXT NOT NULL,
                decided_by TEXT,
                decided_at TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE IF NOT EXISTS optimization_contracts (
                optimization_contract_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                diagnostic_id TEXT NOT NULL,
                challenge_key TEXT NOT NULL,
                slot_key TEXT NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('blocked', 'ready', 'queued', 'superseded')),
                contract_json TEXT NOT NULL,
                job_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, challenge_key, version),
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(diagnostic_id) REFERENCES optimization_diagnostics(diagnostic_id),
                FOREIGN KEY(job_id) REFERENCES jobs(job_id)
            );

            CREATE TABLE IF NOT EXISTS release_records (
                release_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                optimization_contract_id TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                slot_key TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('active', 'kept', 'rolled_back', 'superseded')),
                published_at TEXT NOT NULL,
                release_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(optimization_contract_id) REFERENCES optimization_contracts(optimization_contract_id),
                FOREIGN KEY(asset_id) REFERENCES assets(asset_id)
            );

            CREATE TABLE IF NOT EXISTS performance_observations (
                observation_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                listing_version_id TEXT,
                release_id TEXT,
                phase TEXT NOT NULL CHECK(phase IN ('before', 'after')),
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                source TEXT NOT NULL,
                source_class TEXT NOT NULL CHECK(source_class IN ('first_party', 'external_estimate', 'manual')),
                metrics_json TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(listing_version_id) REFERENCES listing_versions(listing_version_id),
                FOREIGN KEY(release_id) REFERENCES release_records(release_id)
            );

            CREATE TABLE IF NOT EXISTS interference_events (
                interference_event_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                release_id TEXT,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('open', 'resolved')),
                started_at TEXT NOT NULL,
                ended_at TEXT,
                description TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(release_id) REFERENCES release_records(release_id)
            );

            CREATE TABLE IF NOT EXISTS optimization_evaluations (
                optimization_evaluation_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                release_id TEXT NOT NULL,
                decision TEXT NOT NULL CHECK(decision IN ('keep', 'rollback', 'inconclusive')),
                rationale TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(release_id) REFERENCES release_records(release_id)
            );

            CREATE TABLE IF NOT EXISTS production_failures (
                failure_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                slot_key TEXT NOT NULL,
                job_id TEXT,
                asset_id TEXT,
                failure_class TEXT NOT NULL CHECK(failure_class IN (
                    'product_identity', 'product_geometry', 'product_proportion',
                    'composition', 'background', 'typography', 'technical', 'other'
                )),
                hard_stop INTEGER NOT NULL CHECK(hard_stop IN (0, 1)),
                notes TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(job_id) REFERENCES jobs(job_id),
                FOREIGN KEY(asset_id) REFERENCES assets(asset_id)
            );

            CREATE INDEX IF NOT EXISTS jobs_queue_idx
                ON jobs(execution_status, execution_mode, queued_at);
            CREATE INDEX IF NOT EXISTS assets_project_idx
                ON assets(project_id, created_at);
            CREATE INDEX IF NOT EXISTS events_entity_idx
                ON events(entity_type, entity_id, created_at);
            CREATE INDEX IF NOT EXISTS coverage_project_idx
                ON coverage_reports(project_id, created_at);
            CREATE INDEX IF NOT EXISTS contracts_project_idx
                ON image_contracts(project_id, status, slot_key);
            CREATE INDEX IF NOT EXISTS listing_versions_project_idx
                ON listing_versions(project_id, status, version);
            CREATE INDEX IF NOT EXISTS optimization_contracts_project_idx
                ON optimization_contracts(project_id, status, slot_key);
            CREATE INDEX IF NOT EXISTS releases_project_idx
                ON release_records(project_id, status, published_at);
            CREATE INDEX IF NOT EXISTS observations_project_idx
                ON performance_observations(project_id, phase, period_end);
            CREATE INDEX IF NOT EXISTS interference_project_idx
                ON interference_events(project_id, status, started_at);
            CREATE INDEX IF NOT EXISTS production_failures_project_idx
                ON production_failures(project_id, slot_key, created_at);
            """
        )
        conn.execute(
            "INSERT INTO settings(key, value) VALUES('workspace', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(workspace.resolve()),),
        )
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    finally:
        conn.close()
