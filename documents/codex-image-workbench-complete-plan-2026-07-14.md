# Codex Amazon 图片工作台完整产品与实施方案 V1.2

> 文档版本：1.2
> 日期：2026-07-14，最后更新 2026-07-15
> 状态：P-1 Gate 有限制通过；P0 已关闭；P1 结构化 MVP 已通过；P2 结构化 MVP 已通过并进入 PH204 诊断 Gate
> 范围：待上市新品视觉生产 + 已上市产品图片持续优化

### V1.2 修订摘要

- 将自动生图和手动回导定义为同等正式的执行模式，不再把手动模式视为失败降级。
- 明确 `asset-registry.json` 管理可复用资产治理状态，SQLite 管理任务、版本、评估和实验运行态。
- 增加 Registry 程序化候选登记、人工晋升、稳定资产 ID 和 Registry/SQLite 对账要求。
- 冻结旧 `asset-library` 新写入；旧 workflow 和 extractor 必须先迁移到 brand/product/campaign 分层目录。
- 在任何 UI 建设前增加 P-1 纯 CLI 验证，覆盖功能、恢复、吞吐和 Codex 会话轮换。
- 将 Input Normalizer 和确定性排版收缩为 MVP 可控范围，并补充 amazon-ops 接入边界和退役时间表。

## 1. 执行摘要

本项目要建设一个本地运行、由 Codex 驱动的 Amazon 图片生产与运营工作台。

它不是单纯的生图页面，而是管理图片完整生命周期的系统，覆盖：

- 原始资料导入；
- 产品事实与 Claim 校验；
- 竞品视觉分析；
- 卖点与图片序列规划；
- 参考图驱动的生成和编辑；
- 产品、品牌、合规和技术质量检查；
- 人工审批与上线记录；
- 上线后的表现诊断、挑战版本、验证和回滚；
- 成功与失败经验沉淀。

工作台支持两种主要业务模式：

1. 新品模式：面向尚未上市或需要整套重做的产品，从资料输入开始完成主图、副图、A+ 的规划、生成、质检和上线准备。
2. 在售优化模式：面向已上市产品，把已完成的问题诊断转成受控改图任务，生成或编辑挑战版本，上线观察后决定保留、回滚或继续诊断。

两种模式共用产品事实、品牌资产、竞品资料、生图能力、质量规则、版本体系和经验库，不建设两套彼此割裂的系统。

推荐技术形态是“Codex 插件 + 本地 React 工作台 + 本地 MCP 服务 + SQLite”。第一版同时提供 Codex 内置 ImageGen 自动执行和 Prompt 包手动回导，不把 OpenAI Image API 作为前置依赖。

## 2. 建设目标

### 2.1 核心目标

- 把混合输入资料自动整理成结构化、可核对的视觉项目。
- 防止 AI 虚构产品结构、配件、规格、功能和 Claim。
- 用逐图生成合同驱动生产，避免不断抽卡。
- 保存每张图的来源、父版本、输入参考、Prompt、评分和决策。
- 同时支持新品首发和在售产品持续优化。
- 将验证有效和明确失败的经验回流，降低后续项目重复成本。

### 2.2 MVP 暂不包含

- Photoshop 级自由编辑器。
- 通过浏览器自动点击 ChatGPT 网页生图。
- 在本机运行大型扩散模型。
- 未经人工批准自动发布 Amazon 图片。
- 声称 Amazon 可以直接给出每张副图的独立转化贡献。
- 失败后不设上限地重复生成。
- 第一版同时支持所有广告和社媒渠道。

## 3. 核心原则

1. 事实优先于审美：产品 Facts 和 Claim 证据高于 Listing 文案、初步卖点和竞品表达。
2. 默认参考图驱动：优先使用真实产品图片或已批准父图进行编辑和合成。
3. 生成环境，锁定产品：AI 可以生成背景、人物、光影和场景，不得猜测不可见的产品结构。
4. 文字确定性输出：Logo、参数、价格、尺寸和关键文案由工作台排版，不交给生图模型绘制。
5. 每轮只改一个主要变量：每个挑战版本都必须说明 Change Only 和 Preserve。
6. 禁止无限重试：同一 Prompt 失败后不得原样重跑，自动修订有明确轮次上限。
7. 关键状态人工确认：资产的 approved、published、validated、retired，以及实验的 validated、rolled_back 都需要明确证据和人工决定。
8. 优化必须可回滚：任何线上改图都从已记录父版本开始，并提前确定回滚目标。

## 4. 产品形态

工作台是本地系统工具，界面使用网页技术实现。

自动执行模式的系统关系：

    Codex Desktop
      -> Codex Image Workbench 插件
        -> 127.0.0.1 本地 React 页面
        -> 本地 MCP Server
        -> 本地 Node 服务
        -> SQLite 元数据数据库
        -> 本地图片和项目文件
        -> Codex 内置 ImageGen

本地网页按钮不能直接调用 Codex 会话里的内置生图工具。自动执行流程是：

1. 工作台把结构化任务写入本地任务队列。
2. 当前 Codex 任务运行 Workbench Orchestrator 并监听队列。
3. Codex 读取任务并调用内置 ImageGen。
4. 图片保存为本地文件。
5. MCP 将图片路径、运行记录和状态回传工作台。

手动回导模式不依赖活跃 Codex Worker：

1. 工作台导出包含任务 ID、参考图角色、Prompt、不变量、禁止项、尺寸和验收标准的生成包。
2. 用户在 Codex、ChatGPT 或其他可用生图表面执行。
3. 用户把结果拖回工作台。
4. 工作台计算哈希并绑定原任务、父版本和图片槽位。
5. 后续质检、版本树、审批、上线、实验和经验回流与自动模式完全相同。

### 4.1 建议路径

    /Users/lihuan/ai-workspace/codex-image-workbench/   程序源码
    /Users/lihuan/ai-workspace/image-projects/          项目和图片数据

visual-lab、普通文件夹和未来的 Amazon 数据连接器都只是数据来源，工作台不依赖某一个资产库才能运行。

## 5. 系统架构

### 5.1 主要组件

| 组件 | 职责 |
|---|---|
| Workbench UI | 资料导入、规划、生图、质检、线上版本和优化实验 |
| Local Service | 文件、缩略图、导出、SQLite 和任务队列 |
| MCP Server | Codex 与工作台之间的结构化桥接 |
| Workbench Orchestrator | 调度 Skill、调用 ImageGen、维护状态和停止规则 |
| Input Normalizer | 解析 Facts、Listing、卖点、图片和竞品资料 |
| Planner | 生成视觉策略、图片序列和逐图生成合同 |
| Quality Controller | 执行硬门槛、软评分和修复路由 |
| Listing Image Optimizer | 在售诊断、挑战版本、观察和回滚 |
| Asset Lifecycle Manager | 父子关系、候选登记、Registry 引用和审批证据 |
| Provider Adapter | 第一版使用 codex-built-in，未来可接 API |

### 5.2 执行模式与 Provider 边界

第一版必须实现两个正式执行模式：

| execution_mode | 行为 | 是否依赖 API Key |
|---|---|---|
| codex_auto | 活跃 Codex Worker 领取持久化队列任务并调用内置 ImageGen | 否 |
| manual_import | 导出完整生成包，用户生图后回导并继续统一质检和版本流程 | 否 |

`api_background` 只作为未来可选 Provider，不是 MVP 成立条件。自动执行不可用时，项目仍可完整运行到质检、上线、实验和回流。

第一版运行记录建议写为：

    provider: codex-built-in
    surface: codex
    model: unexposed

工作台不写死 Image 2、codex-image-2.0 或其他未被公开确认的底层模型名称。

未来增加 API Provider 时，才记录固定模型 ID、成本、后台重试和无人值守执行。不得因为 P-1 自动队列失败而强迫用户配置 API Key。

### 5.3 Codex Worker 约束

Codex 会话是可替换 Worker，不是系统状态容器。任务必须自包含，不能依赖旧对话上下文才能继续：

- 队列和项目进度持久化在 SQLite；
- 每个任务使用稳定 job ID 和幂等键；
- Worker 领取任务时建立 lease 和 heartbeat；
- 每个任务结束后立即 checkpoint；
- lease 超时后允许新 Codex 会话安全接管；
- UI 必须显示 Worker 在线、离线、运行中和等待恢复状态，不承诺不可验证的常驻后台能力。

## 6. 统一数据模型

### 6.1 核心实体

| 实体 | 用途 |
|---|---|
| Product | 品牌、SKU、站点和产品基础信息 |
| ProductFact | 结构化事实、证据、置信度和不确定状态 |
| Claim | 允许、需限定、无依据或禁止的营销表述 |
| Asset | 产品图、抠图、Logo、竞品图、生成图或线上图 |
| AssetRole | 主参考、结构参考、细节参考、配件参考、品牌锚点、父构图 |
| CompetitorPackage | 一个竞品 ASIN 的有序图片、Listing 文案和竞品角色 |
| Listing | ASIN、站点、文案和当前视觉状态 |
| ImageSlot | 主图、副图槽位或 A+ 模块位置 |
| ImageContract | 页面任务、参考图、不变量、Change Only 和验收标准 |
| GenerationJob | 生成、编辑、合成、排版或导出任务 |
| Evaluation | 硬门槛、软评分、证据和修复决定 |
| ListingVersion | 一次完整线上图片序列和上线时间 |
| OptimizationJob | 诊断、假设、修改变量、观察信号和回滚版本 |
| Decision | 人工审批和状态变更证据 |
| Learning | 有效模式、失败模式和适用边界 |

### 6.2 资产治理状态与实验状态

    raw
      -> candidate
        -> approved
          -> published
            -> validated
              -> retired

raw 或 candidate 也可以进入 rejected。

该状态链以 `visual-lab/asset-registry.json` 为唯一权威源。`evaluating`、`inconclusive` 和 `rolled_back` 属于 ListingVersion 或 OptimizationJob 的实验状态，只保存在工作台运行数据中，不扩展 Registry 状态定义。

### 6.3 Registry 与 SQLite 权威边界

| 数据 | 权威源 |
|---|---|
| 可复用资产 ID、来源、哈希、父子关系和治理状态 | `visual-lab/asset-registry.json` |
| 生成任务、临时版本、评分、ListingVersion、OptimizationJob、lease | 工作台 SQLite |
| 品牌不变量 | `visual-lab/brand-library/` |
| 产品事实和 SKU 参考资产 | `visual-lab/product-library/` |
| Campaign brief、候选构图和项目经验 | `visual-lab/campaign-library/` |

普通生成尝试和废稿只进入 SQLite。用户选中可复用候选后，工作台通过中央 Registry 程序化接口登记为 `candidate`；`approved` 及以上仍保留人工 Gate。

资产在 GenerationJob 创建时铸造稳定 ID，建议格式为 `wb-{brand}-{sku}-{kind}-{ULID}`。晋升进入 Registry 时沿用同一 ID，不重新编号。

### 6.3 输入事实优先级

    已验证产品 Facts 和证据
      > 自有 Listing 文案
      > 初步卖点假设
      > 竞品表述

冲突必须展示。低优先级输入不得静默覆盖高优先级事实。

## 7. 输入体系

### 7.1 已有输入

| 输入 | 工作台处理方式 | 理由 |
|---|---|---|
| 产品图片素材 | 识别角度、清晰度、遮挡、来源和参考角色 | 不同图片锁定不同产品不变量 |
| Listing 文案 | 拆解信息层级和 Claim 台账 | Listing 可能包含旧参数或无依据表达 |
| Product Facts | 转成唯一结构化事实源 | 决定产品形态、规格、配件和功能边界 |
| 核心卖点初步定义 | 保存为候选假设 | 需要结合 VOC、竞品和可视化程度验证 |
| 竞品图片 | 按 ASIN 和槽位顺序保存 | 图片顺序也是竞品策略的一部分 |
| 竞品 Listing | 与对应竞品图片合并 | 用于分析 Claim、文案和视觉表达关系 |

### 7.2 建议增加的输入

| 输入 | 要求 | 理由 |
|---|---|---|
| VOC、Review、QA 或退货原因 | 新品强烈建议，在售优化优先使用 | 揭示真实问题、异议和误解 |
| Claim 与合规证据 | 性能、安全、认证和兼容性 Claim 必须提供 | 防止无依据文字进入图片 |
| 品牌资产和 Do/Don't | 需要正式品牌一致性时必须提供 | 把模糊风格词转成可检查不变量 |
| 项目目标 | 站点、语言、图位、A+ 类型和上线时间 | 决定输出范围和规则 |
| 目标用户和使用场景 | 无法从 VOC 或 Listing 推导时补充 | 决定场景和信息层级 |
| 当前线上图片及顺序 | 在售优化必须提供 | 建立父版本和回滚版本 |
| 上线时间和运营时间线 | 在售优化必须提供 | 支持前后窗口比较 |
| 表现数据和同期运营事件 | 在售优化必须提供 | 排除价格、广告、库存、促销、评论和 Buy Box 干扰 |

### 7.3 建议减少或合并

- 不在 Product Facts、Listing 和卖点表重复维护同一参数。
- 每个竞品的图片和 Listing 合并成一个 ASIN Package。
- 默认分析 3-6 个高相关竞品，不接收无限竞品堆积。
- 已有 approved 品牌系统时，不再重复询问自由风格偏好。
- 不要求补齐所有产品角度，只补当前图序真正需要的视图。
- 不强制每个图片槽位都生成 A/B 两套方案。

## 8. 产品素材覆盖 Gate

生图前，工作台必须判断现有产品素材能否支撑每个计划槽位。

### 8.1 覆盖状态

| 状态 | 含义 | 系统行为 |
|---|---|---|
| ready | 关键结构都有可靠真实参考 | 正常进入生成 |
| ready_with_risk | 产品身份基本完整，但非关键细节不足 | 仅允许安全构图并提示风险 |
| blocked | 缺少关键结构、配件、包装内容或必要角度 | 阻断对应槽位 |
| replaceable | 原方案做不了，但可以换成有证据的表达 | 提出替代任务卡并等待确认 |

### 8.2 素材不足时的反应

工具不能只提示“请补图”，必须输出具体拍摄任务：

    缺失结构：展开后的底座和铰链
    影响槽位：副图2 - 稳定性卖点
    需要补拍：完整展开后的正面45度
    可见要求：所有支脚和中心杆完整可见
    背景：纯白或浅灰
    建议分辨率：长边不低于2000px

工作台可以生成缺失环境、扩展背景、改善光影，但不能生成不可见的接口、按键、铰链、配件和产品背面。

## 9. 新品视觉规划与生产流程

### A0 创建项目

- 选择新品模式。
- 设置产品、品牌、站点、语言和图片范围。
- 上传或链接完整输入资料。

### A1 自动标准化

- 创建 Product Fact Ledger。
- 解析 Listing Claim 和信息层级。
- 对产品图分类并分配参考角色。
- 创建有序竞品 Package。
- 登记初步卖点假设。
- 输出输入质量和冲突报告。

### A2 处理阻断项

- 产品事实冲突时停止。
- 高风险 Claim 无证据时停止。
- 标记看不清、缺失或无法确认的产品细节。
- 一次性汇总需要用户回答的问题，避免多轮零散追问。

### A3 视觉策略

- 提取竞品的品类基准线。
- 识别视觉差异化机会，但不虚构竞品效果结论。
- 用 VOC 和客户异议校验初步卖点。
- 按证据强度、客户相关性、差异化和可视化程度评估卖点。
- 推荐卖点优先级，但不自动锁定。

### A4 图片序列

每个槽位必须定义：

- 图片槽位和页面任务；
- 核心卖点；
- 要回答的客户问题；
- 所需证据；
- 出图方式；
- 素材来源；
- 素材缺口；
- 移动端信息层级。

出图方式包括：

- 真实白底图；
- 确定性产品合成；
- 参考图驱动编辑；
- AI 场景图；
- 信息图；
- 纯排版优化。

### Gate A：策略与图序确认

旧流程的 Gate 1 和 Gate 2 在工作台中合并。用户一次确认：

- 产品 Facts 和不确定项；
- 卖点优先级；
- 主图、副图和 A+ 顺序；
- Claim 边界；
- 不使用的竞品手段；
- 视觉禁区；
- 补拍任务或替代方案。

### A5 逐图生成合同

每张图生成一个 Image Contract：

    Purpose and Amazon slot
    Input image roles and asset IDs
    Product invariants
    Brand invariants
    Claim evidence
    Change only
    Composition and scene
    Text and layout specification
    Strictly avoid
    Technical output requirements
    Acceptance criteria

默认只生成一个推荐方向。只有高价值或高不确定决策才增加一个挑战方案。

### A6 生成与合成

- 产品几何要求高时使用真实产品层。
- Codex ImageGen 负责背景、人物、光影和安全范围内的编辑。
- Logo、文字、图标、尺寸线和免责声明由工作台渲染。
- 每个结果登记为 candidate，并保存父 ID 和生成记录。

### A7 质量检查与修复

- 先跑硬门槛。
- 硬门槛通过后再做商业质量评分。
- 根据问题选择重新排版、局部编辑、重新合成、重生成或拒绝。
- 每轮只改一个主要变量。
- 达到修订上限后停止并请求人工决定。

### Gate B：最终候选确认

用户选择候选并明确批准 asset ID。没有真实上线证据时不能标记 published。

### A8 导出与首发基线

- 输出符合渠道要求的文件和交付 Manifest。
- 保存批准后的完整图片序列。
- 图片正式上线后，登记第一份 ListingVersion，作为后续优化基线。

## 10. 在售产品图片优化流程

### B0 创建在售项目

- 选择在售优化模式。
- 导入当前 Listing 文案和有序图片。
- 登记 ASIN、站点和当前 ListingVersion。

### B1 导入诊断与上下文

- 登记已诊断问题和支持证据。
- 导入对应表现窗口。
- 登记同期价格、广告、促销、库存、Review 和 Buy Box 事件。
- 判断问题是否支持图片假设，还是仍被其他因素干扰。

上市接近一个月不等于自动获得充分改图证据。是否能判断，需要看流量质量、样本量和干扰因素，而不只看天数。

### B2 建立优化合同

每个 OptimizationJob 必须包含：

    Target slot
    Current live parent asset
    Diagnosed problem
    Evidence
    Optimization hypothesis
    Change only
    Preserve list
    Expected signal
    Evaluation condition
    Known confounders
    Rollback version

### B3 选择最小干预方式

| 问题 | 默认动作 |
|---|---|
| 图序不合理 | 优先调整现有图片顺序 |
| 文字过多或层级差 | 重新排版 |
| 产品正确但场景弱 | 基于线上图局部编辑 |
| 卖点表达错误 | 只替换对应槽位 |
| 产品结构或包装错误 | 使用真实素材重新合成 |
| Claim 无依据 | 删除或替换 Claim |
| 主图第一眼竞争力不足 | 创建一个受控主图挑战版本 |
| 整套定位错误 | 重新进入策略与图序规划 |

产品事实和合规错误可以立即修正。其他优化默认每轮只改一个主要变量。

### B4 创建挑战版本

- 优先以当前线上图为父图。
- 保留产品、品牌、槽位任务和不需要变化的版式。
- 默认创建一个主挑战版本。
- 只有必要时增加一个备用版本。
- 不从空白 Prompt 重新抽卡。

### B5 上线前质量 Gate

- 产品准确性；
- Claim 证据与合规；
- 图片规格；
- 移动端可读性；
- 品牌一致性；
- 与 Control 的明确差异；
- 与优化假设一致。

### Gate C：发布确认

用户确认挑战图、目标槽位和回滚版本。MVP 阶段由人工完成 Amazon 发布。

### B6 发布与观察

- 保存改图前完整 ListingVersion。
- 记录发布时间和变更 asset ID。
- 记录观察期内的重要运营事件。
- 尽量避免同期发生无关的大幅修改。

### B7 评估与决定

- 达到预先定义的证据条件后再比较结果。
- 主图修改主要作为点击和第一印象假设。
- 副图和 A+ 修改主要作为理解、异议解决和转化假设。
- 数据不支持单图归因时，不输出确定性归因结论。

结果状态：

    validated     证据支持保留挑战版本
    rolled_back   证据或风险支持恢复 Control
    inconclusive  样本不足或干扰过多，返回诊断
    retired       资产不再适合使用

### B8 经验回流

记录测试变量、证据窗口、结果和适用边界。单一 SKU 或单一流量环境的成功结果，不自动升级为全品牌通用规则。

## 11. 质量控制体系

### 11.1 硬门槛

以下任一项失败都不能批准：

- 产品几何、颜色、材质、配件、包装内容、接口或按键错误；
- 无依据、误导性或禁止 Claim；
- 主图或 A+ 合规失败；
- 错误 Logo 或未批准品牌承诺；
- 严重 AI 畸形、人物错误、乱码或透视问题；
- 尺寸、格式、色彩模式不符合目标规则。

### 11.2 软评分

- 卖点清晰度；
- 移动端可读性；
- 产品视觉占比；
- 信息层级；
- 商业真实感；
- 品牌一致性；
- 与竞品基准的差异化；
- 是否完成该槽位的客户任务。

### 11.3 修复路由

    文字或版式问题        -> 确定性重新排版
    背景或场景问题        -> 局部图片编辑
    轻微产品问题          -> 使用真实参考进行编辑
    严重产品问题          -> 用真实产品层重新合成
    核心概念错误          -> 生成一个明确新方向
    连续没有改善          -> 停止并请求人工决定

### 11.4 防抽卡规则

- 每个决策最多两个初始方向。
- 自动修订最多两到三轮。
- 禁止原样重复失败 Prompt。
- 每轮只改一个主要变量。
- 每次编辑都重复父图和 Preserve 列表。
- 下一轮前先记录失败分类。
- 产品和关键文字尽可能使用确定性图层。

## 12. 现有 AI Workspace 资源复用

### 12.1 核心复用

| 现有资源 | 工作台用途 | 必要改造 |
|---|---|---|
| workflows/amazon-image-workflow | 研究、策略、Gate、质检和迭代思想 | 从文件型线性流程改成结构化状态机 |
| amazon-image-planner-v4 | 图位规划、参考角色、不变量、Change Only、验收标准 | 输出结构化合同；取消全槽位强制 A/B；模型名中立 |
| competitor-visual-analyzer | 品类基准、视觉手段和结构性缺口 | 同时读取竞品 Listing 并保留图序 |
| product-consistency-checker | 产品准确性 Gate | 支持单张挑战图对照真实参考 |
| brand-consistency-checker | 品牌一致性 Gate | 仅在 approved 品牌基线存在时正式评分 |
| asset-curator | 可复用资产登记、父子关系和审批生命周期 | 增加程序化 candidate 写入、原子更新和对账入口；不承载 ListingVersion 实验状态 |
| 现有四套 Rubric | 产品、合规、可读性和商业质量 | 改成带版本和证据的规则引擎 |

### 12.2 改造后使用

| 现有资源 | 主要问题 |
|---|---|
| product-asset-extractor | 仍写旧 asset-library，混合品牌和产品职责；必须在 P-1 前迁移写入目标 |
| image-spec-checker | Amazon 规则写死且缺少健康元数据，需要规则版本化 |
| batch-asset-generator | 旧路径、只产 Prompt，适合后期批量铺量 |
| channel-creative-adapter | 适合 approved 母图后的跨渠道阶段 |
| brand-system-builder | 适合品牌初始化，不应每个图片任务运行 |

### 12.3 工作台不再路由

- amazon-image-planner-v2；
- amazon-image-planner-v3；
- 把 Prompt 交付误认为完成图片生产的旧流程；
- 第一阶段的 cross-channel-campaign-workflow。

### 12.4 需要新增

1. workbench-orchestrator：监听任务、调用 Codex ImageGen、回传文件、维护状态和停止规则。
2. listing-image-optimizer：在售诊断、优化合同、挑战版本、观察和回滚。
3. quality-controller：统一调用质量检查并决定修复路径。
4. input-normalizer：把混合资料转成 Facts、Claims、Assets、竞品 Package 和阻断项。

所有新增 Skill 必须放在 `/Users/lihuan/ai-workspace/skills/` 这一唯一权威源中，由 `install.sh` 部署；插件只引用，不建立第二套 Skill 源。

核心 Skill 自动路由前，必须补齐 last_verified 和 staleness_risk。动态 Amazon 规则不得继续以无日期静态文字长期存在。

### 12.5 Registry 程序化接口

在现有校验脚本基础上增加中央 `registryctl`：

- `register-candidate`：校验路径、哈希、kind、parent 和 ID 后原子登记候选，不要求 approved Gate；
- `promote`：只有携带人工审批人、时间和决策引用时才能晋升 approved 及以上；
- `check`：检查结构、重复 ID、状态、路径和哈希；
- `reconcile`：只读比较 Registry 与工作台 SQLite，报告缺失登记、孤立引用和状态冲突；
- 所有写操作使用文件锁、临时文件和原子替换，工作台不得直接拼接 JSON。

MVP 至少在工作台启动、资产晋升前和人工 `--check` 时执行对账；后台定时对账可后置。

### 12.6 旧路径迁移与退役

`visual-lab/asset-library/` 立即进入只读兼容状态。为保证旧 workflow 在退役前仍可使用，先完成以下兼容改造：

- 产品 Facts、参考图角色和抠图任务写入 `product-library/{product-line}/skus/{sku}/`；
- 品牌风格只引用 `brand-library/{brand}/`，extractor 不再自行生成品牌规则；
- 项目 Prompt、候选构图和失败经验写入 `campaign-library/{campaign}/`；
- 经验证可跨项目复用的资产通过 asset-curator 和 Registry 晋升。

退役节奏：

| 时间点 | 动作 |
|---|---|
| P-1 前 | 修正 extractor、workflow 阶段 4.5/9 和项目合同中的旧写入目标；asset-library 停止新增 |
| P1 验收后 | 新品项目默认只走工作台；amazon-image-workflow 转兼容只读入口 |
| P2 验收后 | v2/v3、toolkit 重复副本和旧 workflow 归档，不再自动路由 |
| 稳定运行后 | 评估旧 asset-library 的迁移或长期只读保留，不做破坏性删除 |

## 13. 工作台信息架构

主导航：

    Projects
    Assets
    Plan
    Studio
    Quality
    Live
    Optimize
    Learnings

### 13.1 Projects

- 新建项目和模式选择；
- 产品、站点、范围和当前阶段；
- 阻断项和下一决策。

### 13.2 Assets

- 产品参考图和角色；
- Product Facts 和 Claim 台账；
- 品牌资产；
- 有序竞品 Package；
- 补拍任务。

### 13.3 Plan

- 视觉策略；
- 卖点优先级；
- 主图、副图和 A+ 序列；
- 逐图 Image Contract；
- 计划审批。

### 13.4 Studio

- 合同和 Prompt 预览；
- 生成、编辑、排版和重新合成；
- 父子版本对比；
- 标注意见和修订记录。

### 13.5 Quality

- 硬门槛结果；
- 产品对照矩阵；
- Claim 和合规证据；
- 移动端预览；
- 修复决定和剩余风险。

### 13.6 Live

- 当前线上图片顺序；
- 上线日期和 ListingVersion 历史；
- Control、Challenger 和 Rollback 关系。

### 13.7 Optimize

- 诊断结果；
- 运营事件时间线；
- 优化假设和单变量合同；
- 发布和评估状态。

### 13.8 Learnings

- 已验证模式；
- 失败 Prompt 和失败分类；
- 可复用构图；
- 适用边界和证据。

## 14. 技术实施方案

### 14.1 建议代码结构

    codex-image-workbench/
    ├── .codex-plugin/plugin.json
    ├── .mcp.json
    ├── packages/
    │   ├── workbench-app/
    │   ├── workbench-server/
    │   ├── mcp-server/
    │   └── shared/
    ├── rules/
    │   ├── amazon-image-specs/
    │   ├── product-quality/
    │   └── mobile-readability/
    ├── migrations/
    ├── tests/
    └── scripts/

工作台专用 Skill 不放在程序源码目录，统一位于：

    /Users/lihuan/ai-workspace/skills/workbench-orchestrator/
    /Users/lihuan/ai-workspace/skills/listing-image-optimizer/
    /Users/lihuan/ai-workspace/skills/quality-controller/
    /Users/lihuan/ai-workspace/skills/input-normalizer/

### 14.2 项目运行目录

    image-projects/{project-id}/
    ├── source-assets/
    ├── competitor-packages/
    ├── generated/
    ├── published-snapshots/
    ├── exports/
    ├── thumbnails/
    └── project-manifest.json

### 14.3 可靠性要求

- 工具执行前先持久化任务和状态。
- Codex 任务中断后，新会话可以通过 lease 超时和 checkpoint 继续。
- Worker 重复领取同一幂等任务不得生成第二份未关联结果。
- 永不覆盖原始图片。
- SQLite 只保存元数据，图片保存在文件系统。
- 使用哈希去重。
- 页面默认加载缩略图。
- 4K 处理并发默认一到两个任务。
- 每次发布和回滚都保留审计记录。

## 15. 本机运行评估

2026-07-14 再次检查当前 Mac：

- MacBook Air，Apple M2，8 核；
- 16 GB 统一内存；
- Node.js 22.22.0；
- npm 10.9.4；
- 16 GB 统一内存足以支持本地服务、SQLite、缩略图和 1-2 个 4K 处理并发；
- 数据盘当前约剩 45 GB，容量使用率约 77%。

硬件可以支持开发和运行，因为图片生成由 Codex 完成，不在本机运行大型生图模型。

当前磁盘已达到 P-1 开工条件。长期运行仍建议设置低于 20 GB 的告警，并通过缩略图、哈希去重和项目归档控制增长。

## 16. 交付阶段

### P-1：执行链可行性 Gate，1-2 个工作日

不建设 UI，仅使用纯 CLI 验证：

- SQLite 持久化队列和自包含任务合同；
- Codex Worker 领取、执行、回传和 checkpoint；
- 强制中断后由新会话恢复；
- 手动生成包导出和结果回导；
- 记录逐任务耗时、输入规模、结果文件、重试和错误；
- 模拟代表性项目负载，测量单会话吞吐和会话轮换频率。

P-1 结束时只决定 `codex_auto` 的自动化等级，不决定项目是否继续；`manual_import` 无条件进入正式 MVP。

#### P-1 实测结论（2026-07-14）

Gate 结果：`PASS WITH LIMITS`。

- 5 个 `codex_auto` 任务全部成功：4 次生成、1 次参考父图编辑；
- 1 个 `manual_import` 任务完成生成包导出、结果回导、哈希和溯源绑定；
- 首个任务从过期 Worker lease 被新 Worker ID 接管，attempt 从 1 增加到 2，随后成功完成；
- 三个未中断生成任务耗时为 26.2、29.3、37.5 秒，中位数约 29.3 秒；
- 参考父图编辑耗时约 81.7 秒；
- 当前 Codex 任务连续完成 5 次内置 ImageGen 调用，两个后续 Worker ID 各完成 2 个任务；
- 5 个内置结果均为 1254 x 1254 PNG，文件被复制到项目目录并记录 SHA-256；
- SQLite 中 6 个测试任务最终均为 GenerationJob `succeeded`，测试产物约 7.5 MB。

支持等级定义为 `interactive_resumable`：需要一个活跃 Codex 任务领取队列，但任务、lease、结果和 checkpoint 可恢复。不得把当前结果描述为官方保证的常驻监听或无人值守后台。

以下验证进入 P0 持续完成，不阻断开工：

- 在用户实际新建的另一个 Codex 任务中执行一次真实跨任务接管；
- 用 15-30 个生成、编辑和检查任务做长负载 soak test；
- 将 GenerationJob 执行成功与图片 QC/approved 明确分层。手动回导成功只代表传输和溯源成功，不代表图片符合合同或已批准。

### P0：共享垂直闭环，3-5 个工作日

- 插件和本地服务骨架；
- 单项目、单图位生成任务；
- 自动 Worker 与手动回导共用任务、结果和版本模型；
- 结果画廊和基础父子版本。

#### P0 核心实测结论（2026-07-15）

状态：`PASS WITH LIMITS / READY FOR P1`。

- 已实现本地 Python 服务、SQLite 正式 schema、CLI、Studio/Quality 工作台和双执行模式；
- `codex_auto` 与 `manual_import` 共用 GenerationJob、Asset、父子版本、事件和 QC 模型；
- GenerationJob 执行状态、技术检查、人工 QC 和 Registry 治理状态已明确分层；
- 手动模式已完成生成包导出、图片回导、SHA-256、技术检查、人工 QC 和候选按钮解锁实测；
- `registryctl` 已支持带文件锁和原子替换的 candidate 登记、审批证据晋升、哈希校验和对账；
- 中央 Registry 只读检查通过，共 30 条资产；浏览器验收未写入中央 Registry；
- 8 项自动化测试通过，覆盖 lease 恢复、幂等、技术 Gate、QC Gate、父子版本、Registry 晋升、HTTP API 和真实 stdio MCP 会话；
- 1280 x 720 与 390 x 844 浏览器实测通过，前端控制台 0 error、0 warning；
- 本地服务当前运行于 `http://127.0.0.1:8765`。
- 薄插件已通过仓库 Marketplace 安装，Codex 状态为 `installed, enabled`；插件不复制业务源码或 Skill；
- 新的独立 Codex 进程已把过期任务从 attempt 1 接管为 attempt 2，并以独立 Worker 关闭测试任务；
- 20 任务状态机 soak 通过：10 个生成合同、10 个父图编辑合同、4 个 Worker、1 次 lease 恢复，20 个技术检查和 QC 均通过。

P0 可以关闭并进入 P1。限制项必须保留：本轮 20 任务 soak 使用确定性 PNG fixture，未调用 ImageGen，因此不能证明模型上下文容量或图片质量稳定性；非交互 `codex exec` 会取消需要用户批准的 MCP 写工具。真实 15-30 次 ImageGen 长负载测试和 Codex Desktop 交互式 MCP 批准验证进入生产加固。当前自动等级仍是 `interactive_resumable`，不得描述为无人值守后台。

### P1：新品 MVP，增加 5-8 个工作日

- 先接收 workflow 现有结构化产物，自动混合资料解析后置；
- Product Facts、Claims 和参考图角色；
- 竞品 Package 分析；
- 策略、图序和 Image Contract；
- 产品素材覆盖 Gate；
- 核心质量检查和人工审批。

#### P1 实测进展（2026-07-15）

状态：`STRUCTURAL MVP PASS / REAL SKU VALIDATION PENDING`。

- 已新增 `p1-intake.1` 结构化输入契约，覆盖 Product Facts、Claims、卖点、产品参考图、竞品 Package、品牌规则和素材覆盖要求；
- 已实现策略准备与生图准备分层，事实未锁定、Claim 未解决或品牌未批准会阻断 Gate 1，产品图不足则输出具体补拍清单并阻断入队；
- 已实现 Gate 1 图片策略、Gate 2 图片序列和 reference-led Image Contract，契约强制产品/品牌不变量、单一 `change_only`、Claim 白名单、Avoid 和验收标准；
- 已接入 P0 共用队列，支持 `codex_auto` 和 `manual_import`，输入或规划被替换时会自动取消旧的排队/待回导任务；任务已被 Worker 租约领取时禁止修改上游输入；
- 已新增 Launch Plan 网页、7 个 P1 MCP 工具、CLI 和 HTTP 路由；
- 11 项自动化测试通过；合成样例已完成覆盖、双 Gate、2 个契约和 2 个手动回导任务的完整状态链；
- 1200 宽桌面与 390 x 844 手机视图通过，浏览器控制台 0 error、0 warning。

当前限制：样例使用合成 fixture，只证明结构、状态和恢复语义，不证明产品图角色识别、真实 SKU 准确性或 ImageGen 图片质量。P1 最终验收仍需选择一个真实待上市 SKU，导入现有 workflow 研究产物，完成一次缺图补拍回路，并把至少一张真实结果走完技术检查、产品/Claim QC 和 candidate 提名。

### P2：在售优化 MVP，增加 5-8 个工作日

- 当前 ListingVersion 导入；
- 诊断和运营事件输入；
- Optimization Contract 和挑战版本；
- 发布与回滚记录；
- 工作台记录图片实际上线时间；
- 手动补充广告、促销、Review 和其他干扰事件；
- amazon-ops 完成注册和冒烟测试后读取 traffic、sales、ledger 和 snapshot 数据；
- 输出保留、回滚或 inconclusive 评估决定。

#### P2 实测进展（2026-07-15）

状态：`STRUCTURAL MVP PASS / PH204 DIAGNOSIS GATE PENDING`。

- 已实现 `p2-intake.1`、ListingVersion、诊断、人工 Gate、单变量 Optimization Contract、发布记录、观察窗口、干扰事件和 keep/rollback/inconclusive 决策；
- 已复用 P0 共用队列、双执行模式、父子版本、技术检查和人工 QC；上游修改会取消待执行挑战任务，任务已被租约领取时禁止修改；
- 已将 Sorftime 数据标记为 `external_estimate`，Sessions/CVR 缺失时明确提示，禁止把销量或排名变化直接归因给图片；
- 已新增 Optimize Plan 网页、11 个 P2 MCP 工具、CLI 和 HTTP 路由，MCP 总工具数为 34；
- PH204 Amazon AE 真实项目已导入：7 条锁定事实、6 张可读产品参考图、6 个竞品 Listing、5 个证据源、10 个 Sorftime 基线周期和当前 MAIN 快照；
- PH204 诊断准备通过，发现当前 MAIN 与产品实拍在底座/外观上存在高置信度候选不一致，且当前源图仅 403 x 500；同时明确记录 5-7 月业绩下滑尚不能归因于图片；
- PH204 改图准备被正确阻断：当前只捕获 MAIN，尚缺整套副图与 A+；UAE VOC 无有效样本，US VOC 仅作为方向性证据；
- 14 项自动化测试通过，覆盖 P0/P1 回归、P2 缺图阻断、发布时点、干扰事件下的 inconclusive 和租约期间禁止修改。
- 1280 x 800 桌面与 390 x 844 手机浏览器验收通过，无页面级横向溢出、无控制台 warning/error；手机端长诊断表使用容器内受控横向滚动。

下一 Gate：补齐 PH204 当前 Listing 全套图片与 A+，补 Seller Central Sessions/CVR 和运营干扰事件时间线，然后由用户批准或退回诊断 v1；批准前不创建挑战版本。

### P3：可选自动化

- Amazon 数据自动同步；
- API 图片 Provider；
- 后台无人值守任务；
- 跨渠道适配和批量矩阵；
- 在权限和回滚机制成熟后增加发布连接器。

双模式可用 MVP 预计需要 14-23 个工作日。该估算包含 P-1 和收缩后的固定模板排版，不包含自由排版引擎、全自动混合输入理解或 API 后台生图。

## 17. 验收标准

### 17.1 P-1 Gate

- 连续任务可以从 SQLite 被领取、执行并记录结果，不需要复制粘贴队列内容。
- queued 和 running 状态都经过强制中断测试，新会话恢复后不丢任务、不重复落盘。
- 每个任务记录 queued、started、finished 时间、类型、输入数量和大小、输出、重试与错误。
- 完成一次代表性项目负载测试，并形成单任务耗时和单会话容量报告。
- 手动生成包可以导出，结果回导后保留 job ID、asset ID、parent ID、槽位和哈希。
- 自动链路不成立时，明确记录限制，正式采用 manual_import，不默认转向收费 API。

### 17.2 新品模式

- 用户可以一次上传完整资料包。
- 工作台能区分 Facts、Claims、卖点假设和竞品证据。
- 素材不足时生成具体补拍任务，只阻断受影响槽位。
- 用户可以确认完整图片序列和逐图合同。
- Codex 可以生成或编辑候选图并回传正确图位。
- 产品、Claim、合规、可读性和技术质量 Gate 可以运行。
- 候选图保存来源、父版本、Prompt、评分和决策。
- 首次上线图片成为完整优化基线。

### 17.3 在售优化模式

- 可以把当前线上图片导入为有序 ListingVersion。
- 可以把诊断结论转成单图位优化合同。
- 挑战版本只改变一个已声明主要变量。
- 发布前已经建立回滚目标。
- 可以记录发布时间和同期运营事件。
- 可以用证据标记 validated、rolled_back 或 inconclusive。
- 经验保留适用上下文，不自动泛化。

### 17.4 安全与治理

- 不用 AI 补全缺失的产品事实。
- 无依据 Claim 不能进入 approved。
- 失败 Prompt 不会无限重复。
- 资产 approved、published、validated、retired，以及实验 rolled_back 都需要人工证据。
- 不覆盖用户现有文件和无关仓库改动。

## 18. 主要风险与控制

| 风险 | 控制方式 |
|---|---|
| 产品结构漂移 | 真实参考角色、产品硬门槛和确定性产品层 |
| 抽卡式迭代 | 单变量合同、父图编辑、轮次限制和失败分类 |
| Claim 无依据 | Claim 台账、证据链接和阻断状态 |
| 错误归因给图片 | ListingVersion、干扰事件时间线和 inconclusive 状态 |
| Skill 或平台规则过时 | last_verified、staleness_risk 和版本化规则包 |
| 流程过重 | 一次导入、一次计划 Gate、一次最终批准 |
| 图片占用磁盘 | 缩略图、哈希去重、归档和清理策略 |
| Codex 中断或无法常驻 | 持久化队列、lease、checkpoint、会话轮换和正式 manual_import 模式 |
| Registry 与 SQLite 漂移 | 程序化候选登记、稳定资产 ID、晋升 Gate 和双向引用对账 |
| 旧目录继续被写入 | P-1 前改 extractor/workflow 写入目标，asset-library 只读兼容 |

## 19. 推荐建设顺序

1. 确认磁盘门槛，并修正 extractor、workflow 和项目合同的旧 asset-library 写入目标。
2. 定义 Registry 程序化接口、稳定资产 ID 和 SQLite 权威边界。
3. 执行 P-1：同时验证 codex_auto、manual_import、中断恢复和会话吞吐。
4. 建立两种执行模式共用的数据模型、版本树和质量入口。
5. 完成新品模式直到最终候选批准，验收后冻结旧新品路径。
6. 在做优化之前先完成 ListingVersion 快照和工作台发布记录。
7. amazon-ops 冒烟通过后接入可提供的数据，人工补齐其不覆盖的运营事件。
8. 完成在售优化直到验证和回滚，随后归档重复旧 Skill 和 workflow。
9. 手工闭环稳定后，再评估 API Provider、后台任务和跨渠道扩展。

这个顺序可以避免界面装饰、Amazon 接口和批量铺量能力拖慢最核心的“新品生产闭环”和“在售优化闭环”。
