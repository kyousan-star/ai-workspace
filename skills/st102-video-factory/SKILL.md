---
name: st102-video-factory
description: 为 VLOGARA ST102 规划、切片、补拍、渲染和质检 TikTok、Instagram Reels、YouTube Shorts 及 Amazon/Shopify 视频。触发词：做ST102视频、ST102视频工厂、切片ST102买家秀、用现有素材做短视频、生成本周TikTok、ST102视频脚本、ST102视频质检、批量出片。支持规划模式和完整出片模式；不用于纯文本直接生成真人动态视频，也不自动发布到外部平台。
metadata:
  last_verified: "2026-07-15"
  staleness_risk: "medium"
---

# ST102 Video Factory

把 ST102 的分散原片变成可审核、可追溯、可重复生产的短视频批次。默认以真实场景内容为主，How-to 为辅，先预览后终版。

## 执行入口

根据用户意图选择模式：

1. **规划模式**：盘点素材、转录、生成内容矩阵、脚本和补拍清单；不得渲染。
2. **切片模式**：只从已授权素材生成切片计划或预览。
3. **完整出片模式**：执行已确认的 cut manifest，生成预览、质检、终版、封面文案和发布台账。
4. **质检模式**：检查现有视频的尺寸、时长、披露、字幕和产品 Claim。

用户未明确要求终版时，默认停在规划或预览阶段。

## 必读顺序

开始任何批次前：

1. 读取 [references/project-paths.md](references/project-paths.md)，定位中央Skill、项目目录和事实源。
2. 读取 [references/st102-facts.md](references/st102-facts.md)，锁定产品事实。
3. 选题时读取 [references/content-strategy.md](references/content-strategy.md)。
4. 使用创作者素材或写产品 Claim 时读取 [references/claims-and-rights.md](references/claims-and-rights.md)。
5. 创建文件或交付时读取 [references/output-contract.md](references/output-contract.md)。

若事实源与本Skill快照冲突，以日期更新、证据更强的事实源为准；记录差异，停止使用冲突 Claim。

## 标准工作流

### 1. 初始化或读取项目

项目不存在时运行：

```bash
python3 scripts/init_project.py
```

新建批次时运行：

```bash
python3 scripts/create_campaign.py --project <project-root> --campaign <YYYY-MM-batch-NN>
```

### 2. 素材盘点

```bash
python3 scripts/inventory_media.py --project <project-root>
```

必须保留原文件，不移动、不重命名、不覆盖。通过绝对路径、SHA-256、时长、分辨率和授权类型识别素材。

需要口播文本时：

```bash
python3 scripts/transcribe_media.py <video> --output-dir <campaign>/transcripts
```

### 3. 生成内容计划

默认比例：

- 70% 场景使用/结果型内容。
- 30% How-to、FAQ 和评论回答型内容。

每条视频只承载一个主要承诺。为每条输出：`content_id`、支柱、Hook、目标观众、镜头清单、已有素材、缺失素材、字幕、Caption、披露、目标渠道和风险 Claim。

批量渲染前必须让用户确认内容计划。

### 4. 建立剪辑清单

每条视频使用一个 JSON cut manifest。字段定义见 [references/output-contract.md](references/output-contract.md)。不得直接凭聊天中的临时时间码渲染终版。

### 5. 渲染预览

先检查依赖：

```bash
python3 scripts/preflight.py --project <project-root>
```

生成单条预览：

```bash
python3 scripts/render_short.py <manifest.json> --mode preview
```

批量生成：

```bash
python3 scripts/render_batch.py <manifest-dir> --mode preview
```

若独立 `ffmpeg`/`ffprobe` 不可用，停止并报告，不调用应用包内不稳定的私有二进制。

### 6. 质检

```bash
python3 scripts/qa_video.py <manifest.json> --video <rendered.mp4> --report <qa.json>
```

必须检查：

- 竖版分辨率、时长和文件可播放性。
- 字幕安全区与可读性。
- 禁用 Claim 和事实冲突。
- 创作者素材授权状态及 `Gifted`/`Sponsored Product Demo` 披露。
- 产品外观、配件和包装边界。

任何硬失败不得进入 `finals/`。

### 7. 终版与发布边界

用户确认预览后才生成 `final`。Skill 只准备发布包，不登录、不上传、不点击 Publish，除非用户在当次任务中明确授权具体平台和具体视频。

## 不得做

- 不把换音乐或换一句 Hook 自动计为全新内容故事。
- 不修改原始视频。
- 不把付费/赠品创作者演示包装成自然买家证言。
- 不使用未验证的 `Zero Wobble`、`1-Second Release`、`Works on Uneven Ground` 等 Claim。
- 不把 Cooking 斜俯拍表述为横臂式真 overhead。
- 不在Skill目录内保存项目原片、预览或成片。
