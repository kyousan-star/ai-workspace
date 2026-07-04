from __future__ import annotations

import base64
import datetime as dt
import email.utils
import hashlib
import hmac
import html
from html.parser import HTMLParser
import http.cookiejar
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "monitor.db"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self._drop_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript", "svg"}:
            self._drop_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "svg"} and self._drop_depth:
            self._drop_depth -= 1

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title += text
        elif not self._drop_depth:
            self.parts.append(text)


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        create table if not exists articles (
          url text primary key,
          account_id text,
          account_name text,
          title text,
          published_at text,
          score integer,
          summary text,
          created_at text not null
        )
        """
    )
    return conn


def request_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 WeChatPublicMonitor/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def request_text_with_opener(opener, url: str, timeout: int = 20, referer: str = "") -> tuple[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 WeChatPublicMonitor/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace"), resp.geturl()


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    drop = {"scene", "clicktime", "enterid", "ascene", "devicetype", "version", "nettype", "abtest_cookie", "lang"}
    kept = [(k, v) for k, v in query if k not in drop]
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(kept), ""))


def load_manual_links(accounts_by_id: dict[str, dict]) -> list[dict]:
    path = DATA_DIR / "manual_links.txt"
    if not path.exists():
        return []
    articles = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        account_id = ""
        url = line
        if "\t" in line:
            account_id, url = line.split("\t", 1)
        account = accounts_by_id.get(account_id, {})
        articles.append(
            {
                "url": normalize_url(url),
                "account_id": account_id,
                "account_name": account.get("name", account_id or "未知来源"),
                "title": "",
                "published_at": "",
                "source": "manual",
            }
        )
    return articles


def parse_rss_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.isoformat()
    except Exception:
        return value


def load_feed_articles(accounts: list[dict]) -> list[dict]:
    feeds = load_json(CONFIG_DIR / "feeds.json", {})
    articles = []
    for account in accounts:
        account_id = account["wechat_id"]
        for feed_url in account_feed_urls(account, feeds):
            try:
                xml = request_text(feed_url)
                root = ET.fromstring(xml)
            except Exception as exc:
                print(f"feed failed: {account_id} {feed_url}: {exc}", file=sys.stderr)
                continue
            for item in root.findall(".//item"):
                link = (item.findtext("link") or "").strip()
                if not link:
                    continue
                articles.append(
                    {
                        "url": normalize_url(link),
                        "account_id": account_id,
                        "account_name": account.get("name", account_id),
                        "title": html.unescape((item.findtext("title") or "").strip()),
                        "published_at": parse_rss_date(item.findtext("pubDate") or ""),
                        "source": "feed",
                    }
                )
    return articles


def parse_wechat_datetime(value: str) -> str:
    value = value.strip().strip('"').strip("'")
    if not value:
        return ""
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = dt.datetime.strptime(value, fmt)
            return parsed.isoformat()
        except ValueError:
            pass
    if value.isdigit():
        try:
            ts = int(value)
            if ts > 10_000_000_000:
                ts = ts // 1000
            return dt.datetime.fromtimestamp(ts).isoformat()
        except ValueError:
            return ""
    return ""


def extract_js_value(page: str, names: list[str]) -> str:
    for name in names:
        patterns = [
            rf"var\s+{re.escape(name)}\s*=\s*htmlDecode\(['\"]([^'\"]+)['\"]\)",
            rf"var\s+{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]",
            rf"(?<![-\w]){re.escape(name)}(?![-\w])\s*:\s*['\"]([^'\"]+)['\"]",
        ]
        for pattern in patterns:
            match = re.search(pattern, page)
            if match:
                return html.unescape(match.group(1)).strip()
    return ""


def extract_article(url: str) -> tuple[str, str, str, str]:
    page = request_text(url)
    parser = TextExtractor()
    parser.feed(page)
    text = re.sub(r"\s+", " ", " ".join(parser.parts))
    text = html.unescape(text)
    title = extract_js_value(page, ["msg_title"]) or html.unescape(parser.title.strip())
    title = re.sub(r"\s+", " ", title).replace("微信公众平台", "").strip(" -_")
    published_at = parse_wechat_datetime(
        extract_js_value(page, ["publish_time", "createTime", "ct", "ori_create_time"])
    )
    account_name = extract_js_value(page, ["nickname", "nick_name"])
    return title, text[:12000], published_at, account_name


def within_recent_window(published_at: str, hours: int) -> bool:
    if not published_at:
        return True
    try:
        parsed = dt.datetime.fromisoformat(published_at)
    except ValueError:
        return True
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    cutoff = dt.datetime.now() - dt.timedelta(hours=hours)
    return parsed >= cutoff


def bing_rss_search(query: str) -> list[dict]:
    url = "https://www.bing.com/search?" + urllib.parse.urlencode(
        {"q": query, "format": "rss", "mkt": "zh-CN"}
    )
    xml = request_text(url)
    root = ET.fromstring(xml)
    results = []
    for item in root.findall(".//item"):
        link = html.unescape((item.findtext("link") or "").strip())
        title = html.unescape((item.findtext("title") or "").strip())
        published_at = parse_rss_date(item.findtext("pubDate") or "")
        if "mp.weixin.qq.com" not in link:
            continue
        results.append({"url": normalize_url(link), "title": title, "published_at": published_at})
    return results


def extract_concatenated_js_url(page: str) -> str:
    parts = re.findall(r"url\s*\+=\s*'([^']*)'", page)
    if not parts:
        return ""
    return "".join(parts).replace("@", "").replace("&amp;", "&")


def resolve_public_link(opener, url: str) -> str:
    page, final_url = request_text_with_opener(opener, url, referer="https://weixin.sogou.com/")
    if "mp.weixin.qq.com" in final_url:
        return final_url
    js_url = extract_concatenated_js_url(page)
    if "mp.weixin.qq.com" in js_url:
        return js_url
    return final_url


def strip_tags(value: str) -> str:
    value = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(re.sub(r"\s+", " ", value).strip())


def normalize_account_name(value: str) -> str:
    return re.sub(r"\s+", "", value or "").casefold()


def target_account_names(account: dict) -> list[str]:
    names = [account.get("name", "")]
    names.extend(account.get("aliases", []))
    return [name for name in names if name]


def is_target_account_name(value: str, account: dict) -> bool:
    normalized = normalize_account_name(value)
    return any(normalized == normalize_account_name(name) for name in target_account_names(account))


def find_account_by_name(value: str, accounts: list[dict]) -> dict:
    for account in accounts:
        if is_target_account_name(value, account):
            return account
    return {}


def account_feed_urls(account: dict, feeds_by_id: dict) -> list[str]:
    urls = []
    urls.extend(account.get("feeds", []))
    urls.extend(feeds_by_id.get(account.get("wechat_id", ""), []))
    return [url for url in dict.fromkeys(urls) if url]


def sogou_weixin_page(opener, query: str, use_day_filter: bool) -> str:
    params = {"type": "2", "query": query, "ie": "utf8"}
    if use_day_filter:
        params["tsn"] = "1"
    url = "https://weixin.sogou.com/weixin?" + urllib.parse.urlencode(params)
    page, _ = request_text_with_opener(opener, url, referer="https://weixin.sogou.com/")
    return page


def sogou_weixin_search(account: dict, recent_hours: int, max_results: int) -> list[dict]:
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    results = []
    seen_urls = set()
    for query in target_account_names(account):
        page = sogou_weixin_page(opener, query, use_day_filter=recent_hours <= 24)
        blocks = re.findall(r"<li\b[^>]*?id=\"sogou_vr_11002601_box_\d+\".*?</li>", page, flags=re.S)
        if not blocks and recent_hours <= 24:
            page = sogou_weixin_page(opener, query, use_day_filter=False)
            blocks = re.findall(r"<li\b[^>]*?id=\"sogou_vr_11002601_box_\d+\".*?</li>", page, flags=re.S)
        for block in blocks:
            title_match = re.search(r"<h3>\s*<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>\s*</h3>", block, flags=re.S)
            if not title_match:
                continue
            raw_href, raw_title = title_match.groups()
            title = strip_tags(raw_title)
            account_match = re.search(r"<span class=\"all-time-y2\">(.*?)</span>", block, flags=re.S)
            result_account = strip_tags(account_match.group(1)) if account_match else ""
            if result_account and not is_target_account_name(result_account, account):
                print(
                    f"skip non-target account: target={account['name']} result={result_account} title={title}",
                    file=sys.stderr,
                )
                continue
            timestamp_match = re.search(r"timeConvert\('(\d+)'\)", block)
            published_at = parse_wechat_datetime(timestamp_match.group(1)) if timestamp_match else ""
            if published_at and not within_recent_window(published_at, recent_hours):
                continue
            href = html.unescape(raw_href)
            if href.startswith("/"):
                href = "https://weixin.sogou.com" + href
            try:
                final_url = resolve_public_link(opener, href)
            except Exception as exc:
                print(f"sogou link resolve failed: {account['name']}: {exc}", file=sys.stderr)
                continue
            if "mp.weixin.qq.com" not in final_url:
                continue
            normalized_url = normalize_url(final_url)
            if normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)
            results.append(
                {
                    "url": normalized_url,
                    "title": title,
                    "published_at": published_at,
                    "account_name": result_account or account["name"],
                }
            )
            if len(results) >= max_results:
                break
        if len(results) >= max_results:
            break
    return results


def load_public_search_articles(accounts: list[dict], settings: dict) -> list[dict]:
    search_cfg = settings.get("public_search", {})
    if not search_cfg.get("enabled", False):
        return []
    max_results = int(search_cfg.get("max_results_per_account", 5))
    delay = float(search_cfg.get("request_delay_seconds", 1.0))
    recent_hours = int(search_cfg.get("recent_hours", 24))
    engine = search_cfg.get("engine", "sogou_weixin")
    articles = []
    seen = set()
    for account in accounts:
        try:
            if engine == "sogou_weixin":
                results = sogou_weixin_search(account, recent_hours, max_results)
            else:
                terms = [account["name"], account["wechat_id"]]
                query = f'site:mp.weixin.qq.com/s ({terms[0]} OR {terms[1]})'
                results = bing_rss_search(query)
        except Exception as exc:
            print(f"public search failed: {account['name']}: {exc}", file=sys.stderr)
            continue
        for result in results[:max_results]:
            url = result["url"]
            if url in seen:
                continue
            seen.add(url)
            articles.append(
                {
                    "url": url,
                    "account_id": account["wechat_id"],
                    "account_name": result.get("account_name") or account["name"],
                    "title": result.get("title", ""),
                    "published_at": result.get("published_at", ""),
                    "source": "public_search",
                }
            )
        time.sleep(delay)
    return articles


def keyword_score(title: str, text: str, settings: dict) -> tuple[int, list[str]]:
    haystack = f"{title}\n{text[:3000]}".lower()
    matched = []
    score = 0
    for area in settings["interest_areas"]:
        hits = [kw for kw in area["keywords"] if kw.lower() in haystack]
        if hits:
            score += int(area["weight"]) * min(3, len(hits))
            matched.append(area["name"])
    for kw in settings.get("low_value_keywords", []):
        if kw.lower() in haystack:
            score -= 2
    return score, sorted(set(matched))


def heuristic_summary(title: str, text: str, matched_areas: list[str]) -> str:
    clean = re.sub(r"\s+", " ", text)
    sentences = re.split(r"(?<=[。！？.!?])", clean)
    picked = [s.strip() for s in sentences if len(s.strip()) >= 18][:4]
    if not picked:
        picked = [clean[:180]]
    lines = [f"关键词命中：{', '.join(matched_areas) if matched_areas else '无'}"]
    lines.append(f"一句话：{title}")
    for idx, sentence in enumerate(picked[:4], 1):
        lines.append(f"{idx}. {sentence[:180]}")
    return "\n".join(lines)


def sort_datetime_value(value: str) -> float:
    if not value:
        return 0.0
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    return parsed.timestamp()


def looks_like_real_account_name(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    if lowered.startswith("data-") or "nickname" in lowered:
        return False
    return 1 < len(value) <= 40


def feishu_sign(secret: str, timestamp: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(string_to_sign, b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def send_feishu(text: str, dry_run: bool) -> None:
    webhook = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    if dry_run or not webhook:
        print(text)
        return
    payload = {"msg_type": "text", "content": {"text": text}}
    secret = os.getenv("FEISHU_BOT_SECRET", "").strip()
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = feishu_sign(secret, timestamp)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        print(body)


def source_label(source: str) -> str:
    labels = {
        "feed": "Feed",
        "manual": "手动补源",
        "public_search": "搜索兜底",
    }
    return labels.get(source, source or "未知")


def source_priority(source: str) -> int:
    return {"feed": 3, "manual": 2, "public_search": 1}.get(source, 0)


def article_identity(row: dict) -> tuple[str, str, str]:
    title = re.sub(r"[\s,，。.!！?？:：;；\-—_《》\"'“”‘’|]+", "", row.get("title", "")).casefold()
    return (row.get("account_id", ""), title, row.get("published_at", ""))


def build_coverage_note(accounts: list[dict], rows: list[dict]) -> str:
    feeds_by_id = load_json(CONFIG_DIR / "feeds.json", {})
    feed_names = [a["name"] for a in accounts if account_feed_urls(a, feeds_by_id)]
    fallback_names = [a["name"] for a in accounts if not account_feed_urls(a, feeds_by_id)]
    sources = sorted({source_label(row.get("source", "")) for row in rows})
    lines = [
        "覆盖状态：",
        f"- Feed 已配置：{len(feed_names)}/{len(accounts)}"
        + (f"（{', '.join(feed_names[:8])}{' 等' if len(feed_names) > 8 else ''}）" if feed_names else ""),
        f"- 搜索兜底账号：{len(fallback_names)}/{len(accounts)}",
    ]
    if rows:
        lines.append(f"- 本次命中文章来源：{', '.join(sources)}")
    return "\n".join(lines)


def compact_datetime(value: str) -> str:
    if not value:
        return "未知"
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%m-%d %H:%M")


def truncate_text(value: str, limit: int) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)] + "…"


def build_digest(rows: list[dict], settings: dict, accounts: list[dict]) -> str:
    today = dt.datetime.now().strftime("%Y-%m-%d")
    recent_hours = int(settings.get("public_search", {}).get("recent_hours", 24))
    feeds_by_id = load_json(CONFIG_DIR / "feeds.json", {})
    feed_count = sum(1 for account in accounts if account_feed_urls(account, feeds_by_id))
    sources = "、".join(sorted({source_label(row.get("source", "")) for row in rows})) if rows else "无"
    if not rows:
        return (
            f"微信公众号监控日报 {today}\n"
            f"过去 {recent_hours} 小时：0 篇\n"
            f"覆盖：Feed {feed_count}/{len(accounts)}，搜索兜底 {len(accounts) - feed_count}/{len(accounts)}"
        )
    max_items = int(settings.get("max_feishu_articles", settings.get("max_articles_per_day", 20)))
    lines = [
        f"微信公众号监控日报 {today}",
        f"过去 {recent_hours} 小时：{len(rows)} 篇",
        f"覆盖：Feed {feed_count}/{len(accounts)}，搜索兜底 {len(accounts) - feed_count}/{len(accounts)}；来源：{sources}",
        "",
    ]
    for idx, row in enumerate(rows[: settings["max_articles_per_day"]], 1):
        if idx > max_items:
            break
        title = truncate_text(row["title"], 42)
        lines.append(f"{idx}. [{row['account_name']}] {compact_datetime(row['published_at'])}｜{title}")
    if len(rows) > max_items:
        lines.append(f"... 另 {len(rows) - max_items} 篇已入库")
    lines.append("")
    lines.append("完整摘要已入库，需展开时再查。")
    return "\n".join(lines).strip()


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    accounts = load_json(CONFIG_DIR / "accounts.json", [])
    settings = load_json(CONFIG_DIR / "settings.json", {})
    if "--recent-hours" in sys.argv:
        try:
            idx = sys.argv.index("--recent-hours")
            recent_hours = int(sys.argv[idx + 1])
        except (ValueError, IndexError):
            raise SystemExit("usage: run_monitor.sh [--dry-run] [--recent-hours HOURS]")
        settings.setdefault("public_search", {})["recent_hours"] = recent_hours
    accounts_by_id = {a["wechat_id"]: a for a in accounts}
    candidates = (
        load_feed_articles(accounts)
        + load_public_search_articles(accounts, settings)
        + load_manual_links(accounts_by_id)
    )
    conn = db()
    new_rows = []
    for candidate in candidates:
        url = candidate["url"]
        if conn.execute("select 1 from articles where url = ?", (url,)).fetchone():
            continue
        try:
            title, text, page_published_at, page_account_name = extract_article(url)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            print(f"article failed: {url}: {exc}", file=sys.stderr)
            continue
        title = candidate.get("title") or title or "未识别标题"
        published_at = page_published_at or candidate.get("published_at", "")
        recent_hours = int(settings.get("public_search", {}).get("recent_hours", 24))
        if candidate.get("source") in {"feed", "manual", "public_search"} and (not published_at or title == "未识别标题"):
            print(f"article missing required metadata: source={candidate.get('source')} title={title} published_at={published_at} url={url}", file=sys.stderr)
            continue
        if candidate.get("source") in {"feed", "manual", "public_search"} and not within_recent_window(published_at, recent_hours):
            continue
        expected_account = accounts_by_id.get(candidate.get("account_id", ""))
        if not expected_account and looks_like_real_account_name(page_account_name):
            expected_account = find_account_by_name(page_account_name, accounts)
            if expected_account:
                candidate["account_id"] = expected_account["wechat_id"]
                candidate["account_name"] = expected_account["name"]
        if not expected_account:
            print(f"article account unknown: actual={page_account_name or 'unknown'} title={title}", file=sys.stderr)
            continue
        if (
            candidate.get("source") in {"feed", "manual", "public_search"}
            and looks_like_real_account_name(page_account_name)
            and not is_target_account_name(page_account_name, expected_account)
        ):
            print(
                f"article account mismatch: target={expected_account['name']} actual={page_account_name} title={title}",
                file=sys.stderr,
            )
            continue
        if looks_like_real_account_name(page_account_name):
            candidate["account_name"] = page_account_name
        score, areas = keyword_score(title, text, settings)
        include_all = bool(settings.get("public_search", {}).get("include_all_recent_articles", False))
        if score <= 0 and not include_all:
            continue
        summary = heuristic_summary(title, text, areas)
        row = {
            "url": url,
            "account_id": candidate.get("account_id", ""),
            "account_name": candidate.get("account_name", "未知来源"),
            "title": title,
            "published_at": published_at,
            "score": score,
            "summary": summary,
            "source": candidate.get("source", ""),
        }
        new_rows.append(row)
    new_rows.sort(key=lambda item: (sort_datetime_value(item["published_at"]), item["score"]), reverse=True)
    deduped = {}
    for row in new_rows:
        key = article_identity(row)
        existing = deduped.get(key)
        if not existing or source_priority(row.get("source", "")) > source_priority(existing.get("source", "")):
            deduped[key] = row
    new_rows = sorted(
        deduped.values(),
        key=lambda item: (sort_datetime_value(item["published_at"]), item["score"]),
        reverse=True,
    )
    if not dry_run:
        for row in new_rows:
            conn.execute(
                "insert or ignore into articles values (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["url"],
                    row["account_id"],
                    row["account_name"],
                    row["title"],
                    row["published_at"],
                    row["score"],
                    row["summary"],
                    dt.datetime.now(dt.timezone.utc).isoformat(),
                ),
            )
        conn.commit()
    else:
        conn.rollback()
    send_feishu(build_digest(new_rows, settings, accounts), dry_run=dry_run)


if __name__ == "__main__":
    main()
