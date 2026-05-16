#!/usr/bin/env bash
set -euo pipefail

export CDP_PROXY_PORT="${CDP_PROXY_PORT:-3457}"
export CODEX_WEB_ACCESS_TMP="${CODEX_WEB_ACCESS_TMP:-/private/tmp/codex-web-access}"

UPSTREAM="/Users/lihuan/.claude/skills/web-access/scripts/check-deps.mjs"

mkdir -p "$CODEX_WEB_ACCESS_TMP"

if [[ ! -f "$UPSTREAM" ]]; then
  echo "upstream web-access script not found: $UPSTREAM" >&2
  exit 1
fi

node "$UPSTREAM"
