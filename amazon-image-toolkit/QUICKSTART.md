# 快速上手指南

## 给你（项目owner）的步骤

### 一次性 setup（5分钟）

```bash
# 1. 把 plugin 复制到本地 ai-workspace
mkdir -p ~/ai-workspace
cp -r "/Users/lihuan/Documents/跨境业务/美国亚马逊业务运营/品类vlogging kit/SAVT101/生图v2/amazon-image-toolkit" ~/ai-workspace/

# 2. 进入 ai-workspace，初始化 git
cd ~/ai-workspace
git init
git remote add origin https://github.com/kyousan-star/ai-workspace.git

# 3. 创建 .gitignore，避免不必要文件污染仓库
cat > .gitignore <<'EOF'
.DS_Store
*.log
node_modules/
.env
# 不要提交项目级的VOC/产品PDF/竞品图等运营数据
# 只提交工具（amazon-image-toolkit），不提交某个产品的具体资料
本品产品信息.pdf
*VOC*.md
本品实拍图/
竞手*/
生图/
生图v*/
*.html
EOF

# 4. 首次提交
git add amazon-image-toolkit/ .gitignore
git commit -m "Initial: amazon-image-toolkit v0.1.0

包含:
- 4个 skills: product-image-planner, competitor-visual-analyzer, 
  image-spec-checker, product-consistency-checker
- 2个资源库: anti-pitfall-rules.md, composition-templates.md
- 基于vlogging kit新品5轮真实迭代经验沉淀"

git branch -M main
git push -u origin main
```

### 安装到 Cowork（2分钟）

在 Cowork 应用里：
1. 打开 Settings → Plugins
2. 选 "Install Local Plugin"
3. 选择文件夹 `~/ai-workspace/amazon-image-toolkit/`
4. 安装完成后，重启 Cowork 让 plugin 生效

### 验证安装

新开一个 Cowork 会话，输入：
```
/product-image-planner
```

如果 plugin 装好了，会看到 skill 被加载的提示。

---

## 给合作伙伴的步骤

发给他这段（或转发本 QUICKSTART.md）：

```bash
# 1. clone 仓库到本地
cd ~
git clone https://github.com/kyousan-star/ai-workspace.git
cd ai-workspace

# 2. 安装到 Cowork
# Settings → Plugins → Install Local Plugin → 选择 amazon-image-toolkit/ 文件夹
```

---

## 日常迭代流程

### 你发现新的AI翻车点 / 想加新模板

```bash
cd ~/ai-workspace

# 修改 anti-pitfall-rules.md 或 composition-templates.md
vim amazon-image-toolkit/resources/anti-pitfall-rules.md  # 加新规则

# 提交
git add amazon-image-toolkit/
git commit -m "feat(rules): 新增 [规则简述]"
git push
```

### 合作伙伴拉取你的更新

```bash
cd ~/ai-workspace
git pull
# Cowork 中重新加载 plugin (Settings → Plugins → 找到 → Reload)
```

### 重要变更走 PR review

```bash
# 你想做重大修改时
git checkout -b feature/new-skill-xyz
# ... 改完
git push origin feature/new-skill-xyz
# 在 GitHub 上创建 PR，让合作伙伴 review 后再 merge
```

---

## 使用 plugin 开新品的标准流程

### Step 1: 准备 workspace
新品的工作目录建议放在你**自己电脑**的某个固定位置（不要放在 ai-workspace git仓库里，那是给工具用的）：

```
~/work/products/SAVT102_新品名/
├── 本品产品信息.pdf
├── 工厂规格书.pdf
├── VOC分析报告.md
├── 本品实拍图/
└── 竞手asin图片参考/
    └── B0XXXXXXXX/
```

### Step 2: 在 Cowork 中打开这个文件夹
让 Cowork 能访问到 workspace。

### Step 3: 调用主skill
```
/product-image-planner

或者直接说："为这个新品规划6张产品图（3副图+3 A+图）"
```

skill 会自动：
1. 扫描你的 workspace
2. 读取所有可用资料
3. 如果竞品图存在，自动调用 competitor-visual-analyzer 先做竞品分析
4. 问你 2-4 个关键问题
5. 生成完整的HTML规划方案到你的 workspace

### Step 4: 拿 HTML 去生图
HTML 里每张图都有 copy 按钮，复制英文 Prompt 到 image2/MJ/即梦等工具生图。

### Step 5: 出图后检查
```
/image-spec-checker        # 检查尺寸合规
/product-consistency-checker  # 检查产品形态在多张图里是否一致
```

### Step 6: 迭代
有问题的图重抽。每次发现新翻车点，记得回头**更新 anti-pitfall-rules.md 并提交到Git**，让规则库越用越聪明。

---

## 故障排查

### Q: plugin 安装失败？
A: 检查目录结构是否完整：必须有 `.claude-plugin/plugin.json` 和 `skills/*/SKILL.md`。

### Q: skill 调用了但没反应？
A: 确认 SKILL.md 的 frontmatter `description` 字段里有触发关键词，且 Cowork 已重启。

### Q: 生成的方案太通用，不够针对性？
A: 检查 workspace 里是否有完整的 `本品产品信息.pdf` 和 `VOC分析报告.md`。资料越完整，方案越精准。

### Q: 合作伙伴 pull 后看不到新内容？
A: 让他在 Cowork 里 "Reload Plugin" 或重启 Cowork。

---

## 下一步发展（v0.2 路线图）

- [ ] 加 `prompt-from-template` skill：从 composition-templates 直接生成新prompt
- [ ] 加 `listing-copy-writer` skill：把图片规划+VOC转化成五点描述+标题
- [ ] 加 `competitor-deep-dive` skill：深度对比单个竞品的优劣
- [ ] 引入 connectors（如直接调 image2 API 出图）
- [ ] 多语言支持（日本/欧洲 Amazon 也用得上）

发现想加的功能，提 issue 到 https://github.com/kyousan-star/ai-workspace/issues
