---
name: amazon-ads-analysis
description: 分析亚马逊Sponsored Products广告报表，进行多报表交叉分析、ACOS/ROAS诊断、搜索词效率分析、时段优化、内卷检测。用于广告优化、广告分析、ACOS诊断、ROAS提升、否定词挖掘、加投词筛选等场景。
---

# 亚马逊SP广告分析 (Amazon Sponsored Products Analysis)

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
├── 高效词筛选：ROAS > 2.5 且有订单
├── 零转化词：Clicks > 10 且 Orders = 0
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
| **展示份额机会** | SP投放报告 | ROAS>2.5 且 Share<5% |
| **真实盈亏** | 销售数据 + SP投放商品 | 净利润 vs 广告ACOS |

---

## 四、关键公式

```python
# 基础指标
ROAS = Sales / Spend
ACOS = Spend / Sales × 100%
盈亏线ACOS = 1 / (1 + 毛利率)  # 毛利率40% → 盈亏线71.4%

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

### 5.1 效率判断

| 指标 | 健康 | 警告 | 危险 |
|------|------|------|------|
| ROAS | >2.5 | 1.5-2.5 | <1.5 |
| ACOS | <40% | 40-60% | >60% |
| CVR | >8% | 5-8% | <5% |
| Buy Box | >95% | 90-95% | <90% |

### 5.2 否定词条件

```
Clicks >= 10 AND Orders = 0 → 否定候选
Clicks >= 20 AND ACOS > 100% → 否定候选
```

### 5.3 加投词条件

```
ROAS >= 2.5 AND Orders >= 2 → 加投候选
ROAS >= 2.0 AND Impression_Share < 5% → 高优加投
```

---

## 六、市场特殊性

### 阿联酋 (AE)

- 时区: GST (UTC+4)
- 工作日: 周日至周四
- 周末: 周五(伊斯兰祈祷日)、周六
- 高效时段: 20:00-23:00, 09:00-11:00

### 美国 (US)

- 时区: PST/EST
- 工作日: 周一至周五
- 高效时段: 晚间20:00-22:00

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

## 八、Python分析代码片段

### 8.1 读取Excel（注意列名）

```python
import pandas as pd

# SP投放商品报告（header在第2行）
df = pd.read_excel('SP广告报告.xlsx', 
                   sheet_name='SP投放商品（W）-更前两周', 
                   header=1)

# 过滤产品和站点
df_product = df[(df['PN'] == 'SAST102') & (df['Market-销售'] == 'AE')]
```

### 8.2 计算ACOS/ROAS

```python
total_spend = df_product['Spend'].sum()
total_sales = df_product['Sales'].sum()
acos = total_spend / total_sales * 100 if total_sales > 0 else float('inf')
roas = total_sales / total_spend if total_spend > 0 else 0
```

### 8.3 时段分析

```python
# 注意：时间列可能是datetime.time类型
df['Hour'] = df['开始时间'].apply(lambda x: x.hour if hasattr(x, 'hour') else 0)
hourly = df.groupby('Hour').agg({'Spend': 'sum', 'Sales': 'sum'})
hourly['ROAS'] = hourly['Sales'] / hourly['Spend']
```

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

- 分析报告示例: [ST102_广告深度分析报告.md](../../ST102_广告深度分析报告.md)
