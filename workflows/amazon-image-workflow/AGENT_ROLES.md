# Agent Roles

## 主控 Agent

职责：

- 初始化项目工作区。
- 读取 workflow 文件和项目输入。
- 拆分任务并调度可并行子 Agent。
- 汇总结果。
- 维护状态文件。
- 在 Gate 节点停下来让用户确认。

输出：

- `01_WORKFLOW/status.md`
- `01_WORKFLOW/decisions.md`
- `01_WORKFLOW/run_log.md`
- 各阶段汇总文件。

## 产品事实 Agent

职责：

- 从产品资料、实拍图、规格、旧图中锁定产品事实。
- 标出不可改变的外观、结构、材质、配件和功能。
- 标出不确定项。

输出：

- `02_RESEARCH/product_facts_locked.md`

## 竞品视觉 Agent

职责：

- 拆解竞品主图、副图、A+ 图。
- 输出结构化的三部分分析，供策略汇总 Agent、图序规划 Agent、Brief/Prompt Agent 读取。

**重要边界**：竞品分析只回答"竞品用了什么手段、结构上有什么问题、使用某手段需要什么前提"。不输出"这个手段转化效果好/差"的效果判断——agent 没有真实转化数据，无法做效果层判断。竞品分析结果用于提取视觉手段，不用于决定本品图序（图序由 Gate 1 用户确认的卖点优先级驱动）。

输出：`02_RESEARCH/competitor_visual_analysis.md`，必须包含以下三个 Part：

---

### Part 1：品类视觉惯例表

回答：这个品类里有哪些视觉表达是用户已有预期的，不做会让用户觉得"少了点什么"。

输出格式：

```
| 信息类型 | 品类标配程度（高/中/低） | 主要竞品覆盖率 | 不做的风险 |
|---|---|---|---|
| 示例：产品白底主图 | 高 | 100% | 不符合亚马逊主图规则，直接下架风险 |
| 示例：使用场景图 | 高 | 90%+ | 用户无法感知使用情境，降低购买意愿 |
| 示例：成分/机制图 | 中 | 60% | 视品类而定，功能性品类缺失会降低信任 |
```

用途：策略汇总 Agent 读此表，确保本品策略覆盖所有高标配项，不遗漏基准线。

---

### Part 2：视觉手段候选库

回答：竞品用了哪些具体的视觉表达手段，本品在对应信息类型上可以参考哪些手段。

**格式要求**：按信息类型归类，跨所有竞品汇总，不是每个竞品单独一行。

输出格式：

```
| 信息类型 | 手段描述 | 来源竞品编号 | 结构层观察 | 使用前提（需用户对照本品判断） |
|---|---|---|---|---|
| 示例：痛点呈现 | 声波对比图，红色噪声道vs绿色人声道 | 竞品A、C | 零阅读成本，颜色即结论；信息密度高时辅助文字不可省 | 前提：降噪是本张图核心任务；有视觉素材支撑对比 |
| 示例：使用场景 | 前侧45°双人合成，灯光打脸+屏幕朝向镜头 | 竞品B | 能同时展示灯光面和屏幕；背面机位会遮挡核心卖点 | 前提：有符合机位的场景素材或计划专门拍摄 |
```

用途：Brief/Prompt Agent（或 amazon-image-planner-v3）读此表，每张图按页面任务取对应行的手段，手段匹配则引用，不匹配则不用，不强行套用。

---

### Part 3：竞品结构性问题清单

回答：竞品图中有哪些结构层面可以观察到的问题，对本品规划有什么启示。

**格式要求**：只写结构层能观察到的问题（视觉焦点、主次关系、卖点与画面对齐度、机位约束等），不写"转化差""效果不好"等效果层判断。

输出格式：

```
| 竞品编号 | 图位 | 结构性问题描述 | 对本品的启示 |
|---|---|---|---|
| 示例：竞品A | 副图2 | 产品被场景元素遮挡超过30%，无法看清核心部件 | 本品合成图需确保产品主体完整可见，场景元素退至背景 |
| 示例：竞品C | 主图 | 背景非纯白，违反亚马逊主图规则 | 本品主图必须纯白底，无例外 |
| 示例：竞品B | 副图3 | 文案堆叠7个卖点，移动端字号不可读 | 本品每张图文案控制在3个信息点以内 |
```

用途：策略汇总 Agent 读此表，在 `image_strategy.md` 中标注需要主动避开的方向；Gate 1 向用户展示时作为"竞品已踩坑，本品不重复"的说明。

## VOC / 卖点 Agent

职责：

- 从 Review、QA、VOC 报告、竞品文案中提炼用户关注点。
- 按用户关注度、竞品覆盖、差异化、可视化潜力排序卖点。

输出：

- `02_RESEARCH/voc_selling_points.md`

## 素材盘点 Agent

职责：

- 盘点实拍图、工厂图、旧 listing 图、其他站点图、logo、字体、品牌资产。
- 判断每张图可直接复用、改造、AI 生成背景、局部编辑或必须新拍。

输出：

- `02_RESEARCH/asset_inventory.md`

## 合规边界 Agent

职责：

- 标出主图规则、平台限制、claim 风险、敏感词、夸大表达和需要人工确认的合规点。

输出：

- `02_RESEARCH/compliance_boundaries.md`

## 图片序列 Agent

职责：

- 读取 `gate1_strategy_summary.md` 中用户锁定的卖点优先级，以此为唯一图序驱动来源。
- 读取 `image_strategy.md` 的品类基准线、素材约束、视觉规避方向三个区块。
- 将卖点优先级转成主图、副图、A+、广告素材的图片序列。
- 每张图只设一个核心任务。
- 标注每张图的出图方式（白底实拍 / 场景合成 / 信息图）和素材来源。
- 显式标注素材缺口，不得假设素材存在。

**禁止**：不得读取 `competitor_visual_analysis.md` Part 2 手段库来推导图序，手段选择属于阶段4。

输出格式：每张图必须包含图位、主角卖点、页面任务、出图方式、素材来源/缺口说明五列。

输出：

- `04_IMAGE_SEQUENCE/listing_image_sequence.md`
- `04_IMAGE_SEQUENCE/aplus_image_sequence.md`
- `04_IMAGE_SEQUENCE/ad_creative_sequence.md`

## Brief / Prompt Agent

职责：

- 读取 `gate1_strategy_summary.md`，提取卖点优先级、用户否决的手段条目、视觉禁区。
- 读取 `listing_image_sequence.md`（及 aplus / ad 序列），获取每张图的页面任务和出图方式。
- 读取 `competitor_visual_analysis.md` Part 2，按每张图的页面任务取对应手段候选条目。
- 调用 `amazon-image-planner-v3` 执行 A/B 双 prompt 生成（传入上游已锁定的图序和卖点优先级，跳过 v3 的 Phase 1/1.5/2）。
- 为每张图标注手段来源（引用 Part 2 第 X 条 / 原创构图）。
- 用户否决的手段和视觉禁区写入每个 prompt 的 STRICTLY AVOID 列表。

**边界**：不更改图序，不重新排卖点优先级，不替用户做手段效果判断。

输出：

- `05_BRIEFS_PROMPTS/image_briefs.md`（每张图执行卡，含 A/B 构图思路、文字清单、手段来源、验收标准）
- `05_BRIEFS_PROMPTS/generation_prompts.md`（每张图 A/B 双 prompt，含 STRICTLY AVOID）
- `05_BRIEFS_PROMPTS/negative_prompts.md`（全组通用 + 各图特殊 negative prompt）
- `05_BRIEFS_PROMPTS/acceptance_criteria.md`（逐图验收标准，B 方案含停顿感有效性检查）

## 质检 Agent 组

建议并行分工：

- 产品准确 Judge
- 合规 Judge
- 卖点清晰 Judge
- 构图 / 移动端 Judge

输出：

- `07_EVALUATION/evaluation_report.md`
- `07_EVALUATION/candidate_ranking.md`

## 迭代 Agent

职责：

- 根据评估结果决定小修、重生成、重构或放弃。
- 每轮只修 1-3 个关键问题。
- 连续两轮无明显改善时停止微调，改为重构。

输出：

- `08_ITERATION/iteration_plan.md`
- `08_ITERATION/revised_prompts.md`
- `08_ITERATION/iteration_log.md`

