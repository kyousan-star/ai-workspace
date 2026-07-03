#!/usr/bin/env python3
"""
亚马逊SP广告快读分析 (US站)
支持亚马逊广告后台原生导出报表(CSV/XLSX)，字段中英文自动映射。

用法:
  python3 analyze_ads.py --search-terms 搜索词报告.csv --margin 0.35 --phase launch
参数:
  --search-terms <file>        搜索词报告(必传)
  --advertised-product <file>  广告商品报告(可选，算广告整体效率)
  --business <file>            业务报告(可选，算广告流量/订单占比)
  --margin 0.35                毛利率=盈亏ACOS(必传，否则默认0.35并告警)
  --phase launch|growth|stable 生命周期阶段(默认stable)
  --core-terms "a,b"           核心保护词根，永不进入否定候选
"""

import argparse
import os
import sys
import pandas as pd

# 与 amazon-ad-optimizer/ppc_config.json 保持一致的阶段阈值
PHASES = {
    "launch": {"negation_min_clicks": 20, "negation_max_spend_x_be_cpa": 3.0, "scale_up_min_orders": 1},
    "growth": {"negation_min_clicks": 15, "negation_max_spend_x_be_cpa": 2.0, "scale_up_min_orders": 2},
    "stable": {"negation_min_clicks": 10, "negation_max_spend_x_be_cpa": 1.5, "scale_up_min_orders": 2},
}

FIELDS = {
    "impressions": ["impressions", "曝光量", "展示次数", "展现次数"],
    "clicks": ["clicks", "点击量", "点击次数"],
    "spend": ["spend", "花费", "cost"],
    "sales": ["7 day total sales", "7 day total sales ($)", "7天总销售额",
              "14 day total sales", "sales", "销售额"],
    "orders": ["7 day total orders (#)", "7 day total orders", "7天总订单量",
               "14 day total orders (#)", "orders", "订单量"],
    "search_term": ["customer search term", "客户搜索词", "搜索词"],
    "match_type": ["match type", "匹配类型"],
    "campaign": ["campaign name", "广告活动名称", "广告活动"],
    "sessions": ["sessions - total", "sessions", "访客数"],
    "units": ["units ordered", "订单数", "总订单"],
}


def read_any(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.xlsx', '.xls'):
        return pd.read_excel(path)
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'latin1'):
        try:
            df = pd.read_csv(path, encoding=enc)
            if len(df.columns) > 1:
                return df
        except Exception:
            continue
    raise ValueError(f"无法读取: {path}")


def map_columns(df):
    """精确匹配优先，其次子串匹配；每个标准字段只映射一次"""
    df.columns = [str(c).strip().lower() for c in df.columns]
    cols = list(df.columns)
    rename, used = {}, set()
    for std, aliases in FIELDS.items():
        hit = None
        for a in aliases:
            a = a.lower()
            exact = [c for c in cols if c == a and c not in used]
            if exact:
                hit = exact[0]
                break
        if not hit:
            for a in aliases:
                a = a.lower()
                sub = [c for c in cols if a in c and c not in used]
                if sub:
                    hit = sub[0]
                    break
        if hit:
            rename[hit] = std
            used.add(hit)
    df = df.rename(columns=rename)
    df = df.loc[:, ~df.columns.duplicated()]
    for col in ('spend', 'sales'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[$,€£%]', '', regex=True),
                                    errors='coerce').fillna(0.0)
    for col in ('impressions', 'clicks', 'orders', 'sessions', 'units'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df


def line(title):
    print(f"\n{'='*60}\n【{title}】\n{'='*60}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search-terms", required=True)
    ap.add_argument("--advertised-product", default=None)
    ap.add_argument("--business", default=None)
    ap.add_argument("--margin", type=float, default=None)
    ap.add_argument("--phase", choices=list(PHASES), default="stable")
    ap.add_argument("--core-terms", default="")
    ap.add_argument("--price", type=float, default=None, help="客单价，用于盈亏CPA否定门槛")
    args = ap.parse_args()

    margin = args.margin
    if margin is None:
        margin = 0.35
        print("[!] 警告: 未传 --margin，用默认35%。请传产品真实毛利率，否则判断不可信！")
    be_roas = 1 / margin
    be_cpa = margin * args.price if args.price else None
    phase = PHASES[args.phase]
    core_terms = [t.strip().lower() for t in args.core_terms.split(",") if t.strip()]

    print(f"盈亏ACOS: {margin*100:.0f}% | 盈亏ROAS: {be_roas:.2f} | 阶段: {args.phase}"
          f" | 保护词: {core_terms or '无'}")

    # ---------- 搜索词报告 ----------
    st = map_columns(read_any(args.search_terms))
    need = {'search_term', 'clicks', 'spend'}
    if not need.issubset(st.columns):
        print(f"[!] 搜索词报告缺少字段: {need - set(st.columns)}")
        sys.exit(1)

    agg = {'clicks': 'sum', 'spend': 'sum'}
    for c in ('impressions', 'sales', 'orders'):
        if c in st.columns:
            agg[c] = 'sum'
    by_term = st.groupby('search_term').agg(agg).reset_index()
    by_term['roas'] = (by_term['sales'] / by_term['spend']).where(by_term['spend'] > 0, 0) \
        if 'sales' in by_term.columns else 0

    line("整体指标(搜索词口径)")
    t_spend, t_sales = by_term['spend'].sum(), by_term.get('sales', pd.Series([0])).sum()
    t_clicks, t_orders = by_term['clicks'].sum(), by_term.get('orders', pd.Series([0])).sum()
    acos = t_spend / t_sales if t_sales > 0 else float('inf')
    print(f"花费 ${t_spend:,.2f} | 销售 ${t_sales:,.2f} | ACOS {acos*100:.1f}% (盈亏线{margin*100:.0f}%)")
    print(f"点击 {t_clicks:,.0f} | 订单 {t_orders:,.0f} | CVR {t_orders/t_clicks*100:.1f}%" if t_clicks else "无点击")
    if acos <= margin:
        print("状态: ✅ 广告盈利")
    elif acos <= margin * (2.0 if args.phase == 'launch' else 1.5):
        print(f"状态: ⚠️ {args.phase}期容忍范围内，关注周趋势")
    else:
        print("状态: 🚨 超出容忍线，需优化")

    # 匹配类型
    if 'match_type' in st.columns and 'sales' in st.columns:
        line("匹配类型效率")
        mt = st.groupby('match_type').agg({'spend': 'sum', 'sales': 'sum', 'orders': 'sum'})
        mt['ROAS'] = (mt['sales'] / mt['spend']).where(mt['spend'] > 0, 0)
        mt['花费占比%'] = mt['spend'] / mt['spend'].sum() * 100
        print(mt[['花费占比%', 'ROAS', 'orders']].round(2).sort_values('ROAS', ascending=False).to_string())

    # 高效词
    if 'orders' in by_term.columns:
        line(f"高效词 (ROAS≥盈亏ROAS {be_roas:.2f} 且订单≥{phase['scale_up_min_orders']})")
        hi = by_term[(by_term['roas'] >= be_roas) &
                     (by_term['orders'] >= phase['scale_up_min_orders'])].sort_values('roas', ascending=False)
        for _, r in hi.head(15).iterrows():
            print(f"  {str(r['search_term'])[:40]:<42} 订单{r['orders']:>3.0f}  ROAS {r['roas']:.2f}")
        if hi.empty:
            print("  (无。新品期属正常，看词的点击和排名趋势)")

        # 否定候选
        gate_desc = f"点击≥{phase['negation_min_clicks']}" + \
            (f" 或花费≥{phase['negation_max_spend_x_be_cpa']}×盈亏CPA(${phase['negation_max_spend_x_be_cpa']*be_cpa:.2f})" if be_cpa else "")
        line(f"否定候选 ({args.phase}期门槛: 零转化且 {gate_desc})")
        zero = by_term[by_term['orders'] == 0]
        gate = zero['clicks'] >= phase['negation_min_clicks']
        if be_cpa:
            gate = gate | (zero['spend'] >= phase['negation_max_spend_x_be_cpa'] * be_cpa)
        neg = zero[gate].sort_values('spend', ascending=False)
        n_shown = 0
        for _, r in neg.iterrows():
            term = str(r['search_term'])
            if any(ct in term.lower() for ct in core_terms):
                print(f"  🛡️ {term[:40]:<40} 点击{r['clicks']:>3.0f} 花费${r['spend']:>7.2f}  保护词-禁否，查Listing/价格")
            else:
                print(f"  ❌ {term[:40]:<40} 点击{r['clicks']:>3.0f} 花费${r['spend']:>7.2f}")
            n_shown += 1
            if n_shown >= 20:
                break
        if neg.empty:
            print("  (无达标否定候选)")
        near = zero[(~gate) & (zero['clicks'] >= phase['negation_min_clicks'] * 0.5)]
        if not near.empty:
            print(f"  👀 另有{len(near)}个词接近门槛，下轮复查")

    # ---------- 广告商品报告(可选) ----------
    ad_clicks = ad_orders = None
    if args.advertised_product:
        ap_df = map_columns(read_any(args.advertised_product))
        line("广告整体效率(广告商品报告)")
        sp, sa = ap_df.get('spend', pd.Series([0])).sum(), ap_df.get('sales', pd.Series([0])).sum()
        ad_clicks = ap_df.get('clicks', pd.Series([0])).sum()
        ad_orders = ap_df.get('orders', pd.Series([0])).sum()
        print(f"花费 ${sp:,.2f} | 销售 ${sa:,.2f} | ACOS {sp/sa*100:.1f}%" if sa > 0 else f"花费 ${sp:,.2f} | 无销售")

    # ---------- 业务报告(可选) ----------
    if args.business:
        biz = map_columns(read_any(args.business))
        line("流量结构(业务报告)")
        sessions = biz.get('sessions', pd.Series([0])).sum()
        units = biz.get('units', pd.Series([0])).sum()
        print(f"总Sessions {sessions:,.0f} | 总订单 {units:,.0f}"
              + (f" | 整体CVR {units/sessions*100:.1f}%" if sessions else ""))
        if ad_clicks and sessions:
            print(f"广告流量占比 {ad_clicks/sessions*100:.1f}% | 广告订单占比 "
                  + (f"{ad_orders/units*100:.1f}%" if units else "N/A")
                  + f" | 自然订单 {units - (ad_orders or 0):,.0f}")

    print(f"\n{'='*60}\n分析完成。完整优化(竞价建议/PDCA闭环)用 amazon-ad-optimizer。\n{'='*60}")


if __name__ == '__main__':
    main()
