#!/usr/bin/env zsh
set -euo pipefail

cd "$(dirname "$0")"

if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

python3 src/monitor.py "$@"
