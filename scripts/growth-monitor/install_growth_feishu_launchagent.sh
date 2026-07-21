#!/bin/zsh
set -euo pipefail

ROOT="/Users/lihuan/Documents/跨境业务/美国亚马逊业务运营/Vlogara logo&站外&shopify/codex/growth-monitor"
LABEL="com.lihuan.vlogara-growth-daily-feishu"
SRC_PLIST="$ROOT/launchd/$LABEL.plist"
DEST_DIR="$HOME/Library/LaunchAgents"
DEST_PLIST="$DEST_DIR/$LABEL.plist"

mkdir -p "$DEST_DIR"
mkdir -p "$ROOT/output/launchd"

plutil -lint "$SRC_PLIST" >/dev/null
cp "$SRC_PLIST" "$DEST_PLIST"

launchctl bootout "gui/$(id -u)" "$DEST_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$DEST_PLIST"
launchctl enable "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true

echo "INSTALL_OK label=$LABEL plist=$DEST_PLIST"
