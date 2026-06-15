# 什么时候用这个工具

## 一句话定位

**Amazon Image Workflow 是新品视觉方案的全链路编排框架。**

从零开始，覆盖竞品研究、策略制定、图序规划、prompt 生成、图片评估、迭代优化到最终交付的完整项目周期。

---

## 适用场景

### ✅ 用这个工具，当你面对的是：

**新品上市前的视觉方案制定**
- 产品还没有 listing 图，或者图片完全需要推倒重来
- 需要从竞品研究开始，一步步确定"卖什么、怎么卖、图怎么排"
- 需要多人协作（运营、设计、文案各看各的部分）

**完整项目周期管理**
- 需要跨多个工作 session 推进（今天做研究，明天做图序，后天出 prompt）
- 需要在关键节点停下来让负责人确认再继续
- 需要记录每个决策的来龙去脉（为什么这样排图序、哪些竞品手段被否决）

**多图批量规划**
- 一次性规划主图 + 副图 + A+ + 广告图的完整图片矩阵
- 需要素材盘点（哪些图要新拍、哪些可以复用、哪些 AI 生成）
- 需要合规边界检查

---

## 不适用场景

### ❌ 不要用这个工具，当你：

- 只需要改一两张现有图片（用 `amazon-image-optimizer`，尚在开发中）
- 已经有图序，只需要快速出 prompt（直接用 `amazon-image-planner-v3`）
- 只是想看看某张竞品图用了什么手段（直接问 Claude 即可）
- 时间紧，不想跑完整流程（用 `amazon-image-planner-v3` 轻量启动）

---

## 运行环境

**Claude Code 或 Codex**（需要文件系统访问权限）

不能在 claude.ai 对话框里直接跑，因为它需要：
- 读写本地文件夹（项目工作区 `PROJECT_ROOT/ai_image_workflow/`）
- 跨 session 续跑（今天做到 Gate 1，明天继续从 Gate 1 之后）
- 并行启动多个子 Agent

---

## 与 amazon-image-planner-v3 的关系

两个工具不是竞争关系，是嵌套关系：

```
amazon-image-workflow（外层，负责项目管理）
    阶段1  竞品研究 + VOC + 素材盘点 + 合规
    Gate1  你确认卖点优先级（图序从这里来）
    阶段3  图序规划
    Gate2  你确认图序
    阶段4  → 调用 amazon-image-planner-v3 生成 A/B 双 prompt
    阶段6  评估
    阶段7  迭代
    Gate3  你确认最终候选
```

**workflow 负责"做什么决策"，v3 负责"把决策变成 prompt"。**

如果你已经通过 workflow 走完了 Gate 2，阶段4会自动调用 v3，不需要你手动切换工具。

---

## 快速判断

```
我有一个新品，需要从零规划整套图片方案
    → 用 amazon-image-workflow

我已经知道图序，只需要出 prompt
    → 用 amazon-image-planner-v3

我有在售品，图片需要优化
    → 用 amazon-image-optimizer（开发中）

我只需要改一张图的 prompt
    → 用 amazon-image-planner-v3
```

---

## 启动方式

打开 `COMMANDS.md`，复制指令1（新项目启动），把 `PROJECT_ROOT` 替换成你的项目路径，发给 Claude Code / Codex。

详细操作见 `README.md`。
