# 报表字段详解

## 1. 流量表现报告 (Business Report)

| 字段 | 英文名 | 说明 |
|------|--------|------|
| 访客数 | Sessions | 独立访客数，一个用户一天算一个 |
| 页面浏览 | Page Views | 总浏览次数，PV/Session看浏览深度 |
| 订单数 | Units Ordered | 总订单（含广告+自然） |
| 销售额 | Ordered Product Sales | 总销售额 |
| 转化率 | Unit Session Percentage | Units / Sessions |
| Buy Box | Featured Offer Percentage | 购物车按钮占比，<95%有跟卖 |

**分析要点**：
- Sessions vs Ad Clicks = 广告流量占比
- Units vs Ad Orders = 广告订单占比
- Buy Box < 95% 需要检查跟卖

---

## 2. SP投放商品报告 (Advertised Product)

| 字段 | 说明 |
|------|------|
| Campaign Name | 广告活动名（含策略信息） |
| Impressions | 曝光次数 |
| Clicks | 点击次数 |
| Spend | 广告花费 |
| Sales | 广告销售额 |
| Orders | 广告订单数 |
| ACOS | Spend/Sales × 100% |

**活动命名解读**：
```
SP-Auto-ASIN   → 自动广告
SP-Keyword-TW  → 关键词广告-大词
SP-Keyword-LT  → 关键词广告-长尾
SP-ASIN        → ASIN定向
```

---

## 3. SP投放报告 (Targeting)

| 字段 | 说明 |
|------|------|
| Targeting | 投放目标（关键词或ASIN） |
| Match Type | EXACT/BROAD/PHRASE/AUTO |
| Top-of-search Impression Share | 搜索顶部展示份额 |

**匹配类型效率对比**：
- EXACT: 精准匹配，通常转化最高
- BROAD: 广泛匹配，流量大但精准度低
- PHRASE: 短语匹配，介于两者之间
- AUTO: 自动匹配（close-match/loose-match等）

---

## 4. 广告搜索词报告 (Search Terms)

| 字段 | 说明 |
|------|------|
| Customer Search Term | 用户实际搜索的词 |
| Targeting | 触发广告的投放词 |
| Match Type | 匹配类型 |
| Spend/Sales/Orders | 词级别效率 |

**搜索词分析逻辑**（阈值随毛利率和生命周期变化，见 SKILL.md 第五节）：
```
高效词: Orders > 0 AND ROAS > 盈亏ROAS(=1/毛利率)
否定词: 零转化且达到当前阶段否定门槛(新品期20次点击/稳定期10次)
观察词: 未达门槛的零转化词 (数据不足)
核心保护词根: 任何阶段不否定
```

---

## 5. 购物时间报告 (Campaign Hourly)

| 字段 | 说明 |
|------|------|
| 开始时间 | 小时（可能是datetime.time类型） |
| 星期 | 周一到周日 |
| Spend/Sales | 时段花费和销售 |

**时区注意**：
- AE站: GST (UTC+4)
- US站: 报告可能是当地时间
- 工作日定义因地区而异

---

## 6. SQP报告 (Search Query Performance)

| 字段 | 说明 |
|------|------|
| Search Query | 搜索词 |
| Purchases: ASIN Count | 该词带来的自然订单数 |

**内卷分析**：
同一词在广告搜索词报告和SQP报告都有订单 = 广告和自然内卷

---

## 7. 销售数据报告

| 字段 | 说明 |
|------|------|
| W Net Rev | 周净收入 |
| W SC+VC+DSP | 周广告花费 |
| W P-Mar | 周净利润（广告后） |
| W Units | 周销量 |

**盈亏判断**：
- W P-Mar > 0 = 周盈利
- 即使广告ACOS高，只要整体盈利就可接受
