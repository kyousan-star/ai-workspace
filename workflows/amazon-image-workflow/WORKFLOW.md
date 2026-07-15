# Amazon Image Workflow

## 总体结构

```text
初始化项目工作区
  -> 并行研究
  -> Gate 1：图片策略确认
  -> 图片序列规划
  -> Gate 2：图片序列确认
  -> Brief / Prompt 生成
  -> 产品资产归档（阶段4.5）
  -> 生图或候选图导入
  -> 并行评估
  -> 迭代决策
  -> Gate 3：最终候选确认
  -> 最终交付
  -> 经验沉淀（含资产库回流）
```

## 阶段 0：初始化

目标：确保业务项目中存在标准项目工作区。

输出：

- `workflow_config.md`
- `01_WORKFLOW/status.md`
- `01_WORKFLOW/decisions.md`
- `01_WORKFLOW/run_log.md`

## 阶段 1：并行研究

可并行启动：

- 产品事实 Agent
- 竞品视觉 Agent
- VOC / 卖点 Agent
- 素材盘点 Agent
- 合规边界 Agent

输出：

- `02_RESEARCH/product_facts_locked.md`
- `02_RESEARCH/competitor_visual_analysis.md`
- `02_RESEARCH/voc_selling_points.md`
- `02_RESEARCH/asset_inventory.md`
- `02_RESEARCH/compliance_boundaries.md`

## 阶段 2：策略汇总

主控 Agent 汇总五个并行研究的输出，形成图片策略，然后停在 Gate 1。

### 各研究输出的消费规则

**读 `product_facts_locked.md`**
- 提取产品名称、外观约束、核心配件、功能边界，写入策略的"产品事实锁定"区块。
- 标注不确定项，Gate 1 前不得自行假设产品外观细节。

**读 `voc_selling_points.md`**
- 提取候选卖点列表，保留每个卖点的差异化程度、VOC 提及频率、视觉可感知性三个维度标注。
- 不自行排序，卖点优先级由 Gate 1 用户确认后锁定。

**读 `competitor_visual_analysis.md` Part 1（品类视觉惯例表）**
- 提取所有"标配程度：高"的条目，列入策略的"品类基准线"区块。
- 这些是本品图片方案必须覆盖的底线，不得遗漏。

**读 `competitor_visual_analysis.md` Part 3（竞品结构性问题清单）**
- 提取对本品有启示的问题条目，列入策略的"视觉规避方向"区块。
- Gate 1 向用户展示时作为"竞品已踩坑，本品不重复"的说明。

**竞品 Part 2（视觉手段候选库）不在此阶段消费。**
- Part 2 留给阶段4 Brief/Prompt Agent（或 amazon-image-planner-v3）在生成每张图 prompt 时按需引用。
- 策略汇总 Agent 不得用 Part 2 的手段来推导图序——图序由 Gate 1 用户确认的卖点优先级驱动。

**读 `compliance_boundaries.md`**
- 提取高风险项，写入策略的"合规边界"区块。
- 高风险项在 Gate 1 必须向用户明确展示。

**读 `asset_inventory.md`**
- 提取素材现状摘要（哪些可复用、哪些必须新拍、哪些需要 AI 生成），写入策略的"素材约束"区块。
- 素材约束会影响图序规划的可行性，阶段3图序规划 Agent 必须读此区块。

### 输出格式

`03_STRATEGY/image_strategy.md` 必须包含以下六个区块：

```
## 1. 产品事实锁定
（来自 product_facts_locked.md，含不确定项标注）

## 2. 候选卖点清单
（来自 voc_selling_points.md，含三维度标注，不排序）

## 3. 品类基准线
（来自竞品 Part 1，只列标配程度：高的条目）

## 4. 视觉规避方向
（来自竞品 Part 3，含对本品的启示说明）

## 5. 合规边界
（来自 compliance_boundaries.md，高风险项完整列出）

## 6. 素材约束
（来自 asset_inventory.md，按图片类型分类说明）
```

`03_STRATEGY/gate1_strategy_summary.md` 是面向用户的精简版，必须包含：
- 候选卖点清单（等待用户排序）
- 品类基准线确认项
- 视觉手段候选库摘要（从 Part 2 中筛选与高可感知性卖点匹配的条目，供用户否决）
- 竞品坑摘要
- 合规高风险项
- 待用户填写的视觉禁区

输出：

- `03_STRATEGY/image_strategy.md`
- `03_STRATEGY/gate1_strategy_summary.md`

然后停在 Gate 1。

## 阶段 3：图片序列规划

在 Gate 1 通过后执行。

### 输入与约束

图片序列 Agent 必须读取以下文件，按优先级顺序：

1. `03_STRATEGY/gate1_strategy_summary.md` — 读取用户锁定的卖点优先级，这是图序的唯一驱动来源。
2. `03_STRATEGY/image_strategy.md` 的"品类基准线"区块 — 确保高标配图位不遗漏。
3. `03_STRATEGY/image_strategy.md` 的"素材约束"区块 — 判断每张图的出图方式可行性。
4. `03_STRATEGY/image_strategy.md` 的"视觉规避方向"区块 — 图序规划时主动绕开竞品踩坑的方向。

**禁止**：图片序列 Agent 不得读取 `competitor_visual_analysis.md` Part 2（视觉手段候选库）来推导图序。手段选择属于阶段4的工作。

### 图序规划原则

- 图序顺序严格遵循 Gate 1 用户确认的卖点优先级，不得自行调整。
- 每张图只承担一个核心任务。
- 品类基准线中"标配程度：高"的图位必须全部覆盖，如有冲突在 `gate2_sequence_summary.md` 中标注。
- 素材约束影响出图方式（白底实拍 / 场景合成 / 信息图），每张图必须标注出图方式和素材来源。
- 素材缺口（需新拍或无法实现的合成）必须在图序中显式标注，不得假装能做到。

### 输出格式

`listing_image_sequence.md` 每行必须包含：

```
| 图位 | 主角卖点（来自 Gate 1 优先级） | 页面任务（一句话） | 出图方式 | 素材来源 / 缺口说明 |
|---|---|---|---|---|
| 主图 | 全套产品 | 一眼看清这是什么产品、包含什么 | 白底实拍 | 已有实拍图可用 |
| 副图1 | [Gate 1 第1优先级卖点] | [任务] | 场景合成 | 需新拍前侧45°白底图 |
| 副图2 | [Gate 1 第2优先级卖点] | [任务] | 信息图 | 无素材要求 |
```

`gate2_sequence_summary.md` 面向用户，必须包含：
- 完整图序表（同上格式）
- 素材缺口清单（需要新拍或采购的素材）
- 品类基准线覆盖确认（哪些标配已覆盖，有无遗漏）
- 有疑问的图位说明（如有）

输出：

- `04_IMAGE_SEQUENCE/listing_image_sequence.md`
- `04_IMAGE_SEQUENCE/aplus_image_sequence.md`
- `04_IMAGE_SEQUENCE/ad_creative_sequence.md`
- `04_IMAGE_SEQUENCE/gate2_sequence_summary.md`

然后停在 Gate 2。

## 阶段 4：Brief / Prompt

在 Gate 2 通过后执行。

### 必读输入（按顺序）

1. `03_STRATEGY/gate1_strategy_summary.md`
   - 读取用户锁定的卖点优先级
   - 读取用户否决的视觉手段条目（不得在 prompt 中引用被否决的手段）
   - 读取视觉禁区声明

2. `04_IMAGE_SEQUENCE/listing_image_sequence.md`（及 aplus / ad 序列）
   - 每张图的主角卖点、页面任务、出图方式，是 prompt 的任务输入
   - 图序不在此阶段更改

3. `02_RESEARCH/competitor_visual_analysis.md` Part 2（视觉手段候选库）
   - 这是 Part 2 在整个 workflow 中唯一被消费的阶段
   - 按每张图的页面任务，取对应信息类型的手段候选条目
   - 使用前提与本品情况匹配 → 引用；不匹配或用户已否决 → 不引用，说明原因

### 执行方式：调用 amazon-image-planner-v3

Brief/Prompt Agent 调用 `amazon-image-planner-v3` 执行，传入以下上下文：

- 图序：来自 `listing_image_sequence.md`（Phase 1.5 已锁定，跳过重新确认）
- 卖点优先级：来自 `gate1_strategy_summary.md`（已锁定）
- 视觉手段候选库：来自竞品 Part 2（已结构化，含使用前提列）
- 用户否决的手段：来自 `gate1_strategy_summary.md`（写入 STRICTLY AVOID）
- 视觉禁区：来自 `gate1_strategy_summary.md`（写入 STRICTLY AVOID）

v3 执行 Phase 0（停顿感评估）→ Phase 3（A/B 双 prompt 生成），跳过 Phase 1/1.5/2（上游已完成）。

每张图 prompt 输出时标注手段来源：引用 Part 2 第 X 条 / 原创构图。

### 执行原则

- 先写执行卡（构图思路、图内文字清单、验收标准），再写 prompt。
- 默认不让生图模型生成最终文字；文字、icon、箭头、尺寸线、免责声明后期添加。
- 每张图输出 A/B 双 prompt：方案 A 功能型，方案 B 停顿感型（T09/T10/T11）。
- 产品形态描述在第一张图锁定，全组图 A/B 两套方案全程一致。
- 每个 prompt 末尾加 STRICTLY AVOID 列表，包含：用户否决手段、视觉禁区、反踩坑规则。

### 输出格式

`image_briefs.md`：每张图一个执行卡，包含主角卖点、页面任务、构图思路（A/B）、图内文字清单（A/B）、手段来源标注、验收标准（A/B）。

`generation_prompts.md`：每张图 A/B 双 prompt，含 STRICTLY AVOID 列表。

`negative_prompts.md`：全组通用 negative prompt + 各图特殊 negative。

`acceptance_criteria.md`：逐图验收标准，B 方案额外检查停顿感有效性（反差合理？产品仍是主角？钩子文案 ≤6 词？）。

输出：

- `05_BRIEFS_PROMPTS/image_briefs.md`
- `05_BRIEFS_PROMPTS/generation_prompts.md`
- `05_BRIEFS_PROMPTS/negative_prompts.md`
- `05_BRIEFS_PROMPTS/acceptance_criteria.md`

## 阶段 4.5：产品资产归档

在阶段4完成后、阶段5生成前执行。调用 `product-asset-extractor`。

目的：把本项目锁定的 SKU 产品形态、参考角色和抠图任务沉淀进 `visual-lab/product-library/{product-line}/skus/{sku}/`，品牌规则引用 `brand-library/{brand}/`，而不是继续写入旧 `asset-library`。

### 输入

- `02_RESEARCH/product_facts_locked.md` — 形态锁定描述
- `00_INPUT/product_photos/` — 实拍图（如尚未抠图）
- `00_INPUT/brand_guide.md` / `00_INPUT/brand_assets/` — 品牌风格

### 执行规则

- 若 SKU 目录已存在，检查本项目产品形态是否与已锁定描述一致：一致则直接复用；有差异则更新并标注证据和原因。
- 若不存在，从 `product-library/_template/skus/_template/` 建立 SKU 目录。
- `asset-library` 只允许作为历史资料读取，不得新增或更新。
- 环境没有内部抠图API，本阶段只产出抠图任务清单交给外部工具/人工处理，不假装能自动完成。

### 输出

- `visual-lab/product-library/{product-line}/skus/{sku}/product-facts-locked.md`（新建或更新）
- `visual-lab/product-library/{product-line}/skus/{sku}/reference-pack.md`（来源、角色和可见范围）
- `visual-lab/product-library/{product-line}/skus/{sku}/cutout-task-list.md`（待处理）
- `visual-lab/product-library/{product-line}/skus/{sku}/metadata.json`
- 品牌规则只记录 `visual-lab/brand-library/{brand}/` 引用，不在产品目录复制

不设独立Gate——本阶段是归档动作，不引入新的决策点，若发现形态描述有分歧则在阶段5生成前提醒用户确认。

## 阶段 5：生成 / 候选图导入

如果环境支持生图，可以批量生成。

如果用户已有候选图，则导入 `06_GENERATIONS/`。

输出：

- `06_GENERATIONS/generation_log.md`
- 候选图片或候选图片路径清单。

## 阶段 6：并行评估

评估维度：

- 产品准确性
- 合规风险
- 卖点清晰度
- 构图和移动端可读性
- 品牌一致性
- 技术质量
- 转化潜力

输出：

- `07_EVALUATION/evaluation_report.md`
- `07_EVALUATION/candidate_ranking.md`

## 阶段 7：迭代决策

根据评分决定：

- pass：进入后期或最终候选。
- revise：小修 1-2 个问题。
- regenerate：重写 prompt 再生成。
- recompose：重构构图。
- reject：放弃该方向。

输出：

- `08_ITERATION/iteration_plan.md`
- `08_ITERATION/revised_prompts.md`
- `08_ITERATION/iteration_log.md`

## 阶段 8：最终确认

主控 Agent 汇总最终候选并停在 Gate 3。

输出：

- `09_FINAL/final_candidate_summary.md`
- `09_FINAL/final_delivery_checklist.md`

## 阶段 9：经验沉淀

项目结束后记录：

- 成功 prompt
- 失败 prompt
- 可复用构图
- 禁止元素
- 类目图片经验

输出（项目内）：

- `10_LEARNINGS/lessons_learned.md`
- `10_LEARNINGS/prompt_library.md`
- `10_LEARNINGS/failure_patterns.md`

### 必须回流到 Campaign 与中央资产治理

项目内 `10_LEARNINGS/` 只对本项目可见。本阶段先把项目上下文完整写入对应 Campaign；只有经过验证、适合跨项目复用的资产才进入中央 Registry：

- 实际上线/过审的构图、成功与失败 Prompt → `visual-lab/campaign-library/{campaign}/learnings/`
- 可复用产品事实和参考角色 → 对应 `product-library/{product-line}/skus/{sku}/`
- 候选可复用图片 → 通过 `asset-curator` 登记到 `asset-registry.json`，默认只能是 `candidate`
- `approved`、`published`、`validated` 和 `retired` 仍需人工 Promotion Gate

只写项目内文件、不回写 Campaign，视为本阶段未完成。不得直接写旧 `asset-library`。
