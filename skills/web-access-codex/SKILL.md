---
name: web-access-codex
description: Use isolated Chrome CDP web access for Codex when a web task needs login state, JavaScript-rendered pages, browser interaction, scrolling, screenshots, media extraction, or websites that static search/fetch cannot handle. Prefer built-in web search for ordinary public information lookup; use this skill only when real browser access materially improves task completion.
---

# Web Access Codex

Use this skill as Codex's isolated bridge to the existing `web-access` CDP proxy implementation without modifying Claude's skill files or sharing Claude's default proxy port.

## Isolation Rules

- Treat `/Users/lihuan/.claude/skills/web-access` as read-only.
- Use Codex proxy port `3457`, not Claude's default `3456`.
- Use Codex temporary files under `/private/tmp/codex-web-access`.
- Use Codex site notes under `/Users/lihuan/.codex/web-access/site-patterns`.
- Never operate on existing user or Claude tabs unless the user explicitly asks for that specific tab.
- Create a new background tab with `/new`, record its `targetId`, and only operate on that target.
- Close every Codex-created tab with `/close` when the task is complete.

## When To Use

Use this skill after ordinary built-in web tools are insufficient or likely insufficient:

- Logged-in websites or private dashboards.
- JavaScript-rendered, lazy-loaded, or interaction-heavy pages.
- Pages requiring click, scroll, expand, pagination, upload, or form interaction.
- Social/ecommerce/platform pages where static fetching commonly fails.
- Tasks that need a browser screenshot, real DOM inspection, image URL extraction, or video frame sampling.

Do not use this skill for simple public search, official documentation lookup, finance/weather/sports/time queries, or tasks where the built-in `web` tool is enough.

## Start Proxy

Use the bundled wrapper:

```bash
/Users/lihuan/.codex/skills/web-access-codex/scripts/start-proxy.sh
```

The wrapper sets:

```bash
CDP_PROXY_PORT=3457
CODEX_WEB_ACCESS_TMP=/private/tmp/codex-web-access
```

If the script reports that Chrome remote debugging is unavailable, tell the user the specific setup needed and stop. Do not fall back to Claude's `3456` proxy.

## API Pattern

Use `http://127.0.0.1:3457` for all API calls:

```bash
curl -s http://127.0.0.1:3457/health
curl -s "http://127.0.0.1:3457/new?url=https://example.com"
curl -s "http://127.0.0.1:3457/info?target=TARGET_ID"
curl -s -X POST "http://127.0.0.1:3457/eval?target=TARGET_ID" -d 'document.title'
curl -s "http://127.0.0.1:3457/screenshot?target=TARGET_ID&file=/private/tmp/codex-web-access/shot.png"
curl -s "http://127.0.0.1:3457/close?target=TARGET_ID"
```

Before interacting with an unfamiliar page, inspect its structure with `/info` and a small `/eval` query. Prefer DOM extraction for text, links, and media URLs; use screenshots when visual layout or rendered media matters.

## Safety

- Avoid bulk opening many pages at once.
- Prefer site-provided links from the DOM over hand-built URLs when operating inside platforms.
- For authenticated or state-changing actions, gather evidence first and ask before submitting, publishing, purchasing, deleting, sending messages, or changing account settings.
- If login is required, ask the user to log in through their Chrome and continue after confirmation.

## References

When detailed API behavior is needed, read the upstream files directly:

- `/Users/lihuan/.claude/skills/web-access/SKILL.md`
- `/Users/lihuan/.claude/skills/web-access/references/cdp-api.md`
