#!/usr/bin/env python3
"""Vlogara 站点漏斗采集器 — 挂在卖家脉搏晨报里的每日 GA4 + GSC API 拉数。

- GA4 Data API（property 541399575）：sessions、页面浏览分布、organic sessions、
  buy_on_amazon_click 事件及 VT101 sponsored demo 视频互动
- Search Console API（https://vlogara.com/）：搜索展示/点击（GSC 数据有 ~2 天延迟）
- 近 3 天窗口逐日 upsert 进 data/daily_metrics.csv（只写 API 来源字段，
  不碰 pinterest_* 和 notes 列），然后重渲染 dashboard
- 产出 data/site_metrics_feishu.txt 并入卖家脉搏飞书消息

凭证：~/.claude/scripts/google_growth_token.json（grace 授权的 refresh_token，
OAuth 客户端在 GCP 项目 monitor-489703）。纯 stdlib，无第三方依赖。
"""

import csv
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # growth-monitor/
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "daily_metrics.csv"
FEISHU_TXT = DATA_DIR / "site_metrics_feishu.txt"
TOKEN_PATH = Path.home() / ".claude/scripts/google_growth_token.json"
RENDER = BASE_DIR / "scripts/render_dashboard.py"

GA4_PROPERTY = "541399575"
GSC_SITE = "https://vlogara.com/"
TODAY = os.environ.get("BRIEF_DATE", date.today().strftime("%Y-%m-%d"))
LOOKBACK_DAYS = 5  # GSC 滞后2-3天，窗口≥5天才能稳定接到最新可用日（3天时会扑空报"窗口内无数据"）

PAGE_BUCKETS = [  # pagePath 前缀 → CSV 列
    ("/products/", "shopify_pdp_views"),
    ("/collections/", "shopify_collection_views"),
    ("/blogs/", "shopify_blog_views"),
]
VT101_PATH = "/products/vlogara-3-in-1-vlogging-kit"
VIDEO_EVENT_COLUMNS = {
    "video_start": "video_starts",
    "video_25": "video_25_views",
    "video_50": "video_50_views",
    "video_75": "video_75_views",
    "video_complete": "video_completes",
    "video_to_amazon_click": "video_to_amazon_clicks",
}
# 2026-07-10 预览隔离上线前做过一次完整埋点链路测试；按事件各扣 1，避免污染正式数据。
VIDEO_EVENT_TEST_ADJUSTMENTS = {
    "2026-07-10": {event_name: 1 for event_name in VIDEO_EVENT_COLUMNS},
}
PLACEMENT_BUCKETS = [  # placement 参数关键词 → CSV 列
    ("home", "home_amazon_clicks"),
    ("pdp", "pdp_amazon_clicks"),
    ("product", "pdp_amazon_clicks"),
    ("collection", "collection_amazon_clicks"),
    ("blog", "blog_amazon_clicks"),
]


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] ga4_gsc: {msg}")


def access_token():
    tok = json.loads(TOKEN_PATH.read_text())
    data = urllib.parse.urlencode({
        "client_id": tok["client_id"], "client_secret": tok["client_secret"],
        "refresh_token": tok["refresh_token"], "grant_type": "refresh_token",
    }).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=30) as r:
        return json.loads(r.read())["access_token"]


def api(at, url, body=None):
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {at}", "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def ga4_report(at, body):
    return api(at, f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY}:runReport", body)


def date_range():
    start = (datetime.strptime(TODAY, "%Y-%m-%d") - timedelta(days=LOOKBACK_DAYS - 1)).strftime("%Y-%m-%d")
    return {"startDate": start, "endDate": TODAY}


def collect_ga4(at):
    """返回 {date: {col: value}}"""
    days = {}

    def day(d):  # GA4 date 维度是 YYYYMMDD
        iso = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        return days.setdefault(iso, {})

    # 1) sessions / pageviews / organic
    r = ga4_report(at, {
        "dateRanges": [date_range()],
        "dimensions": [{"name": "date"}, {"name": "sessionDefaultChannelGroup"}],
        "metrics": [{"name": "sessions"}, {"name": "screenPageViews"}],
    })
    for row in r.get("rows", []):
        d, chan = row["dimensionValues"][0]["value"], row["dimensionValues"][1]["value"]
        sess, pv = int(row["metricValues"][0]["value"]), int(row["metricValues"][1]["value"])
        rec = day(d)
        rec["shopify_sessions"] = rec.get("shopify_sessions", 0) + sess
        rec["shopify_total_page_views"] = rec.get("shopify_total_page_views", 0) + pv
        if chan == "Organic Search":
            rec["organic_search_sessions"] = rec.get("organic_search_sessions", 0) + sess

    # 2) 页面类型分布
    r = ga4_report(at, {
        "dateRanges": [date_range()],
        "dimensions": [{"name": "date"}, {"name": "pagePath"}],
        "metrics": [{"name": "screenPageViews"}],
        "limit": "1000",
    })
    for row in r.get("rows", []):
        d, path = row["dimensionValues"][0]["value"], row["dimensionValues"][1]["value"]
        pv = int(row["metricValues"][0]["value"])
        rec = day(d)
        if path == VT101_PATH or path.startswith(VT101_PATH + "?"):
            rec["vt101_pdp_views"] = rec.get("vt101_pdp_views", 0) + pv
        if path == "/" or path.startswith("/?"):
            rec["shopify_home_views"] = rec.get("shopify_home_views", 0) + pv
        else:
            for prefix, col in PAGE_BUCKETS:
                if path.startswith(prefix):
                    rec[col] = rec.get(col, 0) + pv
                    break

    # 3) buy_on_amazon_click 总数 + placement 分布
    r = ga4_report(at, {
        "dateRanges": [date_range()],
        "dimensions": [{"name": "date"}, {"name": "customEvent:placement"}],
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": {"filter": {"fieldName": "eventName",
                                       "stringFilter": {"value": "buy_on_amazon_click"}}},
    })
    for row in r.get("rows", []):
        d, placement = row["dimensionValues"][0]["value"], row["dimensionValues"][1]["value"].lower()
        n = int(row["metricValues"][0]["value"])
        rec = day(d)
        rec["buy_on_amazon_clicks"] = rec.get("buy_on_amazon_clicks", 0) + n
        for kw, col in PLACEMENT_BUCKETS:
            if kw in placement:
                rec[col] = rec.get(col, 0) + n
                break

    # 4) VT101 sponsored demo 播放、进度、完播、观看后 Amazon 点击
    r = ga4_report(at, {
        "dateRanges": [date_range()],
        "dimensions": [{"name": "date"}, {"name": "eventName"}],
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": {"filter": {"fieldName": "eventName",
                                       "inListFilter": {"values": list(VIDEO_EVENT_COLUMNS)}}},
    })
    for row in r.get("rows", []):
        d, event_name = row["dimensionValues"][0]["value"], row["dimensionValues"][1]["value"]
        col = VIDEO_EVENT_COLUMNS.get(event_name)
        if col:
            rec = day(d)
            iso_date = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            adjustment = VIDEO_EVENT_TEST_ADJUSTMENTS.get(iso_date, {}).get(event_name, 0)
            count = max(0, int(row["metricValues"][0]["value"]) - adjustment)
            rec[col] = rec.get(col, 0) + count

    for rec in days.values():
        s, b = rec.get("shopify_sessions", 0), rec.get("buy_on_amazon_clicks", 0)
        if s:
            rec["buy_click_rate"] = f"{b / s:.4f}"
        starts = rec.get("video_starts", 0)
        vt101_views = rec.get("vt101_pdp_views", 0)
        if vt101_views:
            rec["video_play_rate"] = f"{starts / vt101_views:.4f}"
        if starts:
            rec["video_completion_rate"] = f"{rec.get('video_completes', 0) / starts:.4f}"
    return days


def collect_gsc(at):
    """返回 {date: {impressions, clicks}}；GSC 数据通常滞后 ~2 天"""
    body = {**date_range(), "dimensions": ["date"]}
    url = f"https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(GSC_SITE, safe='')}/searchAnalytics/query"
    r = api(at, url, body)
    out = {}
    for row in r.get("rows", []):
        out[row["keys"][0]] = {
            "google_search_impressions": int(row["impressions"]),
            "google_search_clicks": int(row["clicks"]),
        }
    return out


def collect_gsc_queries(at):
    """窗口内 Top query（按展示降序），回答"展示来自哪里"，省去人工翻 GSC 后台"""
    body = {**date_range(), "dimensions": ["query"], "rowLimit": 10}
    url = f"https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(GSC_SITE, safe='')}/searchAnalytics/query"
    r = api(at, url, body)
    return [{"query": row["keys"][0],
             "impressions": int(row["impressions"]),
             "clicks": int(row["clicks"])}
            for row in sorted(r.get("rows", []),
                              key=lambda x: x["impressions"], reverse=True)]


def upsert_csv(ga4_days, gsc_days):
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    fieldnames = rows[0].keys() if rows else None
    by_date = {r["date"]: r for r in rows}
    all_dates = sorted(set(ga4_days) | set(gsc_days))
    touched = []
    for d in all_dates:
        rec = by_date.get(d)
        if rec is None:
            rec = {k: "" for k in fieldnames}
            rec["date"] = d
            rec["notes"] = "GA4/GSC API 自动回填"
            rows.append(rec)
            by_date[d] = rec
        merged = {**ga4_days.get(d, {}), **gsc_days.get(d, {})}
        for k, v in merged.items():
            if k in rec:
                rec[k] = str(v)
        touched.append(d)
    rows.sort(key=lambda r: r["date"])
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return touched


def build_feishu(ga4_days, gsc_days, gsc_queries=None):
    """一行心跳；有漏斗信号才展开"""
    yesterday = (datetime.strptime(TODAY, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    g = ga4_days.get(yesterday) or ga4_days.get(TODAY) or {}
    label = yesterday if yesterday in ga4_days else TODAY
    sess = g.get("shopify_sessions", 0)
    buys = g.get("buy_on_amazon_clicks", 0)
    # GSC 取窗口内最新有数的一天
    gsc_latest = max(gsc_days) if gsc_days else None
    lines = []
    head = f"站点漏斗（{label}）：{sess} sessions"
    if gsc_latest:
        gi = gsc_days[gsc_latest]
        head += f"；GSC {gi['google_search_impressions']}展示/{gi['google_search_clicks']}点击（{gsc_latest}）"
    else:
        head += "；GSC 窗口内无数据"
    lines.append(head)
    if gsc_queries:
        top = " / ".join(f"{q['query']}（{q['impressions']}展示"
                         + (f"/{q['clicks']}点击" if q["clicks"] else "")
                         + "）" for q in gsc_queries[:3])
        lines.append(f"  └ Top query：{top}")
    if buys:
        lines.append(f"  🎯 buy_on_amazon_click ×{buys}！分布：" + ", ".join(
            f"{col.replace('_amazon_clicks','')} {g[col]}" for _, col in PLACEMENT_BUCKETS
            if g.get(col)) )
    starts = g.get("video_starts", 0)
    if starts:
        lines.append(
            "  🎥 VT101 demo："
            f"start {starts} / 50% {g.get('video_50_views', 0)} / "
            f"complete {g.get('video_completes', 0)} / "
            f"after-video Amazon {g.get('video_to_amazon_clicks', 0)}"
        )
    FEISHU_TXT.write_text(f"DATE:{TODAY}\n" + "\n".join(lines) + "\n", encoding="utf-8")


def main():
    try:
        at = access_token()
        ga4_days = collect_ga4(at)
        gsc_days = collect_gsc(at)
    except urllib.error.HTTPError as e:
        msg = f"API 失败 HTTP {e.code}: {e.read().decode()[:150]}"
        FEISHU_TXT.write_text(f"DATE:{TODAY}\n站点漏斗采集失败：{msg}\n", encoding="utf-8")
        log(msg)
        return
    except Exception as e:
        FEISHU_TXT.write_text(f"DATE:{TODAY}\n站点漏斗采集异常：{type(e).__name__}: {e}\n", encoding="utf-8")
        log(f"异常: {e}")
        return

    try:
        gsc_queries = collect_gsc_queries(at)
    except Exception as e:
        gsc_queries = []
        log(f"GSC query 明细拉取失败（不影响心跳）: {e}")

    touched = upsert_csv(ga4_days, gsc_days)
    build_feishu(ga4_days, gsc_days, gsc_queries)

    if RENDER.exists():
        r = subprocess.run([sys.executable, str(RENDER)], capture_output=True, text=True, timeout=120)
        log(f"dashboard 渲染 exit={r.returncode}")

    log(f"完成：回填 {touched}，GA4 天数 {len(ga4_days)}，GSC 天数 {len(gsc_days)}")


if __name__ == "__main__":
    main()
