#!/usr/bin/env python3
"""Vlogara 站点漏斗采集器 — 挂在卖家脉搏晨报里的每日 GA4 + GSC API 拉数。

- GA4 Data API（property 541399575）：sessions、页面浏览分布、organic sessions、
  AI answer-engine referral sessions、buy_on_amazon_click 及产品视频互动
- Search Console API（https://vlogara.com/）：搜索展示/点击（GSC 数据有 ~2 天延迟）
- 近 5 天窗口逐日 upsert 进 data/daily_metrics.csv（只写 API 来源字段，
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
GSC_PAGE_QUERY_CSV = DATA_DIR / "gsc_page_queries.csv"
AI_REFERRAL_SOURCE_CSV = DATA_DIR / "ai_referral_sources.csv"
FEISHU_TXT = DATA_DIR / "site_metrics_feishu.txt"
TOKEN_PATH = Path.home() / ".claude/scripts/google_growth_token.json"
RENDER = BASE_DIR / "scripts/render_dashboard.py"
AI_DISCOVERY = BASE_DIR / "scripts/ai_discovery_check.py"

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
ST102_PATH = "/products/vlogara-71-cell-phone-tripod"
BLOG_PRODUCTS = {
    "/blogs/news/how-to-choose-a-cell-phone-tripod-for-recording-videos": ("ST102", "Blog 1"),
    "/blogs/news/best-phone-tripod-height-for-vlogging-yoga-cooking-and-streaming": ("ST102", "Blog 2"),
    "/blogs/news/5-moments-that-wrecked-my-first-50-phone-vlogs": ("ST102", "Blog 3"),
    "/blogs/news/best-phone-tripod-for-cooking-videos": ("ST102", "Blog 4"),
    "/blogs/news/best-phone-tripod-for-yoga-workout-videos": ("ST102", "Blog 5"),
    "/blogs/news/71-inch-phone-tripod-vs-60-inch-tripod": ("ST102", "Blog 6"),
    "/blogs/news/phone-tripod-with-bluetooth-remote-for-iphone": ("ST102", "Blog 7"),
    "/blogs/news/how-to-film-overhead-videos-with-a-phone-tripod": ("ST102", "Blog 8"),
    "/blogs/news/phone-vlogging-kit-checklist-light-mic-tripod-mounts": ("VT101", "Blog 9"),
}
VIDEO_PRODUCTS = {
    ST102_PATH: {"prefix": "st102", "label": "ST102"},
    VT101_PATH: {"prefix": "vt101", "label": "VT101"},
}
VIDEO_EVENTS = {
    "video_start": "video_start",
    "video_50": "video_50",
    "video_complete": "video_complete",
    "video_started_to_amazon_click": "video_started_amazon_click",
    "video_completed_to_amazon_click": "video_completed_amazon_click",
}
VIDEO_METRICS_CLEAN_START = "2026-07-13"
LEGACY_VIDEO_MIXED_START = "2026-07-10"
LEGACY_VIDEO_MIXED_END = "2026-07-12"
VIDEO_METRIC_COLUMNS = []
AI_REFERRAL_BUCKETS = [
    ("chatgpt_sessions", "ChatGPT", ("chatgpt", "chat.openai", "openai.com")),
    ("gemini_sessions", "Gemini", ("gemini", "bard.google")),
    ("perplexity_sessions", "Perplexity", ("perplexity",)),
    ("copilot_sessions", "Copilot", ("copilot", "microsoftcopilot")),
    ("claude_sessions", "Claude", ("claude.ai", "anthropic")),
    (
        "other_ai_sessions",
        "Other AI",
        (
            "you.com",
            "poe.com",
            "phind",
            "meta.ai",
            "mistral",
            "grok.com",
            "deepseek",
            "duck.ai",
            "andisearch",
            "komo.ai",
        ),
    ),
]
AI_REFERRAL_COLUMNS = [bucket[0] for bucket in AI_REFERRAL_BUCKETS]
AI_REFERRAL_LABELS = {bucket[0]: bucket[1] for bucket in AI_REFERRAL_BUCKETS}
for product in VIDEO_PRODUCTS.values():
    prefix = product["prefix"]
    VIDEO_METRIC_COLUMNS.extend([
        f"{prefix}_pdp_users",
        f"{prefix}_video_start_users",
        f"{prefix}_video_start_events",
        f"{prefix}_video_50_users",
        f"{prefix}_video_50_events",
        f"{prefix}_video_complete_users",
        f"{prefix}_video_complete_events",
        f"{prefix}_video_started_amazon_click_users",
        f"{prefix}_video_started_amazon_click_events",
        f"{prefix}_video_completed_amazon_click_users",
        f"{prefix}_video_completed_amazon_click_events",
        f"{prefix}_video_play_rate",
        f"{prefix}_video_completion_rate",
    ])
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


def describe_http_error(error):
    """Turn OAuth expiry into an actionable Feishu message; keep other API details."""
    body = error.read().decode(errors="replace")[:500]
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {}
    if payload.get("error") == "invalid_grant":
        return "Google OAuth 授权已失效或被撤销，需要重新授权（invalid_grant）"
    return f"API 失败 HTTP {error.code}: {body[:150]}"


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


def iso_date_from_ga4(value):
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def classify_ai_source(source):
    """Return one mutually exclusive AI referral bucket for a GA4 sessionSource."""
    normalized = (source or "").strip().lower()
    for column, _label, patterns in AI_REFERRAL_BUCKETS:
        if any(pattern in normalized for pattern in patterns):
            return column
    return None


def collect_ga4(at):
    """返回 ({date: {col: value}}, raw_ai_referral_rows)。"""
    days = {}
    ai_referral_rows = []

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

    # 1b) AI answer-engine referrals. These are observed visits, not proof of citation visibility.
    r = ga4_report(at, {
        "dateRanges": [date_range()],
        "dimensions": [{"name": "date"}, {"name": "sessionSource"}],
        "metrics": [{"name": "sessions"}],
        "limit": "1000",
    })
    for row in r.get("rows", []):
        d = row["dimensionValues"][0]["value"]
        source = row["dimensionValues"][1]["value"].strip().lower()
        sessions = int(row["metricValues"][0]["value"])
        rec = day(d)
        bucket = classify_ai_source(source)
        if bucket:
            rec[bucket] = rec.get(bucket, 0) + sessions
            ai_referral_rows.append({
                "date": iso_date_from_ga4(d),
                "source": source,
                "bucket": bucket,
                "sessions": sessions,
            })

    # 2) 页面类型分布
    r = ga4_report(at, {
        "dateRanges": [date_range()],
        "dimensions": [{"name": "date"}, {"name": "pagePath"}],
        "metrics": [{"name": "screenPageViews"}, {"name": "totalUsers"}],
        "limit": "1000",
    })
    for row in r.get("rows", []):
        d, path = row["dimensionValues"][0]["value"], row["dimensionValues"][1]["value"]
        pv = int(row["metricValues"][0]["value"])
        users = int(row["metricValues"][1]["value"])
        rec = day(d)
        product = VIDEO_PRODUCTS.get(path.split("?", 1)[0])
        if product and iso_date_from_ga4(d) >= VIDEO_METRICS_CLEAN_START:
            rec[f"{product['prefix']}_pdp_users"] = users
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

    # 4) 按 PDP 拆分两款产品的视频唯一用户漏斗；eventCount 仅保留作诊断。
    r = ga4_report(at, {
        "dateRanges": [date_range()],
        "dimensions": [{"name": "date"}, {"name": "eventName"}, {"name": "pagePath"}],
        "metrics": [{"name": "eventCount"}, {"name": "totalUsers"}],
        "dimensionFilter": {"filter": {"fieldName": "eventName",
                                       "inListFilter": {"values": list(VIDEO_EVENTS)}}},
        "limit": "1000",
    })
    for row in r.get("rows", []):
        d, event_name, path = [value["value"] for value in row["dimensionValues"]]
        iso_date = iso_date_from_ga4(d)
        product = VIDEO_PRODUCTS.get(path.split("?", 1)[0])
        event_key = VIDEO_EVENTS.get(event_name)
        if not product or not event_key or iso_date < VIDEO_METRICS_CLEAN_START:
            continue
        rec = day(d)
        prefix = product["prefix"]
        rec[f"{prefix}_{event_key}_events"] = int(row["metricValues"][0]["value"])
        rec[f"{prefix}_{event_key}_users"] = int(row["metricValues"][1]["value"])

    for rec in days.values():
        s, b = rec.get("shopify_sessions", 0), rec.get("buy_on_amazon_clicks", 0)
        if s:
            rec["buy_click_rate"] = f"{b / s:.4f}"
        for product in VIDEO_PRODUCTS.values():
            prefix = product["prefix"]
            starts = rec.get(f"{prefix}_video_start_users", 0)
            pdp_users = rec.get(f"{prefix}_pdp_users", 0)
            if pdp_users:
                rec[f"{prefix}_video_play_rate"] = f"{starts / pdp_users:.4f}"
            if starts:
                completes = rec.get(f"{prefix}_video_complete_users", 0)
                rec[f"{prefix}_video_completion_rate"] = f"{completes / starts:.4f}"
    return days, ai_referral_rows


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


def collect_gsc_page_queries(at):
    """逐日采集 9 篇博客的 page × query；GSC 可能省略匿名/极低量查询。"""
    body = {**date_range(), "dimensions": ["date", "page", "query"], "rowLimit": 25000}
    url = f"https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(GSC_SITE, safe='')}/searchAnalytics/query"
    r = api(at, url, body)
    out = []
    for row in r.get("rows", []):
        day, page, query = row["keys"]
        parsed = urllib.parse.urlparse(page)
        path = parsed.path.rstrip("/")
        product_blog = BLOG_PRODUCTS.get(path)
        if not product_blog:
            continue
        product, blog = product_blog
        out.append({
            "date": day,
            "product": product,
            "blog": blog,
            "page": f"https://vlogara.com{path}",
            "query": query,
            "clicks": int(row["clicks"]),
            "impressions": int(row["impressions"]),
            "ctr": f"{float(row.get('ctr', 0)):.6f}",
            "position": f"{float(row.get('position', 0)):.2f}",
        })
    return out


def upsert_gsc_page_queries(new_rows):
    """按 date + page + query 保存历史，避免每日 5 天窗口产生重复。"""
    fieldnames = ["date", "product", "blog", "page", "query", "clicks", "impressions", "ctr", "position"]
    existing = []
    if GSC_PAGE_QUERY_CSV.exists():
        with GSC_PAGE_QUERY_CSV.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    by_key = {(row.get("date", ""), row.get("page", ""), row.get("query", "")): row for row in existing}
    for row in new_rows:
        by_key[(row["date"], row["page"], row["query"])] = row
    rows = sorted(by_key.values(), key=lambda row: (row["date"], row["product"], row["blog"], row["query"]))
    with GSC_PAGE_QUERY_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(new_rows), len(rows)


def upsert_ai_referral_sources(new_rows):
    """按 date + source 保存可识别 AI referral 原始来源，避免丢失取证字段。"""
    fieldnames = ["date", "source", "bucket", "sessions"]
    existing = []
    if AI_REFERRAL_SOURCE_CSV.exists():
        with AI_REFERRAL_SOURCE_CSV.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    by_key = {(row.get("date", ""), row.get("source", "")): row for row in existing}
    for row in new_rows:
        by_key[(row["date"], row["source"])] = {
            **row,
            "sessions": str(row["sessions"]),
        }
    rows = sorted(by_key.values(), key=lambda row: (row["date"], row["bucket"], row["source"]))
    with AI_REFERRAL_SOURCE_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(new_rows), len(rows)


def upsert_csv(ga4_days, gsc_days):
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    fieldnames = list(rows[0].keys()) if rows else ["date", *VIDEO_METRIC_COLUMNS, "notes"]
    notes_index = fieldnames.index("notes") if "notes" in fieldnames else len(fieldnames)
    for column in [*AI_REFERRAL_COLUMNS, *VIDEO_METRIC_COLUMNS]:
        if column not in fieldnames:
            fieldnames.insert(notes_index, column)
            notes_index += 1

    legacy_note = "video_metrics_legacy_mixed_test_traffic; 不用于视频转化判断"
    for row in rows:
        if LEGACY_VIDEO_MIXED_START <= row.get("date", "") <= LEGACY_VIDEO_MIXED_END:
            notes = row.get("notes", "").strip()
            if legacy_note not in notes:
                row["notes"] = f"{notes}; {legacy_note}".strip("; ")
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
            if k in fieldnames:
                rec[k] = str(v)
        if LEGACY_VIDEO_MIXED_START <= d <= LEGACY_VIDEO_MIXED_END:
            notes = rec.get("notes", "").strip()
            if legacy_note not in notes:
                rec["notes"] = f"{notes}; {legacy_note}".strip("; ")
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
    head = f"站点漏斗（{label}）：{sess} sessions（可能含未标记的内部/测试流量）"
    if gsc_latest:
        gi = gsc_days[gsc_latest]
        head += f"；GSC {gi['google_search_impressions']}展示/{gi['google_search_clicks']}点击（{gsc_latest}）"
    else:
        head += "；GSC 窗口内无数据"
    lines.append(head)
    if gsc_queries:
        query_impressions = sum(q["impressions"] for q in gsc_queries)
        query_note = "样本极小，仅观察，不作为内容方向依据" if query_impressions < 20 else "仅作查询趋势观察"
        top = " / ".join(f"{q['query']}（{q['impressions']}展示"
                         + (f"/{q['clicks']}点击" if q["clicks"] else "")
                         + "）" for q in gsc_queries[:3])
        lines.append(f"  └ 近5天 Top query（窗口合计 {query_impressions} 展示；{query_note}）：{top}")
    if buys:
        lines.append(f"  🎯 buy_on_amazon_click ×{buys}！分布：" + ", ".join(
            f"{col.replace('_amazon_clicks','')} {g[col]}" for _, col in PLACEMENT_BUCKETS
            if g.get(col)) )
    ai_referrals = [
        f"{AI_REFERRAL_LABELS[column]} {g[column]}"
        for column in AI_REFERRAL_COLUMNS
        if g.get(column)
    ]
    if ai_referrals:
        lines.append(f"  🤖 AI referral sessions：{', '.join(ai_referrals)}（进站信号，不等同于被引用）")
    for product in VIDEO_PRODUCTS.values():
        prefix, label = product["prefix"], product["label"]
        starts = g.get(f"{prefix}_video_start_users", 0)
        if starts:
            lines.append(
                f"  🎥 {label} demo（用户）："
                f"start {starts} / 50% {g.get(f'{prefix}_video_50_users', 0)} / "
                f"complete {g.get(f'{prefix}_video_complete_users', 0)} / "
                f"started→Amazon {g.get(f'{prefix}_video_started_amazon_click_users', 0)} / "
                f"completed→Amazon {g.get(f'{prefix}_video_completed_amazon_click_users', 0)}"
            )
    FEISHU_TXT.write_text(f"DATE:{TODAY}\n" + "\n".join(lines) + "\n", encoding="utf-8")


def main():
    if AI_DISCOVERY.exists():
        try:
            result = subprocess.run([sys.executable, str(AI_DISCOVERY)], capture_output=True, text=True, timeout=120)
            log(f"AI discovery check exit={result.returncode}")
        except Exception as exc:
            log(f"AI discovery check 异常（不影响 GA4/GSC）: {exc}")

    try:
        at = access_token()
        ga4_days, ai_referral_rows = collect_ga4(at)
        gsc_days = collect_gsc(at)
    except urllib.error.HTTPError as e:
        msg = describe_http_error(e)
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

    try:
        gsc_page_queries = collect_gsc_page_queries(at)
        page_query_new, page_query_total = upsert_gsc_page_queries(gsc_page_queries)
    except Exception as e:
        page_query_new, page_query_total = 0, 0
        log(f"GSC page × query 明细拉取失败（不影响心跳）: {e}")

    try:
        ai_source_new, ai_source_total = upsert_ai_referral_sources(ai_referral_rows)
    except Exception as e:
        ai_source_new, ai_source_total = 0, 0
        log(f"AI referral 原始来源写入失败（不影响心跳）: {e}")

    touched = upsert_csv(ga4_days, gsc_days)
    build_feishu(ga4_days, gsc_days, gsc_queries)

    if RENDER.exists():
        r = subprocess.run([sys.executable, str(RENDER)], capture_output=True, text=True, timeout=120)
        log(f"dashboard 渲染 exit={r.returncode}")

    log(
        f"完成：回填 {touched}，GA4 天数 {len(ga4_days)}，GSC 天数 {len(gsc_days)}，"
        f"博客 page×query 本轮 {page_query_new} 行/历史 {page_query_total} 行，"
        f"AI referral source 本轮 {ai_source_new} 行/历史 {ai_source_total} 行"
    )


if __name__ == "__main__":
    main()
