---
name: amazon-pricing-validator
description: 验证亚马逊每周价格规划是否满足黑五/网一（BFCM）BD/LD/PD 活动报名要求时触发。触发词：BFCM价格验证、黑五价格规划、活动报名价格检查、LD价格、BD价格、PD价格、秒杀报名价、价格历史规划、Was Price检查、60天低价。输入每周价格计划表（Google Sheet 链接或本地 CSV），输出 5 条报名规则的逐周检查结果 + 不合格项修正建议。不适用于：定价策略/利润测算（用 zach-product-research 或 amazon-category-analysis 模块H）。
last_verified: 2026-07-02
staleness_risk: medium
---

# Amazon Pricing Validator · BFCM 活动报名价格验证

## IPO 契约

**INPUT**
- 每周价格计划表，二选一：
  - Google Sheet 链接（需设为"任何知道链接的人均可查看"）
  - 本地 CSV（列结构见 `template.csv`：week / date_start / list_price / your_price / promo_type / promo_price / promo_days / notes）
- 四个参数（开始前向用户确认）：

| 参数 | 说明 |
|------|------|
| `--x` | 最低售价（成本底线） |
| `--list-price` | List Price 锚点价 |
| `--bfcm-target` | 黑五/网一目标活动价 |
| `--event` | 活动类型：BD / LD / PD |

**OUTPUT**
- 终端逐周验证报告（5 条规则红绿标注）
- 可选 `--output result.csv` 带验证结果的表格
- 不合格项的修正建议（哪几周价格要调、调到多少）

**降级规则：** 用户没有现成价格计划表时，先给 `template.csv` 让用户填（或根据用户口述的价格节奏帮忙生成），再跑验证。

## 执行方式

```bash
# Google Sheet
python ~/.claude/skills/amazon-pricing-validator/validate_pricing.py \
  --url "https://docs.google.com/spreadsheets/d/{ID}/edit" \
  --x 20 --list-price 35.99 --bfcm-target 22.99 --event LD

# 本地 CSV
python ~/.claude/skills/amazon-pricing-validator/validate_pricing.py \
  --file plan.csv \
  --x 20 --list-price 35.99 --bfcm-target 22.99 --event LD --output result.csv
```

依赖：`pip install pandas requests`（缺依赖时先装再跑）。

## 5 条验证规则（脚本内置）

1. **List Price** — `L × (1 - 折扣率) ≤ 目标价`
2. **Was Price** — `Was Price × 95% ≥ 目标价`（Was Price 不能被日常促销拉太低）
3. **30天低价** — `30天最低价 × 95% ≥ 目标价`
4. **60天低价** — `60天最低价 ≥ 目标价`（**硬底线，最常踩坑**）
5. **促销频次** — `90天促销天数 < 50%`（超了 Was Price 会被拉低，连带 2/3/4 全崩）

## 结果解读要求

跑完脚本后不要只贴原始输出，必须做两件事：

1. **指出最早出问题的那一周**：60天低价窗口是滚动的，一周定价失误会污染后面 8 周的报名资格——明确"从 W{X} 开始改还来得及/已经来不及"。
2. **给修正后的价格节奏**：不合格时给出具体改法（某周促销价抬到多少、促销天数减到几天），改完可再跑一遍复验。

## 使用时机提醒

黑五/网一报名的价格历史窗口是 60-90 天，即**8-9 月就要开始养价格历史**。10 月才来验证通常已无法补救——主动提醒用户这个时间约束。
