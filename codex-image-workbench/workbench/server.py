from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__
from .core import Workbench
from .util import WorkbenchError


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
MAX_JSON_BODY = 2 * 1024 * 1024
MAX_UPLOAD_BODY = 80 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    app: Workbench
    static_root: Path

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def send_json(self, value: object, status: int = 200) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def send_file(self, path: Path, cache: bool = False, head_only: bool = False) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        payload = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "public, max-age=3600" if cache else "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(payload)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_JSON_BODY:
            raise WorkbenchError("invalid JSON body size")
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WorkbenchError(f"invalid JSON body: {exc}") from exc
        if not isinstance(value, dict):
            raise WorkbenchError("JSON body must be an object")
        return value

    def route(self) -> tuple[str, dict[str, list[str]]]:
        parsed = urlparse(self.path)
        return unquote(parsed.path), parse_qs(parsed.query)

    def do_GET(self) -> None:
        try:
            path, query = self.route()
            if path == "/api/health":
                self.send_json({"ok": True, "version": __version__, "mode": "local"})
                return
            if path == "/api/dashboard":
                self.send_json(self.app.dashboard())
                return
            if path == "/api/projects":
                self.send_json(self.app.list_projects())
                return
            launch_match = re.fullmatch(r"/api/projects/([^/]+)/launch", path)
            if launch_match:
                self.send_json(self.app.get_launch_workspace(launch_match.group(1)))
                return
            optimize_match = re.fullmatch(r"/api/projects/([^/]+)/optimize", path)
            if optimize_match:
                self.send_json(self.app.get_optimization_workspace(optimize_match.group(1)))
                return
            optimize_image = re.fullmatch(
                r"/api/projects/([^/]+)/optimize/listing-images/([^/]+)/media", path
            )
            if optimize_image:
                self.send_file(
                    self.app.get_optimization_listing_image_path(
                        optimize_image.group(1), optimize_image.group(2)
                    ),
                    cache=True,
                )
                return
            project_match = re.fullmatch(r"/api/projects/([^/]+)", path)
            if project_match:
                self.send_json(self.app.get_project(project_match.group(1)))
                return
            if path == "/api/jobs":
                self.send_json(self.app.list_jobs((query.get("project_id") or [None])[0]))
                return
            job_match = re.fullmatch(r"/api/jobs/([^/]+)", path)
            if job_match:
                self.send_json(self.app.get_job(job_match.group(1)))
                return
            asset_match = re.fullmatch(r"/api/assets/([^/]+)", path)
            if asset_match:
                self.send_json(self.app.get_asset(asset_match.group(1)))
                return
            media_match = re.fullmatch(r"/api/assets/([^/]+)/media", path)
            if media_match:
                asset = self.app.get_asset(media_match.group(1))
                self.send_file(Path(asset["source_path"]), cache=True)
                return
            if path == "/api/registry/check":
                self.send_json(self.app.registry_check())
                return
            self.serve_static(path)
        except WorkbenchError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self.send_json({"error": f"internal error: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_HEAD(self) -> None:
        path, _ = self.route()
        if path.startswith("/api/"):
            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)
            return
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        candidate = (self.static_root / relative).resolve()
        if self.static_root not in candidate.parents and candidate != self.static_root:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_file(candidate if candidate.is_file() else self.static_root / "index.html", head_only=True)

    def do_POST(self) -> None:
        try:
            path, query = self.route()
            if path == "/api/projects":
                self.send_json(self.app.create_project(self.read_json()), HTTPStatus.CREATED)
                return
            launch_intake = re.fullmatch(r"/api/projects/([^/]+)/launch/intake", path)
            if launch_intake:
                payload = self.read_json()
                self.send_json(
                    self.app.import_launch_intake(
                        launch_intake.group(1),
                        payload.get("intake") if isinstance(payload.get("intake"), dict) else payload,
                        str(payload.get("source_type", "ui_import")),
                        "user",
                    )
                )
                return
            launch_strategy = re.fullmatch(r"/api/projects/([^/]+)/launch/strategy", path)
            if launch_strategy:
                self.send_json(self.app.save_launch_strategy(launch_strategy.group(1), self.read_json(), "user"))
                return
            launch_gate = re.fullmatch(r"/api/projects/([^/]+)/launch/gates/(gate1|gate2)", path)
            if launch_gate:
                payload = self.read_json()
                self.send_json(
                    self.app.decide_launch_gate(
                        launch_gate.group(1),
                        launch_gate.group(2),
                        str(payload.get("status", "")),
                        payload.get("decision") if isinstance(payload.get("decision"), dict) else {},
                        "user",
                    )
                )
                return
            launch_sequence = re.fullmatch(r"/api/projects/([^/]+)/launch/sequence", path)
            if launch_sequence:
                self.send_json(self.app.save_launch_sequence(launch_sequence.group(1), self.read_json(), "user"))
                return
            launch_contracts = re.fullmatch(r"/api/projects/([^/]+)/launch/contracts", path)
            if launch_contracts:
                self.send_json(self.app.save_image_contracts(launch_contracts.group(1), self.read_json(), "user"))
                return
            launch_queue = re.fullmatch(r"/api/projects/([^/]+)/launch/contracts/queue", path)
            if launch_queue:
                self.send_json(self.app.queue_image_contracts(launch_queue.group(1), "user"))
                return
            optimize_intake = re.fullmatch(r"/api/projects/([^/]+)/optimize/intake", path)
            if optimize_intake:
                payload = self.read_json()
                self.send_json(
                    self.app.import_optimization_intake(
                        optimize_intake.group(1),
                        payload.get("intake") if isinstance(payload.get("intake"), dict) else payload,
                        str(payload.get("source_type", "ui_import")),
                        "user",
                    )
                )
                return
            optimize_diagnosis = re.fullmatch(r"/api/projects/([^/]+)/optimize/diagnosis", path)
            if optimize_diagnosis:
                self.send_json(self.app.save_optimization_diagnosis(optimize_diagnosis.group(1), self.read_json(), "user"))
                return
            optimize_gate = re.fullmatch(r"/api/projects/([^/]+)/optimize/gate", path)
            if optimize_gate:
                payload = self.read_json()
                self.send_json(
                    self.app.decide_optimization_gate(
                        optimize_gate.group(1),
                        str(payload.get("status", "")),
                        payload.get("decision") if isinstance(payload.get("decision"), dict) else {},
                        "user",
                    )
                )
                return
            optimize_contracts = re.fullmatch(r"/api/projects/([^/]+)/optimize/contracts", path)
            if optimize_contracts:
                self.send_json(self.app.save_optimization_contracts(optimize_contracts.group(1), self.read_json(), "user"))
                return
            optimize_queue = re.fullmatch(r"/api/projects/([^/]+)/optimize/contracts/queue", path)
            if optimize_queue:
                self.send_json(self.app.queue_optimization_contracts(optimize_queue.group(1), "user"))
                return
            optimize_release = re.fullmatch(r"/api/projects/([^/]+)/optimize/releases", path)
            if optimize_release:
                self.send_json(self.app.record_optimization_release(optimize_release.group(1), self.read_json(), "user"))
                return
            optimize_observation = re.fullmatch(r"/api/projects/([^/]+)/optimize/releases/([^/]+)/observations", path)
            if optimize_observation:
                self.send_json(
                    self.app.add_optimization_observation(
                        optimize_observation.group(1),
                        optimize_observation.group(2),
                        self.read_json(),
                        "user",
                    )
                )
                return
            optimize_interference = re.fullmatch(r"/api/projects/([^/]+)/optimize/interference", path)
            if optimize_interference:
                self.send_json(
                    self.app.add_optimization_interference_event(
                        optimize_interference.group(1), self.read_json(), "user"
                    )
                )
                return
            optimize_interference_resolve = re.fullmatch(
                r"/api/projects/([^/]+)/optimize/interference/([^/]+)/resolve", path
            )
            if optimize_interference_resolve:
                payload = self.read_json()
                self.send_json(
                    self.app.resolve_optimization_interference_event(
                        optimize_interference_resolve.group(1),
                        optimize_interference_resolve.group(2),
                        str(payload.get("ended_at", "")),
                        "user",
                    )
                )
                return
            optimize_evaluation = re.fullmatch(r"/api/projects/([^/]+)/optimize/releases/([^/]+)/evaluation", path)
            if optimize_evaluation:
                self.send_json(
                    self.app.evaluate_optimization_release(
                        optimize_evaluation.group(1),
                        optimize_evaluation.group(2),
                        self.read_json(),
                        "user",
                    )
                )
                return
            project_jobs = re.fullmatch(r"/api/projects/([^/]+)/jobs", path)
            if project_jobs:
                job, created = self.app.create_job(project_jobs.group(1), self.read_json())
                self.send_json({"created": created, "job": job}, HTTPStatus.CREATED if created else HTTPStatus.OK)
                return
            job_export = re.fullmatch(r"/api/jobs/([^/]+)/export", path)
            if job_export:
                package = self.app.export_package(job_export.group(1))
                self.send_json({"job_id": job_export.group(1), "package": str(package)})
                return
            job_import = re.fullmatch(r"/api/jobs/([^/]+)/import", path)
            if job_import:
                self.handle_import(job_import.group(1), query)
                return
            job_heartbeat = re.fullmatch(r"/api/jobs/([^/]+)/heartbeat", path)
            if job_heartbeat:
                payload = self.read_json()
                self.send_json(
                    self.app.heartbeat(
                        job_heartbeat.group(1),
                        str(payload.get("worker", "")),
                        int(payload.get("lease_seconds", 900)),
                    )
                )
                return
            job_complete = re.fullmatch(r"/api/jobs/([^/]+)/complete", path)
            if job_complete:
                payload = self.read_json()
                self.send_json(
                    self.app.complete_job(
                        job_complete.group(1),
                        str(payload.get("worker", "")),
                        Path(str(payload.get("output", ""))),
                    )
                )
                return
            job_fail = re.fullmatch(r"/api/jobs/([^/]+)/fail", path)
            if job_fail:
                payload = self.read_json()
                self.send_json(
                    self.app.fail_job(
                        job_fail.group(1),
                        str(payload.get("worker", "")),
                        str(payload.get("error", "generation failed")),
                        bool(payload.get("retry", False)),
                    )
                )
                return
            if path == "/api/worker/claim":
                payload = self.read_json()
                self.send_json(
                    self.app.claim_job(
                        str(payload.get("worker", "")), int(payload.get("lease_seconds", 900))
                    )
                )
                return
            evaluation = re.fullmatch(r"/api/assets/([^/]+)/evaluation", path)
            if evaluation:
                payload = self.read_json()
                self.send_json(
                    self.app.evaluate_asset(
                        evaluation.group(1),
                        str(payload.get("status", "")),
                        str(payload.get("notes", "")),
                        payload.get("evidence") or {},
                    )
                )
                return
            candidate = re.fullmatch(r"/api/assets/([^/]+)/candidate", path)
            if candidate:
                self.send_json(self.app.nominate_candidate(candidate.group(1)))
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except WorkbenchError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self.send_json({"error": f"internal error: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_import(self, job_id: str, query: dict[str, list[str]]) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_UPLOAD_BODY:
            raise WorkbenchError("invalid upload size")
        filename = Path((query.get("filename") or ["result.png"])[0]).name
        suffix = Path(filename).suffix.lower() or ".bin"
        upload_dir = self.app.runtime / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        fd, raw_path = tempfile.mkstemp(prefix=f"{job_id}-", suffix=suffix, dir=upload_dir)
        temp_path = Path(raw_path)
        try:
            with os.fdopen(fd, "wb") as handle:
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise WorkbenchError("upload ended early")
                    handle.write(chunk)
                    remaining -= len(chunk)
            self.send_json(self.app.import_result(job_id, temp_path))
        finally:
            temp_path.unlink(missing_ok=True)

    def serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        candidate = (self.static_root / relative).resolve()
        if self.static_root not in candidate.parents and candidate != self.static_root:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if candidate.is_file():
            self.send_file(candidate)
            return
        self.send_file(self.static_root / "index.html")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex Image Workbench local server")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = Workbench(args.root, args.db, args.registry)
    handler = type("WorkbenchHandler", (Handler,), {"app": app, "static_root": Path(__file__).parent / "static"})
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Codex Image Workbench: http://{args.host}:{args.port}", flush=True)
    print(f"Database: {app.db_path}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
