---
name: batch-asset-generator
description: 用某个产品线在 asset-library 里已沉淀的产品资产（形态锁定/抠图/品牌风格/过审构图），交叉 visual-lab/scene-library 的渠道场景模板，批量产出"场景×卖点×渠道"的prompt矩阵，用于铺量广告素材。对应"AI辅助视觉生产工作流"里的"批量资产生产"环节。当用户说"批量出图prompt"、"铺量素材"、"做广告矩阵"、"给这个产品线批量生成素材"时触发。不适用于单SKU精修listing图（用 amazon-image-planner-v2/v3）。
last_verified: 2026-07-01
staleness_risk: medium
---

# Batch Asset Generator

**解决的问题**：现有流程是"1个SKU精修6张listing图"，没有"1个产品 × N场景 × M渠道"批量出prompt的能力。这个skill不生成图片本身（环境没有内部生图API），只批量生成**可直接分发去外部工具跑的prompt矩阵**，把"每张图重新设计"这个人力活自动化掉。

---

## 前置条件

`visual-lab/asset-library/{product-line}/` 必须已存在且完整（形态锁定+抠图+品牌风格）。若不存在，先调用 `product-asset-extractor`，不得跳过直接假设产品形态。

---

## Phase 1：确认矩阵维度

向用户确认三个维度（一次性问清，不分多轮）：

1. **产品线**：用哪个 `asset-library/{product-line}/`
2. **投放渠道**：读 `visual-lab/scene-library/ad-scene-templates.md`，列出可选渠道（Amazon Sponsored / TikTok / Meta / Pinterest），问要覆盖哪几个
3. **卖点**：读 `asset-library/{product-line}/approved-compositions.md`（已验证构图）+ `amazon-image-toolkit/resources/composition-templates.md`（T01-T11通用模板），列出可用卖点表达手法，问优先覆盖哪几个

矩阵规模 = 渠道数 × 卖点数（不擅自扩大，避免产出用户用不完的量）。

---

## Phase 2：交叉生成

对矩阵里每个（渠道, 卖点）组合：

1. 从 `product-facts-locked.md` 取统一形态描述（全矩阵一致，不漂移）
2. 从 `ad-scene-templates.md` 取该渠道的尺寸+基调
3. 从 `approved-compositions.md`（优先，已验证过）或 `composition-templates.md`（T系列）取该卖点的构图骨架
4. 从 `brand-style.md` 取色板/风格关键词
5. 拼出完整prompt，末尾加 STRICTLY AVOID（复用 `anti-pitfall-rules.md`）

**不引用**用户在该产品线历史项目中已否决的手段（若`approved-compositions.md`或项目`gate1_strategy_summary.md`有记录）。

---

## Phase 3：输出

生成一份矩阵表 + 对应prompt清单：

```
| # | 渠道 | 尺寸 | 卖点 | 构图来源 | Prompt |
|---|------|------|------|----------|--------|
| 1 | TikTok | 1080x1920 | 降噪 | T01 | ... |
| 2 | Meta Feed | 1080x1080 | 降噪 | T01 | ... |
```

保存为 `{product-line}_batch_prompts_{YYYY-MM-DD}.html`（沿用amazon-image-planner系列的HTML交付风格，每条prompt带copy按钮），存到用户workspace，不是outputs/。

---

## Phase 4：Hand-off

1. 文件路径
2. 提醒：这批prompt仍需人工/Codex外部逐条生成，本skill只负责批量设计不负责批量出图
3. 出图后建议走 `product-consistency-checker` 做跨渠道产品一致性检查（矩阵量大，走形风险比单SKU精修更高）
4. 生成效果好的组合，回写进 `asset-library/{product-line}/approved-compositions.md`，供下次同产品线批量复用
