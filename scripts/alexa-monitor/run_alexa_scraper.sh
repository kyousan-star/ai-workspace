#!/bin/zsh

LOG_DIR="$HOME/Library/Logs"
mkdir -p "$LOG_DIR"
exec >> "$LOG_DIR/com.lihuan.alexa-scraper.log" 2>> "$LOG_DIR/com.lihuan.alexa-scraper.error.log"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON=/Library/Frameworks/Python.framework/Versions/3.14/bin/python3

cd "$SCRIPT_DIR"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') 开始：Alexa 综合情报（统一脚本）==="
$PYTHON -u alexa_intel_unified.py
UNIFIED_EXIT=$?
echo "=== $(date '+%Y-%m-%d %H:%M:%S') Alexa 综合情报结束（exit $UNIFIED_EXIT）==="

echo "=== $(date '+%Y-%m-%d %H:%M:%S') 开始：Sorftime Top60 关键词权重落盘 ==="
SORFTIME_KEYWORD_SKIP_FEISHU=1 $PYTHON -u sorftime_keyword_intel.py
KEYWORD_EXIT=$?
echo "=== $(date '+%Y-%m-%d %H:%M:%S') Sorftime Top60 关键词权重结束（exit $KEYWORD_EXIT）==="

if [[ "$UNIFIED_EXIT" -ne 0 || "$KEYWORD_EXIT" -ne 0 ]]; then
  exit 1
fi
