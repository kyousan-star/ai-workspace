# 微信公众号监控

这是一个本地安全优先的监控骨架：不登录微信、不读取个人微信、不保存原始 HTML，只处理公开文章链接或公开 RSS 源。

当前决策：本周先使用方案 C（公开搜索）试跑。如果覆盖率和稳定性可以接受，就先继续用方案 C；如果效果不好，再补充方案 B（公开 RSS / 公开索引源）。完整方案见 `方案说明.md`。

## 已配置

- 账号清单：`config/accounts.json`
- 重点领域：亚马逊电商政策、规则/运营打法、方法论/AI赋能、AI领域
- 计划时间：美东时间每天 22:30
- 数据库：`data/monitor.db`
- 原始 HTML：不保存

## 安全原则

- 不使用微信账号、密码、Cookie、扫码登录。
- 不让 AI 操作微信客户端。
- 飞书 Webhook 放在本地 `.env`，不要提交到 Git 或发给第三方。
- 建议在飞书侧重置一次机器人 Webhook，因为当前链接已经出现在聊天上下文中。

## 配置飞书

复制 `.env.example` 为 `.env`，填写飞书机器人信息：

```bash
cp .env.example .env
```

`.env` 示例：

```bash
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/REPLACE_ME
FEISHU_BOT_SECRET=
```

如果飞书机器人开启了“签名校验”，把 secret 写入 `FEISHU_BOT_SECRET`。

## 文章来源

当前支持两种安全来源：

1. 账号级 Feed：在 `config/accounts.json` 的目标账号里增加 `feeds` 数组。
2. 公开 RSS/索引源：把 `config/feeds.example.json` 复制为 `config/feeds.json`，按微信 ID 填入公开 feed URL。
3. 手动公开链接：把公开文章链接放入 `data/manual_links.txt`，每行一个链接。也支持：

```json
{
  "name": "AMZ123跨境电商",
  "wechat_id": "amz123net",
  "feeds": ["https://example.com/rss/amz123net.xml"]
}
```

```text
amz123net	https://mp.weixin.qq.com/s/xxxx
```

后续可以增加新的 provider，但必须保持“不登录个人微信、不读取微信隐私”的边界。

### 批量配置 Wechat2RSS Feed

`config/accounts.json` 已支持保存 `sample_article_url`、`biz`、`biz_id` 和 `feeds`。如果有可用的 Wechat2RSS 私有服务，可以用样本文章链接或公众号 ID 批量添加订阅，并把返回的 RSS 地址写回账号配置：

```bash
WECHAT2RSS_BASE_URL=https://your-wechat2rss.example.com \
WECHAT2RSS_TOKEN=your_token \
python3 src/configure_feeds.py
```

先预览不写配置：

```bash
WECHAT2RSS_BASE_URL=https://your-wechat2rss.example.com \
WECHAT2RSS_TOKEN=your_token \
python3 src/configure_feeds.py --dry-run
```

公共实例测试说明：

- `rsshub.app/freewechat/profile/:biz` 当前返回 403。
- `wechat2rss.xlab.app/feed/:biz_id.xml` 对未公开收录账号返回 404。
- 因此稳定覆盖需要私有 Wechat2RSS 服务或可用第三方 Feed 地址。

## 运行

测试运行，不发送飞书：

```bash
./run_monitor.sh --dry-run
```

真实运行，发送飞书：

```bash
./run_monitor.sh
```

长期按美东时间每天 22:30 运行：

```bash
python3 src/scheduler.py
```

macOS 后台常驻运行：

```bash
chmod +x install_launchd.zsh
./install_launchd.zsh
```

查看日志：

```bash
tail -f logs/scheduler.out.log
tail -f logs/scheduler.err.log
```

## 后续待补

- 接入稳定的公开文章发现源。
- 如需更高质量 AI 摘要，可改为本地大模型或之后再接入正式 API；ChatGPT Plus 网页订阅不适合作为自动化脚本接口。
- 增加周报和关键词预警。
