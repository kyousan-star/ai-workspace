# Report And Deliverable Goal Defaults

Use this reference for HTML reports, dashboards, PPT, PDF, Word, spreadsheets, or boss-readable analysis deliverables.

## Skill Routing

- Amazon business report or dashboard: `amazon-report-design`.
- General research/analysis report or dashboard: `report-design`.
- PPT/PPTX deck: `presentations`.
- Word/DOCX or Google Docs-targeted artifact: `documents`.
- PDF creation/review/layout-sensitive PDF work: `pdf`.
- CSV/XLSX/Google Sheets-ready workbook: `spreadsheets`.

## Deliverable Standards

The goal should require:

- Conclusion-first executive summary.
- Clear source list and date range.
- Metric definitions and assumptions.
- Evidence-backed charts/tables, not decorative visuals.
- Prioritized actions with owner/time/risk when possible.
- Final artifacts saved under `outputs` when this Codex App workspace provides that folder.

For HTML/dashboard goals, verification should include:

- Open the local HTML/app in a browser.
- Check chart rendering, table readability, mobile layout, and no text overlap.
- Confirm links/assets are local or reachable.
- Avoid landing-page style when the user asks for an operational report.

For PPT/PDF/document goals, verification should include:

- Render or inspect pages/slides.
- Check title hierarchy, overflow, chart labels, and source notes.
- Confirm the file opens and exported/derived artifacts are present.

For spreadsheets, verification should include:

- Preserve raw data.
- Create cleaned/analysis tabs when needed.
- Check formulas, filters, number formats, and summary tables.
- Avoid silently changing source rows.

## Common Goal Skeleton

```text
/goal 将用户提供的分析内容或数据整理成老板可读的可交付报告，结论先行，包含证据图表、关键口径、风险说明和下一步动作。
验证：核对数据来源、日期范围和关键指标口径；生成目标格式文件后打开检查页面/幻灯片/工作簿渲染、文字溢出、图表标签、表格可读性和移动端或导出效果；确认最终产物位于 outputs。
约束：不编造数据、来源、结论或未提供的业务背景；不覆盖原始文件；不加入与决策无关的装饰性内容。
边界：只处理用户提供材料、临时处理文件和最终交付物，不修改无关项目或系统配置。
迭代策略：先确定报告结构和关键结论，再生成交付物；每次检查发现布局或口径问题后做聚焦修正，最多 3 轮。
完成条件：报告可打开、核心结论有证据、图表表格可读、无明显溢出，且交付物保存到指定位置。
暂停条件：缺少关键数据、需要外部账号/付费数据、需要法律财务正式判断、需要发布到线上或需要用户确认敏感结论时暂停。
```
