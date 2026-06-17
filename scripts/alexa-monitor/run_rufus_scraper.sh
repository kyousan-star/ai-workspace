#!/bin/zsh

LOG_DIR="$HOME/Library/Logs"
mkdir -p "$LOG_DIR"
exec >> "$LOG_DIR/com.lihuan.rufus-scraper.log" 2>> "$LOG_DIR/com.lihuan.rufus-scraper.error.log"

SCRIPT_DIR="/Users/lihuan/Documents/跨境业务/美国亚马逊业务运营/us 20 asin listing每周监控/20asin rufus问题统计"
PYTHON=/Library/Frameworks/Python.framework/Versions/3.14/bin/python3

cd "$SCRIPT_DIR"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') 开始：Alexa 问题抓取 ==="
$PYTHON -u rufus_scraper.py
RUFUS_EXIT=$?
echo "=== $(date '+%Y-%m-%d %H:%M:%S') Alexa 抓取结束（exit $RUFUS_EXIT）==="

echo ""
echo "=== $(date '+%Y-%m-%d %H:%M:%S') 开始：Sorftime 关键词情报 ==="
$PYTHON -u sorftime_keyword_intel.py
SORFTIME_EXIT=$?
echo "=== $(date '+%Y-%m-%d %H:%M:%S') Sorftime 情报结束（exit $SORFTIME_EXIT）==="
