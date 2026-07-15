# P-1 Status

Date: 2026-07-14

## Gate State

`IN PROGRESS`

## Implemented

- SQLite job and event schema
- stable job and asset IDs
- idempotent job creation
- worker lease, heartbeat, expiry, and reclaim
- non-destructive result persistence with SHA-256
- first-class manual package export and result import
- per-worker and per-job throughput report
- deterministic unit tests for queue and recovery behavior

## Verified So Far

- `python3 -m unittest discover -s tests -v`: 5 tests passed
- cross-process lease recovery:
  - job: `job_01KXHWX4TXCFZR3VSQ73ATQVY2`
  - queued state survived the creating process before the first claim
  - first worker: `codex-session-p1-a`
  - recovery worker: `codex-session-p1-b`
  - attempt count advanced from 1 to 2 after lease expiry
- manual package and result import:
  - job: `job_01KXHWY45168724N5WNE52FK4S`
  - imported result SHA-256: `43200e8226c8644a9bac73ec3063a38ab1536e2696615fff13d4fd7771bbf663`
  - job, asset, slot, output path, bytes, timing, and hash were retained

## Still Required For Gate Decision

- execute built-in ImageGen jobs through at least two worker IDs
- run a representative multi-job workload
- record observed task duration and worker capacity
- state the supported `codex_auto` operating level

P-1 failure cannot remove `manual_import`; it only changes the supported level
of automatic Codex execution.
