# 🔍 亚马逊 ABA 爆品关键词监测工具

一句话介绍：**帮你从亚马逊每周几十万个热搜词里，自动筛出你所在类目正在爆发的关键词。**

比如你做宠物用品，它能帮你发现"dog calming treats"这周突然从10万名冲到500名——这种信号比竞争对手早发现一周，就是你的优势。

---

## 📋 你需要准备什么

### 1. 一个 AI IDE（任选其一）

| IDE | 说明 |
|:---|:---|
| [Kiro](https://kiro.dev) | 亚马逊出品，推荐 |
| [Trae](https://trae.ai) | 字节出品，免费好用 |
| [Cursor](https://cursor.sh) | 老牌 AI IDE |
| 其他支持 MCP 的 AI IDE | 都可以 |

### 2. Python 3.8 以上

打开终端输入 `python --version`，看到 3.8+ 就行。
没装的话去 [python.org](https://www.python.org/downloads/) 下载安装。

### 3. Sorftime MCP（必须配置，免费额度够用）

这是本工具的数据引擎，用来查关键词的搜索量趋势、CPC、竞品数据等。

---

## 🔧 配置 Sorftime MCP（第一次用必看）

### 第一步：获取 Sorftime API Key

1. 打开 [sorftime.com](https://www.sorftime.com)
2. 注册账号（有免费额度）
3. 进入后台，找到 **MCP API Key**，复制下来

### 第二步：在你的 AI IDE 里配置

每个 IDE 的 MCP 配置文件位置不同，但格式一样：

```json
{
  "mcpServers": {
    "sorftimeMCP": {
      "url": "https://mcp.sorftime.com?key=把你的KEY粘贴到这里"
    }
  }
}
```

**各 IDE 配置文件位置：**

| IDE | 配置文件路径 |
|:---|:---|
| Kiro | `.kiro/settings/mcp.json`（项目目录下）或 `~/.kiro/settings/mcp.json`（全局） |
| Trae | 设置 → MCP → 添加服务器 |
| Cursor | `.cursor/mcp.json` |

> 💡 如果你不确定怎么配，直接在 IDE 里搜索 "MCP" 相关设置就能找到。

### 第三步：验证配置

配置好后，在 IDE 的 AI 对话框里问一句：
> "帮我用 sorftime 查一下 dog treats 这个关键词的搜索趋势"

如果能返回数据，说明配置成功。

---

## 🚀 开始使用

### 首次运行：初始化你的类目

在 AI IDE 的对话框里说：

> "帮我运行 general-ABAkeyword-monitor，我要监测【宠物用品】类目"

或者手动执行：

```
python general-ABAkeyword-monitor/main.py init
```

按提示输入你的类目名称（比如"宠物用品"、"美妆护肤"、"户外运动"等）。

AI 会自动帮你：
1. 生成该类目的关键词词典（哪些词属于你的类目）
2. 生成排除规则（排除明显不相关的词）
3. 让你确认后保存

### 日常监测：每周跑一次

初始化完成后，以后每周只需要对 AI 说：

> "帮我跑一下本周的 ABA 数据"

AI 会自动完成 3 个步骤：
1. **抓取**：从 AMZ123 抓取本周 ABA 热搜词榜单
2. **分析**：筛选你的类目词 → 分层（Tier 1/2/3）→ 查 Sorftime 深度数据
3. **报告**：生成一份漂亮的 HTML 报告

报告会保存在 `reports/` 文件夹里，用浏览器打开就能看。

---

## 📊 报告里有什么

- **Tier 1 大潜力词**：排名冲进 TOP 1000 且涨幅巨大的词，附带搜索量趋势图、CPC、竞品分析
- **Tier 2 中潜力词**：排名在 1000-50000 之间快速上升的词
- **Tier 3 长尾词**：排名较低但首次出现或大幅跨越的词
- **赛道聚类**：AI 自动把相关词归类到同一赛道（比如"狗粮赛道"、"猫砂赛道"）
- **核心发现**：本周最值得关注的趋势总结

---

## ❓ 常见问题

### Q: 报错说 Sorftime 未配置？
检查你的 MCP 配置文件里是否正确添加了 sorftimeMCP，key 是否正确。
也可以设置环境变量：`set SORFTIME_API_KEY=你的KEY`（Windows）或 `export SORFTIME_API_KEY=你的KEY`（Mac/Linux）。

### Q: 可以同时监测多个类目吗？
目前一个项目实例监测一个类目。想监测多个类目，复制一份 `general-ABAkeyword-monitor` 文件夹即可。

### Q: 词典不够准怎么办？
初始化时 AI 生成的词典是起点，每次运行会自动学习新词并回写到词典。
你也可以手动编辑 `data/{类目}/category_dict.json` 添加或删除词。

### Q: 数据源是什么？
- **AMZ123**：提供 ABA（Amazon Brand Analytics）热搜词排名和涨跌数据
- **Sorftime**：提供关键词的历史搜索量趋势、CPC、竞品数据等深度信息

### Q: 免费吗？
本工具本身免费开源。Sorftime 有免费额度，日常使用基本够用。

---

## 📁 文件说明

```
general-ABAkeyword-monitor/
├── main.py              # 主入口（init / step1 / step2 / step3）
├── config.py            # 配置（自动提取 Sorftime key）
├── category_init.py     # 类目初始化交互流程
├── classifier.py        # 关键词分类器
├── analyzer.py          # Tier 分层 + 爆发判断
├── sorftime_client.py   # Sorftime 异步查询
├── scraper.py           # AMZ123 数据抓取
├── reporter.py          # HTML 报告生成
├── db.py                # SQLite 历史存储
├── requirements.txt     # Python 依赖（自动安装）
├── SKILL.md             # Kiro IDE 专用描述
├── AGENT_GUIDE.md       # AI Agent 操作指南（跨 IDE 通用）
├── README.md            # 本文件
├── templates/
│   └── report.html      # 报告模板
└── data/                # 运行时生成，按类目隔离
    └── {类目}/
        ├── category_dict.json    # 关键词词典
        ├── exclusion_rules.json  # 排除规则
        └── history.db            # 历史数据
```
