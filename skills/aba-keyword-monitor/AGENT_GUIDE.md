# 亚马逊 ABA 爆品关键词监测系统 - AI Agent 操作指南

> 本文档适用于任何 AI IDE（Kiro、Trae、Antigravity、Cursor 等）。
> Agent 按照本文档指令执行即可完成完整监测流程。

## 前置要求

1. Python 3.8+
2. Sorftime MCP 已配置（必须）

### Sorftime MCP 配置方法

在 IDE 的 MCP 配置文件中添加：
```json
{
  "mcpServers": {
    "sorftimeMCP": {
      "url": "https://mcp.sorftime.com?key=你的API_KEY"
    }
  }
}
```
或设置环境变量：`SORFTIME_API_KEY=你的API_KEY`

---

## 首次使用：类目初始化

### 1. 运行初始化
```bash
python general-ABAkeyword-monitor/main.py init
```
按提示输入目标类目（如"宠物用品"）。

### 2. Agent 任务：生成词典
读取 `reports/.exchange/dict_draft.json`，按其中 prompt 生成词典。
写入 `reports/.exchange/dict_draft_output.json`。

### 3. 确认词典
```bash
python general-ABAkeyword-monitor/main.py init-confirm
```

---

## 日常监测流程

### Step 1：抓取 + 本地匹配
```bash
python general-ABAkeyword-monitor/main.py step1
```

### Agent 任务：LLM 分类
读取 `reports/.exchange/llm_input.json`，对每个关键词：
- 判断是否与目标类目相关
- 分类（标签见 prompt）
- 提供中文翻译

写入 `reports/.exchange/llm_output.json`：
```json
{"keyword": {"label": "ingredient", "zh": "中文翻译"}, ...}
```

### Step 2：分层 + Sorftime 查询
```bash
python general-ABAkeyword-monitor/main.py step2
```

### Agent 任务：写分析摘要
读取 `reports/.exchange/analysis_input.json`，为每个 Tier 1 关键词写 2-3 句中文分析。
做赛道聚类，写核心发现。

写入 `reports/.exchange/analysis_output.json`：
```json
{
  "keyword_analysis": {"keyword": "分析摘要", ...},
  "tracks": [{"name": "赛道名", "icon": "emoji", "keywords": [...], "summary": "描述"}],
  "core_findings": ["发现1", "发现2", ...]
}
```

### Step 3：生成 HTML 报告（必须执行）
```bash
python general-ABAkeyword-monitor/main.py step3
```

**⚠️ 重要：Step 3 是必须执行的最后一步，不可跳过。**
完成 analysis_output.json 写入后，必须立即运行 step3 生成最终 HTML 报告。
报告输出到 `reports/` 目录，文件名格式：`{类目}_monitor_YYYY-WXX-时间戳.html`。
生成后告知用户报告文件路径。

---

## Tier 分层规则

| 等级 | 条件 |
|:---|:---|
| 🔴 Tier 1 | TOP 1000 且涨幅 ≥50% 或 ≥1000 位 |
| 🟡 Tier 2 | 1000-50000 且从 10万+ 进入 5万内 |
| 🟢 Tier 3 | 50000+ 首次出现或大幅跨越 |

## 分类标签说明

| 标签 | 含义 |
|:---|:---|
| ingredient | 核心产品/成分 |
| benefit | 功效/用途 |
| brand | 品牌 |
| condition | 场景/症状 |
| form | 形态/规格 |
| unrelated | 无关 |
