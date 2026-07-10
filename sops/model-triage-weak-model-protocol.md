# 模型分诊与弱模型执行协议（母版）

> 背景：Fable 额度有限。目标不是让 Opus/Sonnet 变成 Fable，而是把「Fable 怎么想」外化成流程，
> 让弱模型执行流程而不是即兴发挥，同时在制度上不给弱模型独立下高风险结论的权力。
> 建立日期：2026-07-09。维护方式见文末。

## 核心原则：结论权与执行权分离

- 弱模型可以干活（拉数、打标、算数、按 SOP 产出报告），但**决定性结论必须过两道闸**：
  - **硬闸**：代码校验（validate 脚本、必查项 gate、数字溯源检查）——不依赖模型自觉
  - **软闸**：Fable 或用户终审——高风险结论标 `【候选结论 · 待终审】`
- 判断依据：这个结论错了会不会造成真金白银损失（压货、烧广告费、砍掉本该做的产品）。
  会 → 结论权上收；不会 → 弱模型可独立收尾。

## 任务分诊表

| 层级 | 执行模型 | 终审 | 适用 skill / 任务 |
|------|---------|------|------------------|
| L1 机械执行 | Sonnet 独跑 | 无需 | amazon-pricing-validator、aba-keyword-monitor、batch-asset-generator、VOC 数据采集与打标、报告渲染、定时任务日常轮次 |
| L2 结构化分析 | Sonnet/Opus + 弱模型协议 | 抽查 | amazon-ad-optimizer（日常微调）、amazon-review-voc-analysis-v3、reddit/tiktok-voc、competitor-traffic-battle、amazon-listing-v2 |
| L3 结论性判断 | Opus + 弱模型协议 | Fable/用户必审 | zach-product-research Go/No-Go、amazon-category-analysis 终验、blue-ocean-finder 决策点、广告大动作（预算>30%/停campaign/批量否词） |
| L4 高模糊探讨 | 只用 Fable | — | 新框架设计、invest 决策、方法论蒸馏、"这个想法怎么样"级讨论 |

Fable 额度只烧在两类事上：L3 终审 + L4；以及把新方法论蒸馏成 SOP（复利动作）。

## 通用弱模型协议（给 skill 加节时复制此母版再定制）

执行者为 Opus/Sonnet/Haiku 时（模型可从 system prompt 得知自身型号），以下强制：

1. **结论权分级**：高风险结论只出「候选判定 + 证据链」，标 `【候选结论 · 待终审】`；
   保守方向结论（No-Go/Hold/观察）可直接给。
2. **唯一事实源**：阈值/规则/参数现场读配置文件，禁止凭记忆写数字；引用注明来源文件。
3. **禁止跳步 + 每步留痕**：SOP 步骤逐一执行，每步结束输出一行中间结论（口径+关键数字+该步判断）。
4. **已知陷阱清单**：逐条自查本次是否踩中（每个 skill 维护自己的清单，来源=历史真实翻车）。
5. **硬校验必过**：有 validate 脚本的 skill，交付前必须跑且通过；禁止绕过校验手工补文件。
6. **交付前强制反证**：回答「这个结论最可能错在哪」「什么数据能推翻它」，并对答案实际做核查
   （拉数据/查文件），不许纸面反证。答不上来的建议降级为观察项。

## 已落地的 skill

- `blue-ocean-finder` — 铁律#7-12 + `references/audit_checklist.md`（GO 前审计关，本协议的原型）
- `zach-product-research` — 「弱模型执行协议」节（2026-07-09）
- `amazon-ad-optimizer` — 「弱模型执行协议」节（2026-07-09）
- `amazon-category-analysis` — 审计关 §2.5 弱模型附则（2026-07-09）

## 金标准回归（用差距反哺 SOP）

1. 挑高频任务，把 Fable 历史产出存为 golden（参考 zach-product-research 的 `evals/` 目录模式）
2. 同一输入用 Sonnet 重跑，diff 差距
3. 差在哪 → 往对应 skill 的陷阱清单补一条
4. 两三轮后护栏就是实测校准的

## 维护方式

- **每次翻车 = 一条新陷阱**：任何任务跑歪/结论翻盘，事后把根因写进对应 skill 的陷阱清单
  （blue-ocean 变体错觉 → 铁律#7 就是这个模式），同时更新本文件「已落地」清单。
- **趁 Fable 有额度**：每当 Fable 解决一个新类型难题，顺手让它把通用方法蒸馏成 skill/SOP 节。
- 新 skill 上线时按分诊表定层级，L2 以上必须带弱模型协议节。
