# AI Workspace

本仓库是所有 AI 工作资产的唯一源头（source of truth）。

## 目录说明

| 目录 | 用途 |
|------|------|
| `skills/` | Claude Code 和 Codex 的可复用 skill |
| `prompts/` | 可复用 prompt 模板 |
| `sops/` | 标准操作流程（Amazon listing、VOC 分析等） |
| `workflows/` | 多步骤自动化流程描述 |
| `briefs/` | 图片 brief、内容 brief |

## 部署规则

**修改 skill 后必须运行 install.sh**，否则 Claude/Codex 读到的仍是旧版本。

```bash
bash install.sh
```

- `install_skill <name>` → 同时部署到 `~/.claude/skills/` 和 `~/.codex/skills/`
- `install_codex_skill <name>` → 仅部署到 `~/.codex/skills/`（Codex 专用 skill）

## 版本控制原则

- 所有修改在此仓库（source）进行，不直接编辑 `~/.claude/skills/` 或 `~/.codex/skills/`
- 修改后：`git add → git commit → git push → bash install.sh`
- 远程仓库：https://github.com/kyousan-star/AI-skills
