# 卖点→构图模板库

> 按"图像功能"组织，跨品类复用率最高。下次新品做相似卖点直接挑模板用，不用从0构思。

## 如何使用本库

1. 找到你要表达的卖点对应的模板
2. 复制模板的构图描述和Prompt骨架
3. 把模板里的 `[产品]` `[卖点细节]` `[场景]` 替换成你的新品
4. 跨参考 `anti-pitfall-rules.md` 加约束
5. 出图

---

## 模板 T01 · 降噪 / 抗干扰

**适用卖点**：noise cancellation / environmental noise reduction / DSP enhancement

**核心机制**：声音保护罩 — 蓝色透明气泡包裹产品/人物，外部灰色噪音碰到气泡破碎淡化，内部干净声波

**构图**：竖版 4:5
- 中心偏右下：下巴到胸口（不露脸），产品夹在衣领上
- 中心：蓝色透明气泡包裹产品周围空间
- 左侧：灰色烟雾+模糊声波碎片（噪音被阻挡）
- 内部：一条蓝色干净人声波从嘴部流入产品

**主标题套路**：动词+对比
- "Your Voice. Not the Noise."
- "Silence the Noise. Keep Your Voice."
- "Cut the Noise. Stay Heard."

**Prompt 骨架**：
```
[Standard Amazon image header with text overlay]

Visual concept: a compact [产品] blocks noise and captures only the 
user's voice.

Composition: tight close-up framing from chin to collarbone only.
A [产品描述] is naturally [attached/clipped] to the [载体] as the 
hero product.

Visual mechanism: a transparent BLUE (#1E88E5) acoustic focus bubble 
surrounds the [产品] and user's [voice source]. OUTSIDE the bubble, 
SOFT GRAY (#94A3B8) semi-transparent drifting smoke and abstract 
sound wave fragments fade away. INSIDE the bubble, ONE clean smooth 
blue voice wave flows naturally from the [voice source] into the 
[产品].
```

**已验证案例**：vlogging kit 副图1 - "Your Voice. Not the Noise."

---

## 模板 T02 · 即插即用 / 简易设置

**适用卖点**：plug & play / no setup / easy to use / no app required

**核心机制**：三步分镜 — 每步一个动作，用编号徽章+连接箭头讲流程

**构图**：竖版 4:5
- 顶部：主标题+副标题
- 三个对角线分布的产品动作镜头
- 每个动作有 ①②③ 蓝色圆角徽章标注
- 蓝色细弧形箭头连接 ① → ② → ③

**主标题套路**：三动词+句号节奏
- "Plug. Clip. Record."
- "Open. Connect. Record."
- "Charge. Pair. Go."

**Prompt 骨架**：
```
Three-panel sequential storyboard with ①②③ blue round badges.

ACTION 1 (upper-left, labeled ①): [第一步动作的产品特写]
ACTION 2 (center, labeled ②): [第二步动作的产品特写]
ACTION 3 (lower-right, labeled ③): [第三步动作 - 通常是手机屏幕显示成果]

Connect with subtle thin BLUE (#1E88E5) curved arrows.
NO human figures, NO disembodied hands.
```

**已验证案例**：vlogging kit 副图2 - "Plug. Clip. Record."

**注意**：避免在三步里出现"无头人物"。要么纯产品+载体（如衣架/折叠衣物），要么完整露脸的真人创作者。

---

## 模板 T03 · 长距离 / 远范围

**适用卖点**：long range / wireless distance / works from far / no cable

**核心机制**：前景设备+远景使用者+蓝色信号弧线连接+距离徽章

**构图**：竖版 4:5
- 前景下1/3：手机+三脚架+接收器，强透视
- 中景到远景：使用者在远处做有意义的动作
- 蓝色虚线弧线连接两端
- 中段加蓝色圆角徽章标距离（"40m / 131ft"）
- 可选：右下角加局部放大圆补足细节

**主标题套路**：动作+收益
- "Step Back. Still Sound Close."
- "Move Free. Stay Heard."
- "Wide Range. Crystal Clarity."

**关键约束**：
1. 远处人物要真的远 — 占画面 **1/10-1/8** 高度（约160-200px in 2000px)
2. 场景必须让"远距离"逻辑成立（旅行Vlog / 户外采访 / 大型演讲，**不是**瑜伽教学 / 课堂讲课）
3. 远处人物身上的产品因为太小看不清 → 用放大圆补

**Prompt 骨架**：
```
Outdoor [scenic location: lake dock / coastal boardwalk / mountain 
overlook / open field] with strong DEPTH PERSPECTIVE.

FOREGROUND: smartphone on [product tripod] with [receiver] plugged in.

BACKGROUND (FAR DISTANT): a content creator standing VERY FAR AWAY 
with [meaningful gesture/pose], wearing [product] clipped to collar.

CRITICAL DISTANCE: the person occupies ONLY 1/10 to 1/8 of frame 
height. Cannot distinguish facial features.

Clean dashed BLUE (#1E88E5) curved wireless signal path connects 
distant person to foreground receiver.

ADD circular magnified inset in lower-right showing macro close-up 
of product clipped on fabric.
```

**已验证案例**：vlogging kit 副图3 - "Step Back. Still Sound Close." (湖边栈道场景)

---

## 模板 T04 · 一键操作 / 单按钮控制

**适用卖点**：one-tap / single button / instant activation

**核心机制**：产品悬浮居中 + 按钮发光高亮 + 左侧问题/右侧解决方案对比

**构图**：横版 1464×600
- 中心：产品 3/4 角度悬浮
- 关键按钮位置发蓝色光晕
- 左侧：问题的视觉化（如灰色噪音破碎）
- 右侧：解决的视觉化（如蓝色干净人声波流出）
- 左侧或上方：主标题
- 右下角小徽章：技术信息

**主标题套路**：动词命令式
- "Cut the Noise."
- "Mute Distraction."
- "One Tap. Total Clarity."

**关键约束**：
- **不要画手指按按钮**（AI画手指畸形率高），用按钮发光自带"被按"感
- 按钮上要有清晰的字母/符号 embossed
- 标题已说功能，图里不要重复加 "PRESS" 之类的箭头标签

**Prompt 骨架**：
```
Hero product floating center-frame, dramatic 3/4 side angle.
The [关键按钮] is HIGHLIGHTED with a soft blue (#1E88E5) radial 
glow, suggesting active control. NO finger gestures, NO press arrows.

LEFT SIDE: chaotic gray noise/problem visualization being dispersed.
RIGHT SIDE: one smooth blue clean wave/solution emerging.

The product acts as the visual barrier — chaos on left, clarity on 
right.

Small label "[tech badge]" in lower-right corner.
```

**已验证案例**：vlogging kit A+1 - "Cut the Noise."

---

## 模板 T05 · 多对一 / 配对使用

**适用卖点**：dual transmitters / multi-device pairing / team recording

**核心机制**：两个使用者面对面+中央接收器+两条蓝色信号汇入

**构图**：横版 1464×600
- 左侧：主标题+副标题（spec改成benefit）
- 中央到右侧：两位创作者面对面坐在桌子两侧
- 桌面中央：手机架在产品tripod上，接收器插底部
- 两条蓝色信号弧线从各自胸前发射器汇入手机接收器
- 明亮自然光，温暖室内场景

**主标题套路**：把spec翻译成benefit
- "Two Voices. One Phone." (不是"2 Mics. 1 Receiver.")
- "Made for Two."
- "Record Together. Solo Setup."

**关键约束**：
- 场景必须明确（家居播客 / 咖啡馆采访 / 工作室vlog）
- 信号线柔和不粗硬（像耳机广告的轻盈线条）
- 严禁"无头人"、"额外白色圆形物体"等AI幻觉
- tripod 形态必须精确（参考产品实拍）

**Prompt 骨架**：
```
Bright modern home podcast scene with two creators facing each other 
across a wooden table, mid-conversation.

LEFT person: [描述] with [产品] clipped to collar.
RIGHT person: [描述] with [产品] clipped to collar.

CENTER on table: smartphone on [product tripod with exact structure 
description] with receiver plugged in at bottom (connection point 
softly blurred).

TWO thin elegant translucent blue (#1E88E5) sound wave arcs flow 
from each creator's chest transmitter and merge into the receiver.

STRICTLY AVOID: NO ring lights on phone holder, NO white circles, 
NO third microphone, NO thick rubber-tube signal lines.
```

**已验证案例**：vlogging kit A+2 - "Two Voices. One Phone."

---

## 模板 T06 · 高音质 / 工艺细节（Soundcore式）

**适用卖点**：studio-grade sound / professional capsule / Hi-Fi audio

**核心机制**：产品本体 + 内部精密结构放大 + 引线标注关键工艺 + 底部认证徽标

**构图**：横版 1464×600
- 深色高级背景（深蓝→炭灰渐变）
- 左侧 50-60%：完整产品 3/4 角度（不剖开整体）
- 右侧 40-50%：大圆形放大圆，露出内部专业组件细节
- 细线引出标注关键工艺名
- 底部 3 个金边圆角小徽标：参数/认证

**主标题套路**：建立信任型
- "Built for Studio-Grade Sound."
- "Engineered for Clarity."
- "Hi-Fi Audio. Pocket Size."

**关键约束**：
- 内部组件**用银/铬色**，不用纯金/铜（避开生锈感）
- 引线指向位置要**与实物对应**（如咪头在侧面就别画在顶部）
- 底部徽标用真实可验证的参数（48kHz、24-bit、Hi-Fi Audio）
- 灯光戏剧化（强rim light），但不要过曝

**Prompt 骨架**：
```
Premium dark gradient background (#0F172A → #1E293B).

LEFT 50%: complete intact [产品] at dramatic 3/4 angle, lit with 
strong rim light. The [关键部位] is on the [正确位置 per real 
product]. Soft cool blue (#1E88E5) particles emanate from this area.

RIGHT 50%: large CIRCULAR MAGNIFIED INSET (with thin white border 
and connecting line) showing extreme close-up of internal [组件名]. 
Components in POLISHED SILVER-CHROME and subtle gold accents only 
(NO brass-yellow, NO copper, NO aged metal).

Three thin annotation lines pointing to: "[工艺1]", "[工艺2]", 
"[工艺3]" in light grey.

Bottom-right: three small gold-edged rounded badges: "[参数1]", 
"[参数2]", "[参数3]".
```

**已验证案例**：vlogging kit A+3 - "Built for Studio-Grade Sound."

**核心借鉴来源**：Soundcore "Enjoy Detail-Rich Sound" 

---

## 模板 T07 · 续航 / 电池寿命

**适用卖点**：long battery / fast charge / multi-day use

**核心机制**：产品+时间轴+使用场景缩略图

**构图**：横版 1464×600（建议）
- 左侧：主标题 + 数字徽章（"30 Hours")
- 中央：电池图标/进度条/时间轴
- 右侧：3-4个小缩略图代表"30小时能做什么"

**主标题套路**：数字+场景
- "30 Hours. 1 Charge."
- "All-Day Power. Pocket Size."
- "Charge Once. Vlog All Week."

**Prompt 骨架**：
```
Clean horizontal layout.

LEFT: large bold "30H" or "30 HOURS" number with subtitle.
CENTER: minimalist battery icon or charging visualization, blue accent.
RIGHT: 3-4 small lifestyle thumbnails showing realistic use cases 
that add up to 30 hours of typical use.

[Product] subtle as supporting element, not hero (this image is 
about the time, not the product per se).
```

**待验证案例**：尚未在本项目中实际应用，但常见于Anker/Soundcore/Hollyland等品牌

---

## 模板 T08 · 多场景兼容 / 通用性

**适用卖点**：works everywhere / multi-scenario / compatible with all

**核心机制**：网格九宫格场景拼图

**构图**：方形 1:1
- 4格或6格网格
- 每格一个不同场景：户外/室内/旅行/会议/直播/采访
- 每格右下角小图标标场景类型
- 中心或顶部：主标题

**主标题套路**：包容性
- "For Every Story. Every Setting."
- "Wherever You Create."
- "One Mic. Every Scene."

**Prompt 骨架**：
```
Grid layout 2x2 or 2x3. Each cell shows a different real-world 
scene with the [产品] in natural use:
- Cell 1: [scene A] with product
- Cell 2: [scene B]
- Cell 3: [scene C]
- Cell 4: [scene D]

Subtle small icons in each cell corner labeling the scene type.
Main headline overlaid at top center.
```

**待验证案例**：尚未在本项目中实际应用

---

## 附录：如何贡献新模板

发现一种新的"卖点→构图"配对？请按以下格式追加：

```markdown
## 模板 TXX · [卖点类型]

**适用卖点**：[英文关键词]

**核心机制**：[一句话描述视觉手法]

**构图**：[尺寸+布局]

**主标题套路**：[2-3个标题候选]

**关键约束**：[特别要注意的点]

**Prompt 骨架**：
```
[可直接复用的Prompt模板]
```

**已验证案例**：[哪个项目用过]
```

每次发现新的成功模式，就在Git里提交，让团队所有成员直接受益。
