# Scene Library

通用**广告场景**模板库，供 `batch-asset-generator` 做"场景×产品×风格"矩阵批量出prompt时用。

与 `amazon-image-toolkit/resources/composition-templates.md`（T01-T11）的区别：
- composition-templates.md 是**listing图位**导向（主图/副图/A+图，服务单SKU精修）
- 本库是**广告渠道**导向（TikTok/Meta/Amazon Sponsored，服务多SKU批量铺量），维度是"这条广告投在哪个渠道、什么尺寸、什么场景基调"，不重复卖点构图逻辑本身——具体卖点怎么表达仍然优先复用 T01-T11 或对应product-line的`approved-compositions.md`。

## 文件

- `ad-scene-templates.md`：按渠道分类的场景基调+尺寸规范模板

## 使用方式

1. `batch-asset-generator` 读取目标product-line的`cutouts/`+`brand-style.md`
2. 从本库按投放渠道选场景模板
3. 从product-line的`approved-compositions.md`（或`composition-templates.md`）选卖点构图手法
4. 两者交叉生成矩阵prompt表，一次性产出全套prompt
