# Amazon Image Workflow

这是一个给亚马逊 Listing 图片、A+ 图、广告图使用的 AI 工作流包。

它只存放通用规则、模板、评分表和启动指令，不存放任何具体项目的输入或产出。

## 使用方式

1. 打开 `COMMANDS.md`。
2. 复制需要的指令。
3. 把 `PROJECT_ROOT` 替换成具体业务项目根目录。
4. 发给 Codex / ChatGPT。

AI 会自动检查业务项目中是否已有 `ai_image_workflow/`：

- 如果没有，会从 `templates/project/` 初始化一份项目工作区。
- 如果已有，会读取 `01_WORKFLOW/status.md` 从当前阶段继续。

## 中央包路径

```text
/Users/lihuan/ai-workspace/workflows/amazon-image-workflow/
```

## 业务项目产出路径

所有项目输入和输出都应写入业务项目下的：

```text
PROJECT_ROOT/ai_image_workflow/
```

不要把具体项目产出写回中央 workflow 包。

## 文件说明

- `COMMANDS.md`：给用户复制指令用。
- `MASTER_AGENT_PROMPT.md`：给主控 Agent 用。
- `WORKFLOW.md`：完整流程。
- `AGENT_ROLES.md`：多 Agent 分工。
- `GATE_RULES.md`：需要停下来让用户确认的节点。
- `PROJECT_FOLDER_CONTRACT.md`：项目文件夹输入输出规范。
- `templates/`：项目工作区和输入文件模板。
- `rubrics/`：图片评分和检查表。
- `schemas/`：状态文件、决策日志、Agent 输出格式。

