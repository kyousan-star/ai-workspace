---
name: asset-curator
description: 管理品牌、产品和 Campaign 视觉资产的登记、去重、来源、哈希、候选、审批、上线、验证和退役状态。触发词：登记品牌资产、整理资产库、晋升approved、资产审批、Golden Set、成功prompt回流、asset curation。默认只能登记为 candidate；任何 approved、published、validated 或 Golden Set 晋升必须停下来取得用户明确确认。
last_verified: 2026-07-15
staleness_risk: medium
---

# Asset Curator

让资产复用建立在证据和审批上，而不是“看起来不错”。

## 生命周期

`raw → candidate → approved → published → validated → retired`

失败或明确否决的资产可标记 `rejected`。状态定义见 `references/asset-lifecycle.md`。

## 执行流程

1. 确认中央 registry 路径；不得把运行镜像当作源。
2. 运行 `scripts/validate_asset_registry.py` 检查结构、状态和晋升证据。
3. 新资产默认登记为 `candidate`，记录父资产、来源路径、哈希、渠道、产品和 Campaign。
4. 准备审批摘要：缩略信息、用途、证据、风险、建议状态。
5. 在任何晋升前停在 Asset Promotion Gate。
6. 只有用户明确列出资产 ID 和目标状态后才修改。
7. 晋升后更新 registry、对应 metadata 和决策日志，再重新验证。

## 程序化入口

工作台和其他自动化不得直接拼接 `asset-registry.json`。统一调用：

```bash
python3 scripts/registryctl.py --registry <registry.json> check
python3 scripts/registryctl.py --registry <registry.json> register-candidate --manifest <asset.json>
python3 scripts/registryctl.py --registry <registry.json> reconcile --sqlite <workbench.sqlite>
```

`register-candidate` 校验来源文件、SHA-256、父资产和重复 ID，并使用文件锁与原子替换。它只能写入 `candidate`。`promote` 必须显式提供审批人、审批时间和决策记录；工作台不得绕过 Promotion Gate。

## 禁止

- 不因文件名含 final、终版、推荐就自动 approved。
- 不因已经上线就自动 validated；validated 需要效果或人工复核证据。
- 不覆盖原文件；新版本必须保留 parent ID。
- 不把竞品图、未授权素材或不明来源资产晋升为自有 Golden Set。
