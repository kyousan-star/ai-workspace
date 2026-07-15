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
