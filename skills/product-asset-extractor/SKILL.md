---
name: product-asset-extractor
description: 把一个产品的实拍图/参考图整理成跨项目可复用的标准资产——产品形态锁定描述、抠图任务清单、品牌风格记录，写入 visual-lab/asset-library/{product-line}/。对应"AI辅助视觉生产工作流"里的"AI产品提取"环节。当用户说"提取产品资产"、"建产品资产库"、"锁定产品形态"、"这个产品线建个资产库"、或在 amazon-image-workflow 阶段4.5被调用时触发。
last_verified: 2026-07-01
staleness_risk: medium
---

# Product Asset Extractor

**解决的问题**：现有 `amazon-image-workflow` 每次都从实拍图里重新描述产品形态、重新挑构图，项目结束后这些描述留在项目文件夹里死掉。这个skill把"产品形态锁定"和"抠图归档"做成跨项目一次做、多次用的资产。

**本环境没有内部抠图API**——不自动处理图像，只做：(1) 用vision直接读实拍图写出形态锁定描述，(2) 生成抠图任务清单交给外部工具/人工处理，(3) 把处理结果归档进资产库结构。

---

## Phase 0：判断 product-line 是否已存在

先问用户这个产品属于哪个 product-line（如 `cellphone-tripod`、`vlogging-kit`），检查 `visual-lab/asset-library/{product-line}/` 是否已存在：

- **已存在**：读取现有 `product-facts-locked.md`，向用户展示，问是否是同一形态的新SKU（可直接复用）还是形态有变化需要更新。不重新提取已锁定的内容。
- **不存在**：进入 Phase 1，从 `visual-lab/asset-library/_template/` 复制骨架新建。

---

## Phase 1：读取实拍图，写形态锁定描述

扫描项目 `00_INPUT/product_photos/`（或用户直接提供的图片路径）。

对每张图用vision提取：
- 尺寸比例、主体颜色、材质（明确写"银/铬色"而非"金色"以避免生锈感，除非产品实际是金色）
- 关键结构位置：按键、接口、logo、活动部件
- 哪些细节因为角度/清晰度**看不清**——标注为"不确定项"，不得自行假设

写入 `product-facts-locked.md`：
- 形态描述（可直接进prompt的英文句子）
- 规格表
- 不确定项清单（必须等用户在Gate确认，不能跳过）

这一步产出与 `workflows/amazon-image-workflow` 阶段2的 `product_facts_locked.md` 应保持一致描述，避免两处形态描述打架。

---

## Phase 2：抠图任务清单

不自动生成透明背景图，而是输出一份任务清单，格式：

```
| 素材源文件 | 需要的抠图角度 | 交给什么工具处理 | 处理后存放路径 |
|---|---|---|---|
| product1.jpg | front | remove.bg / Codex image | cutouts/{sku}_front.png |
| product2.jpg | 45° | 同上 | cutouts/{sku}_45.png |
```

告知用户：处理完把文件放进 `visual-lab/asset-library/{product-line}/cutouts/`，按`{sku}_{角度}.png`命名，之后本skill可以整理归档索引。

若用户已经有抠图结果文件，直接检查命名规范并归位，不重复要求。

---

## Phase 3：品牌风格记录（如项目提供了品牌资料）

若有品牌色板/字体/风格关键词/logo，写入 `brand-style.md`。若 AI-Canvas 里已有该产品线的品牌资产（如某个canvas存了品牌调性探索），提醒用户同步关键结论过来，而不是只读canvas。

---

## Phase 4：写 metadata.json，Hand-off

更新 `metadata.json`（product_line、skus、linked_projects、last_updated）。

向用户汇报：
1. 新建/复用了哪个product-line
2. 形态锁定描述里有哪些不确定项需要确认
3. 抠图任务清单（待外部处理的部分）
4. 下一步：`batch-asset-generator` 可以直接用这份资产库做批量场景矩阵；或继续走 `amazon-image-workflow` 阶段5单张精修
