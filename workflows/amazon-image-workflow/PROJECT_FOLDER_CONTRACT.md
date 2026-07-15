# Project Folder Contract

每个业务项目的图片工作区固定为：

```text
PROJECT_ROOT/ai_image_workflow/
```

中央 workflow 包只读，项目产出只写入业务项目工作区。

## 项目工作区结构

```text
ai_image_workflow/
  workflow_config.md
  00_INPUT/
  01_WORKFLOW/
  02_RESEARCH/
  03_STRATEGY/
  04_IMAGE_SEQUENCE/
  05_BRIEFS_PROMPTS/
  06_GENERATIONS/
  07_EVALUATION/
  08_ITERATION/
  09_FINAL/
  10_LEARNINGS/
```

## 00_INPUT

用户输入资料：

- `product_facts.md`
- `requirements.md`
- `brand_guide.md`
- `competitor_list.md`
- `claims_and_compliance.md`
- `product_photos/`
- `competitor_images/`
- `reviews_or_voc/`
- `current_listing_images/`
- `brand_assets/`

`brand_assets/` 中已批准的品牌资料应引用 `visual-lab/brand-library/{brand}/`，SKU 事实和参考图引用 `visual-lab/product-library/{product-line}/skus/{sku}/`。旧 `asset-library` 仅作历史只读兼容（见阶段4.5）。

## 01_WORKFLOW

流程控制文件：

- `status.md`
- `decisions.md`
- `run_log.md`

## 02_RESEARCH

研究输出：

- `product_facts_locked.md`
- `competitor_visual_analysis.md`
- `voc_selling_points.md`
- `asset_inventory.md`
- `compliance_boundaries.md`

## 03_STRATEGY

策略输出：

- `image_strategy.md`
- `gate1_strategy_summary.md`

## 04_IMAGE_SEQUENCE

图片序列输出：

- `listing_image_sequence.md`
- `aplus_image_sequence.md`
- `ad_creative_sequence.md`
- `gate2_sequence_summary.md`

## 05_BRIEFS_PROMPTS

执行文件：

- `image_briefs.md`
- `generation_prompts.md`
- `negative_prompts.md`
- `acceptance_criteria.md`

## 06_GENERATIONS

生成记录和候选图：

- `generation_log.md`
- 候选图片或候选图片路径。

## 07_EVALUATION

评估输出：

- `evaluation_report.md`
- `candidate_ranking.md`

## 08_ITERATION

迭代输出：

- `iteration_plan.md`
- `revised_prompts.md`
- `iteration_log.md`

## 09_FINAL

最终交付：

- `final_candidate_summary.md`
- `final_delivery_checklist.md`
- 最终图片或交付路径。

## 10_LEARNINGS

经验沉淀：

- `lessons_learned.md`
- `prompt_library.md`
- `failure_patterns.md`
