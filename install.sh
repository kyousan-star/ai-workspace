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

# Codex-only: 仅部署到 ~/.codex/skills，不影响 Claude
install_codex_skill() {
  local name="$1"
  local source_dir="$ROOT/skills/$name"

  if [[ ! -f "$source_dir/SKILL.md" ]]; then
    echo "Missing skill: $source_dir/SKILL.md" >&2
    exit 1
  fi

  mkdir -p "$HOME/.codex/skills/$name"
  rsync -a --delete "$source_dir/" "$HOME/.codex/skills/$name/"

  echo "Installed (codex-only) $name"
}

install_skill amazon-category-analysis
install_skill amazon-listing-v2
install_skill amazon-review-voc-analysis-v2
install_skill amazon-review-voc-analysis-v3
install_skill amazon-ads-analysis
install_skill amazon-ad-optimizer
install_skill amazon-product-dev
install_skill reddit-voc-analysis-v2
install_skill tiktok-voc-analysis-v2
install_skill tiktok-voc-analysis-v3
install_skill listing-rufus-cosmo-audit
install_skill aba-keyword-monitor
install_skill competitor-traffic-battle
install_codex_skill web-access-codex
