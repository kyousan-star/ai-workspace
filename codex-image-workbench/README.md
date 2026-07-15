# Codex Image Workbench

Local Amazon image production and optimization workbench.

## P0 Scope

- launch and optimization projects
- persistent `codex_auto` and `manual_import` jobs
- replaceable worker leases and checkpoints
- result ingestion with SHA-256 and technical checks
- parent-child image versions
- manual QC kept separate from execution success
- candidate registration through atomic `registryctl`
- local Studio and Quality views

P0 supports an active, resumable Codex worker. It does not claim an official
always-on Codex listener or unattended background generation.

## P1 New Product Flow

Launch projects now support a gated planning path:

1. import normalized Product Facts, Claims, selling points, references,
   competitor packages, and brand rules;
2. resolve strategy blockers and product-photo capture requests;
3. approve Gate 1 strategy;
4. approve the Gate 2 image sequence;
5. save reference-led Image Contracts and compile ready contracts into the
   shared generation or manual-import queue.

The browser exposes this path under `Launch Plan`. Codex can use the same path
through seven P1 MCP tools, while the CLI equivalents are:

```bash
python3 -m workbench.cli import-intake --project <project-id> --json examples/p1-intake.json
python3 -m workbench.cli save-strategy --project <project-id> --json examples/p1-strategy.json
python3 -m workbench.cli decide-gate --project <project-id> --gate gate1 --status approved
python3 -m workbench.cli save-sequence --project <project-id> --json examples/p1-sequence.json
python3 -m workbench.cli decide-gate --project <project-id> --gate gate2 --status approved
python3 -m workbench.cli save-contracts --project <project-id> --json examples/p1-contracts.json
python3 -m workbench.cli queue-contracts --project <project-id>
```

The checked-in P1 inputs are synthetic workflow fixtures, not business facts or
image-quality evidence. See `P1-STATUS.md` for the current validation boundary.

## P2 Existing Listing Optimization

Optimize projects use a separate evidence and experiment path:

1. import the current Listing snapshot, verified product references, VOC and
   competitor evidence, external or first-party baseline observations, and
   dated interference events;
2. save an evidence-linked diagnosis and approve its Gate;
3. create one-variable challenge contracts only after the current Listing image
   set and local source images are complete;
4. reuse the shared generation queue, parent-child versions, technical checks,
   and manual QC;
5. record the actual Amazon publication time, post-release observation windows,
   and price, promotion, ads, inventory, review, or competitor interference;
6. record an explicit `keep`, `rollback`, or `inconclusive` decision.

Sorftime observations are stored as `external_estimate`. They do not substitute
for Seller Central Sessions or Unit Session Percentage and do not establish
image causation. The browser exposes this workflow under `Optimize Plan`; eleven
P2 MCP tools and matching CLI/HTTP operations use the same SQLite state.

The first real project is PH204 for Amazon AE. ListingVersion v2 contains the
complete eight-image Listing sequence and seven A+ modules. Generation readiness
passes, while diagnosis v2 remains at the human Gate before any challenge is
queued. See `P2-STATUS.md`.

## Codex Plugin

The thin plugin adapter lives at:

```text
/Users/lihuan/ai-workspace/plugins/codex-image-workbench
```

It contains only the plugin manifest and MCP launcher. Workbench code remains in
this directory, while shared Skills remain under `/Users/lihuan/ai-workspace/skills`.
The repository Marketplace is registered as `personal`, and the plugin is
installed as `codex-image-workbench@personal`.

New Codex tasks load the 34 stdio MCP tools. Write-capable MCP calls require an
interactive approval; non-interactive `codex exec` is not treated as an
unattended worker.

## Run

```bash
cd /Users/lihuan/ai-workspace/codex-image-workbench
./scripts/start.sh --port 8765
```

Open `http://127.0.0.1:8765`.

## Worker CLI

```bash
python3 -m workbench.cli claim --worker codex-workbench
python3 -m workbench.cli complete --job <job-id> --worker codex-workbench --output <image-path>
```

Manual jobs export a complete generation package and accept a dragged-in image
through the local UI. Imported or generated files must still pass technical and
manual QC before candidate registration is enabled.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Run the deterministic 20-job queue and state-machine soak separately:

```bash
python3 scripts/run_p0_soak.py --count 20 --workers 4
```

This soak does not call ImageGen and must not be used as image-quality evidence.
