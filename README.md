# AI Workspace

所有 AI 工作资产的唯一源头（source of truth）。供 Claude Code、Codex 及其他 agent 使用。

## 目录结构

```
AI-skills/
├── skills/        # 可复用 skill（Claude + Codex 共用）
├── prompts/       # 可复用 prompt 模板
├── sops/          # 标准操作流程
├── workflows/     # 多步骤自动化流程
├── briefs/        # 图片 brief、内容 brief
├── CLAUDE.md      # Claude Code 自动加载的工作区说明
├── AGENTS.md      # Codex 自动加载的工作区说明
└── install.sh     # skill 部署脚本
```

## Skill 部署

```bash
bash install.sh
```

- `install_skill <name>` → 同时部署到 `~/.claude/skills/` 和 `~/.codex/skills/`
- `install_codex_skill <name>` → 仅部署到 `~/.codex/skills/`（Codex 专用）

安装后的副本与源码独立，各 agent 互不影响。

## 修改工作流

```
编辑 skills/<name>/  →  git commit  →  git push  →  bash install.sh
```

**不要**直接编辑 `~/.claude/skills/` 或 `~/.codex/skills/`，改动不会被追踪。

## 管理 Skill

**新增**：在 `skills/` 下建文件夹，包含 `SKILL.md`，然后在 `install.sh` 加一行 `install_skill <name>`。

**更新**：编辑源码后运行 `bash install.sh`。

**删除**：
```bash
rm -rf skills/<name>
# 删除 install.sh 中对应行
rm -rf ~/.claude/skills/<name> ~/.codex/skills/<name>
```

## 远程仓库

https://github.com/kyousan-star/AI-skills
