# P-1 Codex Image Workbench CLI Spike

This directory validates the execution contract before any UI or plugin work.
It intentionally uses only Python's standard library and SQLite.

## What It Proves

- self-contained image jobs survive Codex task changes;
- a worker claims jobs through a renewable lease;
- expired jobs can be reclaimed without creating a second database row;
- results retain job, asset, parent, slot, hash, timing, and worker lineage;
- manual prompt-package export and result import use the same result model;
- throughput can be measured per replaceable Codex worker.

It does not claim that Codex Desktop provides an official always-on worker.
An active Codex task still has to claim a `codex_auto` job and call built-in
ImageGen. `manual_import` is a first-class execution mode, not an error path.

## Quick Start

```bash
cd /Users/lihuan/ai-workspace/codex-image-workbench/p1
python3 workbench_p1.py init
python3 workbench_p1.py create --contract contracts/sample-generate.json --mode codex_auto
python3 workbench_p1.py claim --worker codex-session-01
```

After Codex creates an image, finish the claimed job:

```bash
python3 workbench_p1.py complete \
  --job <job-id> \
  --worker codex-session-01 \
  --output /absolute/path/to/generated.png
```

Manual execution uses the same contract:

```bash
python3 workbench_p1.py create --contract contracts/sample-generate.json --mode manual_import
python3 workbench_p1.py export-package --job <job-id> --out artifacts/manual-packages
python3 workbench_p1.py import-result --job <job-id> --file /absolute/path/to/result.png
```

Inspect state and measurements:

```bash
python3 workbench_p1.py list
python3 workbench_p1.py events --limit 50
python3 workbench_p1.py report --out evidence/runtime-report.json
```

Run deterministic queue and recovery tests:

```bash
python3 -m unittest discover -s tests -v
```

## P-1 Boundary

The CLI does not call ImageGen itself because the built-in tool is available
inside a Codex task, not as a local background API. The worker protocol is:

1. claim one JSON job;
2. invoke built-in ImageGen using the returned contract;
3. place the generated file in the workspace;
4. call `complete` with the same worker and job IDs;
5. start a new Codex task when session rotation is needed.
