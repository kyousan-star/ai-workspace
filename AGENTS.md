# AI Workspace — Codex 说明

完整文档见 README.md。

## 关键规则

- 此仓库是所有资产的唯一源头，不直接修改 `~/.codex/skills/`
- 修改 skill 后必须运行 `bash install.sh` 才会生效
- prompts/、sops/、workflows/、briefs/ 是共享资产目录，内容对所有 agent 可见

## Codex 专用 Skill

`web-access-codex` 仅部署到 `~/.codex/skills/`，不影响 Claude。
新增 Codex 专用 skill 用 `install_codex_skill <name>`。

## Skill 修改流程

```
编辑 skills/<name>/SKILL.md  →  bash install.sh  →  git commit  →  git push
```
