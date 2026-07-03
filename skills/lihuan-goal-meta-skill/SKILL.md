---
name: lihuan-goal-meta-skill
description: Turn Lihuan's vague or complex Chinese-first Codex requests into copy-ready `/goal` commands with conservative defaults, verification evidence, file boundaries, pause conditions, and routing to the right local skills. Use when the user asks to write/optimize a Codex goal, says a task is vague, wants a plan converted to `/goal`, starts a multi-step Amazon analysis/report/listing/VOC/category/product-development task, asks for an HTML/PPT/PDF/dashboard deliverable, or wants bounded agent execution before coding, analysis, or document production.
---

# Lihuan Goal Meta Skill

Create a paste-ready Codex `/goal` contract for Lihuan before meaningful multi-step work. Keep the slash command as `/goal`; Chinese body text is preferred unless the user asks for English.

## Default Output

For Chinese requests, output in this order:

1. `推荐执行版（中文，可直接复制）`
2. `默认选择理由`
3. `建议调用的技能`
4. `可选调整`
5. `你可以直接回复`
6. `Goal Draft (English-compatible)` only when useful for tool/team compatibility or when the user asks.

Do not leave placeholders. Do not start the work described by the goal unless the user explicitly asks.

## Goal Contract

Every final goal must include:

```text
/goal [具体结果，不是活动描述]。
验证：[命令、数据核对、截图、日志、产物路径、浏览器检查或导出文件]。
约束：[不能改变的行为、口径、数据、账号、版权、风格、分支或发布规则]。
边界：[允许写入位置、禁止触碰路径、是否只在 outputs 交付]。
迭代策略：[先发现再实现；一次一个聚焦改动；基于证据调整；最多 3 轮聚焦改进]。
完成条件：[哪些证据证明可以停止]。
暂停条件：[凭证、付费、生产、破坏性操作、法律/医疗/金融判断、版权授权、账号所有权、数据口径不清]。
```

## Routing

Before drafting the goal, classify the task and name the likely skill route in `建议调用的技能`.

- Amazon ads, PPC, ACOS, ROAS, search terms, SP/SB/SD: `amazon-ad-optimizer` (含快读模式，原 amazon-ads-analysis 已并入); read `references/amazon-workflows.md`.
- Amazon VOC, reviews, complaints, pain points: `amazon-review-voc-analysis-v3`; read `references/amazon-workflows.md`.
- Amazon listing creation or audit: `amazon-listing-v2` or `listing-rufus-cosmo-audit`; read `references/amazon-workflows.md`.
- Amazon category, product development, competitor traffic, SIF, traffic battle: `amazon-category-analysis`, `amazon-product-dev`, or `competitor-traffic-battle`; read `references/amazon-workflows.md`.
- HTML report, dashboard,老板可读报告, PPT/PDF/document deliverable: `amazon-report-design`, `report-design`, `presentations`, `documents`, `pdf`, or `spreadsheets`; read `references/report-deliverables.md`.
- General coding, app, website, game, bug fix, UI polish, automation: use Codex engineering defaults; read `references/software-goals.md`.
- Spreadsheets or CSV/XLSX analysis: `spreadsheets`; read `references/report-deliverables.md`.

If multiple routes apply, list the minimal sequence, for example: `amazon-ad-optimizer -> amazon-report-design -> spreadsheets`.

## Lihuan Defaults

Use these unless the user says otherwise:

- Chinese-first analysis and final communication.
- Conclusion first, then evidence, then actions.
- Distinguish `事实`, `推断`, and `建议`.
- Never invent missing data, metric definitions, dates, competitor facts, policy claims, or compliance conclusions.
- Preserve raw uploaded data. Write cleaned/intermediate outputs under the workspace, and user-facing deliverables under the thread `outputs` directory when available.
- For Codex App work, prefer local artifacts and browser verification over cloud publishing.
- For reports, produce boss-readable deliverables with clear decision summary, metric definitions, risk notes, and next actions.
- For frontend/HTML deliverables, verify desktop and mobile layout, chart rendering, table readability, and no text/control overlap.
- For Amazon analysis, include action priority, evidence, expected impact, and risk/guardrail.

## Questions

Do not interview by default. Ask only when the answer changes cost, risk, ownership, data interpretation, deployment, or final format.

Prefer numbered choices:

```text
可选调整
1. 交付形态：A HTML报告（默认） / B PPT / C Excel工作簿
2. 分析深度：A 可执行诊断（默认） / B 老板汇报版 / C 全量方法论审计
3. 验证方式：A 本地文件和浏览器检查（默认） / B 加表格口径复核 / C 加截图/PDF导出

你可以直接回复：按默认，或回复类似 1B 2A 3C。
```

## Quality Bar

A good Lihuan goal must make it clear:

- which skill route to use
- which data/files are in scope
- which outputs should be produced
- which metrics or UX states must be verified
- where deliverables should be saved
- what must not be touched
- when Codex should pause instead of guessing

For final goal files, run:

```bash
python3 scripts/lint_lihuan_goal.py <goal-file>
```

## Reference Files

- `references/amazon-workflows.md`: Amazon ads/listing/VOC/category/product routing and verification defaults.
- `references/report-deliverables.md`: HTML/PPT/PDF/spreadsheet deliverable standards.
- `references/software-goals.md`: coding, UI, app, bug fix, and local verification goal patterns.
