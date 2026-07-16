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

# Claude-only: 仅部署到 ~/.claude/skills，不影响 Codex
install_claude_skill() {
  local name="$1"
  local source_dir="$ROOT/skills/$name"

  if [[ ! -f "$source_dir/SKILL.md" ]]; then
    echo "Missing skill: $source_dir/SKILL.md" >&2
    exit 1
  fi

  mkdir -p "$HOME/.claude/skills/$name"
  rsync -a --delete "$source_dir/" "$HOME/.claude/skills/$name/"

  echo "Installed (claude-only) $name"
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

install_skill blue-ocean-finder
install_skill zach-product-research
install_skill amazon-category-analysis
install_skill amazon-listing-v2
install_skill amazon-review-voc-analysis-v3
install_skill amazon-ad-optimizer
# amazon-product-dev 已 deprecated（2026-07-02），迁至 archive/skills/，能力并入 zach-product-research + sops/amazon-decision-thresholds.md
install_skill reddit-voc-analysis-v2
install_skill tiktok-voc-analysis
install_skill listing-rufus-cosmo-audit
install_skill aba-keyword-monitor
install_skill competitor-traffic-battle
install_skill amazon-image-planner-v2
install_skill amazon-image-planner-v3
install_skill product-asset-extractor
install_skill asset-curator
install_skill batch-asset-generator
install_skill amazon-pricing-validator
install_codex_skill web-access-codex
# 2026-07-02 自 ~/.codex/skills 收编的孤儿（原只存在于安装目录，无仓库备份）
install_codex_skill report-design
install_codex_skill lihuan-goal-meta-skill
install_codex_skill lihuan-chat-history
install_codex_skill st102-video-factory
install_claude_skill invest
install_claude_skill teach
install_claude_skill web-access
