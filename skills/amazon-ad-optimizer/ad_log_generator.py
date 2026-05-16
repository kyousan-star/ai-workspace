#!/usr/bin/env python3
"""
Amazon PPC 广告日志生成器
功能: 基于分析结果生成结构化广告日志，支持周报/月报/复盘模式
用法: python ad_log_generator.py <analyzed_data.xlsx> [--mode weekly|monthly|review] [--output log.md]
"""

import pandas as pd
import sys
import os
from datetime import datetime, timedelta


def load_analyzed_data(filepath):
    """加载已分析的数据"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ['.xlsx', '.xls']:
        df = pd.read_excel(filepath, sheet_name=0)
    elif ext == '.csv':
        df = pd.read_csv(filepath)
    else:
        raise ValueError(f"不支持的格式: {ext}")
    print(f"[✓] 加载数据: {len(df)}行")
    return df


def calculate_overview(df):
    """计算核心概览数据"""
    def safe_sum(col):
        return df[col].sum() if col in df.columns else 0

    def safe_mean(col):
        return df[col].mean() if col in df.columns else 0

    total_spend = safe_sum('spend')
    total_sales = safe_sum('sales')
    total_clicks = safe_sum('clicks')
    total_impressions = safe_sum('impressions')
    total_orders = safe_sum('orders')

    return {
        "总花费": total_spend,
        "总销售额": total_sales,
        "总点击": total_clicks,
        "总曝光": total_impressions,
        "总订单": total_orders,
        "ACOS": total_spend / total_sales if total_sales > 0 else 0,
        "CTR": total_clicks / total_impressions if total_impressions > 0 else 0,
        "CVR": total_orders / total_clicks if total_clicks > 0 else 0,
        "CPC": total_spend / total_clicks if total_clicks > 0 else 0,
        "CPA": total_spend / total_orders if total_orders > 0 else 0,
        "ROAS": total_sales / total_spend if total_spend > 0 else 0,
    }


def count_diagnostics(df):
    """统计诊断分布"""
    counts = {}
    if '诊断名称' in df.columns:
        counts = df['诊断名称'].value_counts().to_dict()
    elif '诊断等级' in df.columns:
        counts = df['诊断等级'].value_counts().to_dict()
    return counts


def get_action_items(df):
    """提取具体优化动作"""
    actions = {
        "需精准否定的词": [],
        "需扩大投放的优质词": [],
        "需关闭的投放对象": [],
        "需单独开广告的出单词": [],
        "需观察的词": [],
    }

    if '诊断名称' not in df.columns:
        return actions

    # 出血词/警告词 → 精准否定
    blood_words = df[df['诊断名称'].isin(['出血词', '警告词'])]
    if 'search_term' in blood_words.columns:
        actions["需精准否定的词"] = blood_words['search_term'].head(20).tolist()
    elif 'targeting' in blood_words.columns:
        actions["需精准否定的词"] = blood_words['targeting'].head(20).tolist()

    # 黄金词/优质词/潜力词 → 扩大投放
    gold_words = df[df['诊断名称'].isin(['黄金词', '优质词', '潜力词', '小宝藏'])]
    if 'search_term' in gold_words.columns:
        actions["需扩大投放的优质词"] = gold_words['search_term'].head(20).tolist()
    elif 'targeting' in gold_words.columns:
        actions["需扩大投放的优质词"] = gold_words['targeting'].head(20).tolist()

    # 泛词 → 可能关闭
    weak_words = df[df['诊断名称'].isin(['泛词'])]
    if 'search_term' in weak_words.columns:
        actions["需关闭的投放对象"] = weak_words['search_term'].head(10).tolist()
    elif 'targeting' in weak_words.columns:
        actions["需关闭的投放对象"] = weak_words['targeting'].head(10).tolist()

    return actions


def generate_weekly_log(df, overview, diag_counts, actions):
    """生成周报日志"""
    now = datetime.now()
    week_start = (now - timedelta(days=7)).strftime("%m/%d")
    week_end = now.strftime("%m/%d")

    log = f"""# 📋 亚马逊广告周报
**周期**: {week_start} - {week_end}
**生成时间**: {now.strftime("%Y-%m-%d %H:%M")}

---

## 一、核心数据

| 指标 | 数值 | 状态 |
|------|------|------|
| 总花费 | ${overview['总花费']:,.2f} | {'✅' if overview['ACOS'] < 0.25 else '⚠️'} |
| 总销售额 | ${overview['总销售额']:,.2f} | - |
| ACOS | {overview['ACOS']*100:.1f}% | {'✅ 盈利' if overview['ACOS'] < 0.25 else '⚠️ 偏高' if overview['ACOS'] < 0.40 else '🚨 亏损'} |
| CTR | {overview['CTR']*100:.2f}% | {'✅' if overview['CTR'] > 0.003 else '⚠️'} |
| CVR | {overview['CVR']*100:.1f}% | {'✅' if overview['CVR'] > 0.10 else '⚠️'} |
| CPC | ${overview['CPC']:.2f} | - |
| CPA | ${overview['CPA']:.2f} | - |
| ROAS | {overview['ROAS']:.1f}x | {'✅' if overview['ROAS'] > 4 else '⚠️'} |
| 总订单 | {overview['总订单']:,.0f} | - |
| 总点击 | {overview['总点击']:,.0f} | - |
| 总曝光 | {overview['总曝光']:,.0f} | - |

## 二、诊断分布

"""
    for name, count in sorted(diag_counts.items(), key=lambda x: x[1], reverse=True):
        pct = count / len(df) * 100
        bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
        log += f"- **{name}**: {count}个 ({pct:.1f}%)\n"

    log += "\n## 三、优化动作清单\n\n"

    if actions["需精准否定的词"]:
        log += "### 🚨 需精准否定的词\n"
        for word in actions["需精准否定的词"][:10]:
            log += f"- [ ] `{word}`\n"
        log += "\n"

    if actions["需扩大投放的优质词"]:
        log += "### ⭐ 需扩大投放的优质词\n"
        for word in actions["需扩大投放的优质词"][:10]:
            log += f"- [ ] `{word}` → 单独开广告组，精准+词组+广泛\n"
        log += "\n"

    if actions["需关闭的投放对象"]:
        log += "### 🔻 建议关闭/否定的投放对象\n"
        for word in actions["需关闭的投放对象"][:10]:
            log += f"- [ ] `{word}`\n"
        log += "\n"

    log += """## 四、下周计划

- [ ] 执行上述否定词操作
- [ ] 优质词单独开广告组测试
- [ ] 检查Listing主图/标题/A+
- [ ] 检查预算分配: SP 60% / SB 20% / SD 20%
- [ ] 检查竞价策略是否需要调整
- [ ] 关注核心词的自然排名变化

## 五、备注

> 本周特殊情况记录（秒杀/Coupon/站外活动/断货/跟卖等）:
> 
> _请在此处填写_

---
"""
    return log


def generate_monthly_log(df, overview, diag_counts, actions):
    """生成月报日志"""
    now = datetime.now()
    month_name = now.strftime("%Y年%m月")

    log = f"""# 📊 亚马逊广告月度分析报告
**月份**: {month_name}
**生成时间**: {now.strftime("%Y-%m-%d %H:%M")}
**数据量**: {len(df)}条广告数据

---

## 一、月度数据总览

### 核心指标

| 指标 | 本月数值 | 状态 | 建议 |
|------|---------|------|------|
| 总花费 | ${overview['总花费']:,.2f} | - | - |
| 总销售额 | ${overview['总销售额']:,.2f} | - | - |
| ACOS | {overview['ACOS']*100:.1f}% | {'✅ 盈利' if overview['ACOS'] < 0.25 else '⚠️ 偏高' if overview['ACOS'] < 0.40 else '🚨 亏损'} | {'保持' if overview['ACOS'] < 0.25 else '需优化否定词和竞价'} |
| CTR | {overview['CTR']*100:.2f}% | {'✅ 优秀' if overview['CTR'] > 0.005 else '✅ 正常' if overview['CTR'] > 0.002 else '⚠️ 偏低'} | {'保持' if overview['CTR'] > 0.003 else '优化主图标题'} |
| CVR | {overview['CVR']*100:.1f}% | {'✅ 优秀' if overview['CVR'] > 0.15 else '✅ 正常' if overview['CVR'] > 0.08 else '⚠️ 偏低'} | {'保持' if overview['CVR'] > 0.10 else '优化Listing详情页'} |
| CPC | ${overview['CPC']:.2f} | - | - |
| CPA | ${overview['CPA']:.2f} | - | {'CPA < 毛利则盈利'} |
| ROAS | {overview['ROAS']:.1f}x | {'✅' if overview['ROAS'] > 4 else '⚠️'} | {'保持' if overview['ROAS'] > 4 else '需降低ACOS'} |

### 效率指标

- 每$1广告费产生销售额: **${overview['ROAS']:.2f}**
- 每个广告订单成本: **${overview['CPA']:.2f}**
- 广告占比估算: 需结合自然订单数据

## 二、五维诊断分析

### 2.1 诊断分布统计

"""
    for name, count in sorted(diag_counts.items(), key=lambda x: x[1], reverse=True):
        pct = count / len(df) * 100
        log += f"| {name} | {count}个 | {pct:.1f}% |\n"

    log += f"""

### 2.2 关键发现

"""
    # 优质词占比
    good_names = ['黄金词', '优质词', '潜力词', '小宝藏']
    bad_names = ['出血词', '警告词', '泛词']
    good_count = sum(diag_counts.get(n, 0) for n in good_names)
    bad_count = sum(diag_counts.get(n, 0) for n in bad_names)
    total = len(df) if len(df) > 0 else 1

    log += f"- 优质词占比: **{good_count / total * 100:.1f}%** ({good_count}个)\n"
    log += f"- 问题词占比: **{bad_count / total * 100:.1f}%** ({bad_count}个)\n"
    log += f"- 健康度评分: **{good_count / max(good_count + bad_count, 1) * 100:.0f}分** (优质词占比)\n"

    log += """

## 三、月度优化执行清单

### 🚨 紧急 (本周执行)
"""
    if actions["需精准否定的词"]:
        for w in actions["需精准否定的词"][:5]:
            log += f"- [ ] 精准否定: `{w}`\n"

    log += "\n### ⭐ 重要 (两周内执行)\n"
    if actions["需扩大投放的优质词"]:
        for w in actions["需扩大投放的优质词"][:5]:
            log += f"- [ ] 单独开广告组投放: `{w}`\n"

    log += "\n### 📋 常规 (月内执行)\n"
    log += "- [ ] 更新关键词词库\n"
    log += "- [ ] 检查Listing是否需要优化\n"
    log += "- [ ] 评估广告结构是否需要调整\n"
    log += "- [ ] 检查产品生命周期阶段对应的广告策略\n"

    log += """

## 四、下月策略规划

### 广告结构
- SP 商品推广: 60% 预算
- SB 品牌广告: 20% 预算
- SD 展示型: 20% 预算

### 重点方向
1. 持续放大优质词的投放规模
2. 清理低效/无效的投放对象
3. 测试新的打法策略
4. 优化Listing配合广告效果提升

## 五、备注

> 本月特殊事项:
> - 秒杀活动: _____
> - Coupon使用: _____
> - 站外推广: _____
> - 库存状态: _____
> - 竞品动态: _____

---
*由Amazon PPC智能广告优化系统自动生成*
"""
    return log


def main():
    if len(sys.argv) < 2:
        print("用法: python ad_log_generator.py <analyzed_data.xlsx> [--mode weekly|monthly] [--output log.md]")
        sys.exit(1)

    filepath = sys.argv[1]
    mode = "weekly"
    output_path = None

    for i, arg in enumerate(sys.argv):
        if arg == '--mode' and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1]
        elif arg == '--output' and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    if not output_path:
        base = os.path.splitext(filepath)[0]
        output_path = f"{base}_广告日志_{mode}.md"

    # 加载数据
    df = load_analyzed_data(filepath)

    # 计算概览
    overview = calculate_overview(df)
    diag_counts = count_diagnostics(df)
    actions = get_action_items(df)

    # 生成日志
    if mode == "monthly":
        log = generate_monthly_log(df, overview, diag_counts, actions)
    else:
        log = generate_weekly_log(df, overview, diag_counts, actions)

    # 输出
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(log)

    print(f"\n[✓] 广告日志已生成: {output_path}")
    print(f"  模式: {'月报' if mode == 'monthly' else '周报'}")
    print(f"  数据量: {len(df)}条")
    print(f"  ACOS: {overview['ACOS']*100:.1f}%")
    print(f"  ROAS: {overview['ROAS']:.1f}x")


if __name__ == "__main__":
    main()
