#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
METRICS_CSV = DATA_DIR / "daily_metrics.csv"
UTM_CSV = DATA_DIR / "pinterest_utm_plan.csv"
SOURCE_STATUS_CSV = DATA_DIR / "source_status.csv"
GSC_PAGE_QUERY_CSV = DATA_DIR / "gsc_page_queries.csv"
REDDIT_CSV = DATA_DIR / "reddit_engagement_log.csv"
AI_DISCOVERY_CSV = DATA_DIR / "ai_discovery_status.csv"
AI_PROMPT_CSV = DATA_DIR / "ai_prompt_panel.csv"
LINKTREE_CSV = DATA_DIR / "linktree_metrics.csv"
OUTPUT_HTML = OUTPUT_DIR / "VLOGARA-growth-dashboard.html"


@dataclass
class DailyMetric:
    date: str
    shopify_sessions: Optional[float]
    shopify_total_page_views: Optional[float]
    shopify_home_views: Optional[float]
    shopify_pdp_views: Optional[float]
    vt101_pdp_views: Optional[float]
    shopify_collection_views: Optional[float]
    shopify_blog_views: Optional[float]
    organic_search_sessions: Optional[float]
    chatgpt_sessions: Optional[float]
    gemini_sessions: Optional[float]
    perplexity_sessions: Optional[float]
    copilot_sessions: Optional[float]
    claude_sessions: Optional[float]
    other_ai_sessions: Optional[float]
    google_search_impressions: Optional[float]
    google_search_clicks: Optional[float]
    buy_on_amazon_clicks: Optional[float]
    buy_click_rate: Optional[float]
    home_amazon_clicks: Optional[float]
    pdp_amazon_clicks: Optional[float]
    collection_amazon_clicks: Optional[float]
    blog_amazon_clicks: Optional[float]
    video_starts: Optional[float]
    video_25_views: Optional[float]
    video_50_views: Optional[float]
    video_75_views: Optional[float]
    video_completes: Optional[float]
    video_to_amazon_clicks: Optional[float]
    video_play_rate: Optional[float]
    video_completion_rate: Optional[float]
    st102_pdp_users: Optional[float]
    st102_video_start_users: Optional[float]
    st102_video_50_users: Optional[float]
    st102_video_complete_users: Optional[float]
    st102_video_started_amazon_click_users: Optional[float]
    st102_video_completed_amazon_click_users: Optional[float]
    st102_video_play_rate: Optional[float]
    st102_video_completion_rate: Optional[float]
    vt101_pdp_users: Optional[float]
    vt101_video_start_users: Optional[float]
    vt101_video_50_users: Optional[float]
    vt101_video_complete_users: Optional[float]
    vt101_video_started_amazon_click_users: Optional[float]
    vt101_video_completed_amazon_click_users: Optional[float]
    vt101_video_play_rate: Optional[float]
    vt101_video_completion_rate: Optional[float]
    pinterest_impressions: Optional[float]
    pinterest_outbound_clicks: Optional[float]
    pinterest_outbound_ctr: Optional[float]
    pinterest_saves: Optional[float]
    pinterest_top_pin: str
    notes: str


def parse_number(value: str) -> Optional[float]:
    value = (value or "").strip().replace(",", "")
    if not value:
        return None
    if value.endswith("%"):
        try:
            return float(value[:-1]) / 100
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def format_number(value: Optional[float], kind: str = "number") -> str:
    if value is None:
        return "待录入"
    if kind == "percent":
        return f"{value * 100:.2f}%"
    if abs(value - round(value)) < 0.00001:
        return f"{int(value):,}"
    return f"{value:,.2f}"


def delta(current: Optional[float], previous: Optional[float], kind: str = "number") -> str:
    if current is None or previous is None:
        return "暂无对比"
    change = current - previous
    if kind == "percent":
        return f"{change * 100:+.2f} pp"
    return f"{change:+,.0f}"


def buy_rate(row: Optional[DailyMetric]) -> Optional[float]:
    if row is None:
        return None
    if row.buy_click_rate is not None:
        return row.buy_click_rate
    if row.shopify_sessions and row.buy_on_amazon_clicks is not None:
        return row.buy_on_amazon_clicks / row.shopify_sessions
    return None


def page_view_total(row: Optional[DailyMetric]) -> Optional[float]:
    if row is None:
        return None
    if row.shopify_total_page_views is not None:
        return row.shopify_total_page_views
    values = [
        row.shopify_home_views,
        row.shopify_pdp_views,
        row.shopify_collection_views,
        row.shopify_blog_views,
    ]
    known = [value for value in values if value is not None]
    if not known:
        return None
    return sum(known)


def read_metrics() -> list[DailyMetric]:
    rows: list[DailyMetric] = []
    with METRICS_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                DailyMetric(
                    date=row.get("date", "").strip(),
                    shopify_sessions=parse_number(row.get("shopify_sessions", "")),
                    shopify_total_page_views=parse_number(row.get("shopify_total_page_views", "")),
                    shopify_home_views=parse_number(row.get("shopify_home_views", "")),
                    shopify_pdp_views=parse_number(row.get("shopify_pdp_views", "")),
                    vt101_pdp_views=parse_number(row.get("vt101_pdp_views", "")),
                    shopify_collection_views=parse_number(row.get("shopify_collection_views", "")),
                    shopify_blog_views=parse_number(row.get("shopify_blog_views", "")),
                    organic_search_sessions=parse_number(row.get("organic_search_sessions", "")),
                    chatgpt_sessions=parse_number(row.get("chatgpt_sessions", "")),
                    gemini_sessions=parse_number(row.get("gemini_sessions", "")),
                    perplexity_sessions=parse_number(row.get("perplexity_sessions", "")),
                    copilot_sessions=parse_number(row.get("copilot_sessions", "")),
                    claude_sessions=parse_number(row.get("claude_sessions", "")),
                    other_ai_sessions=parse_number(row.get("other_ai_sessions", "")),
                    google_search_impressions=parse_number(row.get("google_search_impressions", "")),
                    google_search_clicks=parse_number(row.get("google_search_clicks", "")),
                    buy_on_amazon_clicks=parse_number(row.get("buy_on_amazon_clicks", "")),
                    buy_click_rate=parse_number(row.get("buy_click_rate", "")),
                    home_amazon_clicks=parse_number(row.get("home_amazon_clicks", "")),
                    pdp_amazon_clicks=parse_number(row.get("pdp_amazon_clicks", "")),
                    collection_amazon_clicks=parse_number(row.get("collection_amazon_clicks", "")),
                    blog_amazon_clicks=parse_number(row.get("blog_amazon_clicks", "")),
                    video_starts=parse_number(row.get("video_starts", "")),
                    video_25_views=parse_number(row.get("video_25_views", "")),
                    video_50_views=parse_number(row.get("video_50_views", "")),
                    video_75_views=parse_number(row.get("video_75_views", "")),
                    video_completes=parse_number(row.get("video_completes", "")),
                    video_to_amazon_clicks=parse_number(row.get("video_to_amazon_clicks", "")),
                    video_play_rate=parse_number(row.get("video_play_rate", "")),
                    video_completion_rate=parse_number(row.get("video_completion_rate", "")),
                    st102_pdp_users=parse_number(row.get("st102_pdp_users", "")),
                    st102_video_start_users=parse_number(row.get("st102_video_start_users", "")),
                    st102_video_50_users=parse_number(row.get("st102_video_50_users", "")),
                    st102_video_complete_users=parse_number(row.get("st102_video_complete_users", "")),
                    st102_video_started_amazon_click_users=parse_number(row.get("st102_video_started_amazon_click_users", "")),
                    st102_video_completed_amazon_click_users=parse_number(row.get("st102_video_completed_amazon_click_users", "")),
                    st102_video_play_rate=parse_number(row.get("st102_video_play_rate", "")),
                    st102_video_completion_rate=parse_number(row.get("st102_video_completion_rate", "")),
                    vt101_pdp_users=parse_number(row.get("vt101_pdp_users", "")),
                    vt101_video_start_users=parse_number(row.get("vt101_video_start_users", "")),
                    vt101_video_50_users=parse_number(row.get("vt101_video_50_users", "")),
                    vt101_video_complete_users=parse_number(row.get("vt101_video_complete_users", "")),
                    vt101_video_started_amazon_click_users=parse_number(row.get("vt101_video_started_amazon_click_users", "")),
                    vt101_video_completed_amazon_click_users=parse_number(row.get("vt101_video_completed_amazon_click_users", "")),
                    vt101_video_play_rate=parse_number(row.get("vt101_video_play_rate", "")),
                    vt101_video_completion_rate=parse_number(row.get("vt101_video_completion_rate", "")),
                    pinterest_impressions=parse_number(row.get("pinterest_impressions", "")),
                    pinterest_outbound_clicks=parse_number(row.get("pinterest_outbound_clicks", "")),
                    pinterest_outbound_ctr=parse_number(row.get("pinterest_outbound_ctr", "")),
                    pinterest_saves=parse_number(row.get("pinterest_saves", "")),
                    pinterest_top_pin=row.get("pinterest_top_pin", "").strip(),
                    notes=row.get("notes", "").strip(),
                )
            )
    return rows


def read_utm_rows() -> list[dict[str, str]]:
    with UTM_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_source_status_rows() -> list[dict[str, str]]:
    if not SOURCE_STATUS_CSV.exists():
        return []
    with SOURCE_STATUS_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_csv_if_exists(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_gsc_page_query_rows() -> list[dict[str, str]]:
    if not GSC_PAGE_QUERY_CSV.exists():
        return []
    with GSC_PAGE_QUERY_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def gsc_page_query_table_rows(rows: list[dict[str, str]]) -> tuple[str, str]:
    """聚合最近 14 个自然日，展示每篇博客的查询词表现。"""
    if not rows:
        return "尚无可披露的 page × query 数据", '<tr><td colspan="8">GSC 暂无可披露的博客查询词；极低量或匿名查询可能不会返回。</td></tr>'
    latest_date = max(row.get("date", "") for row in rows)
    cutoff = (datetime.strptime(latest_date, "%Y-%m-%d").date() - timedelta(days=13)).isoformat()
    aggregated: dict[tuple[str, str, str, str], dict[str, float | str]] = {}
    for row in rows:
        if row.get("date", "") < cutoff:
            continue
        key = (row.get("product", ""), row.get("blog", ""), row.get("page", ""), row.get("query", ""))
        rec = aggregated.setdefault(key, {"clicks": 0.0, "impressions": 0.0, "weighted_position": 0.0})
        impressions = parse_number(row.get("impressions", "")) or 0
        rec["clicks"] = float(rec["clicks"]) + (parse_number(row.get("clicks", "")) or 0)
        rec["impressions"] = float(rec["impressions"]) + impressions
        rec["weighted_position"] = float(rec["weighted_position"]) + (parse_number(row.get("position", "")) or 0) * impressions
    output = []
    ordered = sorted(aggregated.items(), key=lambda item: (-float(item[1]["impressions"]), item[0][0], item[0][1], item[0][3]))
    for (product, blog, page, query), rec in ordered[:50]:
        impressions = float(rec["impressions"])
        clicks = float(rec["clicks"])
        ctr = clicks / impressions if impressions else 0
        position = float(rec["weighted_position"]) / impressions if impressions else 0
        output.append(
            "<tr>"
            f"<td>{html.escape(product)}</td>"
            f"<td>{html.escape(blog)}</td>"
            f"<td><a href=\"{html.escape(page)}\">page</a></td>"
            f"<td>{html.escape(query)}</td>"
            f"<td>{format_number(impressions)}</td>"
            f"<td>{format_number(clicks)}</td>"
            f"<td>{format_number(ctr, 'percent')}</td>"
            f"<td>{position:.1f}</td>"
            "</tr>"
        )
    return f"{cutoff} 至 {latest_date}（GSC 可能省略匿名/极低量查询）", "\n".join(output)


def read_reddit_rows() -> list[dict[str, str]]:
    if not REDDIT_CSV.exists():
        return []
    with REDDIT_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def reddit_number(value: str) -> int:
    parsed = parse_number(value)
    return int(parsed) if parsed is not None else 0


def reddit_table_rows(rows: list[dict[str, str]]) -> str:
    output = []
    for row in reversed(rows):
        output.append(
            "<tr>"
            f"<td>{html.escape(row.get('date', ''))}</td>"
            f"<td>{html.escape(row.get('subreddit', ''))}</td>"
            f"<td>{html.escape(row.get('cluster', ''))}</td>"
            f"<td>{html.escape(row.get('status', ''))}</td>"
            f"<td><a href=\"{html.escape(row.get('comment_url') or row.get('thread_url', ''))}\">comment</a></td>"
            f"<td>{html.escape(row.get('karma', '') or '待确认')}</td>"
            f"<td>{html.escape(row.get('followup_replies', '') or '0')}</td>"
            f"<td>{html.escape(row.get('notes', ''))}</td>"
            "</tr>"
        )
    return "\n".join(output)


def read_pin_metric_rows() -> tuple[str, list[dict[str, str]]]:
    files = sorted(DATA_DIR.glob("pinterest_pin_metrics_*.csv"))
    if not files:
        return "", []
    latest_file = files[-1]
    with latest_file.open(newline="", encoding="utf-8") as handle:
        return latest_file.name, list(csv.DictReader(handle))


def pin_metrics_table_rows(rows: list[dict[str, str]]) -> str:
    output = []
    for row in rows:
        output.append(
            "<tr>"
            f"<td>{html.escape(row.get('asset_id', ''))}</td>"
            f"<td>{html.escape(row.get('content_group', ''))}</td>"
            f"<td>{html.escape(row.get('pin_title', ''))}</td>"
            f"<td><a href=\"{html.escape(row.get('pin_url', ''))}\">pin</a></td>"
            f"<td>{html.escape(row.get('impressions', '') or 'unavailable')}</td>"
            f"<td>{html.escape(row.get('outbound_clicks', '') or 'unavailable')}</td>"
            f"<td>{html.escape(row.get('saves', '') or '0')}</td>"
            f"<td>{html.escape(row.get('repin_count', '') or '0')}</td>"
            f"<td>{html.escape(row.get('comment_count', '') or '0')}</td>"
            f"<td>{html.escape(row.get('scrape_status', ''))}</td>"
            "</tr>"
        )
    return "\n".join(output)


def latest_complete(metrics: list[DailyMetric]) -> tuple[Optional[DailyMetric], Optional[DailyMetric]]:
    usable = [row for row in metrics if row.date]
    if not usable:
        return None, None
    latest = usable[-1]
    previous = usable[-2] if len(usable) > 1 else None
    return latest, previous


def status_label(latest: Optional[DailyMetric]) -> tuple[str, str]:
    if latest is None:
        return "待初始化", "还没有任何日期行。"
    if (
        latest.shopify_sessions is None
        and latest.google_search_impressions is None
        and latest.pinterest_impressions is None
    ):
        return "等待首日数据", "看板结构已就绪，先录入 GA4、Shopify Analytics、Search Console 与 Pinterest 的第一天数据。"
    if latest.google_search_impressions is not None and latest.google_search_clicks is not None:
        if latest.google_search_clicks == 0 and latest.google_search_impressions >= 200:
            return "优先改 Shopify 搜索点击", "Google 有展示但没有点进网站，先改首页/产品页标题、描述和搜索结果承诺。"
    if latest.shopify_sessions is not None and latest.shopify_sessions < 20:
        return "优先做 Shopify 曝光", "网站访问规模还小，先用 SEO 内容、站外入口和可索引页面拉起 sessions。"
    if latest.shopify_sessions and latest.shopify_pdp_views is not None:
        if latest.shopify_pdp_views / latest.shopify_sessions < 0.25:
            return "优先提升产品页进入率", "访问来了但进入产品页不足，先加强首页、博客和集合页到产品页的桥接。"
    if latest.shopify_sessions and latest.buy_on_amazon_clicks is not None:
        rate = buy_rate(latest)
        if rate is not None and rate < 0.03:
            return "优先改落地页承接", "站内访问有了，但 Amazon 点击率偏低。"
    if latest.pinterest_impressions and latest.pinterest_outbound_clicks is not None:
        if latest.pinterest_outbound_clicks == 0 and latest.pinterest_impressions >= 500:
            return "优先改 Pin 点击", "Pinterest 有曝光但没有带来点击，下一步先改 Pin 图和标题。"
    return "正常观察", "继续积累 3-7 天数据，再判断优化方向。"


def metric_card(title: str, value: str, change: str, note: str) -> str:
    return f"""
      <article class="metric-card">
        <p>{html.escape(title)}</p>
        <strong>{html.escape(value)}</strong>
        <span>{html.escape(change)}</span>
        <small>{html.escape(note)}</small>
      </article>
    """


def table_rows(metrics: list[DailyMetric]) -> str:
    rows = []
    for row in reversed(metrics[-14:]):
        rows.append(
            "<tr>"
            f"<td>{html.escape(row.date)}</td>"
            f"<td>{format_number(row.shopify_sessions)}</td>"
            f"<td>{format_number(page_view_total(row))}</td>"
            f"<td>{format_number(row.shopify_pdp_views)}</td>"
            f"<td>{format_number(row.buy_on_amazon_clicks)}</td>"
            f"<td>{format_number(buy_rate(row), 'percent')}</td>"
            f"<td>{format_number(row.google_search_impressions)}</td>"
            f"<td>{format_number(row.google_search_clicks)}</td>"
            f"<td>{format_number(row.chatgpt_sessions)}</td>"
            f"<td>{format_number(row.gemini_sessions)}</td>"
            f"<td>{format_number(row.perplexity_sessions)}</td>"
            f"<td>{format_number(row.copilot_sessions)}</td>"
            f"<td>{format_number(row.claude_sessions)}</td>"
            f"<td>{format_number(row.other_ai_sessions)}</td>"
            f"<td>{format_number(row.pinterest_outbound_clicks)}</td>"
            f"<td>{html.escape(row.notes)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def utm_table_rows(rows: list[dict[str, str]]) -> str:
    output = []
    for row in rows:
        output.append(
            "<tr>"
            f"<td>{html.escape(row.get('asset_id', ''))}</td>"
            f"<td><span class=\"status\">{html.escape(row.get('status', ''))}</span></td>"
            f"<td>{html.escape(row.get('pin_title', ''))}</td>"
            f"<td><a href=\"{html.escape(row.get('landing_page', ''))}\">landing</a></td>"
            f"<td><code>{html.escape(row.get('utm_url', ''))}</code></td>"
            f"<td>{html.escape(row.get('next_action', ''))}</td>"
            "</tr>"
        )
    return "\n".join(output)


def source_status_table_rows(rows: list[dict[str, str]]) -> str:
    output = []
    for row in rows:
        output.append(
            "<tr>"
            f"<td>{html.escape(row.get('source', ''))}</td>"
            f"<td><span class=\"status\">{html.escape(row.get('status', ''))}</span></td>"
            f"<td>{html.escape(row.get('latest_read', ''))}</td>"
            f"<td>{html.escape(row.get('available_data', ''))}</td>"
            f"<td>{html.escape(row.get('blocker', ''))}</td>"
            f"<td>{html.escape(row.get('next_action', ''))}</td>"
            "</tr>"
        )
    return "\n".join(output)


def latest_two_linktree_rows(
    rows: list[dict[str, str]], window: str
) -> tuple[Optional[dict[str, str]], Optional[dict[str, str]]]:
    matching = sorted(
        (row for row in rows if row.get("window", "").strip() == window),
        key=lambda row: row.get("date", ""),
    )
    if not matching:
        return None, None
    return matching[-1], matching[-2] if len(matching) > 1 else None


def linktree_snapshot_table_rows(rows: list[dict[str, str]]) -> str:
    if not rows:
        return '<tr><td colspan="8">尚未录入 Linktree 登录后数据快照。</td></tr>'
    output = []
    for row in reversed(sorted(rows, key=lambda item: (item.get("date", ""), item.get("window", "")))):
        output.append(
            "<tr>"
            f"<td>{html.escape(row.get('date', ''))}</td>"
            f"<td>{html.escape(row.get('window', ''))}</td>"
            f"<td>{format_number(parse_number(row.get('views', '')))}</td>"
            f"<td>{format_number(parse_number(row.get('clicks', '')))}</td>"
            f"<td>{format_number(parse_number(row.get('click_rate', '')), 'percent')}</td>"
            f"<td>{format_number(parse_number(row.get('amazon_button_clicks', '')))}</td>"
            f"<td>{html.escape(row.get('source', ''))}</td>"
            f"<td>{html.escape(row.get('notes', ''))}</td>"
            "</tr>"
        )
    return "\n".join(output)


def ai_discovery_table_rows(rows: list[dict[str, str]]) -> str:
    if not rows:
        return '<tr><td colspan="6">尚未运行 AI discovery check。</td></tr>'
    output = []
    for row in rows:
        output.append(
            "<tr>"
            f"<td>{html.escape(row.get('source', ''))}</td>"
            f"<td><span class=\"status\">{html.escape(row.get('status', ''))}</span></td>"
            f"<td>{html.escape(row.get('http_status', ''))}</td>"
            f"<td>{html.escape(row.get('summary', ''))}</td>"
            f"<td>{html.escape(row.get('blocker', ''))}</td>"
            f"<td>{html.escape(row.get('next_action', ''))}</td>"
            "</tr>"
        )
    return "\n".join(output)


def ai_prompt_table_rows(rows: list[dict[str, str]]) -> str:
    if not rows:
        return '<tr><td colspan="9">尚未建立 AI prompt panel。</td></tr>'
    output = []
    for row in rows:
        output.append(
            "<tr>"
            f"<td>{html.escape(row.get('prompt_id', ''))}</td>"
            f"<td>{html.escape(row.get('buyer_query', ''))}</td>"
            f"<td>{html.escape(row.get('intent', ''))}</td>"
            f"<td>{html.escape(row.get('last_checked', '') or '未跑基线')}</td>"
            f"<td>{html.escape(row.get('chatgpt_brand_mentioned', '') or '待测')}</td>"
            f"<td>{html.escape(row.get('chatgpt_cited_url', '') or '待测')}</td>"
            f"<td>{html.escape(row.get('gemini_brand_mentioned', '') or '待测')}</td>"
            f"<td>{html.escape(row.get('gemini_cited_url', '') or '待测')}</td>"
            f"<td>{html.escape(row.get('notes', ''))}</td>"
            "</tr>"
        )
    return "\n".join(output)


def render() -> str:
    metrics = read_metrics()
    utm_rows = read_utm_rows()
    source_status_rows = read_source_status_rows()
    ai_discovery_rows = read_csv_if_exists(AI_DISCOVERY_CSV)
    ai_prompt_rows = read_csv_if_exists(AI_PROMPT_CSV)
    linktree_rows = read_csv_if_exists(LINKTREE_CSV)
    gsc_page_query_rows = read_gsc_page_query_rows()
    gsc_page_query_window, gsc_page_query_html = gsc_page_query_table_rows(gsc_page_query_rows)
    reddit_rows = read_reddit_rows()
    pin_metrics_file, pin_metric_rows = read_pin_metric_rows()
    latest, previous = latest_complete(metrics)
    status, status_note = status_label(latest)
    reddit_posted = sum(1 for row in reddit_rows if row.get("status") == "posted")
    reddit_review = sum(1 for row in reddit_rows if row.get("status") != "posted")
    reddit_karma = sum(reddit_number(row.get("karma", "")) for row in reddit_rows)
    reddit_replies = sum(reddit_number(row.get("followup_replies", "")) for row in reddit_rows)
    linktree_latest, linktree_previous = latest_two_linktree_rows(linktree_rows, "last_7_days")
    linktree_lifetime, _ = latest_two_linktree_rows(linktree_rows, "lifetime")

    latest_date = latest.date if latest else "待录入"
    shopify_cards = [
        metric_card(
            "Shopify sessions",
            format_number(latest.shopify_sessions if latest else None),
            delta(latest.shopify_sessions if latest else None, previous.shopify_sessions if previous else None),
            "站点访问规模",
        ),
        metric_card(
            "Shopify page views",
            format_number(page_view_total(latest)),
            delta(page_view_total(latest), page_view_total(previous)),
            "页面被浏览次数",
        ),
        metric_card(
            "Google search impressions",
            format_number(latest.google_search_impressions if latest else None),
            delta(latest.google_search_impressions if latest else None, previous.google_search_impressions if previous else None),
            "自然搜索展示",
        ),
        metric_card(
            "Google search clicks",
            format_number(latest.google_search_clicks if latest else None),
            delta(latest.google_search_clicks if latest else None, previous.google_search_clicks if previous else None),
            "自然搜索进站",
        ),
        metric_card(
            "Buy on Amazon clicks",
            format_number(latest.buy_on_amazon_clicks if latest else None),
            delta(latest.buy_on_amazon_clicks if latest else None, previous.buy_on_amazon_clicks if previous else None),
            "站内到 Amazon 意图",
        ),
        metric_card(
            "Buy click rate",
            format_number(buy_rate(latest), "percent"),
            delta(buy_rate(latest), buy_rate(previous), "percent"),
            "Amazon 点击 / sessions",
        ),
    ]
    page_cards = [
        metric_card(
            "Home views",
            format_number(latest.shopify_home_views if latest else None),
            delta(latest.shopify_home_views if latest else None, previous.shopify_home_views if previous else None),
            "首页承接",
        ),
        metric_card(
            "Product page views",
            format_number(latest.shopify_pdp_views if latest else None),
            delta(latest.shopify_pdp_views if latest else None, previous.shopify_pdp_views if previous else None),
            "产品页承接",
        ),
        metric_card(
            "Collection views",
            format_number(latest.shopify_collection_views if latest else None),
            delta(latest.shopify_collection_views if latest else None, previous.shopify_collection_views if previous else None),
            "类目页承接",
        ),
        metric_card(
            "Blog views",
            format_number(latest.shopify_blog_views if latest else None),
            delta(latest.shopify_blog_views if latest else None, previous.shopify_blog_views if previous else None),
            "内容页承接",
        ),
    ]
    amazon_placement_cards = [
        metric_card(
            "Home Amazon clicks",
            format_number(latest.home_amazon_clicks if latest else None),
            delta(latest.home_amazon_clicks if latest else None, previous.home_amazon_clicks if previous else None),
            "首页 CTA 点击",
        ),
        metric_card(
            "PDP Amazon clicks",
            format_number(latest.pdp_amazon_clicks if latest else None),
            delta(latest.pdp_amazon_clicks if latest else None, previous.pdp_amazon_clicks if previous else None),
            "产品页 CTA 点击",
        ),
        metric_card(
            "Collection Amazon clicks",
            format_number(latest.collection_amazon_clicks if latest else None),
            delta(latest.collection_amazon_clicks if latest else None, previous.collection_amazon_clicks if previous else None),
            "集合页 CTA 点击",
        ),
        metric_card(
            "Blog Amazon clicks",
            format_number(latest.blog_amazon_clicks if latest else None),
            delta(latest.blog_amazon_clicks if latest else None, previous.blog_amazon_clicks if previous else None),
            "博客 CTA 点击",
        ),
    ]
    def linktree_value(row: Optional[dict[str, str]], field: str) -> Optional[float]:
        return parse_number(row.get(field, "")) if row else None

    linktree_cards = [
        metric_card(
            "Linktree views",
            format_number(linktree_value(linktree_latest, "views")),
            delta(linktree_value(linktree_latest, "views"), linktree_value(linktree_previous, "views")),
            "社媒主页点击进入 Linktree",
        ),
        metric_card(
            "Linktree clicks",
            format_number(linktree_value(linktree_latest, "clicks")),
            delta(linktree_value(linktree_latest, "clicks"), linktree_value(linktree_previous, "clicks")),
            "Linktree 内任意按钮点击",
        ),
        metric_card(
            "Linktree click rate",
            format_number(linktree_value(linktree_latest, "click_rate"), "percent"),
            delta(linktree_value(linktree_latest, "click_rate"), linktree_value(linktree_previous, "click_rate"), "percent"),
            "按钮点击 / Linktree views",
        ),
        metric_card(
            "Amazon button clicks",
            format_number(linktree_value(linktree_latest, "amazon_button_clicks")),
            delta(
                linktree_value(linktree_latest, "amazon_button_clicks"),
                linktree_value(linktree_previous, "amazon_button_clicks"),
            ),
            "Linktree Amazon 商品按钮点击",
        ),
    ]
    ai_referral_cards = [
        metric_card(
            "ChatGPT referral sessions",
            format_number(latest.chatgpt_sessions if latest else None),
            delta(latest.chatgpt_sessions if latest else None, previous.chatgpt_sessions if previous else None),
            "GA4 sessionSource 含 chatgpt；不等同于被引用",
        ),
        metric_card(
            "Gemini referral sessions",
            format_number(latest.gemini_sessions if latest else None),
            delta(latest.gemini_sessions if latest else None, previous.gemini_sessions if previous else None),
            "GA4 sessionSource 含 gemini；不等同于被引用",
        ),
        metric_card(
            "Perplexity referral sessions",
            format_number(latest.perplexity_sessions if latest else None),
            delta(latest.perplexity_sessions if latest else None, previous.perplexity_sessions if previous else None),
            "GA4 sessionSource 含 perplexity；不等同于被引用",
        ),
        metric_card(
            "Copilot referral sessions",
            format_number(latest.copilot_sessions if latest else None),
            delta(latest.copilot_sessions if latest else None, previous.copilot_sessions if previous else None),
            "只匹配 copilot 来源，不把普通 Bing 搜索算作 AI",
        ),
        metric_card(
            "Claude referral sessions",
            format_number(latest.claude_sessions if latest else None),
            delta(latest.claude_sessions if latest else None, previous.claude_sessions if previous else None),
            "GA4 sessionSource 含 claude.ai / anthropic；不等同于被引用",
        ),
        metric_card(
            "Other AI referral sessions",
            format_number(latest.other_ai_sessions if latest else None),
            delta(latest.other_ai_sessions if latest else None, previous.other_ai_sessions if previous else None),
            "You.com / Poe / Phind / Meta AI / Mistral / Grok / DeepSeek 等",
        ),
    ]
    def product_video_cards(prefix: str, label: str) -> list[str]:
        def value(row: Optional[DailyMetric], suffix: str) -> Optional[float]:
            return getattr(row, f"{prefix}_{suffix}") if row else None

        return [
            metric_card(
                f"{label} PDP users",
                format_number(value(latest, "pdp_users")),
                delta(value(latest, "pdp_users"), value(previous, "pdp_users")),
                "产品页唯一用户",
            ),
            metric_card(
                f"{label} video start users",
                format_number(value(latest, "video_start_users")),
                delta(value(latest, "video_start_users"), value(previous, "video_start_users")),
                "启动视频的唯一用户",
            ),
            metric_card(
                f"{label} play rate",
                format_number(value(latest, "video_play_rate"), "percent"),
                delta(value(latest, "video_play_rate"), value(previous, "video_play_rate"), "percent"),
                "启动用户 / PDP 用户",
            ),
            metric_card(
                f"{label} 50% users",
                format_number(value(latest, "video_50_users")),
                delta(value(latest, "video_50_users"), value(previous, "video_50_users")),
                "观看至少一半的唯一用户",
            ),
            metric_card(
                f"{label} complete users",
                format_number(value(latest, "video_complete_users")),
                delta(value(latest, "video_complete_users"), value(previous, "video_complete_users")),
                "完整观看的唯一用户",
            ),
            metric_card(
                f"{label} completion rate",
                format_number(value(latest, "video_completion_rate"), "percent"),
                delta(value(latest, "video_completion_rate"), value(previous, "video_completion_rate"), "percent"),
                "完播用户 / 启动用户",
            ),
            metric_card(
                f"{label} started → Amazon",
                format_number(value(latest, "video_started_amazon_click_users")),
                delta(value(latest, "video_started_amazon_click_users"), value(previous, "video_started_amazon_click_users")),
                "启动视频后点击 Amazon 的用户",
            ),
            metric_card(
                f"{label} completed → Amazon",
                format_number(value(latest, "video_completed_amazon_click_users")),
                delta(value(latest, "video_completed_amazon_click_users"), value(previous, "video_completed_amazon_click_users")),
                "完播后点击 Amazon 的用户",
            ),
        ]

    st102_video_cards = product_video_cards("st102", "ST102")
    vt101_video_cards = product_video_cards("vt101", "VT101")
    pinterest_cards = [
        metric_card(
            "Pinterest impressions",
            format_number(latest.pinterest_impressions if latest else None),
            delta(latest.pinterest_impressions if latest else None, previous.pinterest_impressions if previous else None),
            "Pinterest 曝光",
        ),
        metric_card(
            "Pinterest outbound clicks",
            format_number(latest.pinterest_outbound_clicks if latest else None),
            delta(latest.pinterest_outbound_clicks if latest else None, previous.pinterest_outbound_clicks if previous else None),
            "Pinterest 到站点击",
        ),
        metric_card(
            "Pinterest outbound CTR",
            format_number(latest.pinterest_outbound_ctr if latest else None, "percent"),
            delta(latest.pinterest_outbound_ctr if latest else None, previous.pinterest_outbound_ctr if previous else None, "percent"),
            "Pin 曝光到点击效率",
        ),
        metric_card(
            "Pinterest saves",
            format_number(latest.pinterest_saves if latest else None),
            delta(latest.pinterest_saves if latest else None, previous.pinterest_saves if previous else None),
            "未来发现信号",
        ),
    ]
    reddit_cards = [
        metric_card(
            "Public Reddit answers",
            format_number(reddit_posted),
            "优先级高于 Pinterest",
            "已保留在公开帖里的回答",
        ),
        metric_card(
            "Human follow-ups",
            format_number(reddit_replies),
            "看是否有人追问",
            "比链接点击更适合早期判断",
        ),
        metric_card(
            "Karma signal",
            format_number(reddit_karma),
            "弱信号",
            "只用于账号健康，不当作转化",
        ),
        metric_card(
            "Review queue",
            format_number(reddit_review),
            "需等待或放弃",
            "草稿/人工审核/过滤状态",
        ),
    ]

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VLOGARA Growth Dashboard</title>
  <style>
    :root {{
      --bg: #f6f3ec;
      --paper: #fffdf8;
      --ink: #1d1d1f;
      --muted: #6b6f72;
      --line: #ded8cc;
      --green: #1f5956;
      --amber: #9b6a21;
      --red: #b33a2e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      padding: 32px max(20px, 5vw) 24px;
      border-bottom: 1px solid var(--line);
      background: var(--paper);
    }}
    header p {{ margin: 0; color: var(--muted); }}
    h1 {{
      margin: 6px 0 8px;
      font-size: clamp(32px, 5vw, 56px);
      line-height: 1.05;
      letter-spacing: 0;
    }}
    main {{ width: min(1240px, calc(100% - 32px)); margin: 24px auto 56px; }}
    section {{ margin-top: 24px; }}
    h2 {{ margin: 0 0 14px; font-size: 24px; }}
    .summary {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(260px, .42fr);
      gap: 16px;
      align-items: stretch;
    }}
    .decision, .panel, .metric-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--paper);
    }}
    .decision {{ padding: 24px; }}
    .decision strong {{
      display: inline-flex;
      margin-bottom: 10px;
      padding: 4px 10px;
      border-radius: 999px;
      background: #e7f0ed;
      color: var(--green);
      font-size: 13px;
    }}
    .decision h2 {{ font-size: clamp(26px, 4vw, 42px); line-height: 1.08; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .metrics.compact {{
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }}
    .metric-card {{ padding: 18px; min-height: 140px; }}
    .metric-card p {{ margin: 0 0 10px; color: var(--muted); }}
    .metric-card strong {{ display: block; font-size: 30px; line-height: 1.1; }}
    .metric-card span {{ display: block; margin-top: 8px; color: var(--green); font-weight: 700; }}
    .metric-card small {{ display: block; margin-top: 8px; color: var(--muted); }}
    .panel {{ padding: 20px; overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 860px; }}
    th, td {{ padding: 11px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .05em; }}
    code {{ white-space: normal; word-break: break-all; color: var(--green); }}
    a {{ color: var(--green); font-weight: 700; }}
    .status {{ color: var(--green); font-weight: 700; }}
    .rules {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}
    .rule {{
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--paper);
    }}
    .rule strong {{ display: block; margin-bottom: 8px; }}
    .rule p {{ margin: 0; color: var(--muted); }}
    footer {{ margin-top: 28px; color: var(--muted); }}
    @media (max-width: 900px) {{
      .summary, .metrics, .rules {{ grid-template-columns: 1fr; }}
      .metrics.compact {{ grid-template-columns: 1fr; }}
      main {{ width: min(100% - 24px, 720px); }}
      table {{ min-width: 760px; }}
    }}
  </style>
</head>
<body>
  <header>
    <p>VLOGARA daily growth cockpit</p>
    <h1>Shopify Exposure -> Product Views -> Amazon Clicks</h1>
    <p>Latest date: {html.escape(latest_date)} · Shopify demand first, Reddit before Pinterest, Amazon Attribution when approved.</p>
  </header>
  <main>
    <section class="summary">
      <div class="decision">
        <strong>{html.escape(status)}</strong>
        <h2>{html.escape(status_note)}</h2>
        <p>这个看板优先判断 Shopify 自身漏斗：有没有搜索展示和访问、访问有没有进入产品页、产品页/博客/首页有没有产生 Amazon 点击。站外先看 Reddit 回答保留和追问，再看 Pinterest 曝光。</p>
      </div>
      <div class="panel">
        <h2>Today Focus</h2>
        <p><strong>One action only:</strong> 每天只选一个 Shopify 动作优化，第二天用 sessions、PDP views、Amazon clicks 和 buy click rate 验证。Amazon Attribution 下来后再补订单归因。</p>
      </div>
    </section>

    <section>
      <h2>Shopify Growth Funnel</h2>
      <div class="metrics">
        {''.join(shopify_cards)}
      </div>
    </section>

    <section class="panel">
      <h2>Data Source Status</h2>
      <table>
        <thead>
          <tr>
            <th>Source</th><th>Status</th><th>Latest read</th><th>Available data</th><th>Blocker</th><th>Next action</th>
          </tr>
        </thead>
        <tbody>
          {source_status_table_rows(source_status_rows)}
        </tbody>
      </table>
    </section>

    <section class="panel">
      <h2>AI Discovery Health</h2>
      <p>检查 AI 搜索可读取的公开入口、机器可读购买口径与产品事实。PASS 只代表可访问且口径一致，不代表 ChatGPT 或 Gemini 已经引用。</p>
      <table>
        <thead>
          <tr><th>Source</th><th>Status</th><th>HTTP</th><th>Summary</th><th>Blocker</th><th>Next action</th></tr>
        </thead>
        <tbody>{ai_discovery_table_rows(ai_discovery_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>AI Referral Traffic</h2>
      <div class="metrics">{''.join(ai_referral_cards)}</div>
    </section>

    <section class="panel">
      <h2>AI Visibility Prompt Panel</h2>
      <p>每月固定同一组英文 buyer queries，分别记录品牌是否出现、引用 URL 与事实准确性。当前留空代表未跑基线，不能解读为“未被收录”。</p>
      <table>
        <thead>
          <tr><th>ID</th><th>Buyer query</th><th>Intent</th><th>Last checked</th><th>ChatGPT mention</th><th>ChatGPT source</th><th>Gemini mention</th><th>Gemini source</th><th>Notes</th></tr>
        </thead>
        <tbody>{ai_prompt_table_rows(ai_prompt_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Shopify Page Demand</h2>
      <div class="metrics compact">
        {''.join(page_cards)}
      </div>
    </section>

    <section class="panel">
      <h2>Google SEO — Blog Page × Query</h2>
      <p>{html.escape(gsc_page_query_window)}。按 14 天聚合，Position 为展示量加权平均；样本很小时只观察，不据此立即改标题或正文。</p>
      <table>
        <thead>
          <tr>
            <th>Product</th><th>Blog</th><th>Page</th><th>Query</th><th>Impressions</th><th>Clicks</th><th>CTR</th><th>Position</th>
          </tr>
        </thead>
        <tbody>
          {gsc_page_query_html}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Linktree Bio Funnel</h2>
      <p>这是社媒曝光之后、Amazon 跳转之前的独立漏斗。当前卡片使用最近 7 天快照；累计基线为 {format_number(linktree_value(linktree_lifetime, 'views'))} views / {format_number(linktree_value(linktree_lifetime, 'clicks'))} clicks。现阶段通过已登录后台手工快照更新，不冒充 API 自动采集。</p>
      <div class="metrics compact">
        {''.join(linktree_cards)}
      </div>
    </section>

    <section class="panel">
      <h2>Linktree Snapshot Log</h2>
      <table>
        <thead>
          <tr><th>Date</th><th>Window</th><th>Views</th><th>Clicks</th><th>Click rate</th><th>Amazon clicks</th><th>Source</th><th>Notes</th></tr>
        </thead>
        <tbody>{linktree_snapshot_table_rows(linktree_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Amazon Click Placement</h2>
      <div class="metrics compact">
        {''.join(amazon_placement_cards)}
      </div>
    </section>

    <section>
      <h2>ST102 Video Engagement — clean baseline from 2026-07-13</h2>
      <div class="metrics">
        {''.join(st102_video_cards)}
      </div>
    </section>

    <section>
      <h2>VT101 Sponsored Video Engagement — clean baseline from 2026-07-13</h2>
      <div class="metrics">
        {''.join(vt101_video_cards)}
      </div>
    </section>

    <section>
      <h2>Reddit Source Layer</h2>
      <div class="metrics compact">
        {''.join(reddit_cards)}
      </div>
    </section>

    <section class="panel">
      <h2>Reddit Engagement Log</h2>
      <p>Reddit is tracked before Pinterest for this workflow. Early KPI is answer survival and useful follow-up replies, not link clicks.</p>
      <table>
        <thead>
          <tr>
            <th>Date</th><th>Subreddit</th><th>Cluster</th><th>Status</th><th>Comment</th><th>Karma</th><th>Follow-ups</th><th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {reddit_table_rows(reddit_rows)}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Shopify Optimization Rules</h2>
      <div class="rules">
        <article class="rule"><strong>搜索展示低</strong><p>补 SEO 内容页、产品 FAQ、集合页 copy，并提交 sitemap 到 Google Search Console。</p></article>
        <article class="rule"><strong>展示有但点击低</strong><p>改首页、产品页和博客的 SEO title/meta，让搜索结果里直接承诺 tripod 场景和痛点。</p></article>
        <article class="rule"><strong>访问有但 PDP 低</strong><p>加强首页首屏、博客首段、集合页卡片到产品页的入口，减少用户自己找产品。</p></article>
        <article class="rule"><strong>PDP 有但 Amazon 点击低</strong><p>优化首屏 CTA、价格/利益点、信任信息、对比信息，并测试 sticky Amazon 按钮。</p></article>
      </div>
    </section>

    <section>
      <h2>Pinterest Source Layer</h2>
      <div class="metrics compact">
        {''.join(pinterest_cards)}
      </div>
    </section>

    <section class="panel">
      <h2>Pinterest Pin Performance</h2>
      <p>Latest file: <code>{html.escape(pin_metrics_file or 'none')}</code>. Impressions and outbound clicks require Pinterest business analytics; current table records public Pin-page saves, repins and comments only.</p>
      <table>
        <thead>
          <tr>
            <th>Asset</th><th>Group</th><th>Pin title</th><th>Pin</th><th>Impressions</th><th>Outbound clicks</th><th>Saves</th><th>Repins</th><th>Comments</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          {pin_metrics_table_rows(pin_metric_rows)}
        </tbody>
      </table>
    </section>

    <section class="panel">
      <h2>Daily Log</h2>
      <table>
        <thead>
          <tr>
            <th>Date</th><th>Sessions</th><th>Page views</th><th>PDP views</th><th>Amazon clicks</th><th>Buy click rate</th><th>Google impressions</th><th>Google clicks</th><th>ChatGPT</th><th>Gemini</th><th>Perplexity</th><th>Copilot</th><th>Claude</th><th>Other AI</th><th>Pin outbound clicks</th><th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {table_rows(metrics)}
        </tbody>
      </table>
    </section>

    <section class="panel">
      <h2>Pinterest UTM Link Plan</h2>
      <table>
        <thead>
          <tr>
            <th>Asset</th><th>Status</th><th>Pin title</th><th>Landing</th><th>UTM URL</th><th>Next action</th>
          </tr>
        </thead>
        <tbody>
          {utm_table_rows(utm_rows)}
        </tbody>
      </table>
    </section>

    <footer>
      <p>Generated from <code>daily_metrics.csv</code>, <code>linktree_metrics.csv</code>, <code>gsc_page_queries.csv</code>, <code>ai_discovery_status.csv</code>, and <code>ai_prompt_panel.csv</code>. Rebuild with <code>python3 codex/growth-monitor/scripts/render_dashboard.py</code>.</p>
    </footer>
  </main>
</body>
</html>
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(render(), encoding="utf-8")
    print(f"Dashboard written: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
