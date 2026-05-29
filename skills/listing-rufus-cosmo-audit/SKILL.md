---
name: listing-rufus-cosmo-audit
description: Amazon Listing Rufus/COSMO 契合度审计 Skill。对已完成的 Listing 进行结构化审计，评估 Query Intent 覆盖、COSMO 语义完整性、参数密度、自然语言质量和合规风险，输出评分、差距分析和改写建议。当用户提到"listing审计"、"审计listing"、"rufus审计"、"cosmo审计"、"listing audit"、"audit listing"时使用此 skill。
---

# Listing Rufus/COSMO Audit Skill

## Trigger

当用户说以下任意一种：`listing审计`、`审计listing`、`rufus审计`、`cosmo审计`、`listing audit`、`audit listing` — 执行本 skill。

## Input

### 主输入：Listing 内容

用户提供文件路径或直接粘贴 listing 内容。支持以下来源：
- amazon-listing-v2 skill 的输出文件（直接提供文件路径即可）
- 手动粘贴的 listing 文本
- 已上架 listing 的各字段截图或复制文本

审计覆盖的字段（有几个审几个，缺失的字段记录为 gap）：
- Title
- Bullet Points（5 条）
- Product Description / A+ Content
- Backend Search Terms
- Product Specs / Basic Info

### 辅助输入（可选但推荐）

| 材料 | 用途 | 缺失时处理 |
|------|------|------------|
| 本品属性 / Product Fact Bank | 验证 listing 声明是否有事实依据 | 无法做事实准确性核查，Dimension 3 只审格式不验真实性 |
| 实际 Rufus/QA 问题素材 | 作为 Dimension 1 的真实测试用例 | 改用 AI 推断问题，但需在报告中注明 |
| 竞品 Listing | 评估 Parity/Gap 覆盖 | 跳过竞品对比部分 |

---

## Execution：5-Dimension Audit

每个维度 10 分制打分。严格评估，不做模糊赞美。

---

### Dimension 1：Query Intent Match（权重 30%）

**Rufus 做什么**：买家输入自然语言问题 → Rufus 匹配最相关的 listing。

**审计方法**：

**Step 1 — 确定测试问题来源**

优先使用用户提供的实际素材：
- 用户提供的 Rufus 问题 / Amazon QA / 搜索联想词 → 直接作为测试用例，标注来源为"实际数据"
- 未提供素材 → AI 根据品类推断，全部标注"AI 推断（非实际 Rufus 数据）"

**Step 2 — 生成/整理 15 个买家问题**

覆盖以下类型：
- 购买意图：`best [product] for [use case]`
- 对比类：`[product] vs [competitor type]`
- 兼容性：`does [product] work with [device/scenario]`
- 参数查询：`how long/far/heavy/loud is [product]`
- 场景类：`can I use [product] for [activity]`

**Step 3 — 逐题判断**

对每个问题：listing 内容是否给出清晰直接的答案？
- Y（Yes）= 明确回答
- P（Partial）= 部分回答或模糊回答
- N（No）= 无法从 listing 找到答案

**计分公式**：`(Y × 1 + P × 0.4) / 15 × 10`

如果测试用例全部为 AI 推断，得分上限为 8 分（不得满分，因为测试标准本身未经验证）。

**Output**：15 个问题逐条列出，含 Y/P/N 判定、答案所在的 listing 位置（或标记"缺失"）、数据来源标注。

---

### Dimension 2：Semantic Completeness（权重 25%）

**COSMO 做什么**：从结构层面理解"这个产品是什么"，建立语义索引。

**两层审计**：

**Layer A — COSMO 4 类语义关系**（对齐 amazon-listing-v2 的 COSMO 覆盖原则）

| 语义关系 | 含义 | 示例 | 是否覆盖？ |
|----------|------|------|------------|
| isA | 产品是什么（品类、类型、形态） | "a compact phone tripod" | |
| capable of | 能做什么（功能、能力、参数范围） | "extends from 6" to 55"" | |
| used for | 用于什么场景/人群 | "for vlogging, travel, desk setup" | |
| cause | 带来什么结果/用户收益 | "keeps shots steady without blur" | |

每类覆盖 = 1 分，部分覆盖 = 0.5 分，缺失 = 0 分。**Layer A 满分 4 分。**

**Layer B — 5W1H 产品完整性检查**

| 元素 | 问题 | 是否覆盖 |
|------|------|----------|
| WHAT | 产品品类、类型、形态是否明确？ | |
| WHO | 目标用户/使用人群是否说明？ | |
| WHY | 相比替代品的差异化价值是否清晰？ | |
| WHERE | 使用场景是否列举？ | |
| HOW | 使用方式/安装/操作是否说明？ | |
| WHAT'S INCLUDED | 包装内容是否列出？ | |

每项：完全覆盖 = 1 分，部分 = 0.5 分，缺失 = 0 分。**Layer B 满分 6 分。**

**最终 Dimension 2 得分** = Layer A 分（满分 4）+ Layer B 分（满分 6），合计 10 分。

---

### Dimension 3：Structured Specs Density（权重 20%）

**为什么重要**：COSMO 将"数字+单位"索引为结构化数据用于精确匹配。"65ft range"可被索引；"long range"不行。

**审计清单**：
- 统计 listing 中所有 `[数字 + 单位]` 组合（如 "8H"、"200mAh"、"65ft"、"48kHz"）
- 品类关键参数是否齐全（尺寸、重量、续航、范围、功率、容量等——按品类判断）
- 参数是否有上下文？（差：单写 "200mAh"；好："200mAh battery for 8 hours continuous use"）
- 兼容型号是否具体？（差："compatible with iPhone"；好："iPhone 15/14/13/12"）
- 如用户提供了本品属性，检查 listing 中的数值是否与属性一致（标注不一致项）

**评分标准**：
- 9–10：10+ 个 spec 组合，全部有上下文，兼容型号完整，数值与本品属性一致
- 7–8：6–9 个 spec 组合，大多有上下文
- 5–6：3–5 个 spec 组合，部分缺乏上下文
- 3–4：1–2 个 spec 组合
- 0–2：无量化参数

**Search Terms 专项检查**（在此维度附加，不单独计分但计入报告）：

| 检查项 | 结果 |
|--------|------|
| 字节数是否在 250 bytes 以内 | |
| 是否有词根重复（与 title/bullets 或 ST 内部）| |
| 是否含禁用词（品牌词、ASIN、促销词、竞品名）| |
| 是否包含 title/bullets 已充分覆盖的冗余词 | |
| 未覆盖的场景词/同义词/缩写是否补充进去了 | |

---

### Dimension 4：Natural Language Quality（权重 15%）

**为什么重要**：Rufus 偏好像人一样解释产品的文案，而非关键词堆砌的 SEO 文本。

**审计标准**：
- 句子流畅度：bullet 是否可读性强，还是关键词列表？
- 信息重复：title/bullets/description 之间是否大量重复相同内容？
- 关键词堆砌信号：不自然的重复、逗号分隔词链
- 可读性：人类是否能舒适地朗读这段文字？
- 语气一致性：专业信息型 vs 夸张促销型（"BEST EVER!!!"）

**评分标准**：
- 9–10：自然可读，信息量足，零堆砌
- 7–8：整体自然，有轻微不顺畅
- 5–6：明显关键词插入但仍可读
- 3–4：关键词为主，句子碎片化
- 0–2：纯关键词堆砌

---

### Dimension 5：Risk & Compliance（权重 10%）

**审计项目**：
- 无证据的绝对性表达："best"、"#1"、"most popular"、"No.1"
- 医疗/健康功效声明（无认证）
- 质保/终身承诺（与 ToS 冲突）
- 商标符号干扰（TM、® 过多）
- 全大写词滥用
- 竞品品牌名（IP 投诉风险）
- Amazon 政策明确禁止词（促销词、外链、联系方式等）
- 促销时效词（"limited time"、"buy now"等）

**评分标准**：
- 9–10：零违规
- 7–8：1 处轻微问题（如一个 "#1" 声明）
- 5–6：2–3 处问题
- 3–4：多处违规
- 0–2：严重合规风险

---

## Output Format

报告保存至同目录，文件名：`report-[ASIN或产品名]-[YYYY-MM-DD].md`

```markdown
# Listing Audit Report

**Product**: [name/ASIN]
**Date**: [YYYY-MM-DD]
**Listing 来源**: [amazon-listing-v2 输出 / 手动提供]
**辅助资料**: [本品属性：有/无 | Rufus 素材：有/无 | 竞品：有/无]
**Overall Score**: [加权总分]/10

## Score Summary

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Query Intent Match | X/10 | 30% | X.X |
| Semantic Completeness | X/10 | 25% | X.X |
| Structured Specs | X/10 | 20% | X.X |
| Natural Language Quality | X/10 | 15% | X.X |
| Risk & Compliance | X/10 | 10% | X.X |
| **TOTAL** | | | **X.X/10** |

## Grade
- 9–10：A+（Rufus/COSMO 优化到位，可直接上架）
- 8–8.9：A（整体强，局部微调）
- 7–7.9：B（有明确改进空间）
- 6–6.9：C（存在显著缺口）
- <6：D（需要大幅重写）

---

## Dimension 1：Query Intent Match — [X/10]

> 测试用例来源：[实际 Rufus/QA 数据 / AI 推断（非实际 Rufus 数据）]

### Simulated Buyer Questions
| # | Question | Answered? | Where | 来源 |
|---|----------|-----------|-------|------|
| 1 | ... | Y/P/N | Title / Bullet 3 / 缺失 | 实际/AI推断 |
...

### Gaps
[Listing 无法回答的问题列表]

---

## Dimension 2：Semantic Completeness — [X/10]

### Layer A — COSMO 4 类语义关系（满分 4 分）

| 语义关系 | 得分 | 证据（引用 listing 原文） |
|----------|------|--------------------------|
| isA | 1 / 0.5 / 0 | ... |
| capable of | 1 / 0.5 / 0 | ... |
| used for | 1 / 0.5 / 0 | ... |
| cause | 1 / 0.5 / 0 | ... |
| **小计** | X/4 | |

### Layer B — 5W1H 完整性

| 元素 | 状态 | 证据 |
|------|------|------|
| WHAT | ... | ... |
| WHO | ... | ... |
| WHY | ... | ... |
| WHERE | ... | ... |
| HOW | ... | ... |
| INCLUDED | ... | ... |

### 缺失/需补充的内容
[具体说明需要补充什么]

---

## Dimension 3：Structured Specs — [X/10]

### 已找到的 Spec 组合
[列出所有数字+单位组合及所在位置]

### 缺失的关键参数
[品类应有但 listing 没有的参数]

### 上下文缺失的参数
[有数字但没有解释的参数]

### 数值一致性问题（需本品属性）
[如未提供属性则标注"无法核查"]

### Search Terms 检查
| 检查项 | 结果 |
|--------|------|
| 字节数 | X bytes |
| 词根重复 | 有/无，具体：... |
| 禁用词 | 有/无，具体：... |
| 冗余词 | 有/无，具体：... |
| 建议补充 | ... |

---

## Dimension 4：Natural Language Quality — [X/10]

### 问题详情
[具体指出关键词堆砌、重复、语气问题的例子，引用原文]

---

## Dimension 5：Risk & Compliance — [X/10]

### 违规项
| 问题 | 原文引用 | 所在位置 | 建议处理 |
|------|----------|----------|----------|
| ... | ... | ... | ... |

---

## Top 3 优先改进项

1. [影响最大的问题 + 具体改法]
2. [第二优先 + 具体改法]
3. [第三优先 + 具体改法]

---

## 逐字段改写建议

> 注意：以下仅为针对审计问题的定向修改建议，不是完整重写。
> 如需重新生成完整 listing，请使用 amazon-listing-v2 skill 并提供本品属性。

### Title
- 问题：[具体问题]
- 建议修改：[修改后的 title]
- 改动理由：[为什么这样改]

### Bullet Points
针对有问题的条目给出具体改写建议：

**Bullet X（原文有问题）**
- 问题：[描述问题]
- 建议改为：[改写后的文本]
- 改动理由：[为什么]

### Description
- 问题：[具体问题]
- 建议：[定向修改说明]

### Search Terms
- 建议删除：[具体词]（原因）
- 建议补充：[具体词]（原因）

---

## 数据缺口提醒

[列出因缺少辅助资料而无法核查的项目，建议用户下次提供]
```

---

## Rules

1. 严格评分，找问题而不是验证已有内容。每条批评必须附上具体改法。
2. 改写建议只针对审计发现的具体问题，不输出完整重写版本——完整重写需通过 amazon-listing-v2 skill 配合本品属性进行。
3. 不得在改写建议中添加本品属性未提供的参数、认证、兼容型号或质保内容。
4. Dimension 1 的测试问题来源必须在报告中明确标注（实际数据 vs AI 推断）；全部为 AI 推断时，该维度得分上限 8 分。
5. 如未提供 Backend Search Terms，在 Dimension 3 的 ST 检查栏标注"未提供，建议提交后补充审计"。
6. 如未提供本品属性，Dimension 3 的数值一致性检查栏标注"无法核查——建议提供本品属性重新审计"。
7. 加权总分计算：每个维度得分 × 权重后相加，保留一位小数。
8. 报告末尾必须输出"→ listing-v2 重写入口"模块（见下方格式），将审计 gap 结构化为 listing-v2 可直接使用的输入。

---

## 审计结果 → listing-v2 重写入口

审计完成后，在报告最后附加以下模块，方便用户直接衔接 amazon-listing-v2 skill 进行定向重写：

```markdown
## 如需重写：交给 amazon-listing-v2 的 Gap 清单

> 将以下内容连同本品属性一起提供给 amazon-listing-v2 skill，
> 说明"这是一次基于审计的定向重写"，listing-v2 会优先解决这些问题。

### 必须修复的缺口（按优先级）
1. [D1 缺口] 以下买家问题 listing 无法回答：...
2. [D2 缺口] COSMO 语义缺失：...（具体是哪类）
3. [D3 缺口] 缺少以下关键参数：...
4. [D4 缺口] 关键词堆砌问题集中在：...（引用原文位置）
5. [D5 缺口] 合规风险词需删除：...

### 可保留的亮点（不需要重写的部分）
- [字段名]：[具体内容]，建议保留原文

### 数据补充建议（listing-v2 需要但本次审计缺失的输入）
- [ ] 本品属性 / Product Fact Bank（用于 D3 数值核查 + 重写）
- [ ] 实际 Rufus/QA 问题素材（用于 D1 测试，提升得分上限至 10 分）
- [ ] 竞品 Listing（用于 Parity/Gap 分析）
```
