#!/usr/bin/env python3
"""
supply_signal.py — 供给侧时序信号生成器（blue-ocean-finder 的红海预警闸门）

把 New Releases 榜单监控盘（seen_asins.json + 每日榜单 xlsx）固化成
"形态 × 月度上新 × 幸存率 × 品牌上新矩阵"的供给侧信号，供 blue-ocean-finder
在 P2(竞争验证)/P4(可行性快筛) 与 Sorftime 需求侧数据对撞：

  - Sorftime = 需求侧（搜索量 / 增速），判"有没有人要"
  - 本脚本  = 供给侧时序（日均新品数 / 幸存率 / 品牌铺货），判"缝隙是真空还是正在被填"

价格不在此处理：榜单价格列已失效，价格一律以 blue-ocean-finder 跑流程时
用 Sorftime 现抓为准（product_detail / keyword_search_results）。

用法：
    python3 supply_signal.py --data-dir "<监控文件夹>" [--form "关键词1,关键词2"] [--json out.json]

  --data-dir  含 seen_asins.json 和 *榜单*.xlsx 的目录（必填）
  --form      只统计标题命中这些关键词(逗号分隔, 大小写不敏感)的 ASIN；
              不传则输出全部内置形态词典
  --window    近 N 天视为"新上新"用于日均计算(默认 30)
  --json      额外把结构化信号写到该 JSON 路径

设计沿用 keyword_growth_scanner 的分工：数据由本地文件供给，脚本只做计算，
不调 MCP、不联网。
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime

# ── 内置形态词典（贴合手机内容创作装备；--form 可覆盖）──
FORM_LEXICON = {
    "selfie_monitor 后摄监视屏": r"selfie monitor|monitor screen|rear (camera )?screen|back camera monitor|vlog monitor",
    "face_tracking 自动追踪": r"face tracking|auto track|ai track|follow(ing)? track|gesture",
    "auto_open 秒开": r"auto[- ]?open|auto pop|pop[- ]?open|one[- ]?touch|1s open|0\.\d+s",
    "invisible_pole 隐形长杆": r"invisible|3m|9\.8ft|118in|carbon fiber",
    "magnetic 磁吸": r"magnet|magsafe",
    "tripod 三脚架": r"tripod",
    "selfie_stick 自拍杆": r"selfie stick",
    "light 补光": r"\blight\b|led|ring light|fill light",
    "microphone 麦克风": r"micro?phone|lavalier|\bmic\b|wireless mic",
    "gimbal 云台": r"gimbal|stabiliz",
    "kit 套装": r"\bkit\b|bundle|essentials|starter",
    "overhead 俯拍位": r"overhead|desk clamp|tabletop|table top|boom arm",
    "action_cam 生态": r"insta360|osmo|gopro|dji|action cam",
    "creator 定位词": r"content creator|vlog|creator|tiktok|youtube",
}

RED, YELLOW = 15, 8  # 月上新阈值：>RED 红海 / YELLOW-RED 拥挤 / <YELLOW 尚有空间


def load_data(data_dir):
    seen_path = os.path.join(data_dir, "seen_asins.json")
    if not os.path.exists(seen_path):
        sys.exit(f"找不到 {seen_path}")
    seen = json.load(open(seen_path, encoding="utf-8"))

    xlsxs = glob.glob(os.path.join(data_dir, "*.xlsx"))
    dated = []
    for p in xlsxs:
        m = re.search(r"(\d{8})", os.path.basename(p))
        if m:
            dated.append((m.group(1), p))
    if not dated:
        sys.exit(f"{data_dir} 下找不到带日期的榜单 xlsx")
    latest_tag, latest_path = max(dated)
    return seen, latest_tag, latest_path


def read_live_asins(xlsx_path):
    """读最新榜单 xlsx，返回今日仍在榜的 ASIN 集合。"""
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    live = set()
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        hdr_i = next((i for i, r in enumerate(rows) if r and r[0] == "排名"), None)
        if hdr_i is None:
            continue
        hdr = rows[hdr_i]
        try:
            ai = hdr.index("ASIN")
        except ValueError:
            continue
        for r in rows[hdr_i + 1:]:
            if r and len(r) > ai and r[ai]:
                live.add(str(r[ai]).strip())
    wb.close()
    return live


def month_key(d):
    return d[:7]


def analyze_form(seen, live, name, pattern, since_month, window_days, today):
    hits = [(a, v) for a, v in seen.items() if re.search(pattern, v.get("title", ""), re.I)]
    # 排除首日初始化灌入（first_seen == 最早日期）会污染"上新速度"，用 since_month 起算
    fresh = [(a, v) for a, v in hits if month_key(v["first_seen"]) >= since_month]
    if not fresh:
        return None

    by_month = Counter(month_key(v["first_seen"]) for _, v in fresh)
    survivors = [(a, v) for a, v in fresh if a in live]
    survival = len(survivors) / len(fresh) if fresh else 0

    # 近 window_days 日均上新
    recent = [v for _, v in fresh
              if (today - datetime.strptime(v["first_seen"], "%Y-%m-%d").date()).days <= window_days]
    per_day = len(recent) / window_days
    per_month = per_day * 30

    if per_month > RED:
        heat = "🔴红海(灌满中)"
    elif per_month >= YELLOW:
        heat = "🟡拥挤"
    else:
        heat = "🟢尚有空间"

    return {
        "form": name,
        "total_new": len(fresh),
        "by_month": dict(sorted(by_month.items())),
        "survivors_live": len(survivors),
        "survival_rate": round(survival, 3),
        f"per_month_last{window_days}d": round(per_month, 1),
        "heat": heat,
    }


def brand_matrix(seen, since_month, top_n=12):
    brands = ["ULANZI", "UBeesize", "K&F CONCEPT", "TELESIN", "Kaitezenz", "Insta360",
              "Moman", "SYNCO", "Gisotu", "Vlogara", "JOBY", "NEEWER", "Tilta", "MOFT",
              "VRIG", "ORICO", "USKEYVISION", "Belkin", "XILETU", "DJI", "Hohem", "APEXEL",
              "SmallRig", "Ulanzi", "UGREEN", "Aureday", "Sensyne", "ATUMTEK"]
    cnt = defaultdict(list)
    for a, v in seen.items():
        if month_key(v["first_seen"]) < since_month:
            continue
        t = v.get("title", "").upper()
        for b in brands:
            if b.upper() in t:
                cnt[b].append((v["first_seen"], v.get("category", "")[:14], v.get("title", "")[:52]))
                break
    ranked = sorted(((b, items) for b, items in cnt.items() if len(items) >= 3),
                    key=lambda x: -len(x[1]))
    return ranked[:top_n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--form", default="")
    ap.add_argument("--window", type=int, default=30)
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    seen, latest_tag, latest_path = load_data(args.data_dir)
    live = read_live_asins(latest_path)
    today = date.today()

    # 起算月 = 排除最早月(首日灌入存量), 取第二早的月份
    months = sorted({month_key(v["first_seen"]) for v in seen.values()})
    since_month = months[1] if len(months) > 1 else months[0]

    if args.form.strip():
        forms = {kw.strip(): re.escape(kw.strip()) for kw in args.form.split(",") if kw.strip()}
    else:
        forms = FORM_LEXICON

    results = []
    for name, pat in forms.items():
        r = analyze_form(seen, live, name, pat, since_month, args.window, today)
        if r:
            results.append(r)
    results.sort(key=lambda x: -x[f"per_month_last{args.window}d"])

    # ── 报告 ──
    print(f"# 供给侧信号 · {os.path.basename(args.data_dir)}")
    print(f"最新榜单: {latest_tag}  |  今日在榜 ASIN: {len(live)}  |  "
          f"累计追踪: {len(seen)}  |  起算月(排除首日灌入): {since_month}\n")
    print(f"红海速度阈值: 月上新 >{RED}=🔴 / {YELLOW}-{RED}=🟡 / <{YELLOW}=🟢  "
          f"(近{args.window}天日均折算)\n")

    hdr = f"{'形态':<26}{'红海':<14}{'月上新':>7}{'累计':>6}{'幸存率':>8}{'月度上新':>0}"
    print(hdr)
    print("-" * 78)
    for r in results:
        pm = r[f"per_month_last{args.window}d"]
        trend = " ".join(f"{m[-2:]}:{n}" for m, n in r["by_month"].items())
        print(f"{r['form']:<26}{r['heat']:<14}{pm:>7}{r['total_new']:>6}"
              f"{r['survival_rate']*100:>6.0f}%  {trend}")

    print("\n## 品牌上新矩阵（起算月以来 ≥3 款）")
    for b, items in brand_matrix(seen, since_month):
        cats = Counter(c for _, c, _ in items)
        catstr = ",".join(f"{c}×{n}" for c, n in cats.most_common(3))
        print(f"  {b:<16} {len(items):>2}款  [{catstr}]")

    print("\n## 用法提示")
    print("  - 🔴形态: 缝隙已被灌满, blue-ocean P4 应降级/毙掉该方向的对应 spec")
    print("  - 🟢+高幸存率形态: 优先送 zach-product-research 深挖")
    print("  - 幸存率本身 = Go/No-Go 里'新品生存概率'的实证参数")
    print("  - 价格: 榜单价格列已失效, 一律用 Sorftime 现抓")

    if args.json:
        out = {"latest": latest_tag, "live_count": len(live), "tracked": len(seen),
               "since_month": since_month, "forms": results,
               "brands": {b: len(items) for b, items in brand_matrix(seen, since_month)}}
        json.dump(out, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\n结构化信号已写入 {args.json}")


if __name__ == "__main__":
    main()
