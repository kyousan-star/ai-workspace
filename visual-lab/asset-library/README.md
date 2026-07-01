# Asset Library

跨项目复用的视觉资产库，按**产品线**归档。解决的问题：`workflows/amazon-image-workflow` 每次跑完一个项目，产品形态描述、抠图、过审构图、成功prompt都只留在项目文件夹的`10_LEARNINGS/`里，下次同产品线新SKU/新场景要重新来一遍。这里是回流终点。

## 目录结构

```
asset-library/
  {product-line}/                  # 如 cellphone-tripod/、vlogging-kit/
    product-facts-locked.md        # 形态锁定描述（尺寸/颜色/材质/按键位置）
    brand-style.md                 # 品牌色板/字体/风格关键词/logo路径
    cutouts/                       # 标准化产品抠图，命名: {sku}_{front|45|top|side}.png
    approved-compositions.md       # 过审构图+prompt，按卖点打标
    prompt-library.md              # 成功/失败prompt记录
    metadata.json                  # {"product_line", "skus": [], "linked_projects": [], "last_updated"}
```

模板骨架见 `_template/`，新建产品线时复制这个文件夹改名。

## product-line 怎么定义

以"外观和核心功能高度相似、可共用同一套产品形态描述和构图"为界，不是以SKU为界。例如"手机三脚架"下不同长度/颜色的多个SKU算同一个product-line；但如果新品外观结构完全不同（如从三脚架变成磁吸支架），要开新的product-line。

## 与 workflows/amazon-image-workflow 的衔接

- **阶段4.5（产品资产归档）**：项目内`02_RESEARCH/product_facts_locked.md`产出后，若`asset-library/{product-line}/`已存在，直接复用跳过重新提取；若不存在，由`product-asset-extractor`新建。
- **阶段9（经验沉淀）**：项目结束时，除了写项目内`10_LEARNINGS/`，必须把可复用的构图和prompt回写进对应product-line的`approved-compositions.md`和`prompt-library.md`。不回写=这次项目的经验下次用不上。

## 与 AI-Canvas 的关系

AI-Canvas（`plugins/AI-Canvas/`）是通用画布工具，不专属Amazon品类。如果某个canvas里积累的其实是某条产品线的品牌资产（例如品牌logo/调性、竞品参考图），应额外把关键文件同步一份到对应`asset-library/{product-line}/brand-style.md`或`cutouts/`，不要让它只活在孤立的canvas数据里（`visual-lab/ai-canvas-data/canvases/`按canvas ID存储，没有按产品线索引）。
