# P0 Status

Date: 2026-07-15
Decision: CORE PASS / INTEGRATION IN PROGRESS

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

## Verification

- `python3 -m unittest discover -s tests -v`: 7 passed.
- `node --check workbench/static/app.js`: passed.
- `bash -n scripts/start.sh`: passed.
- `HEAD /styles.css`: HTTP 200.
- Registry read-only check: valid, 30 assets.
- Browser: 1280 x 720 and 390 x 844 passed visual and interaction checks.
- Browser console: 0 errors, 0 warnings.
- QC transition verified from `not_run` to `passed`; candidate registration became enabled.
- Central Registry was not modified during browser verification.

## Runtime Demo

- Project: `prj_01KXJ1NB0E73F9F1RS5KJ9A1MR`
- Job: `job_01KXJ1NEWFWXVFYV2DT2F6YRD7`
- Asset: `wb-vlogara-p1-demo-listing-image-01KXJ1NEWFG5BPRPQF6NNY6JYC`
- Database: `runtime/workbench.sqlite`
- Service: `http://127.0.0.1:8765`

## Remaining P0 Integration

1. Package the service as a Codex plugin and add install/uninstall checks.
2. Run a real cross-task Codex worker takeover.
3. Run the 15-30 job soak test and record session rotation limits.
4. Reconcile a promoted real candidate between SQLite and the central Registry after explicit asset approval.

Until these items close, automation support remains `interactive_resumable`, not unattended background execution.
