# P-1 Status

Date: 2026-07-14

## Gate State

`PASS WITH LIMITS`

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

## Built-in ImageGen Results

- 5 `codex_auto` jobs succeeded: 4 generate and 1 parent-image edit
- 1 `manual_import` job succeeded at transport and lineage level
- all 5 built-in results are 1254 x 1254 PNG files
- all 6 database jobs ended in GenerationJob `succeeded`
- generated project artifacts use about 7.5 MB

Observed clean task durations:

| Work | Worker | Seconds |
|---|---|---:|
| generate PT02 | `codex-session-p1-c` | 37.5 |
| generate PT03 | `codex-session-p1-c` | 26.2 |
| generate PT04 | `codex-session-p1-d` | 29.3 |
| edit PT01 parent | `codex-session-p1-d` | 81.7 |

The interrupted first generate took 1270.4 seconds because it included the
user-confirmation pause. It is recovery evidence, not throughput evidence.
The median of the three uninterrupted generate jobs is about 29.3 seconds.

## Decision

`codex_auto` is feasible at the `interactive_resumable` level: an active Codex
task must claim the queue, but persisted jobs, leases, outputs, and checkpoints
can survive worker replacement. This test does not prove an official always-on
Codex listener or unattended background operation.

`manual_import` remains a supported first-class mode. GenerationJob `succeeded`
means execution or import completed; it does not mean the image passed its
contract, QC, or approval gate.

P0 may start.

## Carry Into P0

- prove one handoff in a genuinely separate user-created Codex task
- run a 15-30 operation generation/edit/QC soak test
- keep execution success separate from image evaluation and approval

P-1 limits cannot remove `manual_import`; they only constrain the supported
level of automatic Codex execution.
