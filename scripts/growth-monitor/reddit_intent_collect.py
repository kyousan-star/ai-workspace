#!/usr/bin/env python3
"""
会话触发的 Reddit 采集器（B1）——绕过 search.json 403，走登录态 Chrome 渲染页。

背景：2026-07-19 reddit 对 urllib 直连 www/.../search.json 与 old.reddit HTML 全线 403，
scraper（social_media_voc/reddit-scraper）的 urllib 采集通道已死、自动周报停摆约一周。
定时无人值守时 CDP proxy 起不来（实测哨兵 07-17/18 无人值守 0 候选），所以本采集器
**只在会话内（Chrome+proxy 活着）触发跑**，复用 reddit_sentinel 已验证的 CDP Tab 通道。

两组 query：
- intent：创作者行为/场景/设备意图（customer-in），喂「创作者用例情报台账」
- category：品类词（product-out），喂现有 Reddit VOC（Phase 2 再接 DB/报告生成）

反限流：渲染搜索页比列表页重，连搜约 6 次会被限流（07-19 实测）。默认间隔加大、每轮限量，
并用 seen-ids 去重，让一周切片跨多次触发累积，而非一次狂搜。

用法：
  python3 reddit_intent_collect.py --mode intent --max-queries 8
  python3 reddit_intent_collect.py --mode category --time-filter week
  python3 reddit_intent_collect.py --mode both --subs NewTubers videography --queries "filming by myself" "my setup for"
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# 复用哨兵的 CDP proxy 原语（import 安全：其 main() 有 __name__ 守卫、无顶层副作用）
from reddit_sentinel import ensure_proxy, Tab, BASE_DIR, proxy_get, PAGE_INTERVAL_SEC  # type: ignore


def nav(tab, url: str):
    """全编码导航——哨兵 Tab.goto 用 safe=':/?&=.'，多 & 参数 URL 的 &xxx 会被 proxy
    /navigate 端点当成自身参数吃掉（只剩第一个 q）。这里 safe='' 让整条 URL 作为单值存活。"""
    proxy_get(f"/navigate?target={tab.target}&url={urllib.parse.quote(url, safe='')}")
    time.sleep(PAGE_INTERVAL_SEC)

OUT_DIR = BASE_DIR / "output" / "intent_collect"
SEEN_FILE = BASE_DIR / "data" / "intent_collect_seen_ids.txt"

# ── query 集 ──────────────────────────────────────────────────────────────────
# intent：设备/场景/环境/一人拍锚点（07-19 验证：泛"起号"词捞回 95% 算法焦虑，无效）
INTENT_SUBS = ["NewTubers", "videography", "Vlogging", "mobilefilmmaking", "iPhoneography"]
INTENT_QUERIES = [
    "filming by myself",
    "filming alone",
    "out of frame",
    "my setup for",
    "filming outside",
    "filming in my room",
    "low light",
    "what gear should I get",
]
# category：沿用 scraper 口径（product-out）
CATEGORY_SUBS = ["NewTubers", "videography", "Vlogging", "mobilefilmmaking", "ContentCreators"]
CATEGORY_QUERIES = [
    "phone tripod",
    "iphone tripod",
    "vlogging kit",
    "wireless mic",
    "ring light",
    "shaky video",
]

# ── DOM 扫描：old.reddit 搜索结果页 .search-result-link（07-19 探明 schema）──────
SEARCH_SCAN_JS = r"""
(() => {
  const items = [...document.querySelectorAll('.search-result-link')];
  const num = (s) => { const m = (s||'').match(/-?\d+/); return m ? parseInt(m[0],10) : null; };
  return JSON.stringify(items.map(s => {
    const t = s.querySelector('.search-title');
    const tm = s.querySelector('time');
    return {
      id: (s.getAttribute('data-fullname')||'').replace('t3_',''),
      title: t ? t.textContent.trim() : null,
      permalink: t ? t.href : null,
      author: (s.querySelector('.author')||{}).textContent || null,
      subreddit: (s.querySelector('.search-subreddit-link')||{}).textContent || null,
      num_comments: num((s.querySelector('.search-comments')||{}).textContent),
      score: num((s.querySelector('.search-score')||{}).textContent),
      created: tm ? tm.getAttribute('datetime') : null,
      body: ((s.querySelector('.search-result-body')||{}).textContent||'').trim().slice(0,600)
    };
  }));
})()
"""


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] intent_collect: {msg}", flush=True)


def load_seen() -> set:
    if SEEN_FILE.exists():
        return set(SEEN_FILE.read_text(encoding="utf-8").split())
    return set()


def save_seen(ids: set):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text("\n".join(sorted(ids)), encoding="utf-8")


def search_url(sub: str, query: str, sort: str, tf: str) -> str:
    q = urllib.parse.quote(query)
    return (f"https://old.reddit.com/r/{sub}/search?q={q}"
            f"&restrict_sr=1&sort={sort}&t={tf}&include_over_18=on")


def build_plan(mode: str, subs, queries):
    plan = []
    if mode in ("intent", "both"):
        s = subs or INTENT_SUBS
        qs = queries or INTENT_QUERIES
        plan += [("intent", sub, q) for q in qs for sub in s]
    if mode in ("category", "both"):
        s = subs or CATEGORY_SUBS
        qs = queries or CATEGORY_QUERIES
        plan += [("category", sub, q) for q in qs for sub in s]
    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["intent", "category", "both"], default="intent")
    ap.add_argument("--subs", nargs="+", default=None)
    ap.add_argument("--queries", nargs="+", default=None)
    ap.add_argument("--sort", default="new")
    ap.add_argument("--time-filter", default="month")
    ap.add_argument("--max-queries", type=int, default=8, help="本轮最多跑几个 (sub,query) 组合，防限流")
    ap.add_argument("--interval", type=float, default=8.0, help="每次搜索间隔秒（07-19 实测 2.5s 连搜约6次被限流）")
    ap.add_argument("--no-dedup", action="store_true", help="不按 seen-ids 跳过（默认跳过已采帖）")
    args = ap.parse_args()

    if not ensure_proxy():
        log("CDP proxy 未就绪（需会话内 Chrome+proxy 活着）。退出。")
        return 2

    plan = build_plan(args.mode, args.subs, args.queries)[: args.max_queries]
    seen = set() if args.no_dedup else load_seen()
    log(f"计划 {len(plan)} 个 (sub,query) 组合，间隔 {args.interval}s，已 seen {len(seen)} 帖")

    records, new_ids, throttled = [], set(), False
    with Tab() as tab:
        for i, (axis, sub, query) in enumerate(plan):
            nav(tab, search_url(sub, query, args.sort, args.time_filter))
            try:
                rows = json.loads(tab.eval(SEARCH_SCAN_JS) or "[]")
            except Exception as e:
                log(f"r/{sub} q={query!r} 解析失败: {e}")
                rows = []
            if not rows and i > 0:
                log(f"r/{sub} q={query!r} 返回 0（可能被限流，提前收尾）")
                throttled = True
                break
            fresh = 0
            for r in rows:
                rid = r.get("id")
                if not rid or (rid in seen) or (rid in new_ids):
                    continue
                r["axis"], r["matched_sub"], r["matched_query"] = axis, sub, query
                records.append(r)
                new_ids.add(rid)
                fresh += 1
            log(f"r/{sub} q={query!r}: {len(rows)} 命中 / {fresh} 新")
            if i < len(plan) - 1:
                time.sleep(args.interval)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    out = OUT_DIR / f"collect_{args.mode}_{date}.json"
    payload = {
        "date": date, "mode": args.mode, "sort": args.sort, "time_filter": args.time_filter,
        "planned": len(plan), "throttled": throttled,
        "new_records": len(records), "records": records,
    }
    # 同日多次触发：合并而非覆盖
    if out.exists():
        try:
            prev = json.loads(out.read_text(encoding="utf-8"))
            have = {r["id"] for r in prev.get("records", [])}
            payload["records"] = prev.get("records", []) + [r for r in records if r["id"] not in have]
            payload["new_records"] = len(payload["records"])
        except Exception:
            pass
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    if not args.no_dedup:
        save_seen(seen | new_ids)

    log(f"完成：新增 {len(records)} 帖 → {out.name}"
        f"{'（疑被限流提前收尾，剩余组合下次触发续跑）' if throttled else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
