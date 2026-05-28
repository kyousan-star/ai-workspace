# 抗AI翻车规则库

> 这份规则库沉淀了真实迭代项目踩过的所有坑。每次发现新的翻车点，请追加到本文档。每次 product-image-planner 调用前都应交叉引用本库。

## 一、视觉物理性 (Physical Plausibility)

### 规则 1.1：领夹/夹扣类设备必须显示夹机构
**问题症状**：AI画领夹麦时常把麦克风"贴"或"吸"在衣服上，看不到金属夹的张开机构 → 用户误以为是磁吸款。

**修复约束**：
```
The microphone must be CLIPPED to the shirt fabric via its visible 
metal back-clip — the clip jaw must be openly visible grabbing the 
fabric edge, similar to a clothing peg or badge clip. The microphone 
must NOT appear magnetically attached or floating against the shirt.
```

### 规则 1.2：插头必须真插进端口
**问题症状**：AI画接收器插手机时常把接收器"放在手机旁边"或"悬浮在端口附近"。

**修复约束**：
```
The receiver must be FIRMLY AND FULLY INSERTED into the phone's USB-C 
port — ZERO gap between the receiver's base and the phone's bottom 
edge. The gold USB-C plug must be COMPLETELY HIDDEN inside the phone 
(NOT visible, NOT exposed). Only the receiver's main black body 
sticks out from the phone.
```

### 规则 1.3：组件位置要对应实物
**问题症状**：写"剖开顶部露出咪头"，但实物咪头在侧面mesh grille → 光从错位置发出，视觉不合理。

**修复策略**：先核对实物照片，把咪头/按键/接口的真实位置写进prompt。错位置画出来的光发射、引线标注都不合理。

### 规则 1.4：远景人物大小要真实
**问题症状**：要表达"40m距离"时，AI会把远处人物画到画面1/3-1/4高度，距离感不对。

**修复约束**：
```
CRITICAL DISTANCE: the person must appear as a SMALL DISTANT FIGURE, 
occupying ONLY about 1/10 to 1/8 of the frame height (roughly 
160-200px tall in a 2000px image). Use clear depth perspective — 
the person is small enough that detailed facial features are not 
distinguishable.
```

---

## 二、人体解剖学 (Human Anatomy)

### 规则 2.1：避开手指特写动作
**问题症状**：手指按按钮的特写中，AI画错率约 30-40%：反向关节、6指、关节方向畸形、过细/过粗。

**修复策略**：能不用手指就不用。"按M键"可以改成"M键发蓝光+红色箭头"。

**如果必须用手指**：
```
A single human index finger with exactly TWO joints visible (correct 
human anatomy), pressing the button at a natural angle. The finger 
should be soft-blurred slightly to avoid hard rendering errors. NO 
extra fingers visible, NO distorted hand structure.
```

### 规则 2.2：避开完整人脸特写
**问题症状**：AI画人脸常出现"塑料/CGI皮肤"、"恐怖谷"、五官不对称。

**修复策略**：
- 剪到下巴/胸口（chin to chest）
- 用背影/3/4角度
- 远景小人物（看不清面部）
- 如必须有脸，强调 `photo-realistic skin with natural pores, NOT CGI smoothing`

### 规则 2.3：性别要明确，避开"中性脸"
**问题症状**：不指定性别时，AI易画出"不男不女"的中性脸，让用户出戏。

**修复约束**：
```
Specify gender: "young casual female content creator with smooth 
feminine jawline" OR "young casual male content creator with subtle 
Adam's apple and light beard stubble"
```

---

## 三、材质与配色 (Materials & Colors)

### 规则 3.1：避免大面积纯金/铜色（高翻车率）
**问题症状**：AI渲染纯金/铜色易出现"氧化生锈感"，让产品看着 low / 老旧。

**修复策略**：
- 主体不用金色，改用 **银色/亮铬色** + 金色仅做小点缀（小徽章/边圈）
- 如必须金色，加修饰词："polished mirror gold, NOT brass, NOT copper, NOT aged metal"

### 规则 3.2：蓝色是最安全的"科技感"主色
**经验**：`#1E88E5` 这个蓝在所有AI模型里都被正确理解为"科技感"，且不会翻车成幼稚的卡通蓝。

**配色组合建议**：
- 主背景：浅冷灰渐变 `#FFFFFF → #F0F4F8`
- 科技强调：蓝 `#1E88E5`
- 警示/对比：珊瑚红 `#E53E3E`
- 成功/确认：鲜绿 `#22C55E`
- 深色高级感背景：`#0F172A → #1E293B` 渐变

### 规则 3.3：噪音视觉化要与主体风格统一
**问题症状**：左边粗糙像素破碎、右边柔和光晕泡泡 → 风格割裂。

**修复策略**：噪音用"半透明灰色烟雾飘散+模糊声波条"，与蓝色泡泡风格统一。

---

## 四、文字渲染 (Text Rendering)

### 规则 4.1：图内文字越少，准确率越高
**经验数据**（基于本次5轮迭代）：
- 1-2个短句（如"Cut the Noise."）：成功率 ~95%
- 3-5个标签（如多个步骤名）：成功率 ~75%
- 8+个文字元素（多卡片+参数）：成功率 ~40%

**修复策略**：能砍的都砍，把信息分给图标/视觉效果承担。

### 规则 4.2：避免复杂特殊符号
**易翻车符号**：
- `≤` (小于等于) → 改用 `Up to`
- `–` (en dash) → 改用 `-` 普通短横
- `−36dB` (负号) → 改用 `-36dB` 或 `minus 36 dB`
- `™ ® ©` → 直接省略

### 规则 4.3：标题和图内标签禁止信息重复
**问题症状**：标题已说"Press M"，图里又加红色"PRESS"标签 → 信息冗余浪费视觉资源。

**原则**：标题说什么，图内就不要再重复说。省下的空间放有价值的新信息（小徽章、技术参数、信任标识）。

### 规则 4.4：单字符渲染瑕疵的修复
**问题症状**：标题里的特定字母（如"Cut"的"t"）有时会渲染缺失横线/笔画。

**修复策略**：
- 重抽几次
- 或PS里用文字工具重新打字覆盖（字体推荐 Inter Bold / Helvetica Neue Bold）
- 在Prompt里加：`PERFECTLY RENDERED CRISP TYPOGRAPHY with every letter complete and sharp (especially the [字母X] in "[词]" must be fully formed)`

### 规则 4.5：字体描述避开品牌词
**问题**：写"Apple-style typography"或"Sony广告字体"有侵权暗示。

**修复**：用通用描述：`modern minimalist sans-serif typeface similar to Inter or Helvetica Neue, bold weight, perfectly spelled`

---

## 五、文案策略 (Copy Strategy)

### 规则 5.1：主标题是 Benefit，不是 Spec
**对比**：
- ❌ "2 Mics. 1 Receiver." (产品规格描述)
- ✅ "Two Voices. One Phone." (用户benefit)

**原则**：把spec翻译成用户能立刻理解的"能做什么/给我什么好处"。

### 规则 5.2：短句+句号节奏比长句强
**对比**：
- ❌ "Wireless Lavalier Microphone with Advanced DSP Noise Cancellation Technology" (技术堆砌)
- ✅ "Cut the Noise." (一句话+视觉补足)
- ✅ "Plug. Clip. Record." (三动词节奏)

**原则**：Amazon广告文案的黄金法则 = 短、punchy、有节奏。每个字都要有价值。

### 规则 5.3：避免"形容词通货膨胀"
**避免**：crystal clear / super premium / ultra amazing / cutting-edge
**改用**：具体可验证的事实（48kHz、24-bit、40m range、7h battery）

---

## 六、构图与场景 (Composition & Scenes)

### 规则 6.1：场景必须有"卖点存在的必要性"
**反例**：用"户外瑜伽教学"场景表达"40m收音" — 但瑜伽老师不会站40m外教课，逻辑不合理。

**正例**：用"户外旅行Vlog自录"场景表达"40m收音" — vlogger要展示风景全景，远距离自拍是真实需求。

**原则**：问自己"为什么这个用户会有这个场景？这个场景下他为什么需要这个卖点？" 如果回答不出，换场景。

### 规则 6.2：双视角构图补足细节
**用途**：AI画远景小物体不可靠时（如远处人物胸前的小麦克风）。

**模板**：左侧/上方主场景 + 右下角圆形局部放大圆（带连接线指向被放大的细节）+ 圆旁小标签。

**Prompt约束**：
```
ADD a CIRCULAR MAGNIFIED INSET in the LOWER-RIGHT corner (about 25% 
of frame width, with thin white circular border and a thin connecting 
line pointing to the [被放大的位置]) showing a CLEAN MACRO CLOSE-UP 
of [被放大的细节描述]. The label "[标签]" appears next to the inset.
```

### 规则 6.3：避免"假装合理"的不合理构图
**典型例子**：衣架挂着衣服vs 桌面flat-lay构图 = 物理冲突（挂衣服应该是垂直构图，flat-lay应该是平铺）。

**解决方案**：所有元素的物理姿态必须与整体视角一致。要么改视角，要么改元素姿态。

### 规则 6.4：复杂场景AI翻车风险高，简洁场景更稳
**经验**：
- 纯产品摆拍：成功率 ~90%
- 1-2人简单场景：~75%
- 3+人复杂场景：~40%
- 复杂机械结构（剖面/爆炸图）：~50%

**策略**：能简洁就简洁。复杂场景要做心理准备：抽3-5次取最好。

---

## 七、产品一致性 (Product Consistency)

### 规则 7.1：跨图复用产品必须重复完整描述
**问题症状**：6张图里画的"同一个产品"，按键数量/颜色/位置每张图都略有不同 → AI每张图都在"重新发明"产品。

**修复策略**：在每张图的Prompt里都重复完整的产品形态描述（不要省略以为AI会记住前面图的设定）。建议在plugin资源里维护一个 `unified-product-description.md`，每次出图都粘贴进去。

### 规则 7.2：精确到数字
**对比**：
- ❌ "small buttons on the side" → AI画 1/2/3 个按钮不定
- ✅ "exactly TWO small side buttons on the long side, the upper one labeled 'M', the lower one unmarked"

---

## 八、AI 偏好与禁止词 (AI Quirks & Negative Prompts)

### 规则 8.1：每个Prompt末尾必加 STRICTLY AVOID 列表
**模板**：
```
STRICTLY AVOID: NO [常见AI翻车1], NO [常见AI翻车2], NO logos, NO 
brand names, NO extra text, NO misspelled text, NO 3D render plastic 
look, NO CGI smoothing, NO floating products, NO [此场景特定的翻车点].
```

**经验**：负面词的效果远大于正面描述。AI会主动避开你明确禁止的东西。

### 规则 8.2：摄影器材化描述比"高质量"更管用
**对比**：
- ❌ "high quality, premium, professional photo" → AI还是给你模糊塑料感
- ✅ "shot on Sony A7 with 35mm f/1.4 prime lens, available natural daylight, candid editorial style" → 真实感跃升

### 规则 8.3：明确"不要3D渲染感"
**问题症状**：默认情况下AI图常带"3D软件渲染"的塑料质感。

**修复约束**：
```
PHOTO-REALISTIC (NOT 3D render, NOT CGI, NOT illustration, NOT 
plastic toy look). Natural visible skin texture, real fabric weave 
visible, real metal reflections.
```

---

## 九、迭代效率技巧 (Iteration Efficiency)

### 规则 9.1：高风险图先抽
**原则**：复杂构图、新尝试视觉（如剖面+引线）先抽，验证思路是否走得通。如果走得通，简单的图基本都能稳定出。

### 规则 9.2：成功的图保留Prompt作模板
每次出对的图，把对应的Prompt存档。下次同类卖点直接复用结构，只换产品细节。

### 规则 9.3：失败的图要记录失败原因
不只记"这张不行"，要记"这张哪里不行"（如"M键无字母"、"手指畸形"、"距离感太近"）。这些反馈喂回 anti-pitfall-rules.md 让规则库越用越聪明。

### 规则 9.4：5轮迭代是合理预期
**经验节奏**：
- v1: 初步规划（基础假设）
- v2: 融合借鉴（融入参考方案）  
- v3: 解决质感问题（塑料感、CGI感）
- v4: 解决具体bug（产品形态、AI幻觉）
- v5: 精修细节（文案、构图微调）

**不要期望一次到位**。每轮迭代解决一类问题，5轮通常能达到上架水准。

---

## 十、对接 Amazon 规范 (Amazon Compliance)

### 规则 10.1：主图独立做，不靠AI生成
**原因**：主图要求纯白底+1:1+产品占85%+无文字，AI很难一次满足全部。

**替代方案**：用真实产品照片做去背（remove.bg）+ PS排版到2000×2000纯白底。

### 规则 10.2：副图分辨率要≥1600短边
**原因**：Amazon"鼠标悬停缩放"功能需要长边1600+，否则缩放体验差。

**解决**：AI输出后用 Topaz Gigapixel / Photoshop "保留细节2.0" 放大到 1600×2000 以上。

### 规则 10.3：A+图按Module 4标准
**尺寸**：1464×600（宽幅）或 970×600（标准）。优先选1464×600，视觉更现代。

### 规则 10.4：避开品牌名/Logo渲染
**原因**：AI可能渲染出竞品Logo（Apple、Sony等）触发Amazon审核。

**Prompt约束**：`NO recognizable brand logos, NO Apple logo, NO branded products visible, generic device only`

---

## 附录：如何贡献新规则

发现新的AI翻车点？请按以下格式追加到对应章节：

```markdown
### 规则 X.Y：[简短描述问题]
**问题症状**：[具体描述，最好有截图链接]

**修复策略 / 修复约束**：
[具体的Prompt约束，可以直接复制使用]

**经验来源**：[哪个项目/哪个品类发现的]
```

每追加一条规则就在Git里提交，让团队所有成员立即受益。这个文档**越用越值钱**。
