from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import __version__
from .core import Workbench


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("CODEX_IMAGE_WORKBENCH_ROOT", DEFAULT_ROOT)).expanduser().resolve()
DB_PATH = os.environ.get("CODEX_IMAGE_WORKBENCH_DB")
REGISTRY_PATH = os.environ.get("CODEX_IMAGE_WORKBENCH_REGISTRY")

app = Workbench(
    ROOT,
    Path(DB_PATH).expanduser() if DB_PATH else None,
    Path(REGISTRY_PATH).expanduser() if REGISTRY_PATH else None,
)
mcp = FastMCP(
    "codex-image-workbench",
    instructions=(
        "Use these tools to manage the local Codex Image Workbench queue. "
        "A succeeded generation job is not an approved image: technical checks, manual QC, "
        "and Registry governance remain separate gates."
    ),
)


@mcp.tool()
def workbench_health() -> dict[str, Any]:
    """Return local workbench paths, version, and queue counts."""
    return {
        "ok": True,
        "version": __version__,
        "root": str(app.root),
        "database": str(app.db_path),
        "registry": str(app.registry_path),
        "dashboard": app.dashboard(),
    }


@mcp.tool()
def list_projects() -> list[dict[str, Any]]:
    """List image workbench projects and their current job and asset counts."""
    return app.list_projects()


@mcp.tool()
def get_project(project_id: str) -> dict[str, Any]:
    """Get a project with its slots, generation jobs, and image assets."""
    return app.get_project(project_id)


@mcp.tool()
def create_project(
    name: str,
    project_mode: str,
    brand: str,
    sku: str,
    marketplace: str = "US",
) -> dict[str, Any]:
    """Create a launch or optimize image project."""
    return app.create_project(
        {
            "name": name,
            "project_mode": project_mode,
            "brand": brand,
            "sku": sku,
            "marketplace": marketplace,
        }
    )


@mcp.tool()
def create_generation_job(
    project_id: str,
    slot_key: str,
    prompt: str,
    execution_mode: str = "codex_auto",
    operation: str = "generate",
    parent_asset_id: str | None = None,
    invariants: list[str] | None = None,
    avoid: list[str] | None = None,
    acceptance: list[str] | None = None,
    references: list[dict[str, Any]] | None = None,
    expected_output: dict[str, Any] | None = None,
    max_attempts: int = 3,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Create an automatic or manual generation/edit job from a structured image contract."""
    payload = {
        "slot_key": slot_key,
        "prompt": prompt,
        "execution_mode": execution_mode,
        "operation": operation,
        "parent_asset_id": parent_asset_id,
        "invariants": invariants or [],
        "avoid": avoid or [],
        "acceptance": acceptance or [],
        "references": references or [],
        "expected_output": expected_output or {"format": "png", "aspect_ratio": "1:1"},
        "max_attempts": max_attempts,
    }
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    job, created = app.create_job(project_id, payload)
    return {"created": created, "job": job}


@mcp.tool()
def list_generation_jobs(project_id: str | None = None) -> list[dict[str, Any]]:
    """List generation jobs, optionally restricted to one project."""
    return app.list_jobs(project_id)


@mcp.tool()
def claim_generation_job(worker: str, lease_seconds: int = 900) -> dict[str, Any]:
    """Claim the oldest queued codex_auto job for a resumable Codex worker."""
    return {"job": app.claim_job(worker, lease_seconds)}


@mcp.tool()
def heartbeat_generation_job(job_id: str, worker: str, lease_seconds: int = 900) -> dict[str, Any]:
    """Extend a generation job lease held by the same worker."""
    return app.heartbeat(job_id, worker, lease_seconds)


@mcp.tool()
def complete_generation_job(job_id: str, worker: str, output_path: str) -> dict[str, Any]:
    """Attach a generated image to a leased job and run technical checks."""
    return app.complete_job(job_id, worker, Path(output_path).expanduser())


@mcp.tool()
def fail_generation_job(job_id: str, worker: str, error: str, retry: bool = False) -> dict[str, Any]:
    """Fail a leased job, optionally requeueing it within the configured attempt limit."""
    return app.fail_job(job_id, worker, error, retry)


@mcp.tool()
def export_generation_package(job_id: str) -> dict[str, str]:
    """Export a self-contained prompt and reference package for manual generation."""
    return {"job_id": job_id, "package_path": str(app.export_package(job_id))}


@mcp.tool()
def import_generation_result(job_id: str, output_path: str) -> dict[str, Any]:
    """Import an image for a manual job and run technical checks."""
    return app.import_result(job_id, Path(output_path).expanduser())


@mcp.tool()
def get_asset(asset_id: str) -> dict[str, Any]:
    """Get one image asset with its generation contract and quality states."""
    return app.get_asset(asset_id)


@mcp.tool()
def evaluate_asset(
    asset_id: str,
    status: str,
    notes: str = "",
    evidence: dict[str, Any] | None = None,
    actor: str = "codex",
) -> dict[str, Any]:
    """Record needs_review, passed, or failed manual QC for an image asset."""
    return app.evaluate_asset(asset_id, status, notes, evidence or {}, actor)


@mcp.tool()
def register_candidate(asset_id: str, actor: str = "codex") -> dict[str, Any]:
    """Register a technically and manually approved asset as a Registry candidate."""
    return app.nominate_candidate(asset_id, actor)


@mcp.tool()
def promote_registry_asset(
    asset_id: str,
    status: str,
    approved_by: str,
    approved_at: str,
    decision_ref: str,
    actor: str = "codex",
) -> dict[str, Any]:
    """Promote a registered asset with explicit human decision evidence."""
    return app.promote_registry_asset(
        asset_id, status, approved_by, approved_at, decision_ref, actor
    )


@mcp.tool()
def reject_registry_asset(
    asset_id: str,
    notes: str,
    decided_by: str,
    decided_at: str,
    decision_ref: str,
    actor: str = "codex",
) -> dict[str, Any]:
    """Reject a transient or candidate asset while retaining version lineage."""
    return app.reject_registry_asset(
        asset_id, notes, decided_by, decided_at, decision_ref, actor
    )


@mcp.tool()
def check_registry() -> dict[str, Any]:
    """Run a read-only consistency check against the central asset Registry."""
    return app.registry_check()


@mcp.tool()
def import_launch_intake(
    project_id: str,
    intake: dict[str, Any],
    source_type: str = "codex_normalized",
    actor: str = "codex",
) -> dict[str, Any]:
    """Import normalized P1 product facts, claims, selling points, references, brand, and competitor inputs."""
    return app.import_launch_intake(project_id, intake, source_type, actor)


@mcp.tool()
def get_launch_workspace(project_id: str) -> dict[str, Any]:
    """Get P1 intake, coverage, strategy, Gate decisions, sequence, and image contracts."""
    return app.get_launch_workspace(project_id)


@mcp.tool()
def save_launch_strategy(
    project_id: str,
    strategy: dict[str, Any],
    actor: str = "codex",
) -> dict[str, Any]:
    """Save a P1 visual strategy draft using only IDs and evidence from the imported intake."""
    return app.save_launch_strategy(project_id, strategy, actor)


@mcp.tool()
def decide_launch_gate(
    project_id: str,
    gate_key: str,
    status: str,
    decision: dict[str, Any] | None = None,
    actor: str = "user",
) -> dict[str, Any]:
    """Record an explicit approved or changes_requested decision for Gate 1 or Gate 2."""
    return app.decide_launch_gate(project_id, gate_key, status, decision or {}, actor)


@mcp.tool()
def save_launch_sequence(
    project_id: str,
    sequence: dict[str, Any],
    actor: str = "codex",
) -> dict[str, Any]:
    """Save a slot sequence after Gate 1, preserving selling-point priority and required baselines."""
    return app.save_launch_sequence(project_id, sequence, actor)


@mcp.tool()
def save_image_contracts(
    project_id: str,
    contracts: dict[str, Any],
    actor: str = "codex",
) -> dict[str, Any]:
    """Save reference-led Image Contracts after Gate 2 and calculate per-slot readiness."""
    return app.save_image_contracts(project_id, contracts, actor)


@mcp.tool()
def queue_image_contracts(project_id: str, actor: str = "user") -> dict[str, Any]:
    """Compile ready approved P1 contracts into shared automatic or manual generation jobs."""
    return app.queue_image_contracts(project_id, actor)


@mcp.tool()
def import_optimization_intake(
    project_id: str,
    intake: dict[str, Any],
    source_type: str = "codex_normalized",
    actor: str = "codex",
) -> dict[str, Any]:
    """Import a P2 current Listing snapshot, verified product inputs, evidence, and baseline observations."""
    return app.import_optimization_intake(project_id, intake, source_type, actor)


@mcp.tool()
def get_optimization_workspace(project_id: str) -> dict[str, Any]:
    """Get P2 Listing version, readiness, diagnosis Gate, challenges, releases, observations, and evaluations."""
    return app.get_optimization_workspace(project_id)


@mcp.tool()
def save_optimization_diagnosis(
    project_id: str,
    diagnosis: dict[str, Any],
    actor: str = "codex",
) -> dict[str, Any]:
    """Save an evidence-linked P2 diagnosis without treating correlation as image causation."""
    return app.save_optimization_diagnosis(project_id, diagnosis, actor)


@mcp.tool()
def decide_optimization_gate(
    project_id: str,
    status: str,
    decision: dict[str, Any] | None = None,
    actor: str = "user",
) -> dict[str, Any]:
    """Approve or request changes to the P2 diagnosis before challenge creation."""
    return app.decide_optimization_gate(project_id, status, decision or {}, actor)


@mcp.tool()
def save_optimization_contracts(
    project_id: str,
    contracts: dict[str, Any],
    actor: str = "codex",
) -> dict[str, Any]:
    """Save one-variable P2 challenge contracts and calculate their generation readiness."""
    return app.save_optimization_contracts(project_id, contracts, actor)


@mcp.tool()
def queue_optimization_contracts(project_id: str, actor: str = "user") -> dict[str, Any]:
    """Compile ready P2 challenge contracts into the shared resumable generation queue."""
    return app.queue_optimization_contracts(project_id, actor)


@mcp.tool()
def record_optimization_release(
    project_id: str,
    release: dict[str, Any],
    actor: str = "user",
) -> dict[str, Any]:
    """Record the exact publication time of a QC-approved challenge image."""
    return app.record_optimization_release(project_id, release, actor)


@mcp.tool()
def preflight_optimization_release(
    project_id: str,
    optimization_contract_id: str,
    asset_id: str,
) -> dict[str, Any]:
    """Check release asset, contract, Registry approval, and rollback target without writing state."""
    return app.get_optimization_release_preflight(
        project_id, optimization_contract_id, asset_id
    )


@mcp.tool()
def add_optimization_observation(
    project_id: str,
    release_id: str,
    observation: dict[str, Any],
    actor: str = "codex",
) -> dict[str, Any]:
    """Add a post-release metric window with explicit source and source class."""
    return app.add_optimization_observation(project_id, release_id, observation, actor)


@mcp.tool()
def add_optimization_interference_event(
    project_id: str,
    event: dict[str, Any],
    actor: str = "user",
) -> dict[str, Any]:
    """Record price, promotion, ads, inventory, reviews, or other attribution interference."""
    return app.add_optimization_interference_event(project_id, event, actor)


@mcp.tool()
def resolve_optimization_interference_event(
    project_id: str,
    interference_event_id: str,
    ended_at: str,
    actor: str = "user",
) -> dict[str, Any]:
    """Close an interference event so a clean evaluation can proceed."""
    return app.resolve_optimization_interference_event(project_id, interference_event_id, ended_at, actor)


@mcp.tool()
def evaluate_optimization_release(
    project_id: str,
    release_id: str,
    evaluation: dict[str, Any],
    actor: str = "user",
) -> dict[str, Any]:
    """Record keep, rollback, or inconclusive after checking comparable metrics and open interference."""
    return app.evaluate_optimization_release(project_id, release_id, evaluation, actor)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
