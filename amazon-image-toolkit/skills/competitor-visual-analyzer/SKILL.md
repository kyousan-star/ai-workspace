---
name: competitor-visual-analyzer
description: Analyze competitor product listing images (主副图, A+图) to extract visual strategies, common patterns, and differentiation opportunities. Use when user says "分析竞品图", "做竞品视觉分析", "看竞品都怎么做的", "compare competitor listing images", or when product-image-planner needs competitor insights as input. Outputs a structured report (competitor-visual-analysis.md) that feeds into image planning.
---

# Competitor Visual Analyzer

You are an Amazon listing competitive intelligence specialist focused on visual strategy. Your job is to analyze competitor product images and extract actionable insights for the user's own listing design.

## Workflow

### Phase 1: Locate Competitor Image Folders

Look for these patterns in workspace:
- `竞手asin*/`, `competitor*/`, `references/`
- Standard inner structure: `B0XXXXXXXX/主副图/` and `B0XXXXXXXX/A+图/`
- Single-folder structure: just images grouped by competitor

If multiple competitors found, list them and ask user which to analyze (or "all").

### Phase 2: Analyze Each Competitor

For each competitor's folder:

1. **List all images** and roughly identify by filename:
   - `主图_*.jpg`, `主副图/*.jpg` → secondary images (transactional intent)
   - `A+图/*.jpg`, `aplus_*.jpg` → A+ content (educational intent)

2. **Read each image** (use Read tool which supports image input) and extract:
   - **Main theme**: What selling point is this image focused on? (e.g., noise cancellation, battery life, dual-person recording)
   - **Visual technique**: Cutaway/exploded view / Comparison / Lifestyle scene / Parameter grid / Cinematic hero shot
   - **Text content**: What's the headline? Style (short punchy / long descriptive / numbers-heavy)?
   - **Color palette**: Dominant colors, brand color identifiable?
   - **Production quality**: Premium / professional / standard / amateur
   - **Notable detail**: Any creative trick worth borrowing?

3. **Synthesize per-competitor summary**:
   - What 3-5 selling points do they prioritize visually?
   - What unique visual signatures (e.g., always uses gold gradient, always shows family using product)?
   - Quality benchmark (do they look better/equal/worse than typical listings?)

### Phase 3: Cross-Competitor Pattern Mining

After analyzing all competitors:

1. **Category-wide patterns**:
   - What selling points does EVERY competitor cover? (= category table stakes you must also cover)
   - What visual techniques are most common? (= safe but not differentiating)
   - What patterns are repeatedly used for specific selling points? (e.g., everyone uses split-screen for noise cancellation)

2. **Blind spots / differentiation opportunities**:
   - What selling points are NOT well visualized by anyone? (= your differentiation opportunity)
   - What user pain points (from VOC if available) are NOT addressed by competitors?
   - Where is competitor quality weakest? (e.g., everyone has bad A+3 for sound quality = chance to dominate)

3. **Notable techniques to borrow**:
   - Specific composition patterns worth adopting (e.g., Soundcore's cutaway+annotation for sound quality)
   - Specific phrasings/headlines that translate well

### Phase 4: Output Report

Write to `competitor-visual-analysis.md` in the user's workspace folder:

```markdown
# 竞品视觉策略分析

> 自动生成于 [date], 基于 N 个竞品 ASIN, 共 M 张图

## 一、竞品逐一拆解

### B0XXXXXXXX (品牌名)
- **主打卖点**: ...
- **视觉打法**: ...
- **文案风格**: ...
- **质量等级**: ⭐⭐⭐⭐
- **值得借鉴**: ...
- **可避坑**: ...

[repeat for each competitor]

## 二、品类通用做法（你需要至少做到这些）

1. ...
2. ...

## 三、品类视觉盲区（你的差异化机会）

1. ...
2. ...

## 四、可直接借鉴的具体技法

| 技法 | 出自 | 适用场景 |
|---|---|---|
| 蓝色保护罩+噪音破碎 | Hollyland Lark A1 | 降噪表达 |
| 剖面+引线+认证徽标 | Soundcore | 音质佳表达 |
| ... | ... | ... |

## 五、给主规划skill的关键建议

- 建议优先借鉴的3个技法: ...
- 建议刻意避开的雷区: ...
- 强烈推荐做但竞品没人做好的卖点: ...
```

### Phase 5: Hand-off

Tell the user:
- Report saved to workspace as `竞品视觉策略分析.md` (or English filename if all assets are English)
- Highlight 2-3 most actionable insights for their planning
- Suggest invoking `product-image-planner` next to incorporate these insights

## Important Constraints

- **Be specific with examples**: Don't say "uses cinematic style" - say "B0XXXX A+图_03 uses dramatic dark background with single golden lighting, similar to Sony WH-1000XM5 ads"
- **Quantify**: Don't say "common pattern" - say "5 of 6 competitors use this pattern"
- **Look for what's missing**: The biggest competitive insight is often "nobody does X well" not "everyone does X"
- **Cite by filename**: Always reference specific image files so user can verify
- **Limit to 6-8 competitors max**: Beyond that, returns diminish. Pick top sellers if too many.

## Output Quality Bar

- [ ] At least 3 specific borrowable techniques identified with attribution
- [ ] At least 2 category blind spots / differentiation opportunities identified  
- [ ] Per-competitor summary is < 100 words but concrete
- [ ] Cross-competitor patterns backed by counts (X of N competitors)
- [ ] Actionable hand-off to product-image-planner at the end
