# amazon-image-toolkit

> Amazon产品图全流程工作流：从0到上架的Cowork plugin

## 解决什么问题

每次新品做Amazon副图+A+图通常要经历：
- 读VOC/产品/竞品资料（~30min）
- 设计6张图的构图+文字+Prompt（~90min）
- 生图→发现AI翻车（手指畸形、金色生锈、产品形态不一致…）（~60min）
- 重新迭代Prompt（~60min × N轮）

**总耗时往往3-5小时，且每次都在重新踩同样的坑。**

本plugin把5轮真实迭代的经验沉淀成可复用工具：
- 下次新品规划从 **3小时 → 15分钟**
- 抗AI翻车规则库自动应用，**首次出图成功率从30% → 70%+**
- 跨品类复用，无论新品是麦克风/三脚架/补光灯/充电宝/耳机都能用

## 包含什么

### Skills (4个)

| Skill名 | 触发方式 | 功能 |
|---|---|---|
| `product-image-planner` | 主工作流 | 读workspace→问关键问题→生成HTML规划方案 |
| `competitor-visual-analyzer` | 子工作流 | 扫竞品图文件夹→输出视觉策略分析报告 |
| `image-spec-checker` | 辅助 | 检查图片尺寸是否达标Amazon规范 |
| `product-consistency-checker` | 辅助 | 跨多张图核查产品形态/按键/颜色一致性 |

### Resources (2个)

| 资源 | 用途 |
|---|---|
| `anti-pitfall-rules.md` | AI翻车经验库（手指畸形/金色生锈/远景失真等）|
| `composition-templates.md` | 卖点→构图模板库（降噪/即插即用/远距离等通用模板）|

## 标准 workspace 文件结构

本plugin期待工作目录有以下文件（可缺，但越完整规划越准）：

```
你的项目文件夹/
├── 本品产品信息.pdf          # 产品参数、卖点定义、目标用户
├── 工厂-规格书.pdf            # 产品技术规格
├── VOC分析报告.md             # 该品类的用户评论分析
├── 本品实拍图/                # 产品实拍照片
│   ├── product1.jpg
│   └── ...
└── 竞手asin图片参考/          # 竞品图片
    └── B0XXXXXXXX/
        ├── 主副图/
        └── A+图/
```

## 安装方式

### 方式A：从git仓库安装（推荐，自动同步更新）

```bash
# 你和合作伙伴各自执行
cd ~/ai-workspace  # 或你的项目根目录
git clone https://github.com/kyousan-star/ai-workspace.git .

# 在 Cowork 中安装：
# Settings → Plugins → Install Local Plugin → 选择 amazon-image-toolkit/ 文件夹
```

### 方式B：从 .plugin 压缩包安装

```bash
# 把 amazon-image-toolkit/ 目录打包成 .plugin 文件
cd amazon-image-toolkit
zip -r ../amazon-image-toolkit.plugin .

# 双击 .plugin 文件，Cowork 会引导安装
```

## 更新流程（团队协作）

```bash
# 修改了规则或新增了模板？提交并推送
git add amazon-image-toolkit/
git commit -m "feat: 新增'极简文案'抗翻车规则"
git push

# 合作伙伴拉取
git pull
# Cowork中重新安装一次plugin即可
```

## 快速使用示例

### 场景1：开始一个新品规划

1. 把新品资料放入workspace文件夹（产品信息、VOC、竞品图）
2. 在 Cowork 中：`/product-image-planner`
3. 回答几个关键问题（目标用户、卖点优先级、品牌色等）
4. 收到一份完整的6张图HTML规划方案，含每张图的英文Prompt

### 场景2：评估已出图

1. 把生成的图放进 workspace 的 `生图/` 文件夹
2. `/image-spec-checker` → 检查尺寸是否达标
3. `/product-consistency-checker` → 检查产品在多张图里是否一致

### 场景3：研究竞品

1. 把竞品ASIN的图爬下来放进 `竞手asin图片参考/B0XXXXXXXX/`
2. `/competitor-visual-analyzer` → 自动生成竞品视觉策略报告

## 版本

**v0.1.0** (Initial Release)
- 4 skills + 2 resource libraries
- 基于真实5轮迭代经验沉淀

## 贡献

发现新的AI翻车点？想加新的构图模板？欢迎提PR：

1. Fork仓库
2. 在 `anti-pitfall-rules.md` 或 `composition-templates.md` 追加内容
3. 提交PR，合作伙伴 review

## License

MIT
