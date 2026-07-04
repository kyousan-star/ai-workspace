#!/bin/zsh

LOG_DIR="$HOME/Library/Logs"
mkdir -p "$LOG_DIR"
exec >> "$LOG_DIR/com.lihuan.alexa-scraper.log" 2>> "$LOG_DIR/com.lihuan.alexa-scraper.error.log"

SCRIPT_DIR="/Users/lihuan/Documents/跨境业务/美国亚马逊业务运营/us 20 asin listing每周监控/20asin rufus问题统计"
PYTHON=/Library/Frameworks/Python.framework/Versions/3.14/bin/python3

cd "$SCRIPT_DIR"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') 开始：Alexa 综合情报（统一脚本）==="
$PYTHON -u alexa_intel_unified.py
UNIFIED_EXIT=$?
echo "=== $(date '+%Y-%m-%d %H:%M:%S') Alexa 综合情报结束（exit $UNIFIED_EXIT）==="
