# AI Workspace — Claude Code 说明

完整文档见 README.md。

## 关键规则

- 此仓库是所有资产的唯一源头，不直接修改 `~/.claude/skills/`
- prompts/、sops/、workflows/、briefs/ 是共享资产目录，内容对所有 agent 可见

## 自动化操作规则（重要）

当用户说"新增 skill / SOP / workflow / prompt / brief"或"更新了某个资产"时，**无需用户手动操作**，由 agent 自动完成以下全流程：

### 新增 skill

1. 在 `skills/<name>/` 下创建内容（至少包含 `SKILL.md`）
2. 在 `install.sh` 末尾加一行 `install_skill <name>`（Codex 专用则用 `install_codex_skill`）
3. 在 `/Users/lihuan/AI-skills/` 下运行 `bash install.sh`
4. `git add` → `git commit` → `git push origin main`

### 更新现有 skill

1. 编辑 `skills/<name>/` 下的文件
2. 在 `/Users/lihuan/AI-skills/` 下运行 `bash install.sh`
3. `git add` → `git commit` → `git push origin main`

### 新增或更新 SOP / workflow / prompt / brief

1. 在对应目录（`sops/` / `workflows/` / `prompts/` / `briefs/`）下创建或编辑文件
2. `git add` → `git commit` → `git push origin main`
3. 无需运行 `install.sh`（这些目录直接从仓库读取，不需要部署）

### 触发词示例

- "新增了一个 skill" / "有个新 skill"
- "xxx skill 更新了" / "修改了 xxx skill"
- "新增 SOP" / "更新 workflow" / "加个 prompt"
- 任何涉及 AI-skills 仓库内容变动的描述
