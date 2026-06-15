# Agent Output Contract

所有子 Agent 输出必须写成文件，并包含以下结构。

```text
# [Agent Name] Output

## Scope

本次负责什么。

## Inputs Read

- 读取了哪些文件。

## Findings

- 关键发现。

## Evidence

- 证据、来源、文件路径、图片编号或数据依据。

## Recommendations

- 给主控 Agent 的建议。

## Risks / Uncertainty

- 不确定项和需要人工确认的点。

## Next Interface

- 下游 Agent 可以直接使用的结构化输出。
```

## 输出原则

- 不要只在聊天中给结论。
- 不要写入中央 workflow 包。
- 不要覆盖其他 Agent 的文件，除非主控 Agent 明确要求。
- 引用真实文件路径。
- 不确定就标注不确定，不要脑补产品事实。

