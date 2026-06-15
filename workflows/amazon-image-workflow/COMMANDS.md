# Amazon Image Workflow 快速复制指令

使用方法：

1. 复制下面任意一段指令。
2. 把 `PROJECT_ROOT` 替换成具体业务项目根目录。
3. 发给 Codex / ChatGPT。

中央工作流包路径固定为：

```text
/Users/lihuan/ai-workspace/workflows/amazon-image-workflow/
```

---

## 指令 0：最短启动版

```text
请使用 Amazon Image Workflow。

业务项目根目录：
PROJECT_ROOT

请读取中央工作流包：
/Users/lihuan/ai-workspace/workflows/amazon-image-workflow/

如果 PROJECT_ROOT/ai_image_workflow/ 不存在，请从中央模板 templates/project/ 初始化项目工作区。

然后读取 PROJECT_ROOT/ai_image_workflow/workflow_config.md 和 00_INPUT/ 下的资料，按 workflow 自动推进到下一个 Gate。

所有项目结果只写入 PROJECT_ROOT/ai_image_workflow/，不要写入中央 workflow 包。
```

---

## 指令 1：新项目启动，自动推进到 Gate 1

```text
请使用 Amazon Image Workflow。

业务项目根目录：
PROJECT_ROOT

中央工作流包路径：
/Users/lihuan/ai-workspace/workflows/amazon-image-workflow/

执行要求：
1. 如果 PROJECT_ROOT/ai_image_workflow/ 不存在，请从中央工作流包的 templates/project/ 初始化项目工作区。
2. 如果 workflow_config.md 不存在，请从 templates/input_files/workflow_config.md 创建一份到 PROJECT_ROOT/ai_image_workflow/workflow_config.md，并根据当前项目路径填入默认值。
3. 读取 MASTER_AGENT_PROMPT.md、WORKFLOW.md、AGENT_ROLES.md、GATE_RULES.md、PROJECT_FOLDER_CONTRACT.md。
4. 读取 PROJECT_ROOT/ai_image_workflow/workflow_config.md 和 00_INPUT/ 下的资料。
5. 你是主控 Agent，请自动推进到 Gate 1：图片策略确认。
6. 能并行的子 Agent 并行执行。
7. 所有结果只写回 PROJECT_ROOT/ai_image_workflow/。
8. 不要把项目产出写入中央 workflow 包。
9. Gate 1 前不要反复问我，除非缺失信息会导致产品事实错误或高风险合规错误。
10. 完成后更新 01_WORKFLOW/status.md、decisions.md、run_log.md。
```

---

## 指令 2：Gate 1 通过，继续到 Gate 2

```text
请使用 Amazon Image Workflow。

业务项目根目录：
PROJECT_ROOT

Gate 1 通过。

请读取 PROJECT_ROOT/ai_image_workflow/01_WORKFLOW/status.md，从当前阶段继续，推进到 Gate 2：图片序列确认。

所有项目结果只写入 PROJECT_ROOT/ai_image_workflow/，不要写入中央 workflow 包。
```

---

## 指令 3：Gate 2 通过，生成 Brief 和 Prompt

```text
请使用 Amazon Image Workflow。

业务项目根目录：
PROJECT_ROOT

Gate 2 通过。

请读取：
- PROJECT_ROOT/ai_image_workflow/01_WORKFLOW/status.md
- PROJECT_ROOT/ai_image_workflow/03_STRATEGY/gate1_strategy_summary.md（卖点优先级、否决手段、视觉禁区）
- PROJECT_ROOT/ai_image_workflow/04_IMAGE_SEQUENCE/listing_image_sequence.md（图序和页面任务）
- PROJECT_ROOT/ai_image_workflow/02_RESEARCH/competitor_visual_analysis.md Part 2（视觉手段候选库）

调用 amazon-image-planner-v3 执行阶段4，传入以下上下文：
- 图序来自 listing_image_sequence.md（已锁定，跳过 v3 Phase 1/1.5/2）
- 卖点优先级来自 gate1_strategy_summary.md（已锁定）
- 手段候选库来自竞品 Part 2（按页面任务匹配引用）
- 否决手段和视觉禁区来自 gate1_strategy_summary.md（写入每个 prompt 的 STRICTLY AVOID）

每张图输出 A/B 双 prompt（方案A功能型，方案B停顿感型），标注手段来源。

所有项目结果只写入 PROJECT_ROOT/ai_image_workflow/，不要写入中央 workflow 包。
```

---

## 指令 4：断点续跑

```text
请使用 Amazon Image Workflow。

业务项目根目录：
PROJECT_ROOT

请读取 PROJECT_ROOT/ai_image_workflow/01_WORKFLOW/status.md，从当前阶段继续。

不要从头开始。所有新结果写回 PROJECT_ROOT/ai_image_workflow/。
不要把项目产出写入中央 workflow 包。
```

---

## 指令 5：只做图片诊断

```text
请使用 Amazon Image Workflow 的 diagnosis_only 模式。

业务项目根目录：
PROJECT_ROOT

只诊断当前图片，不重新规划整套图片。

请读取：
- PROJECT_ROOT/ai_image_workflow/00_INPUT/current_listing_images/
- PROJECT_ROOT/ai_image_workflow/00_INPUT/competitor_images/
- PROJECT_ROOT/ai_image_workflow/01_WORKFLOW/status.md（如存在）
- PROJECT_ROOT/ai_image_workflow/04_IMAGE_SEQUENCE/listing_image_sequence.md（如存在）

输出图片诊断报告、问题优先级、迭代 brief 和是否需要回到前序流程的建议。

所有结果写入 PROJECT_ROOT/ai_image_workflow/07_EVALUATION/ 和 08_ITERATION/。
```

---

## 指令 6：只生成 Brief 和 Prompt

```text
请使用 Amazon Image Workflow 的 prompt_only 模式。

业务项目根目录：
PROJECT_ROOT

不要重新做竞品分析和卖点排序。

请基于 PROJECT_ROOT/ai_image_workflow/04_IMAGE_SEQUENCE/listing_image_sequence.md，输出每张图的设计 brief、生图 prompt、negative prompt、后期合成指引和验收标准。

结果写入 PROJECT_ROOT/ai_image_workflow/05_BRIEFS_PROMPTS/。
```

---

## 指令 7：初始化空项目工作区

```text
请使用 Amazon Image Workflow。

业务项目根目录：
PROJECT_ROOT

只做初始化：
1. 如果 PROJECT_ROOT/ai_image_workflow/ 不存在，请从中央工作流包的 templates/project/ 初始化。
2. 从 templates/input_files/ 复制输入文件模板到 PROJECT_ROOT/ai_image_workflow/00_INPUT/。
3. 从 templates/input_files/workflow_config.md 创建 PROJECT_ROOT/ai_image_workflow/workflow_config.md。
4. 初始化 01_WORKFLOW/status.md、decisions.md、run_log.md。

不要开始分析。
```

