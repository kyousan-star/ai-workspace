"""
alexa_intel_unified.py
统一 Alexa 问题情报：关键词 Top5 + 固定竞品 + 自有 ASIN
分四阶段构建，每阶段独立可测。
"""

import json
import math
import os
import re
import shutil
import subprocess
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import requests
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from playwright.sync_api import sync_playwright

# ─── 配置 ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
ASINS_FILE      = SCRIPT_DIR / "asins.txt"        # 固定竞品 ASIN
OWN_ASINS_FILE  = SCRIPT_DIR / "own_asins.txt"    # 自有 ASIN
ARCHIVE_FILE    = SCRIPT_DIR / "alexa_intel_archive.json"
RAW_DIR         = SCRIPT_DIR / "raw"
REPORT_DIR      = SCRIPT_DIR / "reports"

RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d")
RUN_DATETIME  = datetime.now().strftime("%Y-%m-%d %H:%M")

SORFTIME_KEY      = "a2ngm2ruztlecldntdfnrhhretlqzz09"
SORFTIME_ENDPOINT = f"https://mcp.sorftime.com/?key={SORFTIME_KEY}"
KEYWORD_TOP_N     = 5   # 每个关键词取前 N 个自然位 ASIN

KEYWORDS = [
    {"keyword": "tripod for iphone",       "group": "ST102"},
    {"keyword": "selfie stick for iphone", "group": "ST102"},
    {"keyword": "vlogging kit for iphone", "group": "VK101"},
    {"keyword": "vlogging kit",            "group": "VK101"},
]

FEISHU_WEBHOOK = os.getenv(
    "ALEXA_FEISHU_WEBHOOK_URL",
    "https://open.feishu.cn/open-apis/bot/v2/hook/20e06d51-6ac0-4e78-8229-0dd3abd581b3",
)

# Playwright / 抓取配置
COOKIES_FILE        = SCRIPT_DIR / "amazon_cookies.json"
HEADLESS            = os.getenv("ALEXA_HEADLESS", "1").lower() not in {"0", "false", "no"}
DELAY_BETWEEN_ASINS = int(os.getenv("ALEXA_DELAY_BETWEEN_ASINS", "10"))
MAX_RETRIES         = int(os.getenv("ALEXA_MAX_RETRIES", "3"))
NAVIGATION_TIMEOUT  = int(os.getenv("ALEXA_NAVIGATION_TIMEOUT_MS", "60000"))
DOM_READY_TIMEOUT   = int(os.getenv("ALEXA_DOM_READY_TIMEOUT_MS", "15000"))
ALEXA_HINT_TIMEOUT  = int(os.getenv("ALEXA_HINT_TIMEOUT_MS", "20000"))
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}
MIN_SUCCESSFUL_ASINS   = int(os.getenv("ALEXA_MIN_SUCCESSFUL_ASINS", "15"))

# 输出路径
GITHUB_REPO       = Path("/Users/lihuan/Documents/学习提升/AI/claude/桌面 claude code/Scheduled/美日金融市场daily brief")
GITHUB_PAGES_BASE = "https://kyousan-star.github.io/-daily-brief"
GDRIVE_FOLDER_ID  = os.getenv("ALEXA_GDRIVE_FOLDER_ID", "1YCHa8JCIZjv_8FRm_QVDp2FIFUocEwtJ")
GDRIVE_TOKEN      = Path(os.getenv("ALEXA_GDRIVE_TOKEN",
                          "/Users/lihuan/.claude/scripts/gdrive_token.json")).expanduser()
OUTPUT_EXCEL = RAW_DIR   / f"alexa_intel_{RUN_TIMESTAMP}.xlsx"
OUTPUT_HTML  = REPORT_DIR / f"alexa_intel_{RUN_TIMESTAMP}.html"


# ─── Step 1: Sorftime 关键词查询 ───────────────────────────────────────────────

def _call_sorftime(name: str, arguments: dict, timeout: float = 45.0):
    payload = {
        "jsonrpc": "2.0", "id": "1",
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    try:
        resp = requests.post(SORFTIME_ENDPOINT, json=payload, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        print(f"    ⚠ Sorftime {name} 请求失败: {e}")
        return None

    for line in resp.text.splitlines():
        if line.startswith("data:"):
            try:
                msg = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                return None
            if msg.get("result", {}).get("isError"):
                return None
            contents = msg.get("result", {}).get("content", [])
            if contents and contents[0].get("type") == "text":
                raw = contents[0]["text"]
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"_raw": raw}
    return None


def fetch_sorftime_keyword(kw_cfg: dict) -> dict:
    """查单个关键词：搜索量/CPC + Top N 自然位 ASIN。"""
    keyword = kw_cfg["keyword"]
    print(f"  [{keyword}]")

    detail = _call_sorftime("keyword_detail",
                            {"keyword": keyword, "keywordSupportSite": "US"}) or {}
    time.sleep(1)

    page1 = _call_sorftime("keyword_search_results",
                           {"keyword": keyword, "keywordSupportSite": "US",
                            "page": 1, "positionType": 1}) or []
    time.sleep(1.5)

    def _parse_int(raw):
        try:
            return int(str(raw).replace(",", "").replace("K", "000").split(".")[0])
        except Exception:
            return 0

    def _parse_float(raw):
        try:
            return float(str(raw).replace("$", "").strip())
        except Exception:
            return 0.0

    top_n = []
    for rank_i, item in enumerate(page1[:KEYWORD_TOP_N]):
        top_n.append({
            "asin":          item.get("ASIN", ""),
            "rank":          rank_i + 1,
            "brand":         item.get("品牌", ""),
            "price":         round((item.get("价格", 0) or 0) / 100, 2),
            "monthly_sales": item.get("本产品月销量", 0) or 0,
        })

    return {
        "keyword":        keyword,
        "group":          kw_cfg["group"],
        "weekly_search":  _parse_int(detail.get("周搜索量", 0)),
        "monthly_search": _parse_int(detail.get("月搜索量", 0)),
        "cpc":            _parse_float(detail.get("推荐cpc竞价", 0)),
        "competition":    str(detail.get("搜索结果竞品数量", "")),
        "top_n":          top_n,          # list of {asin, rank, brand, price, monthly_sales}
    }


def run_sorftime_phase() -> list[dict]:
    """Phase 1：查全部关键词，返回 keyword_data 列表。"""
    print("\n═══ Phase 1: Sorftime 关键词查询 ═══════════════════════")
    results = []
    for kw_cfg in KEYWORDS:
        data = fetch_sorftime_keyword(kw_cfg)
        results.append(data)
        print(f"    周搜 {data['weekly_search']:,} | Top{KEYWORD_TOP_N}: "
              f"{[x['asin'] for x in data['top_n']]}")
    return results


# ─── Step 2: 合并 ASIN 列表，打标签 ───────────────────────────────────────────

def _load_asin_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    asins = []
    seen = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        asin = re.sub(r"[^A-Z0-9]", "", line.upper())
        if asin and asin not in seen:
            asins.append(asin)
            seen.add(asin)
    return asins


def build_asin_roster(keyword_data: list[dict]) -> dict:
    """
    合并三个来源，去重，每个 ASIN 带完整标签。
    返回 {asin: {is_own, is_fixed, keyword_ranks: {kw: rank}}}
    优先级：own > fixed > keyword-discovered
    """
    own_asins   = set(_load_asin_file(OWN_ASINS_FILE))
    fixed_asins = set(_load_asin_file(ASINS_FILE))

    # 先把所有 ASIN 收集进来
    roster: dict[str, dict] = {}

    def _ensure(asin):
        if asin not in roster:
            roster[asin] = {"is_own": False, "is_fixed": False, "keyword_ranks": {}}

    for asin in own_asins:
        _ensure(asin)
        roster[asin]["is_own"] = True

    for asin in fixed_asins:
        _ensure(asin)
        roster[asin]["is_fixed"] = True

    for kw in keyword_data:
        for entry in kw["top_n"]:
            asin = entry["asin"]
            if not asin:
                continue
            _ensure(asin)
            roster[asin]["keyword_ranks"][kw["keyword"]] = entry["rank"]

    print(f"\n═══ Phase 2: ASIN 名单合并 ═══════════════════════════")
    total = len(roster)
    n_own     = sum(1 for v in roster.values() if v["is_own"])
    n_fixed   = sum(1 for v in roster.values() if v["is_fixed"])
    n_kw_only = sum(1 for v in roster.values()
                    if not v["is_own"] and not v["is_fixed"] and v["keyword_ranks"])
    print(f"  自有: {n_own}  固定竞品: {n_fixed}  关键词发现(新): {n_kw_only}  合计: {total}")

    return roster


# ─── Step 3: Playwright 抓取（复用 rufus_scraper 核心逻辑）──────────────────

def _normalize(text: str) -> str:
    text = re.sub(r'[\xa0​‌‍‎‏­﻿⁠]', ' ', text)
    text = unicodedata.normalize('NFC', text)
    return re.sub(r' +', ' ', text).strip()

_IGNORE_PATTERNS = [
    re.compile(r"^would you like to tell us about a lower price\?$", re.I),
    re.compile(r"^what do customers say\?$", re.I),
    re.compile(r"^what types of things can i ask\?$", re.I),
]

def _is_real_question(text: str) -> bool:
    t = _normalize(text)
    if not t.endswith('?') or len(t) < 10 or len(t) > 160:
        return False
    if any(c in t for c in '{};=><|&+*%@#^~`$\\/'):
        return False
    if re.search(r'\b(var|let|const|function|return|typeof|undefined|null\b.*null\b)\b', t):
        return False
    if not t[0].isupper() or t.count(' ') < 2:
        return False
    return True

def _filter_questions(texts: list) -> list:
    out = []
    for t in texts:
        q = _normalize(t)
        if _is_real_question(q) and not any(p.search(q) for p in _IGNORE_PATTERNS):
            out.append(q)
    return list(dict.fromkeys(out))

def _save_debug(page, asin: str, tag: str):
    try:
        debug_dir = SCRIPT_DIR / "debug"
        debug_dir.mkdir(exist_ok=True)
        stem = f"{asin}_{tag}"
        page.screenshot(path=str(debug_dir / f"{stem}.png"), full_page=False)
        (debug_dir / f"{stem}.html").write_text(page.content(), encoding="utf-8")
    except Exception:
        pass

def _extract_questions(page) -> list:
    ALEXA_SELECTORS = [
        "#dpx-nice-widget-container", "#nile-inline-btf_feature_div",
        "[data-feature-name='nile-inline']", "[data-feature-name*='alexa']",
        "[data-csa-c-slot-id*='nile']", "[data-csa-c-slot-id*='alexa']",
        "#rufus-t3", "#ask-btf_feature_div", "[data-feature-name='rufus']",
        "[id*='rufus']", "[class*='rufus']", "[id*='alexa']", "[class*='alexa']",
    ]
    for sel in ALEXA_SELECTORS:
        try:
            container = page.query_selector(sel)
            if not container:
                continue
            buttons = container.query_selector_all("button, [role='button'], span.a-size-base")
            texts = [_normalize(b.inner_text()) for b in buttons
                     if 8 < len(_normalize(b.inner_text())) < 200]
            if texts:
                print(f"    [策略1] {sel[:40]} → {len(texts)} 个")
                return texts
        except Exception:
            continue
    # 策略2：全页面以?结尾的按钮
    try:
        results = page.evaluate("""() => {
            const q = new Set();
            document.querySelectorAll('button,[role="button"],.a-button-text').forEach(el => {
                const t = (el.innerText||'').replace(/\\u00a0/g,' ').trim();
                if (t.endsWith('?') && t.length>8 && t.length<200 && !t.includes('\\n')) q.add(t);
            });
            return [...q];
        }""")
        filtered = [x for x in (results or []) if _is_real_question(x)]
        if filtered:
            print(f"    [策略2] {len(filtered)} 个")
            return filtered
    except Exception:
        pass
    return []

def _scrape_once(asin: str, context) -> dict:
    url = f"https://www.amazon.com/dp/{asin}"
    print(f"  访问: {url}")
    page = context.new_page()
    try:
        try:
            page.goto(url, timeout=NAVIGATION_TIMEOUT, wait_until="commit")
        except Exception as e:
            if "timeout" not in str(e).lower():
                raise
        try:
            page.wait_for_load_state("domcontentloaded", timeout=DOM_READY_TIMEOUT)
        except Exception:
            pass

        content_lc = page.content().lower()
        title = page.title()
        if "couldn't find that page" in content_lc or "page not found" in title.lower():
            _save_debug(page, asin, "not_found")
            return {"asin": asin, "status": "not_found", "questions": [], "error": ""}
        if "503" in title or "robot" in title.lower() or "Type the characters" in page.content()[:500]:
            _save_debug(page, asin, "blocked")
            return {"asin": asin, "status": "blocked", "questions": [], "error": title}

        # 等待+滚动触发懒加载
        try:
            page.wait_for_selector(
                "#dpx-nice-widget-container,#productTitle,#feature-bullets",
                timeout=ALEXA_HINT_TIMEOUT)
        except Exception:
            pass
        page.wait_for_timeout(2500)
        for pct in [0.15, 0.3, 0.5, 0.7, 0.9, 1.0]:
            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct})")
            page.wait_for_timeout(1200)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(2500)

        questions = _filter_questions(_extract_questions(page))
        if not questions:
            has_content = page.locator("#productTitle,#feature-bullets").count() > 0
            if not has_content:
                _save_debug(page, asin, "error")
                return {"asin": asin, "status": "timeout", "questions": [], "error": "page not loaded"}
            _save_debug(page, asin, "no_rufus")
            return {"asin": asin, "status": "no_rufus", "questions": [], "error": ""}
        print(f"    ✓ {len(questions)} 个问题")
        return {"asin": asin, "status": "ok", "questions": questions, "error": ""}
    except Exception as e:
        try:
            _save_debug(page, asin, "error")
        except Exception:
            pass
        st = "timeout" if "timeout" in str(e).lower() else "error"
        return {"asin": asin, "status": st, "questions": [], "error": str(e)}
    finally:
        try:
            page.close()
        except Exception:
            pass

def scrape_asin(asin: str, context) -> dict:
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            print(f"    ↻ 重试 {attempt}/{MAX_RETRIES}")
            time.sleep(min(10, 2 + attempt * 2))
        result = _scrape_once(asin, context)
        if result["status"] in {"ok", "blocked", "not_found"}:
            break
    return result

def run_playwright_phase(roster: dict) -> tuple[dict, dict]:
    """
    Phase 3：抓取 roster 中所有 ASIN 的 Alexa 问题。
    返回 (asin_questions, run_statuses)
    """
    print(f"\n═══ Phase 3: Playwright 抓取（{len(roster)} 个 ASIN）══════════")
    asin_questions: dict[str, list] = {}
    run_statuses:   dict[str, dict] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=["--no-sandbox", "--disable-gpu",
                  "--disable-blink-features=AutomationControlled",
                  "--window-size=1440,900"],
        )
        context = browser.new_context(
            user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1440, "height": 900},
            locale="en-US", timezone_id="America/New_York",
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        context.route("**/*", lambda route, req: (
            route.abort() if req.resource_type in BLOCKED_RESOURCE_TYPES else route.continue_()))

        if COOKIES_FILE.exists():
            cookies = json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
            valid_ss = {"Strict", "Lax", "None"}
            for c in cookies:
                if c.get("sameSite") not in valid_ss:
                    c["sameSite"] = "None"
                for k in ["hostOnly", "session", "storeId"]:
                    c.pop(k, None)
            context.add_cookies(cookies)
            print(f"✅ 已注入 {len(cookies)} 条 cookie\n")

        asins_ordered = list(roster.keys())
        for i, asin in enumerate(asins_ordered):
            meta = roster[asin]
            tag = "自有" if meta["is_own"] else ("固定竞品" if meta["is_fixed"] else "关键词新")
            print(f"[{i+1}/{len(asins_ordered)}] {asin} [{tag}]")
            result = scrape_asin(asin, context)
            run_statuses[asin]   = result
            asin_questions[asin] = result["questions"]
            if i < len(asins_ordered) - 1:
                print(f"  等待 {DELAY_BETWEEN_ASINS}s...\n")
                time.sleep(DELAY_BETWEEN_ASINS)

        try:
            browser.close()
        except Exception:
            pass

    ok_count = sum(1 for r in run_statuses.values() if r["status"] == "ok")
    print(f"\n✅ 抓取完成：{ok_count}/{len(roster)} 成功")
    return asin_questions, run_statuses


# ─── Step 4: 三层分析 ─────────────────────────────────────────────────────────

def _analyze_question_set(asin_questions: dict) -> dict:
    """通用问题频率分析（高频/中频/独有）。"""
    total = len(asin_questions)
    q2a: dict[str, list] = defaultdict(list)
    for asin, qs in asin_questions.items():
        for q in qs:
            if asin not in q2a[q]:
                q2a[q].append(asin)
    threshold = max(2, math.ceil(total * 0.35))
    high_freq = sorted([(q, a) for q, a in q2a.items() if len(a) >= threshold],
                       key=lambda x: len(x[1]), reverse=True)
    mid_freq  = sorted([(q, a) for q, a in q2a.items() if 2 <= len(a) < threshold],
                       key=lambda x: len(x[1]), reverse=True)
    unique_qs = {asin: [q for q in qs if len(q2a[q]) == 1]
                 for asin, qs in asin_questions.items()}
    return {"total": total, "threshold": threshold, "q2a": dict(q2a),
            "high_freq": high_freq, "mid_freq": mid_freq, "unique": unique_qs}


def run_analysis_phase(keyword_data: list[dict], roster: dict,
                       asin_questions: dict, run_statuses: dict) -> dict:
    """
    Phase 4：三层交叉分析。
    返回 analysis_result dict，供 HTML/Feishu/Excel 使用。
    """
    print("\n═══ Phase 4: 三层分析 ══════════════════════════════════")

    own_asins    = {a for a, m in roster.items() if m["is_own"]}
    fixed_asins  = {a for a, m in roster.items() if m["is_fixed"]}

    # ── 只统计成功抓取的 ASIN ──
    ok_questions = {a: qs for a, qs in asin_questions.items()
                    if run_statuses.get(a, {}).get("status") == "ok" and qs}

    # ── 竞品层（固定40） ──
    competitor_q = {a: ok_questions[a] for a in fixed_asins if a in ok_questions}
    comp_analysis = _analyze_question_set(competitor_q)
    print(f"  竞品层：{len(competitor_q)}/{len(fixed_asins)} 个成功，"
          f"高频 {len(comp_analysis['high_freq'])} 条")

    # ── 自有 ASIN 层 ──
    own_q = {a: ok_questions.get(a, []) for a in own_asins}
    own_status = {a: run_statuses.get(a, {}).get("status", "unknown") for a in own_asins}

    # ── 关键词层：每个关键词 Top5 的问题频率 ──
    keyword_analysis = []
    for kw in keyword_data:
        top5_asins = [e["asin"] for e in kw["top_n"] if e["asin"]]
        top5_ok_q  = {a: ok_questions[a] for a in top5_asins if a in ok_questions}
        kw_analysis = _analyze_question_set(top5_ok_q) if top5_ok_q else {}

        # 自有 ASIN gap：Top5 高频问题中，自有 ASIN 没有的
        top5_hf_questions = {q for q, _ in kw_analysis.get("high_freq", [])}
        own_gap: dict[str, list] = {}
        for own_asin in own_asins:
            own_qs_set = set(ok_questions.get(own_asin, []))
            gap = sorted(top5_hf_questions - own_qs_set)
            if gap:
                own_gap[own_asin] = gap

        # 自有 ASIN 在本关键词的自然位
        own_rank_here = {a: roster[a]["keyword_ranks"].get(kw["keyword"])
                         for a in own_asins if kw["keyword"] in roster[a]["keyword_ranks"]}

        keyword_analysis.append({
            "keyword":        kw["keyword"],
            "group":          kw["group"],
            "weekly_search":  kw["weekly_search"],
            "monthly_search": kw["monthly_search"],
            "cpc":            kw["cpc"],
            "competition":    kw["competition"],
            "top5":           kw["top_n"],
            "top5_ok_count":  len(top5_ok_q),
            "analysis":       kw_analysis,
            "own_gap":        own_gap,
            "own_rank":       own_rank_here,
        })
        hf_count = len(kw_analysis.get("high_freq", []))
        print(f"  [{kw['keyword']}] Top5成功={len(top5_ok_q)}, 高频={hf_count}")

    return {
        "run_date":         RUN_DATETIME,
        "keyword_analysis": keyword_analysis,
        "comp_analysis":    comp_analysis,
        "own_q":            own_q,
        "own_status":       own_status,
        "own_asins":        sorted(own_asins),
        "all_questions":    ok_questions,
        "run_statuses":     run_statuses,
        "roster":           roster,
    }


# ─── Step 4b: WoW 对比 ────────────────────────────────────────────────────────

def load_prev_archive() -> dict | None:
    if not ARCHIVE_FILE.exists():
        return None
    try:
        return json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def compute_wow(current: dict, prev: dict) -> dict:
    """对比竞品层和关键词层的 WoW 变化。"""
    if not prev:
        return {}

    # 竞品层 WoW
    prev_comp_q   = prev.get("competitor_questions", {})
    curr_comp_q   = current["all_questions"]
    prev_all      = set(q for qs in prev_comp_q.values() for q in qs)
    curr_all      = set(q for qs in curr_comp_q.values() for q in qs)

    prev_comp_ana = _analyze_question_set(prev_comp_q) if prev_comp_q else {}
    curr_comp_ana = current["comp_analysis"]
    prev_hf = {q for q, _ in prev_comp_ana.get("high_freq", [])}
    curr_hf = {q for q, _ in curr_comp_ana.get("high_freq", [])}

    # 关键词层 WoW（搜索量+关键词高频问题变化）
    prev_kw_map = {kw["keyword"]: kw for kw in prev.get("keyword_analysis", [])}
    kw_wow = []
    for kw in current["keyword_analysis"]:
        prev_kw = prev_kw_map.get(kw["keyword"])
        if not prev_kw:
            kw_wow.append({"keyword": kw["keyword"], "has_prev": False})
            continue
        weekly_delta  = kw["weekly_search"]  - prev_kw.get("weekly_search", 0)
        monthly_delta = kw["monthly_search"] - prev_kw.get("monthly_search", 0)
        cpc_delta     = round(kw["cpc"] - prev_kw.get("cpc", 0), 2)
        prev_kw_hf    = {q for q, _ in prev_kw.get("top5_high_freq", [])}
        curr_kw_hf    = {q for q, _ in kw["analysis"].get("high_freq", [])}
        kw_wow.append({
            "keyword":        kw["keyword"],
            "has_prev":       True,
            "weekly_delta":   weekly_delta,
            "monthly_delta":  monthly_delta,
            "cpc_delta":      cpc_delta,
            "kw_hf_new":      sorted(curr_kw_hf - prev_kw_hf),
            "kw_hf_dropped":  sorted(prev_kw_hf - curr_kw_hf),
        })

    return {
        "prev_date":      prev.get("run_date", "上周"),
        "comp_hf_new":    sorted(curr_hf - prev_hf),
        "comp_hf_drop":   sorted(prev_hf - curr_hf),
        "brand_new_q":    sorted(curr_all - prev_all),
        "disappeared_q":  sorted(prev_all - curr_all),
        "kw_wow":         kw_wow,
    }


def save_archive(current: dict):
    """存档本次结果，供下周 WoW 使用。"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "run_date":             current["run_date"],
        "keyword_analysis":     [
            {
                "keyword":          kw["keyword"],
                "group":            kw["group"],
                "weekly_search":    kw["weekly_search"],
                "monthly_search":   kw["monthly_search"],
                "cpc":              kw["cpc"],
                "top5_high_freq":   [(q, len(a)) for q, a in kw["analysis"].get("high_freq", [])],
            }
            for kw in current["keyword_analysis"]
        ],
        "competitor_questions": {a: qs for a, qs in current["all_questions"].items()
                                 if current["roster"].get(a, {}).get("is_fixed")},
        "own_questions":        current["own_q"],
    }
    ARCHIVE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 存档已保存: {ARCHIVE_FILE}")


# ─── Step 5: 输出 ─────────────────────────────────────────────────────────────

def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def generate_html(current: dict, wow: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ka   = current["keyword_analysis"]
    ca   = current["comp_analysis"]
    own  = current["own_q"]
    own_statuses = current["own_status"]
    roster = current["roster"]

    CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#f5f7fa; color:#2c3e50; }
.hdr { background: linear-gradient(135deg,#1a237e,#283593); color:white; padding:20px 32px; }
.hdr h1 { font-size:18px; font-weight:600; margin-bottom:4px; }
.hdr .sub { font-size:12px; opacity:.85; }
.wrap { max-width:1100px; margin:0 auto; padding:20px 16px; }
.sec { background:white; border-radius:10px; padding:18px 22px; margin-bottom:18px;
       box-shadow:0 1px 4px rgba(0,0,0,.08); }
.sec h2 { font-size:14px; font-weight:600; color:#1a237e; border-bottom:1px solid #e8ecf0;
          padding-bottom:8px; margin-bottom:14px; }
.sec h3 { font-size:13px; font-weight:600; color:#283593; margin:12px 0 6px; }
table { width:100%; border-collapse:collapse; font-size:12px; }
th { background:#f0f2f8; text-align:left; padding:7px 10px; color:#333; font-weight:600; }
td { padding:6px 10px; border-bottom:1px solid #f0f2f0; vertical-align:top; }
tr:last-child td { border-bottom:none; }
.bar-wrap { background:#eef0f8; border-radius:3px; height:5px; width:80px;
            display:inline-block; vertical-align:middle; }
.bar { background:#3949ab; height:5px; border-radius:3px; }
.tag-h { background:#e8eaf6; color:#3949ab; padding:1px 6px; border-radius:3px; font-size:11px; font-weight:600; }
.tag-m { background:#e8f5e9; color:#2e7d32; padding:1px 6px; border-radius:3px; font-size:11px; }
.tag-u { background:#fce4ec; color:#c62828; padding:1px 6px; border-radius:3px; font-size:11px; }
.wn { color:#2e7d32; font-weight:600; }
.wd { color:#c62828; }
.wow-box { background:#fffde7; border-left:4px solid #f9a825; padding:12px 16px; border-radius:5px; margin-bottom:12px; }
.kw-card { border:1px solid #e0e4f0; border-radius:8px; padding:14px 16px; margin-bottom:12px; }
.kw-title { font-size:13px; font-weight:700; color:#1a237e; }
.kw-meta { font-size:12px; color:#666; margin:4px 0 10px; }
.asin-hd { background:#f0f2f8; padding:3px 8px; border-radius:4px; font-size:12px; font-weight:600; display:inline-block; margin:6px 0 4px; }
.qi { font-size:12px; padding:3px 0 3px 10px; border-left:2px solid #e0e0e0; margin:2px 0; }
.gap-box { background:#fff3e0; border-left:3px solid #ff9800; padding:8px 12px; border-radius:4px; margin-top:8px; font-size:12px; }
details summary { cursor:pointer; font-size:12px; font-weight:600; color:#3949ab; padding:6px 0; }
"""
    parts = [f"""<!DOCTYPE html><html lang="zh"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Alexa 综合情报 {_esc(RUN_TIMESTAMP)}</title><style>{CSS}</style></head>
<body>
<div class="hdr">
  <h1>📊 Alexa 问题综合情报 — 手机三脚架/Vlogging Kit</h1>
  <div class="sub">生成时间：{_esc(RUN_DATETIME)} &nbsp;|&nbsp;
  共抓取 {len(current['all_questions'])} 个ASIN
  {"&nbsp;|&nbsp; 对比基准：" + _esc(wow.get("prev_date","")) if wow else ""}</div>
</div>
<div class="wrap">"""]

    # ── 自有 ASIN ──
    parts.append('<div class="sec"><h2>🏠 自有 ASIN 状态</h2>')
    for own_asin, qs in own.items():
        status = own_statuses.get(own_asin, "unknown")
        parts.append(f'<span class="asin-hd">{_esc(own_asin)}</span> '
                     f'<span style="font-size:12px;color:#666">状态: {_esc(status)}</span>')
        # 在哪些关键词有自然位
        ranks = roster.get(own_asin, {}).get("keyword_ranks", {})
        if ranks:
            rank_str = " | ".join(f"{kw[:25]}→#{r}" for kw, r in ranks.items())
            parts.append(f'<div style="font-size:12px;color:#3949ab;margin:4px 0">自然位: {_esc(rank_str)}</div>')
        else:
            parts.append('<div style="font-size:12px;color:#999;margin:4px 0">未进入各关键词 Top5 自然位</div>')
        if qs:
            for q in qs:
                parts.append(f'<div class="qi">{_esc(q)}</div>')
        else:
            parts.append('<div style="font-size:12px;color:#999;margin:4px 0">暂无 Alexa 问题（新品期正常）</div>')
        # Gap（来自关键词层）
        for kw_item in ka:
            gap = kw_item["own_gap"].get(own_asin, [])
            if gap:
                parts.append(f'<div class="gap-box">⚡ <b>「{_esc(kw_item["keyword"])}」Top5 高频但自有未命中：</b><br>'
                              + " / ".join(_esc(g) for g in gap) + '</div>')
    parts.append('</div>')

    # ── 关键词层 ──
    parts.append('<div class="sec"><h2>🔑 关键词视角 Alexa 问题</h2>')
    GROUP_PREV = ""
    for kw_item in ka:
        if kw_item["group"] != GROUP_PREV:
            parts.append(f'<h3>━ {_esc(kw_item["group"])} 品类</h3>')
            GROUP_PREV = kw_item["group"]
        # WoW 搜索量
        kw_wow_item = next((x for x in wow.get("kw_wow", []) if x["keyword"] == kw_item["keyword"]), None)
        if kw_wow_item and kw_wow_item.get("has_prev"):
            wd = kw_wow_item["weekly_delta"]
            md = kw_wow_item["monthly_delta"]
            cd = kw_wow_item["cpc_delta"]
            def _d(v): return (f'<span class="wn">↑{abs(v):,}</span>' if v>0
                               else (f'<span class="wd">↓{abs(v):,}</span>' if v<0 else '持平'))
            meta_str = (f"周搜：<b>{kw_item['weekly_search']:,}</b>（{_d(wd)}）"
                       f" | 月搜：<b>{kw_item['monthly_search']:,}</b>（{_d(md)}）"
                       f" | CPC：<b>${kw_item['cpc']:.2f}</b>（{'↑' if cd>0 else '↓' if cd<0 else ''}${abs(cd):.2f}）")
        else:
            meta_str = (f"周搜：<b>{kw_item['weekly_search']:,}</b>"
                       f" | 月搜：<b>{kw_item['monthly_search']:,}</b>"
                       f" | CPC：<b>${kw_item['cpc']:.2f}</b>")

        parts.append(f'<div class="kw-card">'
                     f'<div class="kw-title">🔑 {_esc(kw_item["keyword"])}</div>'
                     f'<div class="kw-meta">{meta_str}'
                     f' | 竞品数：{_esc(kw_item["competition"])}'
                     f' | Top5成功抓取：{kw_item["top5_ok_count"]}/{len(kw_item["top5"])}</div>')

        hf = kw_item["analysis"].get("high_freq", [])
        if hf:
            parts.append('<b style="font-size:12px">Top5 高频 Alexa 问题：</b>'
                         '<table style="margin-top:6px"><tr><th>问题</th><th>出现/Top5</th></tr>')
            for q, asins in hf:
                parts.append(f'<tr><td>{_esc(q)}</td><td>{len(asins)}/{kw_item["top5_ok_count"]}</td></tr>')
            parts.append('</table>')
        else:
            parts.append('<div style="font-size:12px;color:#999;margin-top:6px">Top5 暂无高频共性问题</div>')

        # Top5 ASIN 列表
        parts.append('<details style="margin-top:8px"><summary>Top5 ASIN 详情</summary><div style="padding:6px 0">')
        for entry in kw_item["top5"]:
            asin = entry["asin"]
            qs_here = current["all_questions"].get(asin, [])
            is_own = roster.get(asin, {}).get("is_own", False)
            label = " 🏠自有" if is_own else ""
            parts.append(f'<span class="asin-hd">#{entry["rank"]} {_esc(asin)}{_esc(label)}</span>'
                         f' <span style="font-size:11px;color:#666">{_esc(entry["brand"])} | ${entry["price"]:.2f} | 月销{entry["monthly_sales"]:,}</span>')
            if qs_here:
                for q in qs_here:
                    parts.append(f'<div class="qi">{_esc(q)}</div>')
            else:
                st = current["run_statuses"].get(asin, {}).get("status", "?")
                parts.append(f'<div class="qi" style="color:#999">无Alexa问题（{_esc(st)}）</div>')
        parts.append('</div></details></div>')
    parts.append('</div>')

    # ── 竞品全景（固定40个）──
    parts.append('<div class="sec"><h2>📦 竞品全景（固定竞品高频汇总）</h2>')
    if wow:
        new_q  = wow.get("comp_hf_new", [])
        drop_q = wow.get("comp_hf_drop", [])
        if new_q or drop_q:
            parts.append('<div class="wow-box">')
            if new_q:
                parts.append(f'<div class="wn">🆕 新进入高频（{len(new_q)}条）：' +
                              " / ".join(_esc(q) for q in new_q[:5]) + ('...' if len(new_q)>5 else '') + '</div>')
            if drop_q:
                parts.append(f'<div class="wd">📉 退出高频（{len(drop_q)}条）：' +
                              " / ".join(_esc(q) for q in drop_q[:5]) + '</div>')
            parts.append('</div>')

    total = ca.get("total", 1)
    threshold = ca.get("threshold", 2)
    if ca.get("high_freq"):
        parts.append(f'<h3>高频共性问题（≥{threshold} 个竞品，{threshold/total:.0%}+）</h3>'
                     '<table><tr><th>问题</th><th>竞品数</th><th>覆盖率</th></tr>')
        for q, asins in ca["high_freq"]:
            pct = len(asins)/total if total else 0
            bar_w = int(pct*100)
            parts.append(f'<tr><td>{_esc(q)}</td><td>{len(asins)}/{total}</td>'
                         f'<td><span class="bar-wrap"><span class="bar" style="width:{bar_w}%"></span></span> {pct:.0%}</td></tr>')
        parts.append('</table>')

    if ca.get("mid_freq"):
        parts.append(f'<h3>中频问题（2~{threshold-1} 个竞品）</h3>'
                     '<table><tr><th>问题</th><th>竞品数</th></tr>')
        for q, asins in ca["mid_freq"]:
            parts.append(f'<tr><td>{_esc(q)}</td><td>{len(asins)}</td></tr>')
        parts.append('</table>')
    parts.append('</div>')

    # ── 新问题/消失问题 WoW ──
    if wow and (wow.get("brand_new_q") or wow.get("disappeared_q")):
        parts.append('<div class="sec"><h2>🔄 全量问题 WoW 变化</h2>')
        if wow.get("brand_new_q"):
            parts.append(f'<details><summary class="wn">✨ 全新问题（{len(wow["brand_new_q"])}条，上周未见）</summary><div>')
            for q in wow["brand_new_q"]:
                parts.append(f'<div class="qi wn">+ {_esc(q)}</div>')
            parts.append('</div></details>')
        if wow.get("disappeared_q"):
            parts.append(f'<details><summary class="wd">👻 消失的问题（{len(wow["disappeared_q"])}条）</summary><div>')
            for q in wow["disappeared_q"]:
                parts.append(f'<div class="qi wd">- {_esc(q)}</div>')
            parts.append('</div></details>')
        parts.append('</div>')

    parts.append('</div></body></html>')
    html = "\n".join(parts)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"✅ HTML 报告已保存: {OUTPUT_HTML}")
    return OUTPUT_HTML


def push_to_github_pages(html_path: Path) -> str:
    dest = GITHUB_REPO / html_path.name
    try:
        shutil.copy2(str(html_path), str(dest))
        subprocess.run(["git", "add", html_path.name], cwd=str(GITHUB_REPO),
                       check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"alexa intel: {RUN_TIMESTAMP}"],
                       cwd=str(GITHUB_REPO), check=True, capture_output=True)
        subprocess.run(["git", "push"], cwd=str(GITHUB_REPO),
                       check=True, capture_output=True)
        url = f"{GITHUB_PAGES_BASE}/{html_path.name}"
        print(f"🚀 GitHub Pages: {url}")
        return url
    except Exception as e:
        print(f"❌ GitHub Pages 推送失败: {e}")
        return ""


def save_excel_report(current: dict) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    hdr_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    hdr_font = Font(color="FFFFFF", bold=True)

    def _style(ws):
        for c in ws[1]:
            c.fill = hdr_fill; c.font = hdr_font
            c.alignment = Alignment(horizontal="center")

    # Sheet1: 关键词高频 Alexa 问题
    ws1 = wb.active; ws1.title = "关键词Alexa高频"
    ws1.append(["关键词", "品类", "Alexa问题", "Top5出现次数", "周搜索量"])
    _style(ws1)
    for kw in current["keyword_analysis"]:
        for q, asins in kw["analysis"].get("high_freq", []):
            ws1.append([kw["keyword"], kw["group"], q, len(asins), kw["weekly_search"]])
    ws1.column_dimensions["A"].width = 30
    ws1.column_dimensions["C"].width = 65

    # Sheet2: 竞品高频
    ws2 = wb.create_sheet("竞品高频问题")
    ca = current["comp_analysis"]
    total = ca.get("total", 1)
    ws2.append(["问题", "竞品数", "覆盖率"])
    _style(ws2)
    for q, asins in ca.get("high_freq", []):
        ws2.append([q, len(asins), f"{len(asins)/total:.0%}"])
    ws2.column_dimensions["A"].width = 65

    # Sheet3: 自有ASIN gap分析
    ws3 = wb.create_sheet("自有ASIN Gap分析")
    ws3.append(["自有ASIN", "关键词", "缺失高频问题"])
    _style(ws3)
    for kw in current["keyword_analysis"]:
        for own_asin, gaps in kw["own_gap"].items():
            for g in gaps:
                ws3.append([own_asin, kw["keyword"], g])
    ws3.column_dimensions["A"].width = 15
    ws3.column_dimensions["B"].width = 30
    ws3.column_dimensions["C"].width = 65

    # Sheet4: 所有ASIN问题全览
    ws4 = wb.create_sheet("全部ASIN问题")
    ws4.append(["ASIN", "标签", "Alexa问题"])
    _style(ws4)
    roster = current["roster"]
    for asin, qs in current["all_questions"].items():
        meta = roster.get(asin, {})
        tag = "自有" if meta.get("is_own") else ("固定竞品" if meta.get("is_fixed") else "关键词新")
        for q in qs:
            ws4.append([asin, tag, q])
    ws4.column_dimensions["A"].width = 15
    ws4.column_dimensions["C"].width = 65

    wb.save(str(OUTPUT_EXCEL))
    print(f"✅ Excel 已保存: {OUTPUT_EXCEL}")
    return OUTPUT_EXCEL


def send_feishu(current: dict, wow: dict, html_url: str):
    ka = current["keyword_analysis"]
    ca = current["comp_analysis"]
    own = current["own_q"]
    own_statuses = current["own_status"]
    roster = current["roster"]
    total_scraped = len(current["all_questions"])
    ok_count = sum(1 for r in current["run_statuses"].values() if r["status"] == "ok")

    elements = [{
        "tag": "div",
        "text": {"tag": "lark_md",
                 "content": f"**生成时间：** {RUN_DATETIME}　**抓取成功：** {ok_count}/{total_scraped}"}
    }, {"tag": "hr"}]

    # ── 模块一：竞品 ──────────────────────────────────────────
    elements.append({"tag": "div", "text": {"tag": "lark_md",
                     "content": "**📦 【竞品】高频 Alexa 问题**"}})

    # 竞品整体高频
    hf = ca.get("high_freq", [])
    hf_lines = "\n".join(f"{i+1}. {q}（{len(a)}/{ca.get('total', 1)} 个ASIN）"
                         for i, (q, a) in enumerate(hf[:8])) if hf else "暂无高频问题"
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": hf_lines}})
    elements.append({"tag": "hr"})

    # 各关键词 Top5 高频
    curr_group = ""
    for kw_item in ka:
        if kw_item["group"] != curr_group:
            curr_group = kw_item["group"]
            elements.append({"tag": "div", "text": {"tag": "lark_md",
                             "content": f"**━━ {curr_group} 品类 ━━**"}})
        lines = [f"**🔑 {kw_item['keyword']}**　"
                 f"周搜 {kw_item['weekly_search']:,} | 月搜 {kw_item['monthly_search']:,} | CPC ${kw_item['cpc']:.2f}"]
        hf_kw = kw_item["analysis"].get("high_freq", [])
        if hf_kw:
            lines.append(f"Top5自然位高频（{kw_item['top5_ok_count']}个ASIN）：")
            for q, asins in hf_kw[:5]:
                lines.append(f"- {q}（{len(asins)}/{kw_item['top5_ok_count']}）")
        else:
            lines.append("_Top5 暂无高频共性问题_")
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}})
    elements.append({"tag": "hr"})

    # ── 模块二：本品 ──────────────────────────────────────────
    elements.append({"tag": "div", "text": {"tag": "lark_md",
                     "content": "**🏠 【本品】Alexa 问题（B0GY7Y6C63）**"}})
    own_lines = []
    for own_asin, qs in own.items():
        status = own_statuses.get(own_asin, "?")
        ranks = roster.get(own_asin, {}).get("keyword_ranks", {})
        rank_str = " | ".join(f"{k[:20]}→#{v}" for k, v in ranks.items()) if ranks else "未进入Top5自然位"
        own_lines.append(f"抓取状态：{status}　自然位：{rank_str}")
        if qs:
            own_lines.append(f"当周被问（{len(qs)} 条）：")
            for q in qs:
                own_lines.append(f"- {q}")
        else:
            own_lines.append("当周暂无 Alexa 问题（新品期正常）")
        gaps = []
        for kw_item in ka:
            gap = kw_item["own_gap"].get(own_asin, [])
            if gap:
                gaps.append(f"「{kw_item['keyword']}」缺失：" + " / ".join(gap[:3]))
        if gaps:
            own_lines.append("⚡ Gap（竞品高频本品未覆盖）：")
            own_lines.extend(gaps)
    if not own_lines:
        own_lines.append("未配置自有 ASIN")
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(own_lines)}})
    elements.append({"tag": "note", "elements": [{"tag": "plain_text",
                     "content": f"Alexa 综合情报 | {RUN_TIMESTAMP} | 关键词Top{KEYWORD_TOP_N}+固定竞品+自有"}]})

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": "📊 Alexa 问题综合情报周报"},
                       "template": "indigo"},
            "elements": elements,
        }
    }
    try:
        resp = requests.post(FEISHU_WEBHOOK, headers={"Content-Type": "application/json"},
                             data=json.dumps(payload, ensure_ascii=False), timeout=10)
        resp.raise_for_status()
        r = resp.json()
        if r.get("code") == 0 or r.get("StatusCode") == 0:
            print("✅ 飞书已发送")
        else:
            print(f"⚠ 飞书返回: {r}")
    except Exception as e:
        print(f"✗ 飞书失败: {e}")


# ─── 主流程入口（分步测试时可从任一阶段启动）─────────────────────────────────

def main():
    print(f"═══ Alexa 综合情报 {RUN_DATETIME} ═══════════════════════════")

    # Phase 1: Sorftime 关键词查询 → Top5 ASIN
    keyword_data = run_sorftime_phase()

    # Phase 2: 构建统一 ASIN 名单
    roster = build_asin_roster(keyword_data)
    own_count = sum(1 for m in roster.values() if m["is_own"])
    fix_count = sum(1 for m in roster.values() if m["is_fixed"] and not m["is_own"])
    new_count = sum(1 for m in roster.values() if not m["is_fixed"] and not m["is_own"])
    print(f"\n✅ 名单汇总：自有={own_count} 固定竞品={fix_count} 关键词新={new_count} 合计={len(roster)}")

    # Phase 3: Playwright 抓取
    asin_questions, run_statuses = run_playwright_phase(roster)

    # Phase 4: 三层分析
    current = run_analysis_phase(keyword_data, roster, asin_questions, run_statuses)

    # WoW
    save_archive(current)
    prev = load_prev_archive()
    wow  = compute_wow(current, prev) if prev else {}

    # Phase 5: 输出
    html_path = generate_html(current, wow)
    html_url  = push_to_github_pages(html_path)
    save_excel_report(current)
    send_feishu(current, wow, html_url)

    print(f"\n✅ 全部完成 — {RUN_DATETIME}")


if __name__ == "__main__":
    main()
