# 交接给 zach-product-research

决策点①选定 1 个候选后，把 blue-ocean-finder 已采的数据整理成 zach 的 v2 payload，调 `/zach-product-research` 出深挖报告。

**前置：候选必须已过 P4 可行性快筛（`feasibility_gate.md` A段）。** 交接时一并带上 feasibility_gate B段"zach 深挖必须覆盖"的清单 + 交接话术，确保 IP claim chart / 广告现金模型 / 形态评分天花板 / 痛点语料校验 / TAM形态封顶 / 季节交期 这 6 项在深挖里被覆盖并进评分卡——否则会重蹈 overhead"先GO 7.5后被打脸"。

## 已有数据 → zach payload 的映射

blue-ocean-finder 在 P1-P3 已经采到的，直接填进 zach 的对应章节，省重复拉数：

| 已采（本 skill） | 填进 zach payload |
|---|---|
| keyword_trend 增速/CPC | ch02 kpis + keyword_comparison（注意字段名见下）|
| keyword_detail 首页评论分布 | ch02 kpi「首页<100评占比」+ ch09 竞争维度证据 |
| product_search 形态/竞品 | ch03 形态分布 + ch04 形态×竞争矩阵 + ch05 竞品（形态天花板按我方形态封顶，非搜索池）|
| product_reviews 痛点 | ch06 痛点（pain_tagger 量化；**务必核"评论产品的属性"字段确认是目标形态本体，非父体/别变体——语料偏了痛点分布就偏**）|

## ch01.decision_funnel 种子（⛔ 必填，见 zach-product-research SKILL.md 规则10b）

blue-ocean-finder 走过的 P0-P4 判断链，就是 zach payload `ch01.decision_funnel` 的前半段种子——直接复用，不用重新编：

| blue-ocean 阶段 | 填进 decision_funnel 哪一步 |
|---|---|
| P0 方向输入 + 已知锚点 | 第1步，`stage:"start"` |
| 段1需求扫描结果（过/不过、具体YoY数字） | 第2步，`stage:"turn"`（若段1不过转红海位移，这里是关键分岔点） |
| 决策点①用户选择 | 若段1判断需要人工拍板，单列一步`stage:"turn"`，标注这是用户判断非数据自动推出 |
| P2-P4快筛结果 | 一步`stage:"gate"`，列出竞争浅/稳态真/IP干净等快筛项 |
| A5/A5b/A5c跨平台交叉验证(若跑了) | 追加一步`stage:"gate"`，标注"独立渠道确认同一判断"（降不确定性，不改分数）；若发现渠道间判断分歧(如Google Trends vs Amazon)，单列`stage:"turn"`说明分歧归因+默认取哪个渠道为准，不要含糊带过 |
| zach本轮量化结论 | 最后追加`stage:"gate"`（Go/No-Go分数）+ `stage:"final"`（落地规格） |

**报告正文里不要用"zach"或任何工具/人名指代深挖这一步**，用"定向验证阶段""建模量化阶段"等描述性说法——冷读者不知道 zach 是什么，会以为是某种方法论专名。

## ⚠️ zach 渲染器的已知坑（务必避免）

1. **关键词图字段名**：dashboard 读 `monthly_search / cpc / competitors / peak_season`，不是 `search_volume_rank`。填错→图表显示 0。
2. **竞品图字段名**：dashboard 读 `price / monthly_sales / review_count`，competitor_selection_logic 里要带这三个，否则显示 0。
3. **机会卡假数字**：旧版 render 把 `weighted_score×1000` 当月销量凑数（"承接7.0K月销量"）。本地 render_deliverables.py 已修为显示真实 action 文字——确认用的是修过的本地版。
4. **excel_sheets 必须含 11 个固定 Sheet 名**，否则校验不过（数据来源说明/市场概况/类目销量Top100_明细/属性标注_Top100/关键词对比_分段/新品分析/竞品选择逻辑/竞品差评摘要/品牌_竞品格局/进入壁垒评估/Go-NoGo评分卡）。建议再加「数据溯源」sheet 做信任底账。
5. **生成≠正确**：zach 校验只查结构不查数值真假。**渲染后必须逐图肉眼核验**：无 0/空、无凑数、数字对得上原始返回。

## 交付纪律（报告落地时强制）

1. **B 段覆盖自检表**：深挖报告末尾附 feasibility_gate B 段全维度「做了/没做/理由」表，缺行退回（见 feasibility_gate.md）。
2. **分数单一出处**：Go/No-Go 分数只在评分卡处计算一次，摘要/漏斗/结论全部引用该值——teleprompter v1 摘要 6.4 vs 评分卡 6.25 并存的教训。
3. **审计关**：GO / CONDITIONAL GO 拍板前跑 `references/audit_checklist.md`，审计不过先修报告。
4. **版本主权**：vN+1 定稿时一次动作完成三件事——旧版文件头加「⚠️ superseded by vN+1（路径）」、RESUME/续接文档同步新结论、候选种子池状态更新。旧结论存活会在续接会话里复活（overhead v4 出来后 RESUME 还写着 GO 7.5 的教训）。

## 模板

参考已跑通的实例：`蓝海品类筛选/build_overhead_payload.py`（overhead 的 payload 构建器，字段全对、坑全避），直接照抄改数据即可。
