# Codex Web Access Isolation

Codex uses the upstream implementation in `/Users/lihuan/.claude/skills/web-access` as read-only source material and runs its own HTTP proxy on port `3457`.

## Fixed Paths

- Proxy base URL: `http://127.0.0.1:3457`
- Temporary files: `/private/tmp/codex-web-access`
- Codex site notes: `/Users/lihuan/.codex/web-access/site-patterns`
- Upstream implementation: `/Users/lihuan/.claude/skills/web-access`

## Operating Contract

1. Start with `scripts/start-proxy.sh`.
2. Create a new tab with `/new`.
3. Store the returned `targetId` in the working notes for the task.
4. Use only that `targetId` unless the user explicitly asks otherwise.
5. Save screenshots and downloads under `/private/tmp/codex-web-access`.
6. Close Codex-created tabs after use.

Do not use port `3456`; that port is reserved for Claude's default `web-access` workflow.
