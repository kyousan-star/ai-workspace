#!/usr/bin/env python3
"""Vlogara Pinterest 周检哨兵 — 每周日随卖家脉搏晨报运行（其余日期直接跳过）。

维护模式口径：Pinterest 官方 analytics 信号极弱（30 天 1 次展示），不值得日检。
本哨兵只做公开面数据：
1. 从 claude/pinterest-assets/*/publish_results.json + 历史 pinterest_pin_metrics_*.csv
   汇总全部已发布 pin URL（自增量，新 campaign 发布后自动纳入）
   并排除 data/pinterest_paused_assets.csv 中处于私密隔离的 pin
2. CDP 逐个开公开 pin 页，从内嵌 JSON 抽 saves/done 数，检测 pin 是否被删/404
3. 写 pinterest_pin_metrics_{date}.csv（沿用既有 schema），与上一次扫描对比出 delta
4. 总 saves 和 top pin 回填 daily_metrics.csv 当日行（public saves 口径，非官方流量）
5. 产出 data/pinterest_sentinel_feishu.txt 并入卖家脉搏（仅周日有当日文件）

强制运行：PINTEREST_FORCE=1 环境变量（测试用）。
"""

import csv
import glob
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # growth-monitor/
VLOGARA_DIR = BASE_DIR.parent.parent                        # Vlogara logo&站外&shopify/
DATA_DIR = BASE_DIR / "data"
FEISHU_TXT = DATA_DIR / "pinterest_sentinel_feishu.txt"
DAILY_CSV = DATA_DIR / "daily_metrics.csv"
PAUSED_ASSETS_CSV = DATA_DIR / "pinterest_paused_assets.csv"

PROXY = "http://localhost:3456"
TODAY = os.environ.get("BRIEF_DATE", date.today().strftime("%Y-%m-%d"))
PAGE_INTERVAL_SEC = 2.5

METRICS_FIELDS = ["date", "asset_id", "pin_title", "content_group", "status", "pin_url",
                  "landing_page", "utm_content", "impressions", "outbound_clicks", "saves",
                  "repin_count", "comment_count", "done_count", "created_at",
                  "metrics_source", "analytics_limitation", "scrape_status"]


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] pinterest_sentinel: {msg}")


def proxy_get(path):
    with urllib.request.urlopen(f"{PROXY}{path}", timeout=45) as r:
        return json.loads(r.read().decode())


def proxy_eval(target, js):
    req = urllib.request.Request(f"{PROXY}/eval?target={target}", data=js.encode(), method="POST")
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode()).get("value")


def collect_pin_registry():
    """asset_id -> {pin_url, pin_title, content_group, landing_page, utm_content}"""
    reg = {}
    # 历史指标 CSV（带标题/分组等元数据）
    for f in sorted(glob.glob(str(DATA_DIR / "pinterest_pin_metrics_*.csv"))):
        for row in csv.DictReader(open(f, encoding="utf-8")):
            url = (row.get("pin_url") or "").strip()
            if url:
                reg[row["asset_id"]] = {k: row.get(k, "") for k in
                                        ("pin_url", "pin_title", "content_group", "landing_page", "utm_content")}
    # publish_results.json（dict 或 list 两种形态）
    for f in glob.glob(str(VLOGARA_DIR / "claude/pinterest-assets/*/publish_results.json")):
        d = json.load(open(f, encoding="utf-8"))
        items = d.items() if isinstance(d, dict) else [(x.get("asset_id"), x) for x in d]
        for aid, info in items:
            url = (info.get("pin_url") or "").strip()
            if aid and url and aid not in reg:
                reg[aid] = {"pin_url": url, "pin_title": info.get("title", ""),
                            "content_group": "", "landing_page": "", "utm_content": aid}
    return reg


def paused_asset_ids():
    if not PAUSED_ASSETS_CSV.exists():
        return set()
    with open(PAUSED_ASSETS_CSV, encoding="utf-8", newline="") as handle:
        return {
            row["asset_id"]
            for row in csv.DictReader(handle)
            if (row.get("status") or "").startswith("paused")
        }


SCRAPE_JS = r"""
(() => {
  if (document.title.match(/Page not found|找不到/i)) return JSON.stringify({gone: true});
  const html = document.documentElement.innerHTML;
  const m = html.match(/"aggregated_stats"\s*:\s*\{\s*"saves"\s*:\s*(\d+)\s*,\s*"done"\s*:\s*(\d+)/);
  const cm = html.match(/"comment_count"\s*:\s*(\d+)/);
  const rm = html.match(/"repin_count"\s*:\s*(\d+)/);
  const gone = !!document.body.innerText.match(/isn't available|不存在|been removed/i) && !m;
  return JSON.stringify({
    gone,
    saves: m ? parseInt(m[1]) : null,
    done: m ? parseInt(m[2]) : null,
    comments: cm ? parseInt(cm[1]) : null,
    repins: rm ? parseInt(rm[1]) : null
  });
})()
"""


def prev_saves():
    """上一次扫描各 pin 的 saves，用于 delta"""
    files = sorted(glob.glob(str(DATA_DIR / "pinterest_pin_metrics_*.csv")))
    out = {}
    for f in files:  # 后面的覆盖前面的 → 最新值
        for row in csv.DictReader(open(f, encoding="utf-8")):
            if (row.get("pin_url") or "").strip() and (row.get("saves") or "").strip().isdigit():
                out[row["asset_id"]] = int(row["saves"])
    return out


def upsert_daily(total_saves, top_pin):
    rows = list(csv.DictReader(open(DAILY_CSV, encoding="utf-8")))
    by_date = {r["date"]: r for r in rows}
    rec = by_date.get(TODAY)
    if rec is None:
        rec = {k: "" for k in rows[0].keys()}
        rec["date"] = TODAY
        rec["notes"] = "Pinterest 周检哨兵回填（public saves 口径）"
        rows.append(rec)
    rec["pinterest_saves"] = str(total_saves)
    rec["pinterest_top_pin"] = top_pin
    rows.sort(key=lambda r: r["date"])
    with open(DAILY_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def main():
    is_sunday = datetime.strptime(TODAY, "%Y-%m-%d").weekday() == 6
    if not is_sunday and os.environ.get("PINTEREST_FORCE") != "1":
        log("非周日，跳过（PINTEREST_FORCE=1 可强制）")
        return

    paused = paused_asset_ids()
    reg = {aid: meta for aid, meta in collect_pin_registry().items() if aid not in paused}
    if not reg:
        FEISHU_TXT.write_text(f"DATE:{TODAY}\nPinterest 周检：未找到已发布 pin 清单\n", encoding="utf-8")
        return
    baseline = prev_saves()

    target = proxy_get("/new?url=about:blank")["targetId"]
    results, alerts = [], []
    try:
        for aid, meta in sorted(reg.items()):
            proxy_get(f"/navigate?target={target}&url={urllib.parse.quote(meta['pin_url'], safe=':/?&=')}")
            time.sleep(PAGE_INTERVAL_SEC)
            try:
                info = json.loads(proxy_eval(target, SCRAPE_JS) or "{}")
            except (TypeError, json.JSONDecodeError):
                info = {}
            gone = info.get("gone", False)
            saves = info.get("saves")
            if gone:
                alerts.append(f"🚨 pin 疑似被删：{aid}")
            elif saves is not None:
                old = baseline.get(aid)
                if old is not None and saves > old:
                    alerts.append(f"📈 {aid} saves {old}→{saves}")
            results.append({
                "date": TODAY, "asset_id": aid, "pin_title": meta.get("pin_title", ""),
                "content_group": meta.get("content_group", ""),
                "status": "gone" if gone else "posted",
                "pin_url": meta["pin_url"], "landing_page": meta.get("landing_page", ""),
                "utm_content": meta.get("utm_content", ""),
                "impressions": "", "outbound_clicks": "",
                "saves": "" if saves is None else saves,
                "repin_count": "" if info.get("repins") is None else info["repins"],
                "comment_count": "" if info.get("comments") is None else info["comments"],
                "done_count": "" if info.get("done") is None else info["done"],
                "created_at": "", "metrics_source": "pin_page_public_dom",
                "analytics_limitation": "public saves only; official impressions/outbound not collected by sentinel",
                "scrape_status": "ok" if (gone or saves is not None) else "parse_failed",
            })
    finally:
        proxy_get(f"/close?target={target}")

    out = DATA_DIR / f"pinterest_pin_metrics_{TODAY}.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
        w.writeheader()
        w.writerows(results)

    scanned = [r for r in results if r["scrape_status"] == "ok" and r["status"] == "posted"]
    total_saves = sum(int(r["saves"]) for r in scanned if str(r["saves"]).isdigit())
    top = max((r for r in scanned if str(r["saves"]).isdigit()), key=lambda r: int(r["saves"]), default=None)
    upsert_daily(total_saves, top["pin_title"] or top["asset_id"] if top else "")

    lines = [
        f"Pinterest 周检：{len(scanned)}/{len(reg)} pin 存活，公开 saves 合计 {total_saves}"
        "（当前基线主要为发布时自存，仅证 Pin 存活，非自然互动指标）"
        f"；另有 {len(paused)} 条 VT101 pin 处于私密隔离，未扫描"
    ]
    lines += [f"  {a}" for a in alerts[:6]]
    if not alerts:
        lines[0] += "，无异动"
    FEISHU_TXT.write_text(f"DATE:{TODAY}\n" + "\n".join(lines) + "\n", encoding="utf-8")
    log(f"完成：{len(scanned)}/{len(reg)} 存活，saves 合计 {total_saves}，告警 {len(alerts)}")


if __name__ == "__main__":
    main()
