"""Sorftime 异步并发查询客户端"""
import asyncio
import json
import logging
import re
import httpx
import config

logger = logging.getLogger(__name__)

async def _sorftime_call(client, method, arguments):
    try:
        resp = await client.post(
            config.SORFTIME_BASE_URL, params={"key": config.SORFTIME_API_KEY},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                  "params": {"name": method, "arguments": arguments}},
            timeout=config.SORFTIME_TIMEOUT)
        resp.raise_for_status()
        result = None
        for line in resp.text.split("\n"):
            line = line.strip()
            if line.startswith("data: "):
                try:
                    payload = json.loads(line[6:])
                    if "result" in payload:
                        result = payload["result"]
                except json.JSONDecodeError:
                    continue
        return result
    except Exception as e:
        logger.debug(f"Sorftime {method} error: {e}")
        return None

def parse_response(raw):
    if not raw:
        return []
    try:
        text_data = None
        if isinstance(raw, dict) and "content" in raw:
            c = raw["content"]
            if isinstance(c, list) and c:
                text_data = c[0].get("text", "")
        elif isinstance(raw, str):
            text_data = raw
        if not text_data:
            return []
        jm = re.search(r'\{[\s\S]*\}', text_data)
        if not jm:
            return []
        parsed = json.loads(jm.group())
        if not isinstance(parsed, dict):
            return parsed if isinstance(parsed, list) else []
        vols = parsed.get("搜索量趋势", [])
        rnks = parsed.get("搜索排名趋势", [])
        cpcs = parsed.get("推荐竞价趋势", [])
        if not vols and not rnks:
            return parsed.get("data", []) if "data" in parsed else []
        md = {}
        for item in vols:
            m = re.match(r'(\d{4})年(\d{2})月搜索量(-?\d+\.?\d*)', str(item))
            if m:
                mo = f"{m.group(1)}-{m.group(2)}"
                md.setdefault(mo, {})["searchVolume"] = int(float(m.group(3)))
                md[mo]["month"] = mo
        for item in rnks:
            m = re.match(r'(\d{4})年(\d{2})月搜索排名(-?\d+\.?\d*)', str(item))
            if m:
                mo = f"{m.group(1)}-{m.group(2)}"
                md.setdefault(mo, {})["searchRank"] = int(float(m.group(3)))
                md[mo]["month"] = mo
        for item in cpcs:
            m = re.match(r'(\d{4})年(\d{2})月cpc推荐竞价(-?\d+\.?\d*)', str(item))
            if m:
                mo = f"{m.group(1)}-{m.group(2)}"
                md.setdefault(mo, {})["cpc"] = float(m.group(3))
                md[mo]["month"] = mo
        return sorted(md.values(), key=lambda x: x.get("month", ""))
    except Exception:
        return []

def parse_extends(raw):
    if not raw:
        return []
    try:
        text_data = None
        if isinstance(raw, dict) and "content" in raw:
            c = raw["content"]
            if isinstance(c, list) and c:
                text_data = c[0].get("text", "")
        elif isinstance(raw, str):
            text_data = raw
        if not text_data:
            return []
        import ast
        arr = re.search(r'\[[\s\S]*\]', text_data)
        if arr:
            try:
                inner = json.loads(arr.group())
            except json.JSONDecodeError:
                try:
                    inner = ast.literal_eval(arr.group())
                except Exception:
                    inner = []
            if isinstance(inner, list):
                return [i for i in inner[:10] if isinstance(i, dict)]
    except Exception:
        pass
    return []

async def query_full(client, kw, sem):
    async with sem:
        t, d, e = await asyncio.gather(
            _sorftime_call(client, "keyword_trend", {"amzSite": "US", "searchKeyword": kw}),
            _sorftime_call(client, "keyword_detail", {"amzSite": "US", "keyword": kw}),
            _sorftime_call(client, "keyword_extends", {"amzSite": "US", "searchKeyword": kw}))
    r = {}
    if t: r["trend"] = parse_response(t)
    if d:
        p = parse_response(d)
        r["detail"] = p[0] if p else d
    r["extends"] = parse_extends(e)
    return kw, r

async def query_trend(client, kw, sem):
    async with sem:
        t = await _sorftime_call(client, "keyword_trend", {"amzSite": "US", "searchKeyword": kw})
    r = {}
    if t: r["trend"] = parse_response(t)
    return kw, r

async def batch_query(tier1_kws, tier2_kws):
    sem = asyncio.Semaphore(config.SORFTIME_CONCURRENCY)
    results = {}
    async with httpx.AsyncClient(verify=config.VERIFY_SSL) as client:
        tasks = [query_full(client, kw, sem) for kw in tier1_kws]
        tasks += [query_trend(client, kw, sem) for kw in tier2_kws]
        for coro in asyncio.as_completed(tasks):
            kw, data = await coro
            if data:
                results[kw] = data
                logger.info(f"  ok {kw}")
    return results

def query_sorftime_batch(tier1_kws, tier2_kws):
    total = len(tier1_kws) * 3 + len(tier2_kws)
    logger.info(f"Sorftime: Tier1={len(tier1_kws)}x3 + Tier2={len(tier2_kws)}x1 = {total} calls")
    data = asyncio.run(batch_query(tier1_kws, tier2_kws))
    stats = {"tier1_keywords": len(tier1_kws), "tier2_keywords": len(tier2_kws),
             "total_calls": total, "enriched": len(data)}
    return data, stats
