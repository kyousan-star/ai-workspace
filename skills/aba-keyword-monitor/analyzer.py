"""Tier + burst + Sorftime enrichment (generic version)"""
import logging
from dataclasses import dataclass, field
from typing import Optional
import config

logger = logging.getLogger(__name__)

@dataclass
class TrendData:
    keyword: str
    tier: int
    current_rank: int
    previous_rank: Optional[int]
    rank_change: int
    category: str
    combo_label: str
    zh_name: str = ""
    monthly_volumes: list = field(default_factory=list)
    cpc_history: list = field(default_factory=list)
    burst_type: str = "unknown"
    historical_peak_rank: Optional[int] = None
    volume_mom_change: Optional[float] = None
    extended_keywords: list = field(default_factory=list)

def assign_tier(current_rank, rank_change, previous_rank=None):
    prev = previous_rank or (current_rank + rank_change)
    if current_rank <= config.TIER1_RANK_THRESHOLD:
        if rank_change >= config.TIER1_SURGE_ABS:
            return 1
        if prev > 0 and rank_change / prev >= config.TIER1_SURGE_RATIO:
            return 1
    if current_rank <= config.TIER2_RANK_THRESHOLD:
        if prev >= config.TIER2_CROSS_FROM and current_rank <= config.TIER2_CROSS_TO:
            return 2
        if rank_change >= 1000:
            return 2
    if current_rank > config.TIER2_RANK_THRESHOLD:
        if prev >= config.TIER3_CROSS_FROM and current_rank <= config.TIER3_CROSS_TO:
            return 3
        if rank_change >= 5000:
            return 3
    if rank_change > 0:
        if current_rank <= config.TIER1_RANK_THRESHOLD:
            return 1
        if current_rank <= config.TIER2_RANK_THRESHOLD:
            return 2
        return 3
    return 3

def determine_burst_type(monthly_volumes, volume_mom=None):
    if not monthly_volumes:
        return "unknown", None
    ranks = []
    for m in monthly_volumes:
        r = m.get("rank") or m.get("searchRank")
        if r and r > 0:
            ranks.append(r)
    if not ranks:
        return "unknown", None
    peak = min(ranks)
    if volume_mom is not None and volume_mom < -0.3:
        return "declining", peak
    if peak <= config.REBOUND_PEAK_THRESHOLD and len(ranks) > 3:
        pi = ranks.index(peak)
        if pi < len(ranks) - 2:
            return "rebound", peak
    if peak <= 1000:
        if len(ranks) >= 3 and ranks[-1] < ranks[-2] < ranks[-3]:
            return "steady_rise", peak
        return "rebound", peak
    if len(ranks) >= 3 and ranks[-1] < ranks[-2] < ranks[-3]:
        return "steady_rise", peak
    return "first_burst", peak

def determine_burst_with_root(kw, mvols, vmom, t1kws):
    bt, pk = determine_burst_type(mvols, vmom)
    kl = kw.lower()
    for rk in t1kws:
        rl = rk.lower()
        if rl != kl and rl in kl and len(rl) >= 3:
            if bt == "first_burst":
                return "long_tail_expansion", pk
            break
    return bt, pk

def calc_volume_mom(mvols):
    vs = [m.get("searchVolume") or m.get("volume", 0) for m in mvols]
    vs = [v for v in vs if v and v > 0]
    if len(vs) >= 2 and vs[-2] > 0:
        return (vs[-1] - vs[-2]) / vs[-2]
    return None

def enrich_with_sorftime(td, kw_data, t1kws=None):
    t1kws = t1kws or []
    if "trend" in kw_data and isinstance(kw_data["trend"], list):
        td.monthly_volumes = kw_data["trend"]
        td.volume_mom_change = calc_volume_mom(td.monthly_volumes)
        td.burst_type, td.historical_peak_rank = determine_burst_with_root(
            td.keyword, td.monthly_volumes, td.volume_mom_change, t1kws)
    if "detail" in kw_data:
        d = kw_data["detail"]
        td.cpc_history = d if isinstance(d, list) else [d]
    if "extends" in kw_data and isinstance(kw_data["extends"], list):
        td.extended_keywords = kw_data["extends"][:10]

def analyze_keywords_basic(entries, classifications, translations=None):
    results = []
    translations = translations or {}
    for entry in entries:
        kw = entry["keyword"]
        if kw not in classifications:
            continue
        tier = assign_tier(entry["current_rank"], entry["rank_change"], entry.get("previous_rank"))
        td = TrendData(
            keyword=kw, tier=tier, current_rank=entry["current_rank"],
            previous_rank=entry.get("previous_rank"), rank_change=entry["rank_change"],
            category=classifications[kw], combo_label=entry["combo_label"],
            zh_name=translations.get(kw, ""))
        results.append(td)
    results.sort(key=lambda x: (x.tier, -x.rank_change))
    t1 = sum(1 for r in results if r.tier == 1)
    t2 = sum(1 for r in results if r.tier == 2)
    t3 = sum(1 for r in results if r.tier == 3)
    logger.info(f"Tiered: {len(results)}, T1={t1}, T2={t2}, T3={t3}")
    return results

def apply_sorftime_results(results, sf_data):
    t1kws = [r.keyword for r in results if r.tier == 1]
    n = 0
    for td in results:
        if td.tier <= 2 and td.keyword in sf_data:
            enrich_with_sorftime(td, sf_data[td.keyword], t1kws)
            n += 1
    logger.info(f"Enriched: {n} keywords")
    return results
