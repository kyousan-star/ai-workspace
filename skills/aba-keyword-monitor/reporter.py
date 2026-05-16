"""HTML 报告生成器（通用版，类目名动态化）"""
import os
import logging
from datetime import datetime
from dataclasses import asdict

from jinja2 import Environment, FileSystemLoader

import config
from analyzer import TrendData

logger = logging.getLogger(__name__)


def generate_report(results, total_scraped, total_supplement, new_dict_words,
                    analysis=None, excluded_keywords=None, sorftime_stats=None):
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    analysis = analysis or {}
    excluded_keywords = excluded_keywords or {}
    sorftime_stats = sorftime_stats or {}
    category_name = config.get_category_name()
    category_name_en = config.get_category_name_en()

    tier1 = [r for r in results if r.tier == 1]
    tier2 = [r for r in results if r.tier == 2]
    tier3 = [r for r in results if r.tier == 3]
    now = datetime.now()

    keyword_analysis = analysis.get("keyword_analysis", {})
    tracks = analysis.get("tracks", [])
    core_findings = analysis.get("core_findings", [])

    context = {
        "category_name": category_name,
        "category_name_en": category_name_en,
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
        "week_label": f"{now.year} 第 {now.isocalendar()[1]} 周",
        "week_code": f"W{now.isocalendar()[1]:02d}",
        "total_scraped": total_scraped,
        "total_category": total_supplement,
        "tier1_count": len(tier1),
        "tier2_count": len(tier2),
        "tier3_count": len(tier3),
        "tier1": [_enrich(r, keyword_analysis) for r in tier1],
        "tier2": [_enrich(r, keyword_analysis) for r in tier2],
        "tier3": [_enrich(r, keyword_analysis) for r in tier3],
        "tracks": tracks,
        "core_findings": core_findings,
        "new_words": new_dict_words,
        "total_new_words": sum(len(v) for v in new_dict_words.values()),
        "excluded_keywords": excluded_keywords,
        "excluded_count": len(excluded_keywords),
        "sorftime_stats": sorftime_stats,
    }
    env = Environment(loader=FileSystemLoader(config.TEMPLATE_DIR), autoescape=True)
    template = env.get_template("report.html")
    html = template.render(**context)

    week_str = f"{now.year}-W{now.isocalendar()[1]:02d}"
    ts = now.strftime("%Y%m%d%H%M%S")
    filename = f"{category_name_en}_monitor_{week_str}-{ts}.html"
    filepath = os.path.join(config.REPORT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"报告已生成: {filepath}")
    return filepath


def _enrich(td, keyword_analysis=None):
    d = asdict(td)
    keyword_analysis = keyword_analysis or {}
    burst_map = {
        "first_burst": ("\U0001f195 首次爆发", "burst-first"),
        "rebound": ("\U0001f504 回弹", "burst-rebound"),
        "steady_rise": ("\U0001f4c8 持续爆发", "burst-steady"),
        "declining": ("\U0001f4c9 下跌中", "burst-decline"),
        "long_tail_expansion": ("\U0001f331 长尾扩展", "burst-longtail"),
        "unknown": ("\u2753 未知", ""),
    }
    label, css = burst_map.get(td.burst_type, ("\u2753 未知", ""))
    d["burst_type_label"] = label
    d["burst_type_css"] = css
    cat_map = {
        "ingredient": ("\U0001f9ea 核心产品/成分", "cat-ingredient"),
        "benefit": ("\U0001f4aa 功效/用途", "cat-benefit"),
        "brand": ("\U0001f3f7\ufe0f 品牌", "cat-brand"),
        "condition": ("\U0001fa7a 场景/症状", "cat-condition"),
        "form": ("\U0001f48a 形态/规格", "cat-form"),
    }
    cat_label, cat_css = cat_map.get(td.category, (td.category, ""))
    d["category_label"] = cat_label
    d["category_css"] = cat_css
    d["zh_name"] = td.zh_name or ""
    d["analysis_text"] = keyword_analysis.get(td.keyword, "")
    if td.previous_rank and td.previous_rank > 0:
        real_change = td.previous_rank - td.current_rank
        d["rank_direction"] = "up" if real_change > 0 else "down"
        d["rank_change_display"] = f"+{real_change:,}" if real_change > 0 else f"{real_change:,}"
        d["rank_change_abs"] = abs(real_change)
    else:
        d["rank_direction"] = "new"
        d["rank_change_display"] = "NEW"
        d["rank_change_abs"] = 0
    vols = [(m.get("searchVolume") or m.get("volume", 0)) for m in (td.monthly_volumes or [])
            if (m.get("searchVolume") or m.get("volume", 0)) > 0]
    d["latest_volume"] = vols[-1] if vols else 0
    d["peak_volume"] = max(vols) if vols else 0
    cpc_val = None
    for m in reversed(td.monthly_volumes or []):
        if isinstance(m, dict) and m.get("cpc") and float(m["cpc"]) > 0:
            cpc_val = float(m["cpc"])
            break
    if not cpc_val and td.cpc_history:
        for c in reversed(td.cpc_history):
            if isinstance(c, dict):
                v = c.get("cpc") or c.get("bid")
                if v and float(v) > 0:
                    cpc_val = float(v)
                    break
    d["cpc"] = f"${cpc_val:.2f}" if cpc_val else "N/A"
    d["mom_pct"] = f"{td.volume_mom_change * 100:+.0f}%" if td.volume_mom_change is not None else "N/A"
    d["sparkline_data"] = [
        m.get("searchVolume") or m.get("volume", 0)
        for m in (td.monthly_volumes or [])[-12:]
    ]
    return d
