# P0 Status

Date: 2026-07-15
Decision: PASS WITH LIMITS / READY FOR P1

## Delivered

- Local HTTP service and dependency-free workbench UI.
- SQLite schema for projects, slots, jobs, assets, evaluations, events, and worker sessions.
- Shared `codex_auto` and `manual_import` job contract.
- Persistent worker lease, heartbeat, retry, checkpoint, and recovery behavior.
- Manual generation package export and binary result import.
- Asset hash, image metadata, technical checks, manual QC, and parent-child versions.
- Separate execution, technical, QC, and registry states.
- Atomic candidate registration and approved promotion gates through `registryctl`.
- Studio queue, result gallery, version inspector, and Quality view.
- Thin Codex plugin adapter and repository-local Marketplace entry.
- stdio MCP server exposing project, queue, worker, result, QC, and Registry tools.

## Verification

- `python3 -m unittest discover -s tests -v`: 8 passed.
- `node --check workbench/static/app.js`: passed.
- `bash -n scripts/start.sh`: passed.
- `HEAD /styles.css`: HTTP 200.
- Registry read-only check: valid, 30 assets.
- Browser: 1280 x 720 and 390 x 844 passed visual and interaction checks.
- Browser console: 0 errors, 0 warnings.
- QC transition verified from `not_run` to `passed`; candidate registration became enabled.
- Central Registry was not modified during browser verification.
- Plugin validation passed and Codex reports it as `installed, enabled`.
- A fresh Codex process reclaimed an expired lease at attempt 2 and closed the test job.
- A 20-job state-machine soak passed: 10 generate, 10 edit, 4 workers, 1 expiry recovery.

## Runtime Demo

- Project: `prj_01KXJ1NB0E73F9F1RS5KJ9A1MR`
- Job: `job_01KXJ1NEWFWXVFYV2DT2F6YRD7`
- Asset: `wb-vlogara-p1-demo-listing-image-01KXJ1NEWFG5BPRPQF6NNY6JYC`
- Database: `runtime/workbench.sqlite`
- Service: `http://127.0.0.1:8765`

## Remaining Production Hardening

1. Run a 15-30 call soak using actual Codex ImageGen and record model-context rotation limits.
2. Confirm an interactive Codex Desktop task can approve the installed MCP write tools.
3. Reconcile a promoted real candidate between SQLite and the central Registry after explicit asset approval.

P0 may close and P1 may start. Automation support remains `interactive_resumable`, not unattended background execution.
