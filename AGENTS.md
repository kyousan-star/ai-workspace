# AI Workspace — Codex 说明

完整文档见 README.md。

## 关键规则

- 此仓库是所有资产的唯一源头，不直接修改 `~/.codex/skills/`
- prompts/、sops/、workflows/、briefs/ 是共享资产目录，内容对所有 agent 可见

## Skill 健康检查（自动执行）

每次调用任何 skill 前，读取其 SKILL.md frontmatter 中的 `last_verified` 和 `staleness_risk`，按以下规则判断：

| staleness_risk | 超过天数触发警告 |
|---------------|---------------|
| high | 60 天 |
| medium | 90 天 |
| low | 180 天 |

超过阈值时，在执行 skill 前输出一行提示：
> ⚠️ [skill名] 上次验证于 YYYY-MM-DD（已 N 天），staleness_risk: high/medium/low。Amazon 规则可能已变，建议确认后继续。是否继续？

用户确认后正常执行。若未设置 `last_verified`，视为需要立即提示。

## Codex 专用 Skill

`web-access-codex` 仅部署到 `~/.codex/skills/`，不影响 Claude。
新增 Codex 专用 skill 用 `install_codex_skill <name>`。

## 自动化操作规则（重要）

当用户说"新增 skill / SOP / workflow / prompt / brief"或"更新了某个资产"时，**无需用户手动操作**，由 agent 自动完成以下全流程：

### 新增 skill

1. 在 `skills/<name>/` 下创建内容（至少包含 `SKILL.md`）
2. 在 `install.sh` 末尾加一行 `install_skill <name>`（Codex 专用则用 `install_codex_skill`）
3. 在 `/Users/lihuan/ai-workspace/` 下运行 `bash install.sh`
4. `git add` → `git commit` → `git push origin main`

### 更新现有 skill

1. 编辑 `skills/<name>/` 下的文件
2. 在 `/Users/lihuan/ai-workspace/` 下运行 `bash install.sh`
3. `git add` → `git commit` → `git push origin main`

### 新增或更新 SOP / workflow / prompt / brief

1. 在对应目录（`sops/` / `workflows/` / `prompts/` / `briefs/`）下创建或编辑文件
2. `git add` → `git commit` → `git push origin main`
3. 无需运行 `install.sh`（这些目录直接从仓库读取，不需要部署）

### 触发词示例

- "新增了一个 skill" / "有个新 skill"
- "xxx skill 更新了" / "修改了 xxx skill"
- "新增 SOP" / "更新 workflow" / "加个 prompt"
- 任何涉及 ai-workspace 仓库内容变动的描述
