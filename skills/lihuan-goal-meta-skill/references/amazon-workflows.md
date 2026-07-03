# Amazon Workflow Goal Defaults

Use this reference when the request touches Amazon ads, Listing, VOC, category research, product development, or competitor traffic.

## Skill Routing

- Ads/PPC/search terms/ACOS/ROAS/CPC/CVR/TACOS: route to `amazon-ad-optimizer` for action strategy or `amazon-ads-analysis` for report-level analysis.
- VOC/reviews/star ratings/pain points/complaints: route to `amazon-review-voc-analysis-v3`.
- Listing writing or optimization: route to `amazon-listing-v2`.
- Listing audit/Rufus/COSMO/query intent: route to `listing-rufus-cosmo-audit`.
- Category feasibility/Go-No-Go/market opportunity: route to `amazon-category-analysis`.
- Product opportunity/profit/ad sandbox/patent risk: route to `amazon-product-dev`.
- Competitor traffic/SIF/keyword offense-defense/traffic battle: route to `competitor-traffic-battle`.
- If the user wants a polished deliverable, add `amazon-report-design` after the analysis skill.

## Required Goal Clauses

Verification should include the relevant data checks:

- Confirm source files, date ranges, marketplace, currency, and report type.
- Check core metric formulas before conclusions: Spend, Sales, Orders, ACOS, ROAS, CPC, CTR, CVR, CPA, TACOS when available.
- Keep campaign, ad group, targeting, search term, ASIN, and SKU levels separate unless the user asks to aggregate.
- For VOC, separate old accumulated reviews from recent signal when date data exists.
- For competitor/category work, separate observed facts from inference and opportunity hypotheses.

Constraints should include:

- Do not invent missing metrics, Amazon policy facts, competitor revenue, review causes, keyword volume, or compliance claims.
- Do not overwrite raw uploaded data.
- Do not make account-level advertising changes, budget changes, negatives, bid changes, or listing publication unless explicitly requested.
- Do not use unlicensed competitor images, official brand assets, or unsupported claims.

Completion evidence should include:

- A prioritized action list with evidence and risk.
- Metric definitions or assumptions used.
- Clear separation of quick wins, tests, and high-risk actions.
- Output artifacts saved in the requested format or under `outputs` when producing files.

## Common Goal Skeleton

```text
/goal 基于用户提供的亚马逊数据完成一次可执行诊断，先识别数据源、时间范围、站点和字段口径，再输出按优先级排序的优化动作和老板可读摘要。
验证：核对关键字段和指标公式，检查异常值和缺失数据，按正确层级完成分析，并生成带证据、风险和预期影响的行动清单；如生成报告，打开本地文件检查图表、表格和移动端可读性。
约束：不编造缺失数据、广告后台事实、竞品销量、政策结论或未提供的口径；不覆盖原始数据；不直接执行后台改动。
边界：只读取用户提供的数据和明确相关文件，产物写入工作区或 outputs，不修改无关项目文件。
迭代策略：先做字段发现和口径确认，再做分层诊断；遇到数据矛盾先标注假设，最多做 3 轮聚焦修正。
完成条件：核心结论均有数据依据，行动建议可执行且标注优先级/风险，交付物可打开并通过基本检查。
暂停条件：需要广告账号登录、真实投放改动、预算决策、生产数据导出、外部付费数据、法律合规判断或关键口径无法确认时暂停。
```
