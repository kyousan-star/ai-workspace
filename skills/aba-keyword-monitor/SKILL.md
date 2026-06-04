---
name: general-ABA-keyword-monitor
description: 亚马逊 ABA 爆品关键词监测系统（通用版），支持任意类目，从 AMZ123 热搜词榜单自动发现潜力爆发关键词并生成分析报告
inclusion: manual
last_verified: 2026-06-03
staleness_risk: medium
---

# 亚马逊 ABA 爆品关键词监测系统（通用版）

## 概述

从亚马逊 ABA 热搜词榜单中自动发现指定类目的潜力爆发关键词，生成 HTML 分析报告。
支持任意亚马逊类目（保健品、宠物用品、美妆护肤、户外运动等），首次运行时交互式配置。

## 前提

- Python 3.8+（依赖自动安装）
- 必须配置 Sorftime MCP（key 会被 Python 自动提取）

## 首次使用：类目初始化

### Step 0：初始化类目

```bash
python general-ABAkeyword-monitor/main.py init
```

按提示输入目标类目名称（如"宠物用品"），系统会输出 `reports/.exchange/dict_draft.json`。

### Agent 任务：生成类目词典

读取 `reports/.exchange/dict_draft.json`，按 prompt 要求生成初始词典和排除规则。

写入 `reports/.exchange/dict_draft_output.json`：
```json
{
  "category_dict": {"ingredients": [...], "benefits": [...], "brands": [...], "health_markers": [...]},
  "exclusion_rules": {"exclude_patterns": [...], "exclude_keywords": [...]},
  "classification_labels": {"description": "各标签含义描述"}
}
```

### Step 0.5：确认词典

```bash
python general-ABAkeyword-monitor/main.py init-confirm
```

系统展示词典摘要，用户确认后保存。

---

## 日常监测流程（3 步）

### Step 1：抓取 + 本地词典匹配

```bash
python general-ABAkeyword-monitor/main.py step1
```

输出 `reports/.exchange/llm_input.json`。

### Agent 任务：LLM 分类 + 中文翻译

读取 `reports/.exchange/llm_input.json`，对每个关键词分类并翻译。
分类标签根据类目动态生成（见 llm_input.json 中的 prompt）。

写入 `reports/.exchange/llm_output.json`：
```json
{"keyword": {"label": "ingredient", "zh": "中文翻译"}, ...}
```

### Step 2：分层 + Sorftime 异步查询

```bash
python general-ABAkeyword-monitor/main.py step2
```

### Agent 任务：写分析摘要

读取 `reports/.exchange/analysis_input.json`，为每个 Tier 1 关键词写分析摘要。

写入 `reports/.exchange/analysis_output.json`：
```json
{
  "keyword_analysis": {"keyword": "分析摘要", ...},
  "tracks": [{"name": "赛道名", "icon": "emoji", "keywords": [...], "summary": "描述"}],
  "core_findings": ["发现1", "发现2", ...]
}
```

### Step 3：生成最终 HTML 报告（必须执行）

```bash
python general-ABAkeyword-monitor/main.py step3
```

**⚠️ 重要：Step 3 是必须执行的最后一步，不可跳过。**
完成 analysis_output.json 写入后，必须立即运行 step3 生成最终 HTML 报告。
报告输出到 `reports/{category}_monitor_YYYY-WXX-时间戳.html`。
生成后告知用户报告文件路径。

---

## 【数据溯源 Footer - 每份报告必须输出】

每份分析报告的最末行必须输出以下溯源行（单行，不可省略，不可移到报告中间）：

> 📊 数据溯源｜时间范围：[从数据中提取的起止日期，YYYY-MM ~ YYYY-MM，无法确定时填"未知"]｜来源：[工具或平台名，如 Shulex / ABA后台 / Helium10 / 用户上传CSV 等]｜分析日期：[执行本次分析的日期 YYYY-MM-DD]
