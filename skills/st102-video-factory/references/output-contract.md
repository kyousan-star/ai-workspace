# Output Contract

## 项目结构

```text
video-factory/
├── project.yaml
├── inventory/
│   ├── source-manifest.csv
│   ├── media-inventory.csv
│   └── transcripts/
├── campaigns/<campaign-id>/
│   ├── brief.md
│   ├── content-plan.csv
│   ├── scripts/
│   ├── shot-list.md
│   ├── cut-manifests/
│   ├── transcripts/
│   ├── previews/
│   ├── finals/
│   ├── covers/
│   ├── captions/
│   └── qa/
├── approved-library/
└── publish-log/content-log.csv
```

## Cut manifest

每条视频一个JSON：

```json
{
  "content_id": "st102-solo-remote-01",
  "title": "Film solo without running back to your phone",
  "input": "/absolute/path/source.mp4",
  "start": 61.7,
  "end": 70.0,
  "output_dir": "/absolute/path/campaign",
  "output_name": "st102-solo-remote-01",
  "captions_srt": "",
  "logo": "",
  "source_kind": "sponsored_creator",
  "rights_status": "approved_cross_channel",
  "disclosure": "Sponsored Product Demo",
  "claims": ["Bluetooth remote", "solo recording"],
  "channels": ["tiktok", "reels", "shorts"]
}
```

## 文件命名

- 预览：`<content_id>_v01_preview.mp4`
- 终版：`<content_id>_v01_final.mp4`
- 字幕：`<content_id>_v01.srt`
- 封面：`<content_id>_v01_cover.jpg`
- QA：`<content_id>_v01_qa.json`

## 默认技术规格

- 画幅：9:16。
- 预览：720×1280，H.264，AAC。
- 终版：1080×1920，H.264，AAC，`yuv420p`，faststart。
- 单条目标时长：12–25秒；超出不自动失败，但必须在QA报告提示。
- 输出不可覆盖同名文件；必须递增版本或显式使用覆盖参数。

## 内容计划字段

`content_id,pillar,hook,audience,story,source_assets,missing_shots,caption,disclosure,channels,status`

## 发布台账字段

`date,content_id,platform,url,pillar,duration,views,likes,comments,shares,profile_visits,bio_clicks,notes`
