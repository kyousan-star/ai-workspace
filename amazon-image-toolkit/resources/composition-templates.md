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

## 模板 T09 · 产品存在感型（v2新增）

**设计问题**：如何让产品不是"被展示"，而是主动进入用户视觉空间？

**核心机制**：产品占据画面最强视觉位置，制造"它正在向你靠近"的感知，而非"你在看它"。

**适用判断**（按产品类型选实现手法）：

| 产品类型 | 推荐手法 | 不适用 |
|----------|----------|--------|
| 小型手持品（美妆/配件/手机周边） | 广角前伸：模特把产品递向极前景，广角畸变放大 | 大件家具 |
| 有纹理/材质卖点的产品 | 极限近景：产品局部特写占满画面，纹理肉眼可见 | 需要展示尺寸比例的产品 |
| 需要传递强存在感的任何产品 | 产品占画面70-80%+戏剧性单侧打光，几乎无背景 | 场景感是核心卖点时 |

**主标题套路**：动词+状态（不描述功能，描述感觉）
- "Made to Be Held."
- "This Close to Perfect."
- "Take It."

**关键约束**：
1. 产品必须是绝对主角，模特（如有）退到情绪配角
2. 广角前伸手法：`extreme wide-angle lens distortion, product pushed toward camera in extreme foreground, model's arm extending product toward lens` — 不要用普通焦段
3. 极限近景手法：不要试图展示产品全貌，只展示最有质感的局部
4. 产品形态描述必须与 unified form 一致，不因构图变化而漂移

**Prompt 骨架（广角前伸版）**：
```
[Amazon secondary image, 1600x2000, text overlay at top]

Extreme close-up hero shot with dramatic wide-angle lens distortion.

HERO PRODUCT: [产品完整描述] extended toward the camera in the 
extreme foreground, appearing 2-3x larger than real scale. The 
product surface occupies the bottom 60% of the frame.

BACKGROUND: [模特/手] holds the product from behind, arm slightly 
visible in soft-focus mid-ground. Expression: confident, natural.

DEPTH EFFECT: strong near-far perspective compression — product 
sharp and large, background soft and receding.

COLOR: [品牌色/背景色] gradient backdrop, no busy elements.

STRICTLY AVOID: [标准禁止项列表]
```

**Prompt 骨架（极限近景版）**：
```
[Amazon secondary image, 1600x2000, text overlay at top]

Extreme macro close-up of [产品最有质感的部位: 旋钮/织物/金属边框/按键].

The [部位] fills 70-80% of the entire frame. [纹理细节描述: e.g. 
matte aluminum grain visible at microscopic level / stitching 
pattern clearly defined]. 

Shot on Sony A7 with 90mm macro lens, f/2.8. Shallow depth of field.

STRICTLY AVOID: [标准禁止项列表]
```

**已验证案例**：新模板，尚未在真实项目中验证

---

## 模板 T10 · 反差感型（v2新增）

**设计问题**：如何让用户第一眼觉得"这张图有点不一样"，停下来多看一秒？

**核心机制**：品类刻板印象 × 反向情绪元素 = 画面张力

**公式步骤**：
1. 定义该产品给用户的"第一印象关键词"（如：游戏椅=电竞/硬核/男性）
2. 找一个方向相反但逻辑合理的情绪元素（如：猫=柔软/慵懒/家庭感）
3. 验证合理性：这个元素出现在产品旁边，用户会觉得自然还是突兀？
4. 确认它能把用户引向产品正面卖点（反差要服务于卖点，不是为反差而反差）

**品类刻板印象参考**：

| 品类 | 刻板印象词 | 可用反向元素 |
|------|-----------|-------------|
| 电竞/游戏外设 | 硬核/机械/男性/冷 | 猫/儿童/鲜花/针织毯 |
| 工具类 | 粗犷/专业/脏/力量 | 儿童空间/精致厨房/女性独立感 |
| 收纳类 | 极简/冷静/秩序 | 孩子的贴纸/宠物零食/五颜六色的小混乱 |
| 按摩仪/保健品 | 放松/慵懒/松弛 | 高跟鞋/西装/职场压力痕迹 |
| 户外/运动装备 | 粗犷/体能/挑战 | 宠物/家人/温馨仪式感 |

**主标题套路**：揭示隐藏的一面
- "Tougher Than It Looks. Softer Than You Think."
- "For the One Who Does It All."
- "Work Hard. Rest Right."

**关键约束**：
1. 反差元素必须"合理但意外"——猫趴椅子合理，猫靠近刀片不合理
2. 产品仍然是主角，反差元素是配角（用户记住猫但忘了椅子=失败）
3. 反差要服务于某个具体卖点（舒适/易用/适合全家/情绪价值），不是随机加元素
4. 用户画像要提前做（什么人会觉得这个反差有共鸣？）

**Prompt 骨架**：
```
[Amazon secondary image, 1600x2000, text overlay at top]

Scene: [具体场景描述，融合产品的刻板环境和反向情绪元素]

HERO PRODUCT: [产品完整描述] as the clear visual anchor.

CONTRAST ELEMENT: [反向情绪元素] naturally present in the scene — 
[描述它如何与产品形成视觉对比: e.g. soft fur against hard plastic / 
delicate flowers beside matte metal].

The contrast creates a visual question: [用户会产生的疑问, e.g. 
"Why is there a cat on a gaming chair? → Must be comfortable enough 
for even a cat to claim it."]

LIGHTING: [场景光线，建议暖光以软化刻板印象]

STRICTLY AVOID: [反差元素的边界红线: NO dangerous juxtapositions, 
NO confused product role, NO model that outshines the product]
```

**已验证案例**：新模板，参考来源：西西酱《亚马逊图片别做得太正经》游戏椅+猫案例

---

## 模板 T11 · 焦虑场景叙事型（v2新增）

**设计问题**：如何让用户不只是"知道"产品能解决问题，而是"感受到"这个问题？

**核心机制**：先让用户感受到危险/痛点/风险，再让产品出场解决它。上半部分是钩子，下半部分是证明。

**适用产品**：任何解决具体痛点/风险的产品（防护、安全、便携、防丢、防漏、防摔……）

**叙事结构**：
```
上半部分（60%）：危机场景可视化
  ├── 一个用户真实会担心的瞬间（不是泛泛的"问题"）
  ├── 短视频钩子式文案（5字以内，有反问/反转/冲突感）
  └── 场景有足够的情绪张力，让用户停下来

下半部分（40%）：产品结构证明
  ├── 产品本体 + 关键结构标注（为什么它能解决上面的问题）
  └── 让用户从感性回到理性（"原来它真的能保护我"）
```

**主标题套路**：反问式+反击式
- "Snatch This? Not Today."
- "Drop It? Never Again."
- "Soaked? Not a Chance."
- "Lost? Already Found."

**关键约束**：
1. 危机场景必须是用户**真实会担心的**，不能是夸张到失真的（抢手机合理，被闪电劈不合理）
2. 钩子文案必须极短、口语化、有情绪——长文案=失去钩子效果
3. 上半部分情绪越强，下半部分结构证明就越重要（防止显得只是吓人）
4. 产品形态标注要对应实物（引线指向真实存在的结构，不能乱画）

**Prompt 骨架**：
```
[Amazon secondary image, 1600x2000]

UPPER 60% — CRISIS SCENE:
[具体危机场景描述: e.g. busy street, a hand reaching from behind 
toward a phone, motion blur suggesting urgency]

LARGE TEXT OVERLAY at top: "[钩子文案, e.g. 'Snatch This?']"
SECONDARY TEXT: "[反击, e.g. 'Not Today.']"

Strong cinematic lighting. High emotional tension. The viewer feels 
the risk immediately.

LOWER 40% — PRODUCT PROOF:
[产品完整描述] shown in clean isolated view.
THREE thin annotation lines pointing to key structural elements:
  → "[关键结构1, e.g. reinforced anchor pad]"
  → "[关键结构2, e.g. stainless steel loop]"
  → "[关键结构3, e.g. quick-release buckle]"

Calm neutral background for lower section (contrast with tense 
upper section).

STRICTLY AVOID: unrealistic danger scenes, product detached from 
the crisis narrative, annotation lines pointing to non-existent parts
```

**已验证案例**：新模板，参考来源：西西酱《从一张手机挂绳图》Snatch This? Not Today 案例

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
