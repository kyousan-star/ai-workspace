# P2 Existing Listing Optimization Status

Date: 2026-07-19

Status: `STRUCTURAL MVP PASS / PH204 FIRST RELEASE PENDING`

## Implemented

- `p2-intake.1` normalizes current Listing versions, local image snapshots,
  verified product facts and references, Claims, VOC, competitors, baseline
  observations, and dated interference events.
- Diagnosis readiness and generation readiness are separate. Missing current
  Listing images can block challenges without blocking evidence review.
- Evidence-linked diagnoses require explicit issue IDs, severity, confidence,
  findings, hypotheses, known evidence references, and target metrics.
- A human diagnosis Gate precedes one-variable challenge contracts.
- Challenge contracts reuse the P0 generation queue, execution modes, asset
  versions, technical checks, and manual QC. Replacing upstream inputs cancels
  pending challenge jobs; leased jobs block revision.
- Release records require the actual Amazon publication time and the exact
  QC-approved contract result.
- Post-release observations preserve source and source class. Sorftime is stored
  as `external_estimate`, not first-party conversion data.
- Open interference events prevent `keep` or `rollback`; the workbench still
  permits an explicit `inconclusive` decision.
- Optimize Plan is available in the browser. CLI, HTTP, and eleven P2 MCP tools use
  the same SQLite state.

## PH204 Validation

Project ID: `prj_01KXJE5NV4THZG9NM4V54DEXCQ`

- ListingVersion v2 contains the complete ordered image set: `MAIN`, `PT01`-`PT07`,
  and `APLUS01`-`APLUS07`, plus seven locked facts, six product references, six
  competitor Listings, registered evidence, and ten Sorftime baseline periods.
- Diagnosis v2 and the optimization Gate are approved. It records a high-confidence
  MAIN product-fidelity mismatch, an unsupported absolute durability claim in
  `APLUS03`, and a proof gap around stability and hinge performance.
- PT02 `wb-halorient-ph204-listing-image-01KXNJ6JPGP0C9CJ7BS21FZ42V` passed
  technical and manual QC and was explicitly approved by the user on 2026-07-16.
  Its Registry state is `approved`; it has not been recorded as `published`.
- MAIN v3 `wb-ph204-main-real-photo-v3` uses actual PH204 photo pixels on pure
  white and passed internal geometry/compliance QC. It is a `candidate`, not a
  user-approved release asset.
- PT04 `wb-ph204-pt04-real-contact-surfaces-v1` passed internal QC and is a
  `candidate`. User visual approval is still required, and it remains held behind
  the PT02 single-variable observation window.
- MAIN v1 and v2 are `rejected`. MAIN v2 was demoted after compliance re-review
  because it contains a non-included phone and generated/mockup product pixels.
- PT06 v1, v2, and v4 are retained as `rejected` lineage. Their failure reasons
  cover raw background, inaccurate labels and proof mapping, edge distortion, and
  incoherent composite scale/lighting. PT06 is blocked pending better folded-state
  photography.
- Seven APLUS03 attempts remain failed transient results. None is approved or
  registered for reuse.
- Workbench SQLite and `visual-lab/asset-registry.json` reconcile with no missing
  workbench asset or hash mismatch across the 16 workbench assets and 38 Registry
  assets.
- PT02 Release Preflight passes contract, contract-to-asset, technical/QC,
  Registry approval, and rollback-target checks. Its release template intentionally
  leaves `published_at` empty until the Amazon AE frontend changes.

## Immediate Gates

1. Upload only the approved PT02 image to Amazon AE.
2. After the image is visibly live on the product detail page, record the actual
   publication timestamp in the workbench. There is currently no release record.
3. Start the 14-day single-variable observation window and capture Sessions, Unit
   Session Percentage/CVR, sales, price, coupon, ads, inventory, Reviews, and
   competitor changes. Sorftime can supplement but cannot replace Seller Central
   conversion data.
4. Review MAIN v3 and PT04 as offline candidates. Do not publish another image
   during PT02's observation window.
5. Keep PT06 blocked until a clean folded-state reshoot is available. PT05 and the
   APLUS03 proof image remain future production work, not part of the first test.

## Verification

- 20 automated tests pass across P0, P1, P2, Registry, and MCP coverage.
- MCP stdio exposes 37 tools, including Registry promote/reject and optimization
  release preflight.
- JavaScript and shell syntax checks pass.
- The PH204 state-sync run created a SQLite backup and Registry backup before
  writing, then verified the seven corrected/imported assets by state and SHA-256.
