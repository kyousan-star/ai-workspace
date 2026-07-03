#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键词增速扫描器 —— blue-ocean-finder 的核心引擎(缝隙签名·段1 需求侧打分)

定位：把"手动拉几个词靠感觉"变成"批量算 YoY/量/CPC → 排序 → 吐在涨的缝隙词"。
工程现实：Sorftime MCP 只能 LLM 交互调，标准脚本调不了。所以本脚本只做**打分**——
  数据(keyword_trend 原始返回)由 LLM 用 MCP 拉好、存成 JSON，喂给本脚本算分排序。

输入：JSON 文件 = keyword_trend 原始返回的列表（MCP 直接返回的 dict 数组）
输出：按缝隙段1分排序的表 + scored CSV

打分(0-10，需求增速权重最高，呼应'增速驱动'原则)：
  growth(50%): YoY 同比增速     volume(30%): 落在可做量带   cpc(20%): 越低越好
用法：python3 keyword_growth_scanner.py <trends.json>
"""
from __future__ import annotations
import csv, json, re, sys
from pathlib import Path

VOL_RE = re.compile(r"搜索量\s*([\d,]+)")
CPC_RE = re.compile(r"cpc推荐竞价\s*([\d.]+)")

def parse_series(item: dict) -> tuple[list[int], float | None]:
    vols = []
    for s in item.get("搜索量趋势", []):
        m = VOL_RE.search(str(s))
        if m:
            vols.append(int(m.group(1).replace(",", "")))
    cpcs = []
    for s in item.get("推荐竞价趋势", []):
        m = CPC_RE.search(str(s))
        if m:
            try: cpcs.append(float(m.group(1)))
            except ValueError: pass
    cpc = cpcs[-1] if cpcs else None
    return vols, cpc

def yoy(vols: list[int]) -> float | None:
    # 只认真同比：不足13个月不再用首尾比降级（首尾比对新词/噪音词会造出假YoY，
    # 实证：'teleprompter for iphone' 多月为0仍被算出-28%）
    if len(vols) >= 13 and vols[-13] > 0:
        return vols[-1] / vols[-13] - 1
    return None

def data_quality(vols: list[int]) -> list[str]:
    """词级数据守卫：命中任一 → 该词标❓不可评，不进自动排序，转人工验证。"""
    issues = []
    if len(vols) < 13:
        issues.append("月数<13无同比基线")
    zeros = sum(1 for v in vols if v == 0)
    if vols and zeros >= max(2, len(vols) // 4):
        issues.append("多月为0(噪音级)")
    nz = sorted(v for v in vols if v > 0)
    if nz and nz[len(nz) // 2] < 1000:
        issues.append("中位量<1k(噪音级)")
    return issues

def spike_suspect(vols: list[int]) -> bool:
    """垂直起量嫌疑：近3月才有量、此前接近0 → 疑词形迁移(亚马逊搜索入口变化)，
    须拉词族相邻词(父词/同义词)对照总盘是否平移，不能直接当新需求。"""
    if len(vols) >= 5 and vols[-1] >= 3000:
        head = vols[:-3]
        if head and max(head) <= vols[-1] * 0.15:
            return True
    return False

def growth_score(y: float | None) -> float:
    if y is None: return 0.0
    # +80%→10, +30%→8, 0→4, -30%→1
    return max(0.0, min(10.0, 4 + y * 100 / 12.5))

def volume_score(v: int) -> float:
    # 可做量带 3k-80k 最高；过小(niche太小)或过大(多半红海/大词)扣分
    if v < 1000: return 2.0
    if v < 3000: return 5.0
    if v <= 80000: return 10.0
    if v <= 150000: return 6.0
    return 3.0

def cpc_score(c: float | None) -> float:
    if c is None: return 5.0
    if c < 1.0: return 10.0
    if c < 1.5: return 8.0
    if c < 2.0: return 6.0
    return 4.0

def flag(y: float | None) -> str:
    if y is None: return "?"
    if y >= 0.30: return "🟢涨"
    if y >= -0.10: return "⚪平"
    return "🔴跌"

def score_item(item: dict) -> dict:
    vols, cpc = parse_series(item)
    latest = vols[-1] if vols else 0
    y = yoy(vols)
    issues = data_quality(vols)
    spike = spike_suspect(vols)
    g, vsc, csc = growth_score(y), volume_score(latest), cpc_score(cpc)
    total = round(0.5*g + 0.3*vsc + 0.2*csc, 2)
    fl = "❓不可评" if issues else flag(y)
    if spike:
        fl += "|🆕垂直起量→查词族迁移"
    return {
        "关键词": item.get("关键词", ""),
        "最新月搜": latest,
        "YoY": f"{y*100:+.0f}%" if y is not None else "—",
        "CPC": cpc if cpc is not None else "—",
        "flag": fl,
        "缝隙段1分": total,
        "数据质量": "; ".join(issues) if issues else "OK",
        "_g": round(g,1), "_v": round(vsc,1), "_c": round(csc,1),
    }

def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("用法: python3 keyword_growth_scanner.py <trends.json>")
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("results", [])
    rows = [score_item(it) for it in items]
    rows.sort(key=lambda r: r["缝隙段1分"], reverse=True)

    out = Path(sys.argv[1]).with_name("scored_" + Path(sys.argv[1]).stem + ".csv")
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    print(f"扫描 {len(rows)} 个词 → 按缝隙段1分排序：\n")
    print(f"{'词':36s}{'最新月搜':>9s}{'YoY':>7s}{'CPC':>6s}{'段1分':>7s}  标")
    for r in rows:
        print(f"{r['关键词'][:34]:34s}{r['最新月搜']:>9,}{r['YoY']:>7s}{str(r['CPC']):>6s}{r['缝隙段1分']:>7}  {r['flag']}")
    rising = [r for r in rows if r["flag"].startswith("🟢涨") and r["缝隙段1分"] >= 7]
    print(f"\n🟢 在涨且段1分≥7(进段2竞争验证): {len(rising)} 个 → " + ", ".join(r["关键词"] for r in rising[:8]))
    manual = [r for r in rows if "❓" in r["flag"] or "🆕" in r["flag"]]
    if manual:
        print(f"\n❓ 不可自动评/需人工验证 {len(manual)} 个（新词查词族迁移，噪音词直接弃）：")
        for r in manual:
            print(f"   {r['关键词'][:40]:40s} 最新{r['最新月搜']:,}  [{r['数据质量']}]{' 🆕垂直起量' if '🆕' in r['flag'] else ''}")
    print(f"\n输出: {out}")

if __name__ == "__main__":
    main()
