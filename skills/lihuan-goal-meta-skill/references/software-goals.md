# Software Goal Defaults

Use this reference for coding, app/site/game creation, bug fixes, UI polish, automation scripts, local tools, and refactors.

## Defaults

- If an existing repo is present, inspect project scripts, docs, tests, and conventions before editing.
- If no repo exists, create the smallest local MVP that proves the core workflow.
- Do not add auth, backend, payments, cloud sync, production deployment, paid APIs, or account systems unless requested.
- For UI work, verify desktop and mobile screenshots or browser states; text and controls must not overlap.
- For bug fixes, prefer a regression test or the smallest repeatable reproduction.
- For generated apps/sites, start a local dev server when needed and give the user the URL.

## Verification Examples

- Frontend: run lint/build/test if available, start local app, inspect browser console, check desktop/mobile layout.
- Backend/API: run unit tests, exercise one representative API call, inspect logs.
- CLI/script: run against a small fixture, verify output file/content, handle errors.
- Refactor: run relevant tests and confirm public behavior/API remains unchanged.

## Common Goal Skeleton

```text
/goal 在现有项目中实现用户请求的最小可验证改动，先读取项目命令和相关文件，再完成核心用户可见流程或明确的 bug 修复，并避免无关重构。
验证：运行项目提供的最小相关检查；如是 UI，启动本地应用并检查桌面/移动端和控制台；如是 bug，补充或运行能证明修复的复现/回归检查。
约束：不改变无关公开 API、数据格式、认证、支付、生产配置、路由或视觉体系，除非用户明确要求。
边界：只修改与该功能/bug 直接相关的源文件、样式、测试和必要夹具，不触碰无关模块、凭证、生产配置或默认分支发布。
迭代策略：一次做一个聚焦改动，每次有意义改动后重跑检查；同一问题连续失败 2 次后换证据来源，最多 3 轮聚焦改进。
完成条件：核心流程或 bug 修复有运行证据，相关检查通过或明确说明缺少配置，剩余风险被列出。
暂停条件：需要凭证、付费服务、生产数据、破坏性迁移、线上发布、版权素材、法律/医疗/金融判断或产品方向无法判断时暂停。
```
