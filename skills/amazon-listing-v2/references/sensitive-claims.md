# Amazon Listing 敏感词分层词表（skill 部署版）

```
last_verified: 2026-07-14（Codex 初次整理；A层未对照后台实测，B层锚定FDA/EPA/FTC法规原文）
覆盖品类: 一般消费品（摄影/Vlogging配件为主）。成人用品（H&SO）、食品、药械、儿童玩具等
          强监管品类不在覆盖范围——进入前必须先跑该品类专项政策核查，不得直接套用本表
过期规则: 距 last_verified 超过 90 天 → skill 审计输出中标黄提醒「词表待核对」
核对触发: 用户说「核对敏感词词表」→ 执行文末〈季度核对协议〉，核完更新本戳
```

> **同步源**：本文件的上游是 `~/Documents/跨境业务/跨境知识库/playbooks/Amazon Listing敏感词前置拦截SOP.md`（Codex 整理，2026-07-14）。
> 更新纪律：SOP 改动后同步本文件；被 Amazon 驳回/抑制的实战命中词**回填两处**。
> 边界与定位：这不是 Amazon 官方完整禁词表——很多词是语境触发，本表只是**第一道粗筛**。真正权威是 Seller Central 类目模板 + 实战驳回实录；词表没收录的声明也要走 B 层"证据后置"逻辑兜底。拿不准时从严。
> 共享方：`amazon-listing-v2`（撰写时拦截）、`listing-rufus-cosmo-audit`（审计 Dimension 5 对照）。

## 三档处理规则

| 层级 | 处理方式 | 判定时机 |
|---|---|---|
| A. 无条件删除 | 命中即删，不为 SEO 保留，不改写成同义夸张词 | 写作前 + 成稿后各扫一次 |
| B. 证据后置 | 事实库有证书/测试报告/法规依据才可写；无证据 → 删除或降级 | **写作前**在事实库判定（allowed_output 列） |
| C. 绝对化降级 | 有测试标准/保修政策 → 改具体参数；没有 → 删除 | 写作前判定，成稿后复核 |

---

## A 层：无条件删除

### 排名、背书、平台暗示
```text
Best Seller, #1, No.1, Top Rated, Amazon's Choice, Amazon recommended,
official, five-star, 5-star, review gift
```

### 促销、价格、物流、时效
```text
free shipping, discount, sale, coupon, limited time, lowest price,
cheapest, deal, clearance, buy one get one
```
处理：正文字段不写促销/价格/物流承诺，交给 coupon、promotion、广告模块。

### 站外导流和联系信息
```text
website, URL, email, phone, WhatsApp, Instagram, TikTok, Facebook,
support@, www., http
```

### 竞品品牌、ASIN、平台规避词
```text
ASIN, B0..., better than [competitor brand], replacement for [competitor brand]
```
竞品品牌和 ASIN 默认不进正文和 Search Terms。

### ⚠️ 兼容性表达例外（摄影/Vlogging 配件类目关键规则）

`compatible with [brand/device]` **不是**一律删除：

- **可写**：事实准确的设备兼容声明，且属于本类目常规表达 —— `compatible with iPhone 15/14/13`、`fits GoPro Hero 12/11`、`for DJI Osmo Mobile`。这是三脚架/Vlogging Kit 品类的刚需流量词，误删会直接伤流量。
- **写法**：用 `compatible with / fits / for`，具体到型号；**不用** `better than`、`replacement for`、`same as`。
- **不可写**：兼容性未经实测验证；或把设备品牌放进品牌字段、用作商标性使用。
- **商标性技术名词单列（本品类高频风险面）**：`MagSafe`、`Lightning`、`GoPro`、`DJI OSMO`、`Bluetooth` 等是注册商标，只能做指示性合理使用——写 `compatible with MagSafe chargers`，不写 `MagSafe tripod`（把商标当自己产品属性）；不用对方 logo；Bluetooth 商标使用理论上需 SIG 认证资质。这块各品牌规范不同，首次使用某商标词前查该品牌官方 trademark guideline，命中即在审计 ③ 档提示人工确认。
- 事实库中兼容型号必须有来源（实测/规格书），否则按"需确认"处理，不进正式稿。

---

## B 层：证据后置（无证据 → 删除或降级）

### 医疗、健康、治疗、人体结构功能（FDA 边界）
```text
cure, treat, prevent, diagnose, heal, therapy, therapeutic, pain relief,
anti-inflammatory, arthritis, diabetes, anxiety, depression, insomnia, ADHD,
eczema, psoriasis, acne treatment, restore hair growth, regenerate cells,
collagen production, fat burning, weight loss
```
无 FDA/医疗器械合规依据 → 删除疾病/治疗/预防/诊断类表达。可降级为体验词（soft feel、lightweight、designed for daily use），不得暗示治疗效果。

### 杀菌、抗菌、抗病毒、除虫、净化功效（EPA 边界）
```text
antibacterial, antimicrobial, disinfect, sanitize, sterilize, kills germs,
kills bacteria, kills viruses, virus-proof, mold-proof, mildew-proof,
repels insects, pest control, UV sterilization, ozone,
air purifier kills, water purifier kills
```
有 UV/银离子/滤芯等结构 ≠ 可以写杀菌功效。可降级为结构事实（replaceable filter、UV light component），不写 kills/sterilizes/disinfects。

### 环保、绿色、无毒、可降解（FTC Green Guides 边界）
```text
eco-friendly, green, sustainable, environmentally friendly, biodegradable,
compostable, recyclable, recycled, zero waste, carbon neutral, plastic free,
non-toxic, ozone friendly, BPA-free, PVC-free, formaldehyde-free
```
- 未限定的 eco-friendly/green/sustainable 默认删除或改具体事实（made with recycled polyester + 比例依据）。
- free-of 类（BPA-free 等）必须有 supplier declaration 或 test report，且不得暗示替代物质无风险。
- non-toxic 必须能证明对人和环境均无相应风险，不能泛写。

### 认证、监管背书、测试、专业推荐
```text
FDA approved, FDA registered, FDA certified, EPA approved, EPA registered,
USDA organic, UL certified, ETL certified, NSF certified, FCC certified,
CE certified, RoHS compliant, CPSIA compliant, food grade, medical grade,
clinical grade, dermatologist approved, doctor recommended, clinically proven,
lab tested, patented, patent pending
```
- 证书编号、认证主体、适用 SKU、有效期不清楚 → 不写。
- `FDA approved` 默认高风险（FDA 明确并非所有监管产品都经上市前批准）。
- food grade/medical grade 不能凭材料常识写，必须有标准或供应商文件。

### Made in USA / 原产地（FTC Made in USA Rule）
```text
Made in USA, Made in America, USA made, American made,
Designed in USA, Assembled in USA
```
- Made in USA 须满足 FTC 要求，品牌/设计/包装在美国 ≠ 可写。
- 仅设计在美国 → Designed in USA（仍需确认不误导）；仅组装 → 单独确认加工实质和进口零部件比例。

---

## C 层：绝对化词（降级为参数或删除）

```text
best, perfect, ultimate, most advanced, strongest, safest, harmless,
no side effects, risk-free, indestructible, unbreakable, never, always,
100% waterproof, leakproof forever, lifetime, guaranteed
```
- 无测试标准/保修政策 → 删除。
- 有测试标准 → 改具体参数：IPX7 water resistance、drop-tested from X ft、holds up to X lb。
- lifetime 仅在明确售后政策支持且类目合规时可写。

---

## 降级映射表（删词时优先给替代，保住卖点信息量）

| 原表达 | 层级 | 替代表达（须事实库支持） |
|---|---|---|
| antibacterial surface | B | smooth easy-to-clean surface |
| FDA approved material | B | food-contact material, if supported |
| eco-friendly design | B | made with recycled polyester (X%), if supported |
| non-toxic | B | 具体 free-of 声明 + 供应商文件，或删除 |
| best tripod for vlogging | A/C | tripod for vlogging and travel |
| 100% waterproof | C | IPX7 water-resistant, if supported |
| unbreakable | C | drop-tested from X ft, if supported |
| lifetime warranty | C | X-year warranty（须与实际售后政策一致） |
| strongest | C | holds up to X lb / supports X kg |

---

## Search Terms 专项规则

- 后台词不是"藏词区"：A 层词、正文被删的 B/C 层词，**禁止转移进 Search Terms**。
- 竞品品牌、ASIN、医疗功效、促销、外链、联系方式在 ST 中同样违规。
- 成稿后对 ST 单独复扫一次。

## 维护机制（四道防线，权重从高到低）

1. **实战回流（权重最高）**：Listing 被 Amazon 驳回、抑制或强制改写时，把命中词 + 触发语境（品类、字段、上下文句子）回填文末「实战黑名单」，并同步上游 SOP。记录"词 + 语境"，不只记词（如 antimicrobial 在普通布料 listing 高风险，在有 EPA 路径的产品可能可写）。这是唯一反映真实执法的信号。
2. **过期提醒**：skill 每次审计输出本表 last_verified；超 90 天标黄，提示用户触发核对。
3. **季度核对协议**（触发词「核对敏感词词表」，会话触发，不设自动调度）：
   - A 层 + 平台执行口径：查 Seller Central News/论坛官方公告、Restricted Products 页、Search Terms 规则页、在售类目模板——用 title-policy pack 的 L1/L2/U 纪律（官方原文才算确认，三方说法挂限定词）
   - B 层：FDA/EPA/FTC 仅在涉及新品类或有已知修法时核，不必每季度全查
   - 核完更新头部 last_verified 戳 + 变更记录，同步上游 SOP
4. **新品类硬门**：进入头部「覆盖品类」之外的品类（成人用品、食品、药械、儿童等）→ 第一个 listing 前先做该品类专项政策核查（受限词 + 图文规则 + 类目模板），产出单独词表或本表扩展区，不得裸套本表。

### 实战黑名单（被驳回/抑制实录，持续回填）

| 日期 | 命中词 | 品类/字段 | 语境 | 处理结果 |
|---|---|---|---|---|
| （暂无记录） | | | | |
