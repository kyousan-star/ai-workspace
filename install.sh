#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install_skill() {
  local name="$1"
  local source_dir="$ROOT/skills/$name"

  if [[ ! -f "$source_dir/SKILL.md" ]]; then
    echo "Missing skill: $source_dir/SKILL.md" >&2
    exit 1
  fi

  mkdir -p "$HOME/.codex/skills/$name"
  mkdir -p "$HOME/.claude/skills/$name"

  rsync -a --delete "$source_dir/" "$HOME/.codex/skills/$name/"
  rsync -a --delete "$source_dir/" "$HOME/.claude/skills/$name/"

  echo "Installed $name"
}

install_skill amazon-category-analysis
install_skill amazon-review-voc-analysis-v2
