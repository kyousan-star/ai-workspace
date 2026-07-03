# 停顿感构图模板库（v2 新增）

v2 专用三个模板，对应西西酱打法。与 T01-T08 功能型模板并行使用，不替代。

---

## T09 · 产品存在感型

**设计问题**：如何让产品不是"被展示"，而是主动进入用户视觉空间？

**核心机制**：产品占据画面最强视觉位置，制造"它正在向你靠近"的感知。

**按产品类型选手法**：

| 产品类型 | 手法 | 不适用 |
|----------|------|--------|
| 小型手持品（美妆/配件/手机周边） | 广角前伸：模特把产品递向极前景，广角畸变放大 | 大件家具 |
| 有纹理/材质卖点 | 极限近景：产品局部特写占满画面 | 需要展示尺寸比例的产品 |
| 需要传递强存在感的产品 | 产品占画面 70-80%+戏剧性单侧打光，几乎无背景 | 场景感是核心卖点时 |

**主标题套路**：动词+状态，不描述功能，描述感觉
- "Made to Be Held."
- "This Close to Perfect."
- "Take It."

**关键约束**：
1. 产品必须是绝对主角，模特退到情绪配角
2. 广角前伸：prompt 必须写 `extreme wide-angle lens distortion, product pushed toward camera in extreme foreground`
3. 极限近景：不展示产品全貌，只展示最有质感的局部
4. 产品形态描述必须与 unified form 一致

**Prompt 骨架（广角前伸版）**：
```
[Amazon secondary image, 1600x2000, text overlay at top]

Extreme close-up hero shot with dramatic wide-angle lens distortion.

HERO PRODUCT: [产品完整描述] extended toward the camera in the
extreme foreground, appearing 2-3x larger than real scale.
The product surface occupies the bottom 60% of the frame.

BACKGROUND: [模特/手] holds the product from behind, arm slightly
visible in soft-focus mid-ground. Expression: confident, natural.

DEPTH EFFECT: strong near-far perspective compression — product
sharp and large, background soft and receding.

STRICTLY AVOID: [标准禁止项列表]
```

**Prompt 骨架（极限近景版）**：
```
[Amazon secondary image, 1600x2000, text overlay at top]

Extreme macro close-up of [产品最有质感的部位].
The [部位] fills 70-80% of the entire frame.
[纹理细节描述: matte aluminum grain / stitching pattern / etc.]

Shot on Sony A7 with 90mm macro lens, f/2.8. Shallow depth of field.

STRICTLY AVOID: [标准禁止项列表]
```

---

## T10 · 反差感型

**设计问题**：如何让用户第一眼觉得"这张图有点不一样"，停下来多看一秒？

**核心机制**：品类刻板印象 × 反向情绪元素 = 画面张力

**公式步骤**：
1. 定义该产品给用户的"第一印象关键词"
2. 找一个方向相反但逻辑合理的情绪元素
3. 验证合理性：用户会觉得自然还是突兀？
4. 确认它能把用户引向产品正面卖点

**品类刻板印象速查**：

| 品类 | 刻板印象词 | 可用反向元素 |
|------|-----------|-------------|
| 电竞/游戏外设 | 硬核/机械/男性/冷 | 猫/儿童/鲜花/针织毯 |
| 工具类 | 粗犷/专业/力量 | 儿童空间/精致厨房/女性独立感 |
| 收纳类 | 极简/冷静/秩序 | 孩子的贴纸/宠物零食/可爱混乱 |
| 按摩仪/保健品 | 放松/松弛 | 高跟鞋/西装/职场压力痕迹 |
| 户外/运动装备 | 粗犷/体能 | 宠物/家人/温馨仪式感 |

**主标题套路**：揭示隐藏的一面
- "Tougher Than It Looks. Softer Than You Think."
- "For the One Who Does It All."
- "Work Hard. Rest Right."

**关键约束**：
1. 反差元素必须"合理但意外"——合理才能引发正面联想
2. 产品仍然是主角，用户记住猫忘了椅子=失败
3. 反差要服务于具体卖点（舒适/易用/情绪价值），不能随机加元素

**Prompt 骨架**：
```
[Amazon secondary image, 1600x2000, text overlay at top]

Scene: [融合产品刻板环境和反向情绪元素的具体场景]

HERO PRODUCT: [产品完整描述] as the clear visual anchor.

CONTRAST ELEMENT: [反向情绪元素] naturally present in the scene —
[描述视觉对比: e.g. soft fur against hard plastic].

The contrast creates a visual question: [用户会产生的疑问及其
正面联想, e.g. "Must be comfortable enough for even a cat."]

LIGHTING: [暖光软化刻板印象]

STRICTLY AVOID: NO dangerous juxtapositions, NO model that
outshines the product, NO random props unrelated to the contrast logic
```

---

## T11 · 焦虑场景叙事型

**设计问题**：如何让用户不只是"知道"产品能解决问题，而是"感受到"这个问题？

**核心机制**：先让用户感受到危险/痛点/风险，再让产品出场解决。上半钩子，下半证明。

**适用产品**：任何解决具体痛点/风险的产品（防护/安全/防丢/防漏/防摔……）

**叙事结构**：
```
上半部分（60%）：危机场景可视化
  - 用户真实会担心的瞬间（不是泛泛的"问题"）
  - 短视频钩子式文案（≤6词，有反问/反转/冲突感）
  - 足够的情绪张力，让用户停下来

下半部分（40%）：产品结构证明
  - 产品本体 + 关键结构标注
  - 让用户从感性回到理性
```

**主标题套路**：反问式+反击式
- "Snatch This? Not Today."
- "Drop It? Never Again."
- "Soaked? Not a Chance."

**关键约束**：
1. 危机场景必须真实可信，不能夸张到失真
2. 钩子文案极短、口语化、有情绪——长文案=失去钩子效果
3. 产品引线标注要对应实物位置，不能乱画

**Prompt 骨架**：
```
[Amazon secondary image, 1600x2000]

UPPER 60% — CRISIS SCENE:
[具体危机场景: e.g. busy street, a hand reaching from behind
toward a phone, motion blur suggesting urgency]

LARGE TEXT OVERLAY at top: "[钩子文案, e.g. 'Snatch This?']"
SECONDARY TEXT: "[反击, e.g. 'Not Today.']"

Strong cinematic lighting. High emotional tension.

LOWER 40% — PRODUCT PROOF:
[产品完整描述] shown in clean isolated view.
THREE thin annotation lines pointing to key structural elements:
  → "[关键结构1]"
  → "[关键结构2]"
  → "[关键结构3]"

Calm neutral background for lower section.

STRICTLY AVOID: unrealistic danger scenes, annotation lines
pointing to non-existent parts, product detached from crisis narrative
```
