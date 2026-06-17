"""
sorftime_keyword_intel.py
直连 Sorftime MCP SSE 协议，查询关键词竞争格局，交叉比对监控 ASIN，推送飞书周报。
不依赖 Claude CLI，纯 Python + requests 实现。
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests

# ─── 配置 ───────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
ASINS_FILE = SCRIPT_DIR / "asins.txt"
OWN_ASINS_FILE = SCRIPT_DIR / "own_asins.txt"  # 填写自己品牌的 ASIN，一行一个

SORFTIME_KEY = "a2ngm2ruztlecldntdfnrhhretlqzz09"
SORFTIME_ENDPOINT = f"https://mcp.sorftime.com/?key={SORFTIME_KEY}"

# 每个关键词拉几页自然位（每页 20 条）→ 总覆盖 Top N
SEARCH_RESULT_PAGES = 3  # Top 60，足以覆盖大部分有效排名

KEYWORDS = [
    {"keyword": "tripod for iphone",        "group": "ST102"},
    {"keyword": "selfie stick for iphone",  "group": "ST102"},
    {"keyword": "vlogging kit for iphone",  "group": "VK101"},
    {"keyword": "vlogging kit",             "group": "VK101"},
]

FEISHU_WEBHOOK = os.getenv(
    "RUFUS_FEISHU_WEBHOOK_URL",
    "https://open.feishu.cn/open-apis/bot/v2/hook/20e06d51-6ac0-4e78-8229-0dd3abd581b3"
)

RUN_DATE = datetime.now().strftime("%Y-%m-%d %H:%M")
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d")


# ─── Sorftime MCP 客户端（Streamable HTTP 模式）────────────────────────────
# Sorftime 用的是 streamable HTTP：POST 发 JSON-RPC，响应以 SSE event 格式返回。
# 不需要保持长连接，每次 call_tool 是独立的 HTTP POST。

def call_sorftime_tool(name: str, arguments: dict, timeout: float = 45.0):
    """直接 POST 调用 Sorftime MCP 工具，解析 SSE 格式响应。"""
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    try:
        resp = requests.post(
            SORFTIME_ENDPOINT,
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"    ⚠ {name} 请求失败: {e}")
        return None

    # 解析 SSE 格式：找 data: 行
    data_str = None
    for line in resp.text.splitlines():
        if line.startswith("data:"):
            data_str = line[5:].strip()
            break

    if not data_str:
        print(f"    ⚠ {name} 响应无 data 行")
        return None

    try:
        msg = json.loads(data_str)
    except json.JSONDecodeError as e:
        print(f"    ⚠ {name} 响应 JSON 解析失败: {e}")
        return None

    if msg.get("result", {}).get("isError"):
        print(f"    ⚠ {name} 返回错误: {msg['result'].get('content', '')}")
        return None

    contents = msg.get("result", {}).get("content", [])
    if contents and contents[0].get("type") == "text":
        raw_text = contents[0]["text"]
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            return {"_raw": raw_text}
    return None


# ─── ASIN 文件读取 ───────────────────────────────────────────────────────────

def load_asins(path: Path) -> set[str]:
    if not path.exists():
        return set()
    asins = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        asin = re.sub(r"[^A-Z0-9]", "", line.upper())
        if asin:
            asins.add(asin)
    return asins


# ─── 数据查询 ────────────────────────────────────────────────────────────────

def fetch_keyword_data(kw_config: dict) -> dict:
    """查单个关键词：detail + 多页 search_results，返回汇总结果。"""
    keyword = kw_config["keyword"]
    print(f"\n  [{keyword}]")

    # 1. keyword_detail
    detail = call_sorftime_tool(
        "keyword_detail",
        {"keyword": keyword, "keywordSupportSite": "US"},
    ) or {}
    time.sleep(1)

    # 2. keyword_search_results（多页）
    products: list[dict] = []
    for page in range(1, SEARCH_RESULT_PAGES + 1):
        page_data = call_sorftime_tool(
            "keyword_search_results",
            {"keyword": keyword, "keywordSupportSite": "US", "page": page, "positionType": 1},
        )
        if not page_data or not isinstance(page_data, list):
            break
        for rank_offset, item in enumerate(page_data):
            products.append({
                "asin": item.get("ASIN", ""),
                "rank": (page - 1) * 20 + rank_offset + 1,
                "title": item.get("标题", ""),
                "price": round((item.get("价格", 0) or 0) / 100, 2),
                "monthly_sales": item.get("本产品月销量", 0) or 0,
                "brand": item.get("品牌", ""),
                "seller": item.get("卖家", ""),
            })
        print(f"    第{page}页: {len(page_data)} 条")
        time.sleep(1.5)

    # 解析 detail 字段
    weekly = 0
    monthly = 0
    cpc = 0.0
    competition = ""
    raw_weekly = detail.get("周搜索量", "0")
    raw_monthly = detail.get("月搜索量", "0")
    raw_cpc = detail.get("推荐cpc竞价", "0")
    raw_comp = detail.get("搜索结果竞品数量", "")
    try:
        weekly = int(str(raw_weekly).replace(",", "").replace("K", "000").split(".")[0])
    except Exception:
        pass
    try:
        monthly = int(str(raw_monthly).replace(",", "").replace("K", "000").split(".")[0])
    except Exception:
        pass
    try:
        cpc = float(str(raw_cpc).replace("$", "").strip())
    except Exception:
        pass
    competition = str(raw_comp)

    return {
        "keyword": keyword,
        "group": kw_config["group"],
        "weekly_search": weekly,
        "monthly_search": monthly,
        "cpc": cpc,
        "competition": competition,
        "products": products,   # 按自然位排序
    }


# ─── 交叉比对 ────────────────────────────────────────────────────────────────

def cross_check(kw_data: dict, monitored: set[str], own: set[str]) -> dict:
    """检查哪些监控 ASIN / 自有 ASIN 出现在自然位排名中。"""
    monitored_hits = []
    own_hits = []
    for p in kw_data["products"]:
        asin = p["asin"]
        if asin in own:
            own_hits.append(p)
        elif asin in monitored:
            monitored_hits.append(p)
    return {"own": own_hits, "monitored": monitored_hits}


# ─── 飞书推送 ────────────────────────────────────────────────────────────────

def build_feishu_card(results: list[dict], hits: list[dict], own: set[str], monitored: set[str]) -> dict:
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**查询时间：** {RUN_DATE}　　**关键词数：** {len(results)}　　**总覆盖自然位：** Top {SEARCH_RESULT_PAGES * 20}"
            }
        },
        {"tag": "hr"},
    ]

    for kw_data, hit in zip(results, hits):
        keyword = kw_data["keyword"]
        group = kw_data["group"]
        weekly = kw_data["weekly_search"]
        monthly = kw_data["monthly_search"]
        cpc = kw_data["cpc"]
        products = kw_data["products"]
        own_hits = hit["own"]
        monitored_hits = hit["monitored"]

        lines = [f"**🔑 {keyword}**　`{group}`"]
        lines.append(
            f"周搜：**{weekly:,}** | 月搜：**{monthly:,}** | CPC：**${cpc:.2f}** | 竞品数：{kw_data['competition']}"
        )

        # 自有 ASIN
        if own_hits:
            lines.append("**✅ 我的 ASIN 在自然位：**")
            for p in own_hits:
                lines.append(
                    f"- **#{p['rank']}** {p['asin']}　月销 {p['monthly_sales']:,}　${p['price']:.2f}"
                )
        elif own:
            lines.append("⚠️ **我的 ASIN 未进入 Top %d 自然位**" % (SEARCH_RESULT_PAGES * 20))

        # 监控竞品出现在排名中
        if monitored_hits:
            lines.append("**📌 监控竞品自然位：**")
            for p in monitored_hits[:5]:
                lines.append(
                    f"- #{p['rank']} {p['asin']} ({p['brand']})　月销 {p['monthly_sales']:,}"
                )
            if len(monitored_hits) > 5:
                lines.append(f"- …共 {len(monitored_hits)} 个监控竞品上榜")

        # Top3
        if products:
            lines.append("**Top 3 自然位：**")
            for p in products[:3]:
                lines.append(
                    f"- #{p['rank']} {p['asin']} ({p['brand']})　月销 {p['monthly_sales']:,}　${p['price']:.2f}"
                )

        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "\n".join(lines)}
        })
        elements.append({"tag": "hr"})

    # 尾注
    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": f"Sorftime 关键词情报 | {RUN_TIMESTAMP} | 自然位 Top {SEARCH_RESULT_PAGES * 20}"}]
    })

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "📈 关键词竞争情报周报"},
                "template": "green"
            },
            "elements": elements,
        }
    }


def send_feishu(payload: dict):
    try:
        resp = requests.post(
            FEISHU_WEBHOOK,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload, ensure_ascii=False),
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            print("\n✅ 飞书关键词情报已发送")
        else:
            print(f"\n⚠ 飞书返回: {result}")
    except Exception as e:
        print(f"\n✗ 飞书推送失败: {e}")


# ─── 本地 JSON 存档 ──────────────────────────────────────────────────────────

def save_archive(results: list[dict], hits: list[dict]):
    out_dir = SCRIPT_DIR / "raw"
    out_dir.mkdir(exist_ok=True)
    archive = {
        "run_date": RUN_DATE,
        "keywords": [
            {
                "keyword": r["keyword"],
                "group": r["group"],
                "weekly_search": r["weekly_search"],
                "monthly_search": r["monthly_search"],
                "cpc": r["cpc"],
                "products": r["products"],
                "own_hits": h["own"],
                "monitored_hits": h["monitored"],
            }
            for r, h in zip(results, hits)
        ]
    }
    out_path = out_dir / f"sorftime_keyword_intel_{RUN_TIMESTAMP}.json"
    out_path.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 存档已保存: {out_path}")


# ─── 主流程 ─────────────────────────────────────────────────────────────────

def main():
    print("─── Sorftime 关键词情报 ──────────────────────────────")

    monitored = load_asins(ASINS_FILE)
    own = load_asins(OWN_ASINS_FILE)
    print(f"监控 ASIN：{len(monitored)} 个　自有 ASIN：{len(own)} 个")
    if not own:
        print("  ⚠ own_asins.txt 为空，将只显示监控竞品排名（不显示自有 ASIN 入池状态）")

    results: list[dict] = []
    hits: list[dict] = []

    for kw_config in KEYWORDS:
        kw_data = fetch_keyword_data(kw_config)
        hit = cross_check(kw_data, monitored, own)
        results.append(kw_data)
        hits.append(hit)

    # 保存存档
    save_archive(results, hits)

    # 推送飞书
    payload = build_feishu_card(results, hits, own, monitored)
    send_feishu(payload)

    print("\n✅ Sorftime 情报任务完成")


if __name__ == "__main__":
    main()
