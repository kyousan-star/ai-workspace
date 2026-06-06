# Amazon Pricing Validator

验证亚马逊每周价格规划是否满足黑五/网一（BFCM）BD/LD/PD 活动报名要求。

## 安装依赖

```bash
pip install pandas requests
```

## 用法

### 从 Google Sheet 读取
```bash
python validate_pricing.py \
  --url "https://docs.google.com/spreadsheets/d/你的表格ID/edit" \
  --x 20 \
  --list-price 35.99 \
  --bfcm-target 22.99 \
  --event LD
```

> Google Sheet 需设置为"任何知道链接的人均可查看"

### 从本地 CSV 读取
```bash
python validate_pricing.py \
  --file template.csv \
  --x 20 \
  --list-price 35.99 \
  --bfcm-target 22.99 \
  --event LD \
  --output result.csv
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `--x` | 最低售价（成本底线） |
| `--list-price` | List Price 锚点价 |
| `--bfcm-target` | 黑五/网一目标活动价 |
| `--event` | 活动类型：BD / LD / PD |
| `--output` | 可选，输出带验证结果的 CSV |

## Google Sheet 模板列说明

| 列名 | 说明 | 示例 |
|------|------|------|
| `week` | 周标识 | W35 |
| `date_start` | 周起始日期 YYYY-MM-DD | 2026-08-24 |
| `list_price` | 本周 List Price | 35.99 |
| `your_price` | 本周 Your Price（日常售价）| 26.99 |
| `promo_type` | 促销类型：none / coupon / BD / LD / PD / sale | coupon |
| `promo_price` | 促销价（无促销留空）| 23.99 |
| `promo_days` | 本周促销天数（0-7）| 5 |
| `notes` | 备注（可选）| 备战黑五 |

## 5 条验证规则

1. **List Price** — `L × (1 - 折扣率) ≤ 目标价`
2. **Was Price** — `Was Price × 95% ≥ 目标价`（Was Price 不能太低）
3. **30天低价** — `30天最低价 × 95% ≥ 目标价`
4. **60天低价** — `60天最低价 ≥ 目标价`（硬底线，最常踩坑）
5. **促销频次** — `90天促销天数 < 50%`（否则 Was Price 被拉低）
