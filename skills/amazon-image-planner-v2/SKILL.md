---
name: amazon-image-planner-v2
description: 为亚马逊产品规划图片方案，每张图输出 A/B 双 prompt——方案A传统功能型，方案B停顿感型（产品存在感/反差感/焦虑场景叙事）。用于制作差异化图片或 A/B test。当用户说"用v2规划图"、"A/B生图方案"、"试试西西酱打法"、"stopping power版本"、"做双方案图规划"时触发。
last_verified: 2026-06-04
staleness_risk: medium
---

# Amazon Image Planner v2

> **内容源（source of truth）**：`ai-workspace/amazon-image-toolkit/skills/product-image-planner-v2/SKILL.md`。本文件是部署适配版（中文 frontmatter + 精简 references）；内容改动**先改 source 再同步到这里**，不要只改这份。`references/` 是 toolkit `resources/` 完整库的 v2 专用精简版（T09-T11 + 防坑要点），toolkit 完整库变更时需同步两处（v3 的 references 同源，一并同步）。

每张图输出 **A/B 双 prompt**：
- **方案 A**：传统功能型（讲清楚卖点）
- **方案 B**：停顿感型（让用户先停下来）

两套方案分别生图，可放到不同 listing 槽位做 A/B test。

---

## Phase 0：停顿感评估（先于读文件）

在扫描 workspace 之前，内部完成产品类型判断，确定每张图的方案 B 推荐模板。

**每张图先问自己两个问题**：
1. 这张图的主要任务是什么？——`功能说明`（让用户理解卖点/参数/用法）还是 `停顿钩子`（让用户刷图时停下来，产生"咦，这个不一样"）
2. 如果用停顿钩子打法，这个产品适合哪种？

**推荐逻辑**：

| 产品特征 | 推荐方案 B 模板 | 理由 |
|----------|---------------|------|
| 小型手持品、美妆、女性生活方式 | T09 产品存在感型 | 产品天然适合"递向镜头"的存在感构图 |
| 有强烈品类刻板印象（电竞/工具/收纳） | T10 反差感型 | 刻板印象越强，反差张力越大 |
| 解决具体痛点/风险（防护/防丢/防漏/防摔） | T11 焦虑场景叙事型 | 痛点可视化比功能说明更有说服力 |
| 纯技术参数驱动、理性决策品类 | 方案 B 仍用功能型模板 | 停顿感打法不适合纯理性决策品类，不强行套钩子 |

这是推荐，Phase 2 等用户确认后再执行。

---

## Phase 1：Discovery

扫描 workspace 读取：
- 产品信息：`*产品信息*.pdf`、`*product_info*.pdf`、`*spec*.pdf`
- VOC 报告：`*VOC*分析*.md`、`*voc_report*.md`
- 实拍图：`本品实拍图/`、`product_photos/`
- 竞品参考：`竞手*asin*/`、`competitor*/`

提取：产品名称/尺寸/规格、目标用户画像、核心卖点 Top 5、VOC 痛点、竞品视觉策略。

若竞品文件夹存在且无近期分析报告，自动调用 `competitor-visual-analyzer`。

---

## Phase 2：Clarification（最多 4 个问题，1 次批量提问）

**必问**：
1. 图片组合范围（几张副图 + 几张 A+ 图）？
2. 视觉风格：高端科技感 / 暖色生活方式 / 极简 / 大胆用色？
3. 品牌色或排版约束？
4. **v2 专属**：根据 Phase 0 评估，给出每张图的方案 B 推荐，请用户确认或调整：

   > "基于产品类型，我推荐以下方案 B 打法，请确认：
   > - 副图1：T11 焦虑场景叙事（理由：核心卖点是防护痛点）
   > - 副图2：T10 反差感（理由：品类刻板印象明显）
   > - 副图3：T09 产品存在感（理由：手持小产品适合）
   > - A+图：功能型为主，A+ 宽图不适合钩子打法
   > 你可以调整任意一张，或全部保持我的推荐。"

---

## Phase 3：应用规则与模板

**方案 A**：参考功能型构图逻辑（降噪/即插即用/长距离/续航/多对一/工艺细节等）

**方案 B**：读取 `./references/composition-templates-v2.md`，按用户确认的模板写 prompt

**所有 prompt 必须执行**（读取 `./references/anti-pitfall-rules-key.md`）：
- 产品形态描述在 planning 开始时锁定，A/B 两套方案全程一致
- 金属零件用银/铬色，不用纯金/铜
- 不画手指按键，改用按键发光+箭头
- 远景人物占画面 1/10-1/8
- 每个 prompt 末尾加 STRICTLY AVOID 列表（8-15 项）
- 指定拍摄设备（`shot on Sony A7 with [X]mm lens`）

---

## Phase 4：输出 HTML 规划文档

生成单一 HTML 文件，**每张图包含 A/B 双 Tab**。

### 每张图卡片结构

```
Header: badge (副图/A+) + 尺寸 + 图片标题

讲述逻辑        — 这张图解决什么问题
构图思路        — 方案A构图 | 方案B构图（各自描述）
图内文字清单    — 方案A文字 | 方案B文字（B的文案更短更口语化）
参考图          — workspace 参考图文件名
验收标准        — 方案A验收 | 方案B验收
                  B额外检查：反差合理？产品仍是主角？钩子文案≤6词？

Prompt（A/B 双 Tab，各有 copy 按钮）
  [Tab A] 传统功能型 Prompt    [Copy A]
  [Tab B] 停顿感型 Prompt      [Copy B]
```

### HTML 顶部全局卡片（在图片卡片之前）

```
统一产品形态约束（锁定的产品描述，A/B 两套都用这个）
统一色板
统一排版规范
A/B Test 使用指引：
  - 方案A：主站/主ASIN，稳定转化
  - 方案B：A/B test variant，优先放搜索结果页最吃第一眼的槽位（主图/副图1）
  - 建议 test 周期：4-6周，对比 CTR 和转化率
  - 若B的CTR升但转化率降：钩子有效，产品描述需跟进优化
```

### HTML 技术规范

- Sticky 顶部导航（锚点跳转）
- A/B Tab 切换：原生 CSS + JS，无外部依赖
- Tab A 背景：白色；Tab B 背景：浅暖黄 `#FFFBF0`
- Copy 按钮独立（clipboard API + execCommand fallback）
- 无 emoji

**文件命名**：`{产品名}_生图方案v2_{YYYY-MM-DD}.html`，保存到用户 workspace 文件夹（不是 outputs/）。

---

## Phase 5：Hand-off

1. 文件路径（computer:// 链接）
2. 生图顺序建议：方案 B 先跑高风险图（T10/T11 AI 理解难度较大）
3. 出图后调用 `product-consistency-checker` 检查 A/B 两套产品形态一致性
4. A/B test 槽位建议

---

## 与 v1 差异速查

| 维度 | v1 | v2 |
|------|----|----|
| 出发点 | 产品有什么功能 | 用户为什么会停下来 |
| 模板 | 功能型 | 功能型 + T09/T10/T11 停顿感型 |
| 输出 | 每张图一个 prompt | 每张图 A/B 双 prompt |
| Phase 0 | 无 | 停顿感评估 + 模板推荐 |

**重要约束**：
- Phase 0 给推荐，Phase 2 等用户确认，不自作主张
- 方案 B prompt 结构同样清晰，STRICTLY AVOID 同样完整
- T10 反差感必须完成"刻板印象→反向元素"推导才能写 prompt
