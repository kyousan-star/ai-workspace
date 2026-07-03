---
name: amazon-ads-analysis
description: 上传SP广告报表文件做快速交叉分析时触发。触发词：SP广告报表分析、搜索词报告、ACOS/ROAS诊断、否定词挖掘、加投词筛选、广告与自然流量内卷、分时竞价。适用于已有报表文件、只需快速读数和诊断的场景，US站为主，支持亚马逊原生导出报表，阈值毛利驱动并与 amazon-ad-optimizer 共享。不适用于：需要完整广告优化SOP和执行方案（用 amazon-ad-optimizer）；分析竞品广告数据（用 competitor-traffic-battle）。
last_verified: 2026-07-03
staleness_risk: medium
---

# 亚马逊SP广告分析 (Amazon Sponsored Products Analysis) — US站快读模式

> 定位: amazon-ad-optimizer 的轻量前置——只需快速读数和诊断时用本skill；要完整优化SOP、竞价建议、PDCA闭环时用 optimizer。两者共用同一套毛利驱动阈值(`../amazon-ad-optimizer/ppc_config.json`)。

## 适用场景

- 广告ACOS过高需要优化
- 广告预算分配优化
- 搜索词效率分析
- 广告与自然流量内卷诊断
- 分时竞价策略制定

---

## 一、报表清单与分析价值

### 1.1 必要报表

| 报表 | 来源 | 核心字段 | 分析价值 |
|------|------|----------|----------|
| **流量表现** | Business Report | Sessions, CVR, Buy Box% | 整体流量、转化率、跟卖检测 |
| **SP投放商品** | Advertised Product | Spend, Sales, Orders | 广告活动效率、趋势分析 |
| **SP投放报告** | Targeting Report | Match Type, Impression Share | 匹配类型效率、竞价机会 |
| **广告搜索词** | Search Terms | Customer Search Term | 高效词/否定词挖掘 |
| **购物时间** | Campaign Hourly | Hour, Day of Week | 时段效率分析 |

### 1.2 可选报表

| 报表 | 分析价值 |
|------|----------|
| **销售数据** | 真实盈亏（含广告后净利润） |
| **SQP数据** | 自然订单，内卷分析 |
| **广告位报告** | TOS/ROS/PP效率对比 |

---

## 二、分析流程（5步法）

```
第一步：全局评估
├── 产品是否盈利？（销售数据）
├── Buy Box是否正常？（流量表现，<95%有问题）
├── 整体CVR如何？（流量表现）
└── 判断：问题在广告还是产品本身？

第二步：广告效率诊断
├── 各广告活动ACOS/ROAS（SP投放商品）
├── 匹配类型效率：EXACT vs BROAD vs AUTO（SP投放报告）
├── 展示份额分析：高ROAS + 低份额 = 加投机会
└── 广告位效率：TOS vs ROS vs PP

第三步：搜索词分析
├── 高效词筛选：ROAS > 盈亏ROAS 且有订单
├── 零转化词：达到当前生命周期否定门槛（见5.2）
├── SQP交叉：广告和自然都有订单 = 可降投
└── 意图分类：品牌词/品类词/竞品词/长尾词

第四步：时间维度分析
├── 时段效率：哪些小时ROAS高/低
├── 星期效率：工作日vs周末（注意时区）
├── 趋势分析：ACOS是否改善
└── 低效时段浪费：花费占比 vs 订单占比

第五步：输出建议
├── 否定词清单（附理由）
├── 加投词清单（附理由）
├── 竞价调整建议
└── 预算重分配建议
```

---

## 三、交叉分析矩阵

| 分析目的 | 报表组合 | 计算方法 |
|----------|----------|----------|
| **广告流量占比** | 流量表现 + SP投放商品 | Ad Clicks / Total Sessions |
| **广告订单占比** | 流量表现 + SP投放商品 | Ad Orders / Total Orders |
| **内卷检测** | 广告搜索词 + SQP | 同词广告&自然都有单 |
| **展示份额机会** | SP投放报告 | ROAS>盈亏ROAS 且 Share<5% |
| **真实盈亏** | 销售数据 + SP投放商品 | 净利润 vs 广告ACOS |

---

## 四、关键公式

```python
# 基础指标
ROAS = Sales / Spend
ACOS = Spend / Sales × 100%
盈亏ACOS = 毛利率 = (售价×(1-佣金率) - 产品成本 - FBA费) / 售价
# 毛利率40% → 盈亏ACOS 40%（ACOS超过毛利率即广告亏损）
盈亏ROAS = 1 / 盈亏ACOS  # 毛利率40% → 盈亏ROAS 2.5

# 流量分析
广告流量占比 = Ad_Clicks / Total_Sessions
广告订单占比 = Ad_Orders / Total_Orders
自然订单 = Total_Orders - Ad_Orders

# 内卷分析
内卷花费 = 广告和自然都有订单的词的花费
内卷比例 = 内卷花费 / 总广告花费
```

---

## 五、阈值参考

> 阈值唯一事实源: `../amazon-ad-optimizer/ppc_config.json`（毛利驱动 + 生命周期分档），与 amazon-ad-optimizer 完全一致。以下为按盈亏线表达的速查，**分析前必须先拿到产品毛利率**。

### 5.1 效率判断（以盈亏ACOS=毛利率为基准）

| 指标 | 健康 | 警告 | 危险 |
|------|------|------|------|
| ACOS | < 盈亏线 | 盈亏线 ~ 盈亏线×1.5 | > 盈亏线×1.5 |
| ROAS | > 盈亏ROAS | 盈亏ROAS×0.67 ~ 盈亏ROAS | < 盈亏ROAS×0.67 |
| CVR | >15% | 5-15% | <5% |
| Buy Box | >95% | 90-95% | <90% |

### 5.2 否定词条件（分生命周期，与 optimizer 一致）

```
新品期(launch, 上架1-2月):  Clicks >= 20 且 Orders = 0，或花费 >= 3×盈亏CPA
成长期(growth):            Clicks >= 15 且 Orders = 0，或花费 >= 2×盈亏CPA
稳定期(stable):            Clicks >= 10 且 Orders = 0
核心保护词根: 任何阶段都不否定，零转化先查Listing/价格/竞品
盈亏CPA = 毛利率 × 售价
```

### 5.3 加投词条件

```
ROAS >= 盈亏ROAS AND Orders >= 1(新品期)/2(成长期后) → 加投候选
ROAS >= 盈亏ROAS×0.8 AND Impression_Share < 5% → 高优加投(高效率低份额)
```

### 5.4 新品期(上架1-2月)特别口径

- 目标函数是 **收录+排名+单量**，不是 ACOS；ACOS 容忍到盈亏线×2
- 数据按周分段看趋势（CVR是否爬坡、CPC是否下降），不要合并两周当一个快照
- 单量少时 CVR/ROAS 统计噪音大，任何词级判断至少 10 次点击起步

---

## 六、市场特殊性（默认US站）

### 美国 (US) — 本skill默认市场

- 时区: 广告报表默认 PST（太平洋时间）；跨美东美西4小时时差，时段分析以PST口径解读
- 工作日: 周一至周五；周末流量结构偏休闲品类
- 高效时段: 通常 18:00-22:00 当地时间，具体以自己数据为准
- 归因窗口: SP报表7天，SB/SD报表14天，交叉分析必须统一口径
- 大促节奏: Prime Day(7月)、返校季(8月)、黑五网一(11月)、圣诞(12月)，大促前2-3周CPC开始上涨

### 其他市场

非US站点(如AE)另行确认时区、工作日结构（AE周末为周五周六）和货币，再套用本流程。

---

## 七、输出模板

### 7.1 分析报告结构

```markdown
# [产品] 广告深度分析报告

## 一、执行摘要
### 1.1 流量核心指标
### 1.2 广告效率指标
### 1.3 关键发现（3-5条）

## 二、广告活动分析
## 三、匹配类型效率
## 四、广告位效率
## 五、搜索词分析
## 六、时段分析
## 七、内卷分析
## 八、优化建议
## 九、根因诊断

## 附录
- A. 数据来源
- B. 分析方法论
```

### 7.2 否定词输出格式

```markdown
| 搜索词 | Clicks | Orders | Spend | ACOS | 否定理由 |
|--------|--------|--------|-------|------|----------|
| xxx | 25 | 0 | 50 | ∞ | 零转化 |
```

### 7.3 加投词输出格式

```markdown
| 搜索词 | ROAS | 展示份额 | 建议操作 |
|--------|------|----------|----------|
| xxx | 3.5 | 0.5% | 提高竞价30% |
```

---

## 八、分析脚本

`scripts/analyze_ads.py` 支持亚马逊US广告后台**原生导出报表**（Search Term Report / Advertised Product Report / Business Report，CSV或XLSX），字段中英文自动映射：

```bash
python scripts/analyze_ads.py \
  --search-terms 搜索词报告.csv \
  --advertised-product 广告商品报告.csv \   # 可选
  --business 业务报告.csv \                # 可选，用于广告流量占比
  --margin 0.35 --phase launch
```

输出: 整体指标、匹配类型效率、高效词/否定候选清单（阈值随 --margin 和 --phase 动态推导）。

若是公司ERP格式报表（含PN/Market列的多sheet汇总表），列名不标准，让 Claude 直接读文件按第二节流程手工分析。

---

## 九、常见问题

### Q1: ACOS高但产品盈利？

检查销售数据报告的净利润。广告ACOS不等于整体盈亏，需看:
- 产品毛利率
- 自然订单占比
- 整体净利润

### Q2: 如何判断内卷？

交叉分析广告搜索词和SQP数据：
- 同一词在两个报表都有订单 = 内卷
- 内卷词可考虑降低广告投入

### Q3: 展示份额很低正常吗？

<5%较常见，关键看效率：
- 高ROAS + 低份额 = 加投机会
- 低ROAS + 低份额 = 正常，不需加投

---

## 十、相关资源

- 完整优化流程（矩阵诊断/竞价建议/PDCA闭环）: `../amazon-ad-optimizer/SKILL.md`
- 共享阈值配置: `../amazon-ad-optimizer/ppc_config.json`

---

## 【数据溯源 Footer - 每份报告必须输出】

每份分析报告的最末行必须输出以下溯源行（单行，不可省略，不可移到报告中间）：

> 📊 数据溯源｜时间范围：[从数据中提取的起止日期，YYYY-MM ~ YYYY-MM，无法确定时填"未知"]｜来源：[工具或平台名，如 Shulex / ABA后台 / Helium10 / 用户上传CSV 等]｜分析日期：[执行本次分析的日期 YYYY-MM-DD]
