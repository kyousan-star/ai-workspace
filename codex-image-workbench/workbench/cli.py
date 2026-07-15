from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .core import Workbench
from .util import WorkbenchError


DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise WorkbenchError("JSON input must be an object")
    return value


def emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex Image Workbench CLI")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--registry", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")
    sub.add_parser("dashboard")
    sub.add_parser("projects")

    create_project = sub.add_parser("create-project")
    create_project.add_argument("--json", type=Path, required=True)

    show_project = sub.add_parser("show-project")
    show_project.add_argument("--project", required=True)

    create_job = sub.add_parser("create-job")
    create_job.add_argument("--project", required=True)
    create_job.add_argument("--json", type=Path, required=True)

    jobs = sub.add_parser("jobs")
    jobs.add_argument("--project")

    claim = sub.add_parser("claim")
    claim.add_argument("--worker", required=True)
    claim.add_argument("--lease-seconds", type=int, default=900)

    heartbeat = sub.add_parser("heartbeat")
    heartbeat.add_argument("--job", required=True)
    heartbeat.add_argument("--worker", required=True)
    heartbeat.add_argument("--lease-seconds", type=int, default=900)

    complete = sub.add_parser("complete")
    complete.add_argument("--job", required=True)
    complete.add_argument("--worker", required=True)
    complete.add_argument("--output", type=Path, required=True)

    fail = sub.add_parser("fail")
    fail.add_argument("--job", required=True)
    fail.add_argument("--worker", required=True)
    fail.add_argument("--error", required=True)
    fail.add_argument("--retry", action="store_true")

    export = sub.add_parser("export-package")
    export.add_argument("--job", required=True)

    import_result = sub.add_parser("import-result")
    import_result.add_argument("--job", required=True)
    import_result.add_argument("--file", type=Path, required=True)

    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--asset", required=True)
    evaluate.add_argument("--status", choices=["needs_review", "passed", "failed"], required=True)
    evaluate.add_argument("--notes", default="")

    candidate = sub.add_parser("register-candidate")
    candidate.add_argument("--asset", required=True)

    asset = sub.add_parser("show-asset")
    asset.add_argument("--asset", required=True)

    launch = sub.add_parser("launch")
    launch.add_argument("--project", required=True)

    intake = sub.add_parser("import-intake")
    intake.add_argument("--project", required=True)
    intake.add_argument("--json", type=Path, required=True)

    strategy = sub.add_parser("save-strategy")
    strategy.add_argument("--project", required=True)
    strategy.add_argument("--json", type=Path, required=True)

    gate = sub.add_parser("decide-gate")
    gate.add_argument("--project", required=True)
    gate.add_argument("--gate", choices=["gate1", "gate2"], required=True)
    gate.add_argument("--status", choices=["approved", "changes_requested"], required=True)
    gate.add_argument("--json", type=Path)

    sequence = sub.add_parser("save-sequence")
    sequence.add_argument("--project", required=True)
    sequence.add_argument("--json", type=Path, required=True)

    contracts = sub.add_parser("save-contracts")
    contracts.add_argument("--project", required=True)
    contracts.add_argument("--json", type=Path, required=True)

    queue_contracts = sub.add_parser("queue-contracts")
    queue_contracts.add_argument("--project", required=True)

    optimize = sub.add_parser("optimize")
    optimize.add_argument("--project", required=True)

    optimize_intake = sub.add_parser("import-optimization-intake")
    optimize_intake.add_argument("--project", required=True)
    optimize_intake.add_argument("--json", type=Path, required=True)

    diagnosis = sub.add_parser("save-diagnosis")
    diagnosis.add_argument("--project", required=True)
    diagnosis.add_argument("--json", type=Path, required=True)

    diagnosis_gate = sub.add_parser("decide-diagnosis")
    diagnosis_gate.add_argument("--project", required=True)
    diagnosis_gate.add_argument("--status", choices=["approved", "changes_requested"], required=True)
    diagnosis_gate.add_argument("--json", type=Path)

    optimization_contracts = sub.add_parser("save-optimization-contracts")
    optimization_contracts.add_argument("--project", required=True)
    optimization_contracts.add_argument("--json", type=Path, required=True)

    queue_optimization = sub.add_parser("queue-optimization-contracts")
    queue_optimization.add_argument("--project", required=True)

    release = sub.add_parser("record-release")
    release.add_argument("--project", required=True)
    release.add_argument("--json", type=Path, required=True)

    observation = sub.add_parser("add-observation")
    observation.add_argument("--project", required=True)
    observation.add_argument("--release", required=True)
    observation.add_argument("--json", type=Path, required=True)

    interference = sub.add_parser("add-interference")
    interference.add_argument("--project", required=True)
    interference.add_argument("--json", type=Path, required=True)

    resolve_interference = sub.add_parser("resolve-interference")
    resolve_interference.add_argument("--project", required=True)
    resolve_interference.add_argument("--event", required=True)
    resolve_interference.add_argument("--ended-at", required=True)

    release_evaluation = sub.add_parser("evaluate-release")
    release_evaluation.add_argument("--project", required=True)
    release_evaluation.add_argument("--release", required=True)
    release_evaluation.add_argument("--json", type=Path, required=True)

    sub.add_parser("registry-check")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        app = Workbench(args.root, args.db, args.registry)
        if args.command == "init":
            result = {
                "ok": True,
                "root": str(app.root),
                "database": str(app.db_path),
                "registry": str(app.registry_path),
            }
        elif args.command == "dashboard":
            result = app.dashboard()
        elif args.command == "projects":
            result = app.list_projects()
        elif args.command == "create-project":
            result = app.create_project(read_json(args.json))
        elif args.command == "show-project":
            result = app.get_project(args.project)
        elif args.command == "create-job":
            job, created = app.create_job(args.project, read_json(args.json))
            result = {"created": created, "job": job}
        elif args.command == "jobs":
            result = app.list_jobs(args.project)
        elif args.command == "claim":
            result = app.claim_job(args.worker, args.lease_seconds)
        elif args.command == "heartbeat":
            result = app.heartbeat(args.job, args.worker, args.lease_seconds)
        elif args.command == "complete":
            result = app.complete_job(args.job, args.worker, args.output)
        elif args.command == "fail":
            result = app.fail_job(args.job, args.worker, args.error, args.retry)
        elif args.command == "export-package":
            result = {"job_id": args.job, "package": str(app.export_package(args.job))}
        elif args.command == "import-result":
            result = app.import_result(args.job, args.file)
        elif args.command == "evaluate":
            result = app.evaluate_asset(args.asset, args.status, args.notes)
        elif args.command == "register-candidate":
            result = app.nominate_candidate(args.asset)
        elif args.command == "show-asset":
            result = app.get_asset(args.asset)
        elif args.command == "launch":
            result = app.get_launch_workspace(args.project)
        elif args.command == "import-intake":
            result = app.import_launch_intake(args.project, read_json(args.json), actor="cli")
        elif args.command == "save-strategy":
            result = app.save_launch_strategy(args.project, read_json(args.json), actor="cli")
        elif args.command == "decide-gate":
            result = app.decide_launch_gate(
                args.project,
                args.gate,
                args.status,
                read_json(args.json) if args.json else {},
                actor="cli",
            )
        elif args.command == "save-sequence":
            result = app.save_launch_sequence(args.project, read_json(args.json), actor="cli")
        elif args.command == "save-contracts":
            result = app.save_image_contracts(args.project, read_json(args.json), actor="cli")
        elif args.command == "queue-contracts":
            result = app.queue_image_contracts(args.project, actor="cli")
        elif args.command == "optimize":
            result = app.get_optimization_workspace(args.project)
        elif args.command == "import-optimization-intake":
            result = app.import_optimization_intake(args.project, read_json(args.json), actor="cli")
        elif args.command == "save-diagnosis":
            result = app.save_optimization_diagnosis(args.project, read_json(args.json), actor="cli")
        elif args.command == "decide-diagnosis":
            result = app.decide_optimization_gate(
                args.project,
                args.status,
                read_json(args.json) if args.json else {},
                actor="cli",
            )
        elif args.command == "save-optimization-contracts":
            result = app.save_optimization_contracts(args.project, read_json(args.json), actor="cli")
        elif args.command == "queue-optimization-contracts":
            result = app.queue_optimization_contracts(args.project, actor="cli")
        elif args.command == "record-release":
            result = app.record_optimization_release(args.project, read_json(args.json), actor="cli")
        elif args.command == "add-observation":
            result = app.add_optimization_observation(args.project, args.release, read_json(args.json), actor="cli")
        elif args.command == "add-interference":
            result = app.add_optimization_interference_event(args.project, read_json(args.json), actor="cli")
        elif args.command == "resolve-interference":
            result = app.resolve_optimization_interference_event(
                args.project, args.event, args.ended_at, actor="cli"
            )
        elif args.command == "evaluate-release":
            result = app.evaluate_optimization_release(args.project, args.release, read_json(args.json), actor="cli")
        elif args.command == "registry-check":
            result = app.registry_check()
        else:
            raise WorkbenchError(f"unknown command: {args.command}")
        emit(result)
        return 0
    except (WorkbenchError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
