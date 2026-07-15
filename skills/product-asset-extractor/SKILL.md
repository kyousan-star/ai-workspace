---
name: product-asset-extractor
description: 把产品实拍图和参考图整理成跨项目可复用的 SKU 事实、参考角色和抠图任务，写入 visual-lab/product-library/{product-line}/skus/{sku}/，品牌规则只引用 brand-library。对应 amazon-image-workflow 阶段4.5。触发词：提取产品资产、建产品资产库、锁定产品形态、产品线资产库。
last_verified: 2026-07-14
staleness_risk: medium
---

# Product Asset Extractor

**解决的问题**：现有 `amazon-image-workflow` 每次都从实拍图里重新描述产品形态、重新挑构图，项目结束后这些描述留在项目文件夹里。这个 skill 把 SKU 级“产品形态锁定”和“抠图归档”做成跨项目一次做、多次用的资产。

**本环境没有内部抠图API**——不自动处理图像，只做：(1) 用vision直接读实拍图写出形态锁定描述，(2) 生成抠图任务清单交给外部工具/人工处理，(3) 把处理结果归档进资产库结构。

---

## Phase 0：确定品牌、product-line 和 SKU

确认品牌、product-line 和 SKU，检查 `visual-lab/product-library/{product-line}/skus/{sku}/` 是否已存在：

- **已存在**：读取现有 `product-facts-locked.md` 和 `reference-pack.md`，核对是否需要补充或更新，不重复提取已锁定内容。
- **不存在**：从 `visual-lab/product-library/_template/skus/_template/` 建立 SKU 目录；不得从旧 `asset-library` 模板创建新项目。
- `visual-lab/asset-library/` 仅允许读取历史资料，禁止新增或更新。

---

## Phase 1：读取实拍图，写形态锁定描述

扫描项目 `00_INPUT/product_photos/`（或用户直接提供的图片路径）。

对每张图用vision提取：
- 尺寸比例、主体颜色、材质（明确写"银/铬色"而非"金色"以避免生锈感，除非产品实际是金色）
- 关键结构位置：按键、接口、logo、活动部件
- 哪些细节因为角度/清晰度**看不清**——标注为"不确定项"，不得自行假设

写入 `visual-lab/product-library/{product-line}/skus/{sku}/product-facts-locked.md`：
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

任务清单写入 `visual-lab/product-library/{product-line}/skus/{sku}/cutout-task-list.md`。处理后的文件放入同一 SKU 目录下的 `cutouts/`，按 `{sku}_{角度}.png` 命名；在 `reference-pack.md` 登记来源、参考角色和可见范围。

若用户已经有抠图结果文件，直接检查命名规范并归位，不重复要求。

---

## Phase 3：品牌规则引用（如项目提供了品牌资料）

若有品牌色板、字体、风格关键词或 Logo，只核对并引用 `visual-lab/brand-library/{brand}/`。不得在 SKU 目录新建 `brand-style.md`，也不得从项目资料静默改写 approved 品牌规则。未登记资料交给 `brand-system-builder` 或 `asset-curator` 处理。

---

## Phase 4：写 metadata.json，Hand-off

更新 SKU 目录内 `metadata.json`（brand、product_line、sku、linked_projects、last_updated），并保持 `reference-pack.md` 与事实库同步。

向用户汇报：
1. 新建或复用了哪个 SKU 资产目录
2. 形态锁定描述里有哪些不确定项需要确认
3. 抠图任务清单（待外部处理的部分）
4. 引用的品牌库路径和未登记品牌资料
5. 下一步：继续走 `amazon-image-workflow` 阶段5，或由后续工作台生成 Image Contract
