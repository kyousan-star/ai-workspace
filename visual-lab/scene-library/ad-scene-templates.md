# 广告场景模板库

> 按投放渠道组织。每个场景条目描述"基调+尺寸+背景类型"，具体卖点表达手法交给 T01-T11（`amazon-image-toolkit/resources/composition-templates.md`）或product-line自己的`approved-compositions.md`去填。

## 如何使用

1. 选投放渠道 → 定尺寸和基调
2. 选卖点构图手法（复用T-系列或product-line已验证构图）
3. 把product-line的`cutouts/`产品抠图作为素材层，套进本模板的构图骨架
4. 输出的是**一批**prompt，不是一张——批量矩阵的"批量"来自渠道×卖点×风格的组合枚举，不是重新设计

---

## Amazon Sponsored / Listing 附属广告

**尺寸**：1200×628（横版信息流）/ 1600×2000（竖版详情页）

**基调**：与listing图一致，理性说服为主，可直接复用`composition-templates.md`里已验证的T模板

---

## TikTok / TikTok Shop

**尺寸**：1080×1920（9:16 全屏竖版）

**基调**：
- 强调"停顿感"（真人手持/生活场景优先于纯白底图）
- 前3帧要素：产品在画面中即时可辨识，避免纯文字开场
- 可套用 T09（产品存在感）/ T11（焦虑场景叙事）——这两个模板本身就是为"停下来"设计的
- 背景优先真实生活场景（卧室/通勤/户外自拍视角），不用纯白摄影棚背景

**STRICTLY AVOID**：过度商业感的摄影棚布光、大段说明性文字覆盖、明显广告感构图

---

## Meta（Facebook/Instagram）Feed & Story

**尺寸**：Feed 1080×1080（1:1）/ Story 1080×1920（9:16）

**基调**：
- Feed：产品+场景平衡，可用T05（多对一/场景化）、T08（多场景网格）
- Story：接近TikTok基调，但可以稍微保留品牌感排版（Meta用户对"广告感"容忍度略高于TikTok）

---

## Pinterest

**尺寸**：1000×1500（2:3）

**基调**：
- 生活方式/美学优先，弱化促销文案，强调"这个场景我也想要"
- 适合T05（多对一场景）、T07（续航/场景缩略图，改成"一天生活场景"叙事）
- 参考 `visual-lab/ai-canvas-data/canvases/canvas_C1DC6uXBzG` 里VLOGARA tripod的Pinterest pin做法（已有真实积累，建议同步进对应product-line的`approved-compositions.md`）

---

## 附录：如何新增渠道

按以下格式追加：

```markdown
## {渠道名}

**尺寸**：

**基调**：

**STRICTLY AVOID**（如有渠道特殊限制，如TikTok对纯广告感的算法惩罚）：
```
