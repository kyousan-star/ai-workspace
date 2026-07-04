# Mission: Claude Skill Engineering

## Why
已在用 Claude Code 管理亚马逊运营、投资分析等复杂工作流，skills 是让 Claude 帮忙生成和迭代的。目标是从"会用"升级到"会设计"——能判断一个 skill 好不好、哪里有问题、该怎么改，然后让 Claude 去执行改动。不需要自己写代码。

## Success looks like
- 拿到一个陌生 skill，能判断它的结构是否合理、触发描述有没有问题
- skill 输出不稳定或不触发时，能说清楚问题出在哪，告诉 Claude 怎么修
- 设计新 skill 时，能提出清晰的 IPO 需求（喂什么进去、要拿到什么出来）
- 知道什么时候需要 hook，能描述需求让 Claude 来写

## Constraints
- 不会编程，不手写代码或 JSON
- 学习时间碎片化，每次课程 30 分钟内完成
- 已有基础：多个 skill 实际使用经验，理解 SKILL.md 基本概念

## Out of scope
- 手写 hooks、Python 脚本、JSON 配置
- Claude API 底层机制
- 非 Claude Code 环境（LangChain 等）
