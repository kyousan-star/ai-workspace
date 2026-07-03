#!/usr/bin/env python3
"""
Amazon PPC 广告数据解析引擎 v2 (US站)
功能: 解析广告后台导出的CSV/XLSX → 清洗 → 分层 → 矩阵诊断 → 竞价建议 → 动作日志(PDCA闭环)

用法:
  python ad_data_parser.py <input_file> --margin 0.35 --price 44.99 --phase launch
参数:
  --margin 0.35        毛利率(=盈亏ACOS)。必须传产品真实值，缺省用config默认并告警
  --price 44.99        客单价，传入后输出每个词的具体建议竞价
  --phase launch|growth|stable  生命周期阶段，决定否词门槛和ACOS容忍度(默认stable)
  --core-terms "a,b"   核心保护词根(逗号分隔)，含这些词根的搜索词永不进入否定候选
  --attribution 7|14   销售额归因窗口，默认7(SP报表口径)
  --actions-log <path> PDCA动作日志JSON路径(默认与输入文件同目录 ad_actions_log.json)
  --no-actions-log     禁用动作日志
  --output <path>      输出Excel路径
"""

import pandas as pd
import numpy as np
import sys
import os
import json
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "..", "ppc_config.json")
RULES_PATH = os.path.join(SCRIPT_DIR, "..", "references", "diagnosis_rules.json")

# 兜底配置(ppc_config.json 缺失时使用)
FALLBACK_CONFIG = {
    "margin_default": 0.35,
    "phases": {
        "launch": {"negation_min_clicks": 20, "negation_max_spend_x_be_cpa": 3.0,
                   "acos_tolerance_multiplier": 2.0, "observe_max_clicks": 10, "scale_up_min_orders": 1},
        "growth": {"negation_min_clicks": 15, "negation_max_spend_x_be_cpa": 2.0,
                   "acos_tolerance_multiplier": 1.5, "observe_max_clicks": 8, "scale_up_min_orders": 2},
        "stable": {"negation_min_clicks": 10, "negation_max_spend_x_be_cpa": 1.5,
                   "acos_tolerance_multiplier": 1.0, "observe_max_clicks": 5, "scale_up_min_orders": 2},
    },
    "impression_thresholds_kw": {"low": 500, "mid": 5000},
    "impression_thresholds_asin": {"low": 200, "mid": 2000},
    "click_thresholds": {"low": 5, "mid": 20},
    "ctr_thresholds": {"low": 0.002, "mid": 0.005},
    "cvr_thresholds": {"low": 0.05, "mid": 0.15},
    "acos_multipliers": {"excellent": 0.5, "good": 1.0, "high": 1.5},
    "bid_calc": {"cvr_smoothing_k": 10,
                 "phase_bid_multiplier": {"launch": 1.3, "growth": 1.1, "stable": 1.0},
                 "max_bid_change_pct": 0.5},
}

SCALE_UP_NAMES = ["黄金词", "优质词", "潜力词", "蓝海长尾词", "小宝藏", "待放量词", "放大候选词", "准黄金词"]


def load_json(path, fallback=None, label=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[✓] 已加载{label}: {os.path.normpath(path)}")
        return data
    except Exception as e:
        if fallback is not None:
            print(f"[!] {label}加载失败({e})，使用内置兜底")
            return fallback
        raise


CONFIG = load_json(CONFIG_PATH, FALLBACK_CONFIG, "共享配置")
RULES = load_json(RULES_PATH, {}, "诊断规则")

# ============================================================
# 字段映射：exact优先，归因窗口显式选择，防撞名
# ============================================================
FIELD_MAPPING = {
    "impressions": ["impressions", "曝光量", "展现次数", "impression", "展示次数"],
    "clicks": ["clicks", "点击量", "点击次数", "click"],
    "spend": ["spend", "花费", "cost", "广告花费", "费用", "total spend"],
    "search_term": ["customer search term", "搜索词", "search term", "客户搜索词"],
    "targeting": ["targeting", "投放", "投放对象", "keyword or product targeting"],
    "match_type": ["match type", "匹配类型", "match_type"],
    "campaign": ["campaign name", "广告活动", "campaign", "广告活动名称"],
    "ad_group": ["ad group name", "广告组", "ad group", "广告组名称"],
    "asin": ["advertised asin", "推广的asin", "advertised_asin"],
    "placement": ["placement", "广告位", "展示位置"],
    "acos": ["total advertising cost of sales (acos)", "acos", "广告投入产出比"],
    "cpc": ["cost per click (cpc)", "cpc", "每次点击费用", "平均每次点击费用"],
}

# 归因窗口相关字段单独处理
SALES_ALIASES = {
    7: ["7 day total sales", "7 day total sales ($)", "7天总销售额"],
    14: ["14 day total sales", "14 day total sales ($)", "14天总销售额"],
    0: ["sales", "销售额", "广告销售额", "total sales"],
}
ORDERS_ALIASES = {
    7: ["7 day total orders (#)", "7 day total orders", "7天总订单量", "7天总订单数(#)"],
    14: ["14 day total orders (#)", "14 day total orders", "14天总订单量"],
    0: ["orders", "订单量", "广告订单量", "total orders"],
}


def detect_and_read_file(filepath):
    """自动检测文件格式并读取"""
    ext = os.path.splitext(filepath)[1].lower()

    if ext in ['.csv', '.tsv', '.txt']:
        for encoding in ['utf-8-sig', 'utf-8', 'gbk', 'gb18030', 'latin1']:
            for sep in [',', '\t', ';']:
                try:
                    df = pd.read_csv(filepath, encoding=encoding, sep=sep, nrows=5)
                    if len(df.columns) > 1:
                        df = pd.read_csv(filepath, encoding=encoding, sep=sep)
                        print(f"[✓] 文件读取成功: {encoding} | 分隔符: {repr(sep)} | {len(df)}行 × {len(df.columns)}列")
                        return df
                except Exception:
                    continue
        raise ValueError(f"无法读取文件: {filepath}")

    elif ext in ['.xlsx', '.xls', '.xlsm']:
        df = pd.read_excel(filepath)
        print(f"[✓] Excel文件读取成功: {len(df)}行 × {len(df.columns)}列")
        return df

    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def _match_alias(columns, aliases, used_cols):
    """先精确匹配再子串匹配，返回命中的原始列名"""
    for alias in aliases:
        a = alias.lower().strip()
        for col in columns:
            if col in used_cols:
                continue
            if col == a:
                return col
    for alias in aliases:
        a = alias.lower().strip()
        for col in columns:
            if col in used_cols:
                continue
            if a in col:
                return col
    return None


def normalize_columns(df, attribution=7):
    """标准化列名。exact优先防撞名；sales/orders按归因窗口显式选择。"""
    df.columns = [str(c).strip().lower() for c in df.columns]
    columns = list(df.columns)
    col_map = {}
    used_cols = set()

    # 销售额/订单：优先指定归因窗口，其次另一窗口，最后通用名
    windows = [attribution, 14 if attribution == 7 else 7, 0]
    for std_name, alias_dict in [("sales", SALES_ALIASES), ("orders", ORDERS_ALIASES)]:
        for w in windows:
            hit = _match_alias(columns, alias_dict[w], used_cols)
            if hit:
                col_map[hit] = std_name
                used_cols.add(hit)
                if w not in (attribution, 0):
                    print(f"[!] 归因窗口注意: {std_name} 使用了{w}天口径列'{hit}'，与要求的{attribution}天不一致")
                break

    for std_name, aliases in FIELD_MAPPING.items():
        if std_name in col_map.values():
            continue
        hit = _match_alias(columns, aliases, used_cols)
        if hit:
            col_map[hit] = std_name
            used_cols.add(hit)

    df = df.rename(columns=col_map)
    # 撞名检测
    dup = df.columns[df.columns.duplicated()].tolist()
    if dup:
        print(f"[!] 警告: 检测到重复列名 {dup}，保留首列")
        df = df.loc[:, ~df.columns.duplicated()]

    print(f"[✓] 字段映射完成: {sorted(set(col_map.values()))}")
    return df


def clean_data(df):
    """数据清洗"""
    initial_rows = len(df)

    for col in ['spend', 'sales', 'cpc', 'acos']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[$€£¥%,]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    for col in ['impressions', 'clicks', 'orders']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    df = df.dropna(how='all')

    if 'acos' in df.columns:
        mask = df['acos'] > 1
        df.loc[mask, 'acos'] = df.loc[mask, 'acos'] / 100

    print(f"[✓] 数据清洗完成: {initial_rows}行 → {len(df)}行")
    return df


def calculate_derived_metrics(df):
    """计算衍生指标"""
    if 'impressions' in df.columns and 'clicks' in df.columns:
        df['ctr'] = np.where(df['impressions'] > 0, df['clicks'] / df['impressions'], 0)
    if 'clicks' in df.columns and 'orders' in df.columns:
        df['cvr'] = np.where(df['clicks'] > 0, df['orders'] / df['clicks'], 0)
    if 'clicks' in df.columns and 'spend' in df.columns:
        df['cpc_calc'] = np.where(df['clicks'] > 0, df['spend'] / df['clicks'], 0)
    if 'spend' in df.columns and 'sales' in df.columns:
        df['acos_calc'] = np.where(df['sales'] > 0, df['spend'] / df['sales'], np.inf)
    if 'spend' in df.columns and 'orders' in df.columns:
        df['cpa'] = np.where(df['orders'] > 0, df['spend'] / df['orders'], np.inf)
    if 'sales' in df.columns and 'spend' in df.columns:
        df['roas'] = np.where(df['spend'] > 0, df['sales'] / df['spend'], 0)
    print("[✓] 衍生指标计算完成: CTR/CVR/CPC/ACOS/CPA/ROAS")
    return df


# ============================================================
# 分层
# ============================================================
def classify_impressions(val, is_asin=False):
    t = CONFIG["impression_thresholds_asin"] if is_asin else CONFIG["impression_thresholds_kw"]
    if val == 0:
        return "无曝光"
    elif val <= t["low"]:
        return "低曝光"
    elif val <= t["mid"]:
        return "中曝光"
    return "高曝光"


def classify_clicks(val):
    t = CONFIG["click_thresholds"]
    if val == 0:
        return "无点击"
    elif val <= t["low"]:
        return "低点击"
    elif val <= t["mid"]:
        return "中点击"
    return "高点击"


def classify_ctr(val):
    t = CONFIG["ctr_thresholds"]
    if val < t["low"]:
        return "低CTR"
    elif val < t["mid"]:
        return "中CTR"
    return "高CTR"


def classify_cvr(val):
    t = CONFIG["cvr_thresholds"]
    if val == 0:
        return "0转化"
    elif val < t["low"]:
        return "低转化"
    elif val < t["mid"]:
        return "中转化"
    return "高转化"


def classify_acos(val, break_even):
    m = CONFIG["acos_multipliers"]
    if val == 0 or val == np.inf:
        return "无数据"
    elif val < break_even * m["excellent"]:
        return "极佳"
    elif val <= break_even * m["good"]:
        return "良好"
    elif val <= break_even * m["high"]:
        return "偏高"
    return "过高"


def apply_classification(df, break_even_acos):
    is_asin_col = False
    if 'targeting' in df.columns:
        is_asin_col = df['targeting'].astype(str).str.match(r'^[Bb]0[A-Za-z0-9]{8}$', na=False).any()

    if 'impressions' in df.columns:
        df['曝光分层'] = df['impressions'].apply(lambda x: classify_impressions(x, is_asin_col))
    if 'clicks' in df.columns:
        df['点击分层'] = df['clicks'].apply(classify_clicks)
    if 'ctr' in df.columns:
        df['CTR分层'] = df['ctr'].apply(classify_ctr)
    if 'cvr' in df.columns:
        df['转化分层'] = df['cvr'].apply(classify_cvr)
    if 'acos_calc' in df.columns:
        df['ACOS分层'] = df['acos_calc'].apply(lambda x: classify_acos(x, break_even_acos))

    print("[✓] 指标分层完成")
    return df


# ============================================================
# 诊断（规则来自 references/diagnosis_rules.json）
# ============================================================
def diagnose_row(row, phase_cfg, be_cpa, core_terms):
    clicks = row.get('clicks', 0)
    impressions = row.get('impressions', 0)
    spend = row.get('spend', 0.0)
    term = str(row.get('search_term', row.get('targeting', ''))).lower()

    st_rules = RULES.get("search_term_rules", {})
    zc_rules = RULES.get("zero_conversion_rules", {})
    ni_rule = RULES.get("no_impression_rule")

    # 无曝光
    if impressions == 0 and ni_rule:
        rule = ni_rule
    # 0转化
    elif row.get('转化分层') == '0转化':
        t = CONFIG["click_thresholds"]
        if clicks > t["mid"]:
            rule = zc_rules.get("高点击_0转化")
        elif clicks > t["low"]:
            rule = zc_rules.get("中点击_0转化")
        else:
            rule = zc_rules.get("低点击_0转化")
    else:
        key = f"{row.get('曝光分层', '')}_{row.get('CTR分层', '')}_{row.get('转化分层', '')}"
        rule = st_rules.get(key)

    if rule:
        result = {
            "诊断等级": rule["level"], "诊断名称": rule["name"],
            "问题分析": rule["problem"], "广告目的": rule["purpose"],
            "广告策略": rule["action"], "预期结果": rule["result"],
        }
    else:
        result = {
            "诊断等级": "📊", "诊断名称": "标准",
            "问题分析": "各指标表现中等", "广告目的": "全面优化提升",
            "广告策略": "根据具体数据调整竞价/否词/Listing", "预期结果": "有提升空间",
        }

    # 否定判定（相位感知 + 保护词）
    is_protected = any(ct in term for ct in core_terms) if core_terms and term else False
    negation = ""
    if row.get('转化分层') == '0转化' and clicks > 0:
        hit_clicks = clicks >= phase_cfg["negation_min_clicks"]
        hit_spend = be_cpa is not None and spend >= phase_cfg["negation_max_spend_x_be_cpa"] * be_cpa
        if is_protected:
            negation = "🛡️保护词-禁止否定(先查Listing/价格/竞品)"
        elif hit_clicks or hit_spend:
            reason = []
            if hit_clicks:
                reason.append(f"点击{clicks}≥{phase_cfg['negation_min_clicks']}")
            if hit_spend:
                reason.append(f"花费${spend:.2f}≥{phase_cfg['negation_max_spend_x_be_cpa']}×盈亏CPA")
            negation = "❌否定候选(" + "，".join(reason) + ")"
        elif clicks <= phase_cfg["observe_max_clicks"]:
            negation = "⏸️数据不足-观察"
        else:
            negation = "👀接近门槛-下轮复查"
    result["否定判定"] = negation
    return result


# ============================================================
# 竞价建议
# ============================================================
def suggest_bids(df, margin, price, phase):
    """建议竞价 = 盈亏ACOS × 客单价 × 平滑CVR × phase系数，调价幅度限±max_change"""
    bc = CONFIG["bid_calc"]
    k = bc["cvr_smoothing_k"]
    phase_mult = bc["phase_bid_multiplier"].get(phase, 1.0)
    max_change = bc["max_bid_change_pct"]

    total_clicks = df['clicks'].sum() if 'clicks' in df.columns else 0
    total_orders = df['orders'].sum() if 'orders' in df.columns else 0
    overall_cvr = total_orders / total_clicks if total_clicks > 0 else 0.05

    def calc(row):
        clicks = row.get('clicks', 0)
        orders = row.get('orders', 0)
        cvr_smoothed = (orders + k * overall_cvr) / (clicks + k)
        raw_bid = margin * price * cvr_smoothed * phase_mult
        cur_cpc = row.get('cpc_calc', 0)
        if cur_cpc > 0:
            lo, hi = cur_cpc * (1 - max_change), cur_cpc * (1 + max_change)
            bid = min(max(raw_bid, lo), hi)
            delta = (bid - cur_cpc) / cur_cpc * 100
            direction = f"{'+' if delta >= 0 else ''}{delta:.0f}%"
        else:
            bid = raw_bid
            direction = "新投放参考价"
        return pd.Series({"建议竞价": round(bid, 2), "调价方向": direction,
                          "平滑CVR": round(cvr_smoothed, 4)})

    bid_df = df.apply(calc, axis=1)
    df = pd.concat([df, bid_df], axis=1)
    print(f"[✓] 竞价建议完成: 整体CVR={overall_cvr*100:.1f}% | 公式=毛利率×客单价×平滑CVR×{phase_mult}(phase系数)")
    return df


# ============================================================
# PDCA 动作日志
# ============================================================
def load_actions_log(path):
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] 动作日志读取失败: {e}")
    return {"runs": []}


def verify_previous_actions(log, df):
    """核验上一轮动作在本期数据中的效果"""
    if not log["runs"]:
        return pd.DataFrame()
    prev = log["runs"][-1]
    term_col = 'search_term' if 'search_term' in df.columns else ('targeting' if 'targeting' in df.columns else None)
    if term_col is None:
        return pd.DataFrame()

    cur = df.set_index(df[term_col].astype(str).str.lower())
    rows = []
    for act in prev.get("actions", []):
        t = str(act["term"]).lower()
        if t in cur.index:
            c = cur.loc[t]
            if isinstance(c, pd.DataFrame):
                c = c.iloc[0]
            cur_spend, cur_orders = float(c.get('spend', 0)), int(c.get('orders', 0))
            if act["action"] == "精准否定":
                verdict = "❌否定未执行或未生效(仍有花费)" if cur_spend > 0 else "✅已止血"
            else:
                d_orders = cur_orders - act.get("orders", 0)
                verdict = f"✅订单+{d_orders}" if d_orders > 0 else ("➖订单持平" if d_orders == 0 else f"⚠️订单{d_orders}")
            rows.append({"词": act["term"], "上期动作": act["action"],
                         "上期花费": act.get("spend"), "本期花费": cur_spend,
                         "上期订单": act.get("orders"), "本期订单": cur_orders,
                         "核验结论": verdict})
        else:
            verdict = "✅已消失(否定生效)" if act["action"] == "精准否定" else "⚠️本期无数据"
            rows.append({"词": act["term"], "上期动作": act["action"],
                         "上期花费": act.get("spend"), "本期花费": 0,
                         "上期订单": act.get("orders"), "本期订单": 0,
                         "核验结论": verdict})
    return pd.DataFrame(rows)


def append_actions(log, df, phase, input_file):
    """把本轮推荐动作写入日志，供下轮核验"""
    term_col = 'search_term' if 'search_term' in df.columns else ('targeting' if 'targeting' in df.columns else None)
    if term_col is None:
        return log, 0
    actions = []
    for _, row in df.iterrows():
        entry = {"term": str(row[term_col]), "clicks": int(row.get('clicks', 0)),
                 "spend": round(float(row.get('spend', 0)), 2), "orders": int(row.get('orders', 0))}
        if str(row.get('否定判定', '')).startswith('❌'):
            entry["action"] = "精准否定"
            actions.append(entry)
        elif row.get('诊断名称') in SCALE_UP_NAMES:
            entry["action"] = "放大投放"
            if "建议竞价" in row.index and pd.notna(row.get("建议竞价")):
                entry["suggested_bid"] = float(row["建议竞价"])
            actions.append(entry)
    log["runs"].append({"date": datetime.now().strftime("%Y-%m-%d"),
                        "file": os.path.basename(input_file),
                        "phase": phase, "actions": actions})
    return log, len(actions)


# ============================================================
# 汇总
# ============================================================
def generate_summary(df, margin, phase):
    s = {
        "总行数": len(df),
        "总花费": float(df.get('spend', pd.Series(dtype=float)).sum()),
        "总销售额": float(df.get('sales', pd.Series(dtype=float)).sum()),
        "总点击": int(df.get('clicks', pd.Series(dtype=int)).sum()),
        "总曝光": int(df.get('impressions', pd.Series(dtype=int)).sum()),
        "总订单": int(df.get('orders', pd.Series(dtype=int)).sum()),
    }
    m = {
        "盈亏ACOS(=毛利率)": f"{margin*100:.0f}%",
        "生命周期阶段": phase,
        "整体ACOS": f"{s['总花费']/s['总销售额']*100:.1f}%" if s['总销售额'] > 0 else "N/A",
        "整体CTR": f"{s['总点击']/s['总曝光']*100:.2f}%" if s['总曝光'] > 0 else "N/A",
        "整体CVR": f"{s['总订单']/s['总点击']*100:.1f}%" if s['总点击'] > 0 else "N/A",
        "平均CPC": f"${s['总花费']/s['总点击']:.2f}" if s['总点击'] > 0 else "N/A",
        "平均CPA": f"${s['总花费']/s['总订单']:.2f}" if s['总订单'] > 0 else "N/A",
        "ROAS": f"{s['总销售额']/s['总花费']:.2f}x" if s['总花费'] > 0 else "N/A",
    }
    if s['总销售额'] > 0 and s['总花费'] > 0:
        acos = s['总花费'] / s['总销售额']
        tol = CONFIG["phases"][phase]["acos_tolerance_multiplier"]
        if acos <= margin:
            m["盈亏状态"] = "✅盈利(ACOS低于盈亏线)"
        elif acos <= margin * tol:
            m["盈亏状态"] = f"⚠️{phase}期容忍范围内(盈亏线×{tol}以内)，关注趋势"
        else:
            m["盈亏状态"] = f"🚨超出{phase}期容忍线(盈亏线×{tol})，需立即优化"
    return {"数据概览": s, "整体指标": m}


def main():
    ap = argparse.ArgumentParser(description="Amazon PPC 广告数据解析引擎 v2")
    ap.add_argument("input_file")
    ap.add_argument("--margin", type=float, default=None, help="毛利率=盈亏ACOS，如0.35")
    ap.add_argument("--profit-rate", type=float, default=None, help="(兼容旧参数名)同--margin")
    ap.add_argument("--price", type=float, default=None, help="客单价，用于竞价建议")
    ap.add_argument("--phase", choices=["launch", "growth", "stable"], default="stable")
    ap.add_argument("--core-terms", default="", help="核心保护词根，逗号分隔")
    ap.add_argument("--attribution", type=int, choices=[7, 14], default=7)
    ap.add_argument("--actions-log", default=None)
    ap.add_argument("--no-actions-log", action="store_true")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    margin = args.margin if args.margin is not None else args.profit_rate
    if margin is None:
        margin = CONFIG.get("margin_default", 0.35)
        print(f"[!] 警告: 未传 --margin，使用配置默认 {margin*100:.0f}%。请传产品真实毛利率，否则所有ACOS判断不可信！")
    phase = args.phase
    phase_cfg = CONFIG["phases"][phase]
    core_terms = [t.strip().lower() for t in args.core_terms.split(",") if t.strip()]
    be_cpa = margin * args.price if args.price else None

    output_path = args.output or f"{os.path.splitext(args.input_file)[0]}_分析结果.xlsx"
    actions_log_path = args.actions_log or os.path.join(
        os.path.dirname(os.path.abspath(args.input_file)), "ad_actions_log.json")

    print(f"\n{'='*60}\n  Amazon PPC 广告数据解析引擎 v2 (US站)\n"
          f"  盈亏ACOS: {margin*100:.0f}% | 阶段: {phase} | 归因: {args.attribution}天\n"
          f"  客单价: {'$%.2f' % args.price if args.price else '未提供(跳过竞价建议)'}"
          f" | 保护词: {core_terms if core_terms else '无'}\n{'='*60}\n")

    df = detect_and_read_file(args.input_file)
    df = normalize_columns(df, args.attribution)
    df = clean_data(df)
    df = calculate_derived_metrics(df)
    df = apply_classification(df, margin)

    print("▸ 矩阵诊断...")
    diag = df.apply(lambda r: pd.Series(diagnose_row(r, phase_cfg, be_cpa, core_terms)), axis=1)
    df = pd.concat([df, diag], axis=1)
    print(f"[✓] 诊断完成: {len(df)}条")

    if args.price:
        df = suggest_bids(df, margin, args.price, phase)

    # PDCA: 核验上轮 + 记录本轮
    verify_df = pd.DataFrame()
    if not args.no_actions_log:
        log = load_actions_log(actions_log_path)
        verify_df = verify_previous_actions(log, df)
        if not verify_df.empty:
            print(f"[✓] 上期动作核验: {len(verify_df)}条 (详见Excel'上期动作核验'sheet)")
        log, n_actions = append_actions(log, df, phase, args.input_file)
        with open(actions_log_path, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=1)
        print(f"[✓] 本轮{n_actions}条推荐动作已写入日志: {actions_log_path}")

    summary = generate_summary(df, margin, phase)

    # 输出Excel
    neg_df = df[df['否定判定'].astype(str).str.startswith('❌')] if '否定判定' in df.columns else pd.DataFrame()
    scale_df = df[df['诊断名称'].isin(SCALE_UP_NAMES)] if '诊断名称' in df.columns else pd.DataFrame()

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='完整分析数据', index=False)
        if not neg_df.empty:
            neg_df.to_excel(writer, sheet_name='否定候选', index=False)
        if not scale_df.empty:
            scale_df.to_excel(writer, sheet_name='放大候选', index=False)
        if not verify_df.empty:
            verify_df.to_excel(writer, sheet_name='上期动作核验', index=False)
        summary_df = pd.DataFrame([{"指标": k, "数值": v}
                                   for sec in [summary["数据概览"], summary["整体指标"]]
                                   for k, v in sec.items()])
        summary_df.to_excel(writer, sheet_name='数据概览', index=False)

    print(f"\n{'='*60}\n  分析完成! Excel报告: {output_path}\n{'='*60}")
    for k, v in summary["整体指标"].items():
        print(f"  {k}: {v}")
    if '诊断名称' in df.columns:
        print("\n  诊断分布:")
        for name, count in df['诊断名称'].value_counts().items():
            print(f"    {name}: {count}个")
    if not neg_df.empty or not scale_df.empty:
        print(f"\n  ❌ 否定候选 {len(neg_df)}个 | ⭐ 放大候选 {len(scale_df)}个")


if __name__ == "__main__":
    main()
