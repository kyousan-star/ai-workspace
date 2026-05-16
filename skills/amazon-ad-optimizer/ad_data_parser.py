#!/usr/bin/env python3
"""
Amazon PPC 广告数据解析引擎
功能: 自动解析亚马逊广告后台导出的CSV/XLSX数据，执行数据清洗、指标量化分层、矩阵诊断
用法: python ad_data_parser.py <input_file> [--profit-rate 0.25] [--output output.xlsx]
"""

import pandas as pd
import numpy as np
import sys
import os
import json
from datetime import datetime

# ============================================================
# 配置区：阈值可根据类目调整
# ============================================================
CONFIG = {
    # 盈亏ACOS（默认25%，应由用户输入计算）
    "break_even_acos": 0.25,
    # 曝光量分层阈值（关键词广告）
    "impression_thresholds_kw": {"none": 0, "low": 500, "mid": 5000},
    # 曝光量分层阈值（ASIN广告）
    "impression_thresholds_asin": {"none": 0, "low": 200, "mid": 2000},
    # 点击次数分层阈值
    "click_thresholds": {"none": 0, "low": 5, "mid": 20},
    # CTR分层阈值
    "ctr_thresholds": {"low": 0.002, "mid": 0.005},
    # CVR分层阈值
    "cvr_thresholds": {"low": 0.05, "mid": 0.15},
    # ACOS分层（基于盈亏ACOS的倍数）
    "acos_multipliers": {"excellent": 0.5, "good": 1.0, "high": 1.5},
}

# ============================================================
# 字段映射：中英文字段名自动匹配
# ============================================================
FIELD_MAPPING = {
    # 曝光量
    "impressions": ["impressions", "曝光量", "展现次数", "impression", "展示次数"],
    # 点击量
    "clicks": ["clicks", "点击量", "点击次数", "click"],
    # 花费
    "spend": ["spend", "花费", "cost", "广告花费", "费用", "total spend"],
    # 销售额
    "sales": ["sales", "销售额", "7 day total sales", "14 day total sales",
              "广告销售额", "total sales", "7天总销售额", "14天总销售额"],
    # 订单量
    "orders": ["orders", "订单量", "7 day total orders", "14 day total orders",
               "广告订单量", "total orders", "7天总订单量", "14天总订单量"],
    # 搜索词
    "search_term": ["customer search term", "搜索词", "search term", "客户搜索词"],
    # 投放对象
    "targeting": ["targeting", "投放", "投放对象", "keyword or product targeting"],
    # 匹配类型
    "match_type": ["match type", "匹配类型", "match_type"],
    # 广告活动
    "campaign": ["campaign name", "广告活动", "campaign", "广告活动名称"],
    # 广告组
    "ad_group": ["ad group name", "广告组", "ad group", "广告组名称"],
    # ASIN
    "asin": ["advertised asin", "asin", "推广的asin", "advertised_asin"],
    # 广告位
    "placement": ["placement", "广告位", "展示位置"],
    # ACOS
    "acos": ["acos", "total advertising cost of sales", "广告投入产出比"],
    # CPC
    "cpc": ["cpc", "cost per click", "每次点击费用", "平均每次点击费用"],
}


def detect_and_read_file(filepath):
    """自动检测文件格式并读取"""
    ext = os.path.splitext(filepath)[1].lower()

    if ext in ['.csv', '.tsv']:
        # 尝试不同编码和分隔符
        for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb18030', 'latin1']:
            for sep in [',', '\t', ';']:
                try:
                    df = pd.read_csv(filepath, encoding=encoding, sep=sep, nrows=5)
                    if len(df.columns) > 1:
                        df = pd.read_csv(filepath, encoding=encoding, sep=sep)
                        print(f"[✓] 文件读取成功: {encoding} | 分隔符: {repr(sep)} | {len(df)}行 × {len(df.columns)}列")
                        return df
                except:
                    continue
        raise ValueError(f"无法读取文件: {filepath}")

    elif ext in ['.xlsx', '.xls', '.xlsm']:
        df = pd.read_excel(filepath)
        print(f"[✓] Excel文件读取成功: {len(df)}行 × {len(df.columns)}列")
        return df

    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def normalize_columns(df):
    """标准化列名，中英文自动匹配"""
    col_map = {}
    df.columns = [str(c).strip().lower() for c in df.columns]

    for standard_name, aliases in FIELD_MAPPING.items():
        for alias in aliases:
            alias_lower = alias.lower()
            for col in df.columns:
                if alias_lower == col or alias_lower in col:
                    col_map[col] = standard_name
                    break
            if standard_name in col_map.values():
                break

    df = df.rename(columns=col_map)
    mapped = [v for v in col_map.values()]
    print(f"[✓] 字段映射完成: {len(mapped)}个字段已识别 → {mapped}")
    return df


def clean_data(df):
    """数据清洗"""
    initial_rows = len(df)

    # 清理货币符号和百分号
    for col in ['spend', 'sales', 'cpc', 'acos']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[$€£¥%,]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 清理数值列
    for col in ['impressions', 'clicks', 'orders']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # 去除全空行
    df = df.dropna(how='all')

    # ACOS如果是百分比形式(>1)则除以100
    if 'acos' in df.columns:
        mask = df['acos'] > 1
        df.loc[mask, 'acos'] = df.loc[mask, 'acos'] / 100

    print(f"[✓] 数据清洗完成: {initial_rows}行 → {len(df)}行 (清除{initial_rows - len(df)}行)")
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

    print(f"[✓] 衍生指标计算完成: CTR/CVR/CPC/ACOS/CPA/ROAS")
    return df


def classify_impressions(val, is_asin=False):
    """曝光量分层"""
    thresholds = CONFIG["impression_thresholds_asin"] if is_asin else CONFIG["impression_thresholds_kw"]
    if val == 0:
        return "无曝光"
    elif val <= thresholds["low"]:
        return "低曝光"
    elif val <= thresholds["mid"]:
        return "中曝光"
    else:
        return "高曝光"


def classify_clicks(val):
    """点击次数分层"""
    t = CONFIG["click_thresholds"]
    if val == 0:
        return "无点击"
    elif val <= t["low"]:
        return "低点击"
    elif val <= t["mid"]:
        return "中点击"
    else:
        return "高点击"


def classify_ctr(val):
    """CTR分层"""
    t = CONFIG["ctr_thresholds"]
    if val < t["low"]:
        return "低CTR"
    elif val < t["mid"]:
        return "中CTR"
    else:
        return "高CTR"


def classify_cvr(val):
    """转化率分层"""
    t = CONFIG["cvr_thresholds"]
    if val == 0:
        return "0转化"
    elif val < t["low"]:
        return "低转化"
    elif val < t["mid"]:
        return "中转化"
    else:
        return "高转化"


def classify_acos(val, break_even=None):
    """ACOS分层"""
    be = break_even or CONFIG["break_even_acos"]
    m = CONFIG["acos_multipliers"]
    if val == 0 or val == np.inf:
        return "无数据"
    elif val < be * m["excellent"]:
        return "极佳"
    elif val <= be * m["good"]:
        return "良好"
    elif val <= be * m["high"]:
        return "偏高"
    else:
        return "过高"


def apply_classification(df, break_even_acos=None):
    """对所有数据行打分层标签"""
    be = break_even_acos or CONFIG["break_even_acos"]

    # 检测是否ASIN广告
    is_asin = False
    if 'targeting' in df.columns:
        asin_pattern = df['targeting'].astype(str).str.match(r'^[A-Z0-9]{10}$', na=False)
        is_asin_col = asin_pattern.any()
    else:
        is_asin_col = False

    if 'impressions' in df.columns:
        df['曝光分层'] = df['impressions'].apply(lambda x: classify_impressions(x, is_asin_col))

    if 'clicks' in df.columns:
        df['点击分层'] = df['clicks'].apply(classify_clicks)

    if 'ctr' in df.columns:
        df['CTR分层'] = df['ctr'].apply(classify_ctr)

    if 'cvr' in df.columns:
        df['转化分层'] = df['cvr'].apply(classify_cvr)

    if 'acos_calc' in df.columns:
        df['ACOS分层'] = df['acos_calc'].apply(lambda x: classify_acos(x, be))

    # 生成组合标签
    cols_for_combo = []
    for c in ['曝光分层', '点击分层', '转化分层', 'ACOS分层']:
        if c in df.columns:
            cols_for_combo.append(c)

    if cols_for_combo:
        df['诊断组合'] = df[cols_for_combo].apply(lambda row: '_'.join(str(v) for v in row), axis=1)

    print(f"[✓] 指标分层完成: {len(cols_for_combo)}个维度分层标记")
    return df


# ============================================================
# 诊断规则引擎
# ============================================================
DIAGNOSIS_RULES = {
    # 搜索词30种场景的诊断规则
    "高曝光_高点击_高转化": {
        "level": "🌟🌟🌟", "name": "黄金词",
        "problem": "完美表现，需保持并扩大",
        "purpose": "保持单量，放大绩效",
        "action": "记录坑位→提高竞价→单独开组→扩大投放",
        "result": "持续保持，单量增加"
    },
    "中曝光_高点击_高转化": {
        "level": "⭐⭐", "name": "优质词",
        "problem": "曝光可以进一步扩大",
        "purpose": "提升单量",
        "action": "提高竞价扩大曝光→单独开广告组",
        "result": "点击量和单量增加"
    },
    "低曝光_高点击_高转化": {
        "level": "💎", "name": "潜力词",
        "problem": "竞价过低或预算不足",
        "purpose": "提升曝光和单量",
        "action": "大幅提高竞价→确保首页前半部→务必单独投放",
        "result": "单量明显增加"
    },
    "高曝光_低点击_低转化": {
        "level": "🔻", "name": "泛词",
        "problem": "关键词匹配度不高或太泛，Listing吸引力不足",
        "purpose": "降ACOS，提高转化率",
        "action": "精准否定→低价广泛单独开组→检查匹配度和竞争力",
        "result": "转化率上升，ACOS降低"
    },
    "高曝光_低点击_中转化": {
        "level": "📊", "name": "大词低CTR",
        "problem": "词流量大但主图/标题/品牌无优势",
        "purpose": "提高点击率",
        "action": "标题主图体现词属性→开视频广告SBV",
        "result": "点击量和单量增加"
    },
    "高曝光_低点击_高转化": {
        "level": "🎯", "name": "高转化低CTR",
        "problem": "主图吸引力不够，竞品优势明显",
        "purpose": "提高点击率",
        "action": "主图标题体现词属性和场景→开SBV视频广告",
        "result": "点击量大幅增加，单量显著提升"
    },
    "低曝光_低点击_高转化": {
        "level": "🔎", "name": "小宝藏",
        "problem": "含竞品品牌词或偶然出单，竞价可能过低",
        "purpose": "提高曝光和点击",
        "action": "提高竞价/调整广告位→务必单独开广告投放",
        "result": "点击量和单量增加"
    },
    "高点击_0转化": {
        "level": "🚨", "name": "出血词",
        "problem": "关键词匹配度很低，严重浪费广告费",
        "purpose": "降广告费，提高整体权重",
        "action": "在对应广告组做精准否定",
        "result": "广告花费大幅减少"
    },
    "中点击_0转化": {
        "level": "⚠️", "name": "警告词",
        "problem": "匹配度不高或Listing竞争力不足",
        "purpose": "降广告费，提高转化率",
        "action": "反查匹配度→不匹配做精准否定→匹配则优化Listing+促销",
        "result": "花费减少，可能增加订单"
    },
    "低点击_0转化": {
        "level": "⏸️", "name": "观察",
        "problem": "数据量不足不具参考性",
        "purpose": "测试，稳定广告体系",
        "action": "不做调整，继续观察积累数据",
        "result": "不调整"
    },
}


def diagnose_row(row):
    """对单行数据进行诊断"""
    if '诊断组合' not in row:
        return {"诊断": "数据不足", "等级": "⏸️", "动作": "需要更多数据"}

    combo = row['诊断组合']

    # 特殊处理0转化场景
    if '0转化' in combo:
        clicks = row.get('clicks', 0)
        if clicks > 20:
            key = "高点击_0转化"
        elif clicks > 5:
            key = "中点击_0转化"
        else:
            key = "低点击_0转化"
    else:
        # 简化组合名用于匹配
        parts = combo.split('_')
        exposure = parts[0] if len(parts) > 0 else ""
        click_part = parts[1] if len(parts) > 1 else ""
        conv_part = parts[2] if len(parts) > 2 else ""

        # 用CTR替代点击分层(搜索词分析用CTR)
        ctr_level = row.get('CTR分层', '中CTR')
        if ctr_level == '高CTR':
            click_str = '高点击'
        elif ctr_level == '低CTR':
            click_str = '低点击'
        else:
            click_str = '中点击'

        key = f"{exposure}_{click_str}_{conv_part}"

    if key in DIAGNOSIS_RULES:
        rule = DIAGNOSIS_RULES[key]
        return {
            "诊断等级": rule["level"],
            "诊断名称": rule["name"],
            "问题分析": rule["problem"],
            "广告目的": rule["purpose"],
            "广告策略": rule["action"],
            "预期结果": rule["result"],
        }

    return {
        "诊断等级": "📊",
        "诊断名称": "标准",
        "问题分析": "各指标表现中等",
        "广告目的": "全面优化提升",
        "广告策略": "根据具体数据调整竞价/否词/Listing",
        "预期结果": "各指标有提升空间",
    }


def generate_summary(df):
    """生成汇总分析报告"""
    summary = {
        "数据概览": {
            "总行数": len(df),
            "总花费": df.get('spend', pd.Series([0])).sum(),
            "总销售额": df.get('sales', pd.Series([0])).sum(),
            "总点击": df.get('clicks', pd.Series([0])).sum(),
            "总曝光": df.get('impressions', pd.Series([0])).sum(),
            "总订单": df.get('orders', pd.Series([0])).sum(),
        },
        "整体指标": {},
        "分层分布": {},
    }

    total_spend = summary["数据概览"]["总花费"]
    total_sales = summary["数据概览"]["总销售额"]
    total_clicks = summary["数据概览"]["总点击"]
    total_impressions = summary["数据概览"]["总曝光"]
    total_orders = summary["数据概览"]["总订单"]

    summary["整体指标"] = {
        "整体ACOS": f"{total_spend / total_sales * 100:.1f}%" if total_sales > 0 else "N/A",
        "整体CTR": f"{total_clicks / total_impressions * 100:.2f}%" if total_impressions > 0 else "N/A",
        "整体CVR": f"{total_orders / total_clicks * 100:.1f}%" if total_clicks > 0 else "N/A",
        "平均CPC": f"${total_spend / total_clicks:.2f}" if total_clicks > 0 else "N/A",
        "平均CPA": f"${total_spend / total_orders:.2f}" if total_orders > 0 else "N/A",
        "ROAS": f"{total_sales / total_spend:.1f}x" if total_spend > 0 else "N/A",
    }

    # 分层分布统计
    for col in ['曝光分层', '点击分层', '转化分层', 'ACOS分层', 'CTR分层']:
        if col in df.columns:
            summary["分层分布"][col] = df[col].value_counts().to_dict()

    return summary


def generate_ad_log(df, summary, output_path=None):
    """生成广告日志"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    s = summary["数据概览"]
    m = summary["整体指标"]

    # 统计诊断结果
    diag_counts = {}
    if '诊断名称' in df.columns:
        diag_counts = df['诊断名称'].value_counts().to_dict()

    log = f"""{'═' * 60}
📋 亚马逊广告分析日志
{'═' * 60}
生成时间: {now}
数据范围: 30天广告数据
{'─' * 60}

一、核心数据概览
  总花费: ${s['总花费']:,.2f}  |  总销售额: ${s['总销售额']:,.2f}
  ACOS: {m['整体ACOS']}     |  ROAS: {m['ROAS']}
  总点击: {s['总点击']:,}     |  总曝光: {s['总曝光']:,}
  CTR: {m['整体CTR']}       |  CVR: {m['整体CVR']}
  CPC: {m['平均CPC']}       |  CPA: {m['平均CPA']}
  广告订单: {s['总订单']:,}
  盈亏状态: {'盈利 ✅' if s['总销售额'] > s['总花费'] * 3 else '需优化 ⚠️'}

二、诊断结果摘要
"""

    for name, count in sorted(diag_counts.items(), key=lambda x: x[1], reverse=True):
        log += f"  {name}: {count}个\n"

    # 分层分布
    log += f"\n三、指标分层分布\n"
    for col_name, dist in summary.get("分层分布", {}).items():
        log += f"\n  {col_name}:\n"
        for level, count in sorted(dist.items(), key=lambda x: x[1], reverse=True):
            log += f"    {level}: {count}个 ({count / len(df) * 100:.1f}%)\n"

    log += f"""
四、优化建议清单
  □ 黄金词/优质词: 保持并扩大投放
  □ 出血词(高点击0转化): 立即精准否定
  □ 警告词(中点击0转化): 检查匹配度后决定否定
  □ 潜力词(低曝光高转化): 提高竞价扩大曝光
  □ 泛词(高曝光低转化): 做精准否定+低价广泛
  □ 大词低CTR: 开视频广告SBV

五、下期计划
  □ 执行否定词操作
  □ 优质词单独开广告组
  □ Listing优化(主图/标题/A+)
  □ 检查预算分配: SP 60% / SB 20% / SD 20%
  □ 7天后复盘对比数据变化

{'═' * 60}
"""

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(log)
        print(f"[✓] 广告日志已生成: {output_path}")

    return log


def main():
    if len(sys.argv) < 2:
        print("用法: python ad_data_parser.py <input_file> [--profit-rate 0.25] [--output output.xlsx]")
        print("示例: python ad_data_parser.py search_term_report.csv --profit-rate 0.30")
        sys.exit(1)

    filepath = sys.argv[1]
    profit_rate = CONFIG["break_even_acos"]
    output_path = None

    # 解析命令行参数
    for i, arg in enumerate(sys.argv):
        if arg == '--profit-rate' and i + 1 < len(sys.argv):
            profit_rate = float(sys.argv[i + 1])
        elif arg == '--output' and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    if not output_path:
        base = os.path.splitext(filepath)[0]
        output_path = f"{base}_分析结果.xlsx"

    print(f"\n{'=' * 60}")
    print(f"  Amazon PPC 广告数据解析引擎")
    print(f"  盈亏ACOS: {profit_rate * 100:.0f}%")
    print(f"{'=' * 60}\n")

    # Step 1: 读取文件
    print("▸ Step 1: 读取文件...")
    df = detect_and_read_file(filepath)

    # Step 2: 标准化列名
    print("▸ Step 2: 标准化列名...")
    df = normalize_columns(df)

    # Step 3: 数据清洗
    print("▸ Step 3: 数据清洗...")
    df = clean_data(df)

    # Step 4: 计算衍生指标
    print("▸ Step 4: 计算衍生指标...")
    df = calculate_derived_metrics(df)

    # Step 5: 指标分层
    print("▸ Step 5: 指标量化分层...")
    df = apply_classification(df, profit_rate)

    # Step 6: 矩阵诊断
    print("▸ Step 6: 矩阵诊断...")
    diagnosis_results = df.apply(diagnose_row, axis=1, result_type='expand')
    df = pd.concat([df, diagnosis_results], axis=1)
    print(f"[✓] 诊断完成: {len(df)}条数据已诊断")

    # Step 7: 生成汇总
    print("▸ Step 7: 生成汇总报告...")
    summary = generate_summary(df)

    # 输出Excel（多Sheet）
    print(f"▸ 输出分析结果...")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 全部数据
        df.to_excel(writer, sheet_name='完整分析数据', index=False)

        # 按诊断名称分组
        if '诊断名称' in df.columns:
            for name in df['诊断名称'].unique():
                subset = df[df['诊断名称'] == name]
                safe_name = str(name)[:31]  # Excel sheet名最长31字符
                subset.to_excel(writer, sheet_name=safe_name, index=False)

        # 汇总Sheet
        summary_df = pd.DataFrame([
            {"指标": k, "数值": v}
            for section in [summary["数据概览"], summary["整体指标"]]
            for k, v in section.items()
        ])
        summary_df.to_excel(writer, sheet_name='数据概览', index=False)

    print(f"[✓] 分析结果已输出: {output_path}")

    # 生成广告日志
    log_path = os.path.splitext(output_path)[0] + "_广告日志.txt"
    log = generate_ad_log(df, summary, log_path)

    # 打印摘要
    print(f"\n{'=' * 60}")
    print(f"  分析完成!")
    print(f"  Excel报告: {output_path}")
    print(f"  广告日志: {log_path}")
    print(f"{'=' * 60}")

    # 打印关键数据
    print(f"\n  整体ACOS: {summary['整体指标']['整体ACOS']}")
    print(f"  整体CTR: {summary['整体指标']['整体CTR']}")
    print(f"  整体CVR: {summary['整体指标']['整体CVR']}")
    print(f"  平均CPC: {summary['整体指标']['平均CPC']}")
    print(f"  ROAS: {summary['整体指标']['ROAS']}")

    if '诊断名称' in df.columns:
        print(f"\n  诊断分布:")
        for name, count in df['诊断名称'].value_counts().items():
            print(f"    {name}: {count}个")


if __name__ == "__main__":
    main()
