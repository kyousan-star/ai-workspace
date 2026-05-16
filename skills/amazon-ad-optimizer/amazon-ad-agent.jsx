import { useState, useEffect, useCallback, useMemo } from "react";

const COLORS = {
  bg: "#0a0e17",
  card: "#111827",
  cardHover: "#1a2332",
  border: "#1e293b",
  accent: "#f59e0b",
  accentDim: "#b45309",
  success: "#10b981",
  danger: "#ef4444",
  warning: "#f59e0b",
  info: "#3b82f6",
  text: "#e2e8f0",
  textDim: "#94a3b8",
  textMuted: "#64748b",
  purple: "#8b5cf6",
  cyan: "#06b6d4",
  pink: "#ec4899",
  emerald: "#10b981",
};

const EXPOSURE_LEVELS = ["无曝光", "低曝光", "中曝光", "高曝光"];
const CLICK_LEVELS = ["无点击", "低点击", "中点击", "高点击"];
const ORDER_LEVELS = ["无转化", "低转化", "中转化", "高转化"];
const ACOS_LEVELS = ["极佳", "良好", "偏高", "过高"];

const AD_TYPES = [
  { id: "auto", name: "自动广告", sub: ["紧密匹配", "宽泛匹配", "同类商品", "关联商品"] },
  { id: "sp_kw", name: "手动关键词广告", sub: ["广泛匹配", "词组匹配", "精确匹配"] },
  { id: "sp_cat", name: "手动类目广告", sub: ["品类投放", "ASIN投放"] },
  { id: "sp_asin", name: "手动ASIN定位", sub: ["捡漏定位", "优势定位", "互补定位", "流量闭合"] },
  { id: "sb", name: "品牌广告", sub: ["商品集合", "旗舰店子页面", "视频广告"] },
  { id: "sd", name: "展示型广告", sub: ["商品投放", "再营销浏览定向"] },
  { id: "dsp", name: "DSP广告", sub: ["程序化展示"] },
];

const AD_STRATEGIES = [
  { id: "exposure", name: "打曝光/打收录", icon: "👁️", desc: "提升品牌曝光度和关键词收录" },
  { id: "click", name: "打点击", icon: "👆", desc: "优化CTR获取精准流量" },
  { id: "conversion", name: "打转化/降ACOS", icon: "🎯", desc: "提升CVR降低广告成本" },
  { id: "offense", name: "打进攻", icon: "⚔️", desc: "抢占竞品流量坑位" },
  { id: "defense", name: "打防守", icon: "🛡️", desc: "守住自有流量闭环" },
  { id: "haiwang", name: "海王广告", icon: "🌊", desc: "低价广撒网触达多类目" },
  { id: "bargain", name: "捡漏广告", icon: "💰", desc: "低竞价捡漏长尾流量" },
  { id: "offsite", name: "站外配合", icon: "🌐", desc: "Woot/测评/Deal站外联动" },
];

const CLICK_FACTORS = [
  { cat: "产品因素", items: ["首图质量", "附图/A+/视频", "产品标题", "产品价格", "评分/评论数", "亮点差异化", "促销/折扣/秒杀", "亚马逊标签(BS/AC)", "多颜色/尺码显示", "配送方式/时效"] },
  { cat: "广告因素", items: ["广告竞价", "匹配方式/否词", "广告位置", "流量精准性", "关键词搜索量", "预算充足度", "竞价策略", "品牌知名度", "竞品环境", "购物车/库存"] },
];

function getDiagnosis(exp, click, conv, acos) {
  const strategies = [];
  const problems = [];
  const actions = [];

  if (exp === 0) {
    problems.push("无曝光：关键词未被收录或竞价过低");
    actions.push("检查Listing埋词、后台Search Terms", "提高基础竞价至建议竞价", "检查是否有购物车/库存问题");
  } else if (exp === 1) {
    problems.push("低曝光：竞价不足或关键词搜索量小");
    actions.push("提高广告竞价和广告位溢价", "扩展相关长尾词增加曝光面", "检查广告预算是否过早耗尽");
  }

  if (click === 0 && exp > 0) {
    problems.push("有曝光无点击：主图/标题/价格竞争力不足");
    actions.push("优化主图突出产品亮点", "调整标题突出核心卖点", "检查价格竞争力和促销设置");
  } else if (click === 1) {
    problems.push("低点击率：流量匹配度或Listing吸引力待提升");
    actions.push("检查关键词与产品匹配度", "优化主图A+视频提升吸引力", "考虑开品牌视频广告SBV");
  } else if (click === 3) {
    if (conv <= 1) {
      problems.push("高点击低转化：流量质量问题或Listing转化障碍");
      actions.push("精准否定不相关搜索词", "优化Listing页面提升说服力", "检查价格/评论/竞品竞争力");
    }
  }

  if (conv === 0 && click > 0) {
    if (click >= 2) {
      problems.push("有点击无转化：严重的流量匹配或产品竞争力问题");
      actions.push("立即精准否定无效搜索词", "从售价/评论/品牌力维度全面检查", "考虑暂停该投放对象");
    } else {
      problems.push("数据量不足，不具参考性");
      actions.push("继续观察积累数据", "暂不做调整");
    }
  } else if (conv === 3) {
    problems.push("高转化表现优异");
    actions.push("记录广告位和自然位，持续保持", "尝试提高竞价扩大曝光", "单独开广告组放大优质词绩效");
    strategies.push("优质词提取，放大广告绩效");
  }

  if (acos === 3) {
    problems.push("ACOS过高：广告投入产出失衡");
    actions.push("降低高花费低转化词的竞价", "精准否定高消费无转化词", "优化Listing提高转化率以摊薄CPC");
  } else if (acos === 0) {
    strategies.push("ACOS极佳，可适当提高预算扩大规模");
  }

  if (exp >= 2 && click >= 2 && conv >= 2 && acos <= 1) {
    strategies.push("🌟 黄金组合！保持并扩大投放");
  }
  if (exp >= 2 && click <= 1 && conv >= 2) {
    strategies.push("开视频广告SBV提升点击率");
  }
  if (exp <= 1 && click >= 2 && conv >= 2) {
    strategies.push("提高竞价和预算获取更多曝光");
  }

  return {
    problems: problems.length ? problems : ["数据表现正常，继续监测"],
    actions: actions.length ? actions : ["维持当前策略，定期复盘"],
    strategies,
  };
}

function Badge({ children, color = COLORS.accent }) {
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 4,
      fontSize: 11, fontWeight: 600, background: color + "22", color,
      border: `1px solid ${color}44`, marginRight: 4, marginBottom: 2,
    }}>{children}</span>
  );
}

function MetricBar({ label, value, max, color }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: COLORS.textDim, marginBottom: 3 }}>
        <span>{label}</span>
        <span style={{ color }}>{typeof value === "number" ? value.toLocaleString() : value}</span>
      </div>
      <div style={{ height: 6, background: COLORS.border, borderRadius: 3, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${pct}%`, background: `linear-gradient(90deg, ${color}, ${color}88)`,
          borderRadius: 3, transition: "width 0.6s ease",
        }} />
      </div>
    </div>
  );
}

function TabButton({ active, onClick, children, icon }) {
  return (
    <button onClick={onClick} style={{
      padding: "10px 16px", border: "none", borderRadius: 8,
      background: active ? COLORS.accent + "22" : "transparent",
      color: active ? COLORS.accent : COLORS.textDim,
      cursor: "pointer", fontSize: 13, fontWeight: active ? 700 : 500,
      borderBottom: active ? `2px solid ${COLORS.accent}` : "2px solid transparent",
      transition: "all 0.2s", display: "flex", alignItems: "center", gap: 6,
      whiteSpace: "nowrap",
    }}>
      {icon && <span>{icon}</span>}{children}
    </button>
  );
}

function Card({ children, style = {} }) {
  return (
    <div style={{
      background: COLORS.card, border: `1px solid ${COLORS.border}`,
      borderRadius: 12, padding: 20, ...style,
    }}>{children}</div>
  );
}

function SectionTitle({ children, icon }) {
  return (
    <h3 style={{ color: COLORS.text, fontSize: 16, fontWeight: 700, margin: "0 0 16px 0", display: "flex", alignItems: "center", gap: 8 }}>
      {icon && <span style={{ fontSize: 20 }}>{icon}</span>}{children}
    </h3>
  );
}

function Select({ value, onChange, options, label }) {
  return (
    <div style={{ marginBottom: 12 }}>
      {label && <label style={{ fontSize: 12, color: COLORS.textDim, display: "block", marginBottom: 4 }}>{label}</label>}
      <select value={value} onChange={e => onChange(Number(e.target.value))} style={{
        width: "100%", padding: "8px 10px", background: COLORS.bg, border: `1px solid ${COLORS.border}`,
        borderRadius: 6, color: COLORS.text, fontSize: 13, outline: "none",
      }}>
        {options.map((o, i) => <option key={i} value={i}>{o}</option>)}
      </select>
    </div>
  );
}

// Profit Calculator
function ProfitCalculator({ profitData, setProfitData }) {
  const { price, cost, fbaFee, commission, adSpend, units } = profitData;
  const revenue = price * units;
  const totalCost = (cost + fbaFee) * units + (price * commission / 100 * units) + adSpend;
  const profit = revenue - totalCost;
  const profitRate = revenue > 0 ? (profit / revenue * 100) : 0;
  const breakEvenAcos = revenue > 0 ? ((revenue - (cost + fbaFee) * units - price * commission / 100 * units) / revenue * 100) : 0;
  const tacos = revenue > 0 ? (adSpend / revenue * 100) : 0;

  return (
    <Card>
      <SectionTitle icon="💰">利润核算 & 盈亏分析</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 16 }}>
        {[
          ["售价($)", price, v => setProfitData(p => ({ ...p, price: +v }))],
          ["成本($)", cost, v => setProfitData(p => ({ ...p, cost: +v }))],
          ["FBA费($)", fbaFee, v => setProfitData(p => ({ ...p, fbaFee: +v }))],
          ["佣金(%)", commission, v => setProfitData(p => ({ ...p, commission: +v }))],
          ["广告费($)", adSpend, v => setProfitData(p => ({ ...p, adSpend: +v }))],
          ["月销量", units, v => setProfitData(p => ({ ...p, units: +v }))],
        ].map(([label, val, setter], i) => (
          <div key={i}>
            <label style={{ fontSize: 11, color: COLORS.textDim }}>{label}</label>
            <input type="number" value={val} onChange={e => setter(e.target.value)} style={{
              width: "100%", padding: "6px 8px", background: COLORS.bg, border: `1px solid ${COLORS.border}`,
              borderRadius: 6, color: COLORS.text, fontSize: 13, outline: "none", boxSizing: "border-box",
            }} />
          </div>
        ))}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10 }}>
        {[
          ["月利润", `$${profit.toFixed(0)}`, profit >= 0 ? COLORS.success : COLORS.danger],
          ["利润率", `${profitRate.toFixed(1)}%`, profitRate >= 15 ? COLORS.success : profitRate >= 0 ? COLORS.warning : COLORS.danger],
          ["盈亏ACOS", `${breakEvenAcos.toFixed(1)}%`, COLORS.info],
          ["TACoS", `${tacos.toFixed(1)}%`, tacos < 10 ? COLORS.success : tacos < 20 ? COLORS.warning : COLORS.danger],
        ].map(([label, val, color], i) => (
          <div key={i} style={{
            textAlign: "center", padding: 10, background: color + "11",
            borderRadius: 8, border: `1px solid ${color}33`,
          }}>
            <div style={{ fontSize: 11, color: COLORS.textDim, marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 18, fontWeight: 800, color }}>{val}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// Diagnosis Panel
function DiagnosisPanel() {
  const [exp, setExp] = useState(2);
  const [click, setClick] = useState(2);
  const [conv, setConv] = useState(1);
  const [acos, setAcos] = useState(2);
  const [adType, setAdType] = useState(0);

  const diagnosis = useMemo(() => getDiagnosis(exp, click, conv, acos), [exp, click, conv, acos]);
  const comboId = `${EXPOSURE_LEVELS[exp]}_${CLICK_LEVELS[click]}_${ORDER_LEVELS[conv]}_ACOS${ACOS_LEVELS[acos]}`;

  const totalCombos = EXPOSURE_LEVELS.length * CLICK_LEVELS.length * ORDER_LEVELS.length * ACOS_LEVELS.length;

  return (
    <Card>
      <SectionTitle icon="🔬">广告诊断分析矩阵</SectionTitle>
      <div style={{ fontSize: 12, color: COLORS.textDim, marginBottom: 12 }}>
        4指标 × 4档位 = {totalCombos} 种完整矩阵组合 | 当前组合: <Badge color={COLORS.cyan}>{comboId}</Badge>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
        <Select label="📊 曝光量" value={exp} onChange={setExp} options={EXPOSURE_LEVELS} />
        <Select label="👆 点击次数" value={click} onChange={setClick} options={CLICK_LEVELS} />
        <Select label="🛒 广告订单(转化)" value={conv} onChange={setConv} options={ORDER_LEVELS} />
        <Select label="📈 ACOS水平" value={acos} onChange={setAcos} options={ACOS_LEVELS} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: COLORS.danger, marginBottom: 8 }}>⚠️ 问题诊断</div>
          {diagnosis.problems.map((p, i) => (
            <div key={i} style={{ fontSize: 12, color: COLORS.textDim, padding: "6px 0", borderBottom: `1px solid ${COLORS.border}` }}>
              <span style={{ color: COLORS.danger, marginRight: 6 }}>●</span>{p}
            </div>
          ))}
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: COLORS.success, marginBottom: 8 }}>✅ 优化动作</div>
          {diagnosis.actions.map((a, i) => (
            <div key={i} style={{ fontSize: 12, color: COLORS.textDim, padding: "6px 0", borderBottom: `1px solid ${COLORS.border}` }}>
              <span style={{ color: COLORS.success, marginRight: 6 }}>→</span>{a}
            </div>
          ))}
        </div>
      </div>

      {diagnosis.strategies.length > 0 && (
        <div style={{ marginTop: 12, padding: 10, background: COLORS.accent + "11", borderRadius: 8, border: `1px solid ${COLORS.accent}33` }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: COLORS.accent, marginBottom: 6 }}>💡 策略建议</div>
          {diagnosis.strategies.map((s, i) => (
            <div key={i} style={{ fontSize: 12, color: COLORS.text }}>{s}</div>
          ))}
        </div>
      )}
    </Card>
  );
}

// Ad Structure Panel
function AdStructurePanel() {
  const [selectedType, setSelectedType] = useState(null);

  return (
    <Card>
      <SectionTitle icon="🏗️">广告类型 & 结构</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 8, marginBottom: 16 }}>
        {AD_TYPES.map((t, i) => (
          <div key={t.id} onClick={() => setSelectedType(selectedType === i ? null : i)} style={{
            padding: 12, borderRadius: 8, cursor: "pointer", transition: "all 0.2s",
            background: selectedType === i ? COLORS.accent + "22" : COLORS.bg,
            border: `1px solid ${selectedType === i ? COLORS.accent : COLORS.border}`,
          }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: selectedType === i ? COLORS.accent : COLORS.text }}>{t.name}</div>
            <div style={{ fontSize: 11, color: COLORS.textMuted, marginTop: 4 }}>{t.sub.length}种子类型</div>
          </div>
        ))}
      </div>
      {selectedType !== null && (
        <div style={{ padding: 12, background: COLORS.bg, borderRadius: 8, border: `1px solid ${COLORS.border}` }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: COLORS.accent, marginBottom: 8 }}>{AD_TYPES[selectedType].name} - 投放子类型</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {AD_TYPES[selectedType].sub.map((s, i) => (
              <Badge key={i} color={COLORS.info}>{s}</Badge>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

// Strategy Matrix
function StrategyMatrix() {
  const [selectedStrategy, setSelectedStrategy] = useState(null);

  const strategyDetails = {
    exposure: { tactics: ["固定竞价确保曝光稳定", "Listing埋词增强相关性", "扩展广泛匹配覆盖更多词", "开自动广告4种匹配类型测试"], bidStrategy: "固定竞价", focus: "曝光量 > 点击率" },
    click: { tactics: ["优化主图/标题提升CTR", "精准投放高相关词", "广告位抢占搜索结果首页顶部", "开品牌视频广告SBV"], bidStrategy: "动态竞价-提高和降低", focus: "CTR > 转化率" },
    conversion: { tactics: ["精准否定无效搜索词", "提高投放词精准度", "优化Listing转化要素", "降低高消费低产出词竞价"], bidStrategy: "动态竞价-只降低", focus: "ACOS < 盈亏线" },
    offense: { tactics: ["竞品ASIN定位广告", "竞品品牌关键词投放", "4种广告类型全面进攻", "SD商品投放抢竞品页面"], bidStrategy: "固定竞价/动态提降", focus: "流量抢占 > ACOS" },
    defense: { tactics: ["自家ASIN互投流量闭环", "品牌词防御投放", "多SKU霸屏广告坑位", "展示型广告Retargeting"], bidStrategy: "动态竞价-只降低", focus: "防御效率" },
    haiwang: { tactics: ["超低竞价(建议竞价的10-20%)", "投放100+SKU或关键词", "高预算(不担心花光)", "选择高关联度类目投放"], bidStrategy: "动态竞价-只降低", focus: "低CPC广撒网" },
    bargain: { tactics: ["竞价$0.15-0.20超低出价", "竞价策略选只降低", "适用于有自然单和评论的产品", "针对ACOS高的大词热词"], bidStrategy: "动态竞价-只降低", focus: "利润 > 单量" },
    offsite: { tactics: ["Woot清库存+广告配合", "Deal站冲排名+广告承接", "测评积累评论后加大广告", "站外引流提升关联标签"], bidStrategy: "按阶段调整", focus: "站内外联动" },
  };

  return (
    <Card>
      <SectionTitle icon="⚡">广告策略矩阵</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 8, marginBottom: 16 }}>
        {AD_STRATEGIES.map(s => (
          <div key={s.id} onClick={() => setSelectedStrategy(selectedStrategy === s.id ? null : s.id)} style={{
            padding: 12, borderRadius: 8, cursor: "pointer", transition: "all 0.2s",
            background: selectedStrategy === s.id ? COLORS.purple + "22" : COLORS.bg,
            border: `1px solid ${selectedStrategy === s.id ? COLORS.purple : COLORS.border}`,
          }}>
            <div style={{ fontSize: 20, marginBottom: 4 }}>{s.icon}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: selectedStrategy === s.id ? COLORS.purple : COLORS.text }}>{s.name}</div>
            <div style={{ fontSize: 11, color: COLORS.textMuted, marginTop: 2 }}>{s.desc}</div>
          </div>
        ))}
      </div>
      {selectedStrategy && strategyDetails[selectedStrategy] && (
        <div style={{ padding: 16, background: COLORS.bg, borderRadius: 8, border: `1px solid ${COLORS.purple}33` }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: COLORS.purple, marginBottom: 8 }}>执行战术</div>
              {strategyDetails[selectedStrategy].tactics.map((t, i) => (
                <div key={i} style={{ fontSize: 12, color: COLORS.textDim, padding: "4px 0" }}>
                  <span style={{ color: COLORS.purple }}>▸</span> {t}
                </div>
              ))}
            </div>
            <div>
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: COLORS.textMuted }}>竞价策略</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.accent }}>{strategyDetails[selectedStrategy].bidStrategy}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: COLORS.textMuted }}>核心关注</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.cyan }}>{strategyDetails[selectedStrategy].focus}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

// Data Upload & Cleaning Simulator
function DataPanel() {
  const [step, setStep] = useState(0);
  const steps = [
    { title: "1. 下载广告数据", desc: "从亚马逊广告后台下载30天全部广告报告", details: ["商品推广搜索词报告", "投放报告", "广告位报告", "已购买商品报告", "Rufus提示词报告"] },
    { title: "2. 数据清洗", desc: "AI自动清洗和标准化数据格式", details: ["去除空值和异常数据", "统一货币和日期格式", "合并多报告数据", "计算衍生指标(CTR/CVR/CPA)"] },
    { title: "3. 指标量化分层", desc: "4大指标按阈值自动分层标记", details: ["曝光量: 无/低/中/高 (基于类目中位数)", "点击率: 无/低/中/高 (基于平均CTR)", "转化率: 无/低/中/高 (基于平均CVR)", "ACOS: 极佳/良好/偏高/过高 (基于盈亏线)"] },
    { title: "4. 组合矩阵分析", desc: "4指标×4档位生成256种组合诊断", details: ["搜索词维度分析 (30种场景)", "投放对象维度分析 (10种场景)", "ASIN维度分析 (4种场景)", "词频维度分析 (6种场景)", "投放类型分析 (占比/效率)"] },
    { title: "5. 智能诊断&优化", desc: "AI生成针对性诊断报告和优化方案", details: ["问题定位: 找出广告瓶颈", "策略匹配: 推荐最佳打法", "执行清单: 生成操作SOP", "预算分配: 优化预算结构"] },
    { title: "6. 监测&复盘", desc: "持续监测数据变化并自动复盘", details: ["广告日志自动记录", "周/月数据对比分析", "效果追踪和预警", "策略迭代优化建议"] },
  ];

  return (
    <Card>
      <SectionTitle icon="📊">数据处理工作流</SectionTitle>
      <div style={{ display: "flex", gap: 4, marginBottom: 16, overflowX: "auto" }}>
        {steps.map((s, i) => (
          <div key={i} onClick={() => setStep(i)} style={{
            flex: 1, minWidth: 80, padding: "8px 6px", borderRadius: 6, cursor: "pointer",
            background: step === i ? COLORS.emerald + "22" : i < step ? COLORS.emerald + "11" : COLORS.bg,
            border: `1px solid ${step === i ? COLORS.emerald : COLORS.border}`,
            textAlign: "center", transition: "all 0.2s",
          }}>
            <div style={{ fontSize: 18 }}>{i <= step ? "✅" : "⬜"}</div>
            <div style={{ fontSize: 10, color: step === i ? COLORS.emerald : COLORS.textMuted, fontWeight: step === i ? 700 : 400, marginTop: 2 }}>
              Step {i + 1}
            </div>
          </div>
        ))}
      </div>
      <div style={{ padding: 16, background: COLORS.bg, borderRadius: 8, border: `1px solid ${COLORS.emerald}33` }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: COLORS.emerald, marginBottom: 4 }}>{steps[step].title}</div>
        <div style={{ fontSize: 13, color: COLORS.text, marginBottom: 12 }}>{steps[step].desc}</div>
        {steps[step].details.map((d, i) => (
          <div key={i} style={{ fontSize: 12, color: COLORS.textDim, padding: "3px 0" }}>
            <span style={{ color: COLORS.emerald }}>▸</span> {d}
          </div>
        ))}
      </div>
    </Card>
  );
}

// Click Factors Analysis
function ClickFactorsPanel() {
  return (
    <Card>
      <SectionTitle icon="🔍">影响广告点击的13大因素</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {CLICK_FACTORS.map((group, gi) => (
          <div key={gi}>
            <div style={{
              fontSize: 13, fontWeight: 700, marginBottom: 8,
              color: gi === 0 ? COLORS.pink : COLORS.info,
              padding: "6px 10px", background: (gi === 0 ? COLORS.pink : COLORS.info) + "11",
              borderRadius: 6,
            }}>{group.cat}</div>
            {group.items.map((item, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 8, padding: "6px 0",
                borderBottom: `1px solid ${COLORS.border}`,
              }}>
                <span style={{ fontSize: 11, color: COLORS.textMuted, width: 16 }}>{i + 1}.</span>
                <span style={{ fontSize: 12, color: COLORS.text }}>{item}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}

// Lifecycle Strategy
function LifecyclePanel() {
  const phases = [
    { name: "新品期", period: "1-2个月", color: COLORS.info, strategy: "高相关精准词主攻，广告为主→自然过渡", adRatio: "70-80%", focus: "关键词收录+排名", bidType: "固定竞价" },
    { name: "成长期", period: "2-4个月", color: COLORS.emerald, strategy: "扩展中相关词，目标前3页排名", adRatio: "50-60%", focus: "扩词扩流", bidType: "动态提高和降低" },
    { name: "稳定期", period: "5-6个月+", color: COLORS.accent, strategy: "扩展低相关词+类目流量+竞品流量", adRatio: "30-40%", focus: "利润最大化", bidType: "动态只降低" },
    { name: "衰退期", period: "视情况", color: COLORS.danger, strategy: "铺开入口，保本CPC通投", adRatio: "降至最低", focus: "ROI维持", bidType: "动态只降低" },
  ];

  return (
    <Card>
      <SectionTitle icon="📈">产品生命周期广告策略</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        {phases.map((p, i) => (
          <div key={i} style={{
            padding: 14, borderRadius: 8, background: p.color + "08",
            border: `1px solid ${p.color}33`,
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 14, fontWeight: 800, color: p.color }}>{p.name}</span>
              <Badge color={p.color}>{p.period}</Badge>
            </div>
            <div style={{ fontSize: 12, color: COLORS.text, marginBottom: 8 }}>{p.strategy}</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6 }}>
              {[["广告占比", p.adRatio], ["核心", p.focus], ["竞价", p.bidType]].map(([l, v], j) => (
                <div key={j}>
                  <div style={{ fontSize: 10, color: COLORS.textMuted }}>{l}</div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: COLORS.textDim }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// Ad Plays SOP
function AdPlaysSOP() {
  const plays = [
    { name: "乞丐捡漏法", desc: "竞价$0.15-0.20，策略只降低", tag: "低成本", color: COLORS.success },
    { name: "品牌蹭流法", desc: "广泛投放类目品牌词", tag: "蹭流量", color: COLORS.info },
    { name: "错词法", desc: "投放高搜索量拼写错误词", tag: "低竞争", color: COLORS.cyan },
    { name: "西班牙语法", desc: "核心词翻译西语精准投放", tag: "蓝海词", color: COLORS.purple },
    { name: "ASIN定位4组法", desc: "捡漏+优势+互补+闭合", tag: "精准", color: COLORS.accent },
    { name: "竞品进攻法", desc: "4种广告全面打击竞品", tag: "进攻", color: COLORS.danger },
    { name: "Ranking收录法", desc: "不看ACOS只看排名权重", tag: "排名", color: COLORS.pink },
    { name: "广告霸屏防御", desc: "多SKU投同词/ASIN闭环", tag: "防御", color: COLORS.emerald },
    { name: "海王打法", desc: "超低竞价触达50+类目", tag: "引流", color: COLORS.info },
    { name: "Coupon刷广告", desc: "大折扣拉高CTR/CVR权重", tag: "白帽", color: COLORS.accent },
    { name: "预算递增法", desc: "提前3-5h超预算触发热门", tag: "技巧", color: COLORS.cyan },
    { name: "马甲法", desc: "继承高权重Campaign", tag: "高级", color: COLORS.purple },
    { name: "自动广告4拆法", desc: "4匹配类型独立测试", tag: "测试", color: COLORS.success },
    { name: "阶梯竞价法", desc: "5-10组阶梯竞价找最优", tag: "测试", color: COLORS.warning },
    { name: "标签打法", desc: "纠正/优化系统标签", tag: "标签", color: COLORS.pink },
    { name: "流量定位法", desc: "找到最高转化流量来源", tag: "旺季", color: COLORS.danger },
  ];

  return (
    <Card>
      <SectionTitle icon="📋">广告打法SOP库 (16种策略)</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
        {plays.map((p, i) => (
          <div key={i} style={{
            padding: 10, borderRadius: 8, background: COLORS.bg,
            border: `1px solid ${COLORS.border}`, display: "flex", flexDirection: "column", gap: 4,
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: COLORS.text }}>{p.name}</span>
              <Badge color={p.color}>{p.tag}</Badge>
            </div>
            <div style={{ fontSize: 11, color: COLORS.textMuted }}>{p.desc}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// Main App
export default function AmazonAdAgent() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [profitData, setProfitData] = useState({
    price: 29.99, cost: 8, fbaFee: 5.5, commission: 15, adSpend: 500, units: 200,
  });

  const tabs = [
    { id: "dashboard", name: "控制面板", icon: "🎛️" },
    { id: "diagnosis", name: "诊断分析", icon: "🔬" },
    { id: "strategy", name: "策略矩阵", icon: "⚡" },
    { id: "structure", name: "广告结构", icon: "🏗️" },
    { id: "plays", name: "打法SOP", icon: "📋" },
    { id: "lifecycle", name: "生命周期", icon: "📈" },
    { id: "factors", name: "影响因素", icon: "🔍" },
    { id: "workflow", name: "数据流程", icon: "📊" },
  ];

  return (
    <div style={{
      minHeight: "100vh", background: COLORS.bg, color: COLORS.text,
      fontFamily: "'Noto Sans SC', 'SF Pro Display', -apple-system, sans-serif",
    }}>
      {/* Header */}
      <div style={{
        padding: "16px 20px", borderBottom: `1px solid ${COLORS.border}`,
        background: "linear-gradient(180deg, #111827 0%, #0a0e17 100%)",
        position: "sticky", top: 0, zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 28 }}>🚀</span>
            <div>
              <h1 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: COLORS.accent, letterSpacing: -0.5 }}>
                Amazon PPC 智能广告优化系统
              </h1>
              <p style={{ margin: 0, fontSize: 11, color: COLORS.textMuted }}>
                4指标 × 4档位 = 256种矩阵组合 | 16种打法SOP | 7种广告类型 | 8种策略目的 | AI智能诊断
              </p>
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {[
              ["SP 商品推广", "60%", COLORS.info],
              ["SB 品牌广告", "20%", COLORS.purple],
              ["SD 展示型", "20%", COLORS.pink],
            ].map(([label, pct, color], i) => (
              <div key={i} style={{
                padding: "4px 10px", borderRadius: 6, fontSize: 11,
                background: color + "15", border: `1px solid ${color}33`, color,
              }}>
                {label} <strong>{pct}</strong>
              </div>
            ))}
          </div>
        </div>
        <div style={{ display: "flex", gap: 2, overflowX: "auto" }}>
          {tabs.map(t => (
            <TabButton key={t.id} active={activeTab === t.id} onClick={() => setActiveTab(t.id)} icon={t.icon}>
              {t.name}
            </TabButton>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: 20, maxWidth: 1200, margin: "0 auto" }}>
        {activeTab === "dashboard" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <ProfitCalculator profitData={profitData} setProfitData={setProfitData} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <DiagnosisPanel />
              <StrategyMatrix />
            </div>
            <AdPlaysSOP />
          </div>
        )}
        {activeTab === "diagnosis" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <DiagnosisPanel />
            <Card>
              <SectionTitle icon="📊">搜索词分析维度 (30种场景)</SectionTitle>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))", gap: 6 }}>
                {[
                  "中曝光_高点击率_高转化", "低曝光_高点击率_中转化", "低曝光_高点击率_高转化",
                  "高曝光_低点击率_低转化", "高曝光_低点击率_中转化", "低曝光_低点击率_高转化",
                  "中曝光_低点击率_低转化", "高曝光_低点击率_高转化", "低曝光_低点击率_中转化",
                  "低点击量_0转化", "中点击量_0转化", "高点击量_0转化",
                  "中曝光_中点击率_中转化", "高曝光_高点击率_高转化", "低曝光_中点击率_低转化",
                  "中曝光_高点击率_低转化", "高曝光_中点击率_高转化", "中曝光_中点击率_高转化",
                  "低曝光_中点击率_中转化", "高曝光_高点击率_低转化", "中曝光_中点击率_低转化",
                  "低曝光_中点击率_高转化", "高曝光_中点击率_中转化", "中曝光_低点击率_中转化",
                  "中曝光_低点击率_高转化", "高曝光_高点击率_中转化", "低曝光_低点击率_低转化",
                  "中曝光_高点击率_中转化", "高曝光_中点击率_低转化", "低曝光_高点击率_低转化",
                ].map((s, i) => {
                  const hasZero = s.includes("0转化");
                  const hasHigh = s.includes("高转化") && s.includes("高点击率");
                  return (
                    <div key={i} style={{
                      padding: "6px 10px", borderRadius: 6, fontSize: 11,
                      background: hasZero ? COLORS.danger + "11" : hasHigh ? COLORS.success + "11" : COLORS.bg,
                      border: `1px solid ${hasZero ? COLORS.danger + "33" : hasHigh ? COLORS.success + "33" : COLORS.border}`,
                      color: hasZero ? COLORS.danger : hasHigh ? COLORS.success : COLORS.textDim,
                    }}>
                      {i + 1}. {s}
                    </div>
                  );
                })}
              </div>
            </Card>
            <Card>
              <SectionTitle icon="📋">五大维度汇总分析</SectionTitle>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10 }}>
                {[
                  { title: "搜索词分析", count: "30种", color: COLORS.info, items: ["曝光×点击×转化组合", "含3种0转化场景"] },
                  { title: "投放对象分析", count: "10种", color: COLORS.purple, items: ["点击×转化组合", "含3种0转化场景"] },
                  { title: "ASIN分析", count: "4种", color: COLORS.pink, items: ["高/中转化率", "0转化(按点击量)"] },
                  { title: "词频分析", count: "6种", color: COLORS.accent, items: ["高/中/低转化率", "0转化(按点击量)"] },
                  { title: "投放类型", count: "5种", color: COLORS.emerald, items: ["出单词未投放", "精准/词组否定词"] },
                ].map((d, i) => (
                  <div key={i} style={{
                    padding: 12, borderRadius: 8, background: d.color + "08",
                    border: `1px solid ${d.color}33`, textAlign: "center",
                  }}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: d.color }}>{d.count}</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: COLORS.text, marginBottom: 6 }}>{d.title}</div>
                    {d.items.map((item, j) => (
                      <div key={j} style={{ fontSize: 10, color: COLORS.textMuted }}>{item}</div>
                    ))}
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}
        {activeTab === "strategy" && <StrategyMatrix />}
        {activeTab === "structure" && <AdStructurePanel />}
        {activeTab === "plays" && <AdPlaysSOP />}
        {activeTab === "lifecycle" && <LifecyclePanel />}
        {activeTab === "factors" && <ClickFactorsPanel />}
        {activeTab === "workflow" && <DataPanel />}
      </div>
    </div>
  );
}
