# P2 Existing Listing Optimization Status

Date: 2026-07-15

Status: `STRUCTURAL MVP PASS / PH204 DIAGNOSIS GATE PENDING`

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
- Optimize Plan renders the locally captured current Listing images with slot and
  dimensions through a project-scoped media endpoint.

## PH204 Validation

Project ID: `prj_01KXJE5NV4THZG9NM4V54DEXCQ`

- ListingVersion v2 imports seven locked product facts, six readable product
  references, six competitor Listing records, seven registered evidence sources,
  and ten Sorftime baseline periods.
- The complete current image set is local and ordered: `MAIN`, `PT01`-`PT07`, and
  `APLUS01`-`APLUS07`. All 15 files are readable and carry source URL, SHA-256,
  dimensions, and capture date.
- Brand Story is recorded as supporting evidence. Its one brand hero and sixteen
  related-product carousel thumbnails are not mixed into the PH204 image slots.
- Diagnosis readiness is `passed`.
- Generation readiness is `passed`; no image contract can be queued until the
  human diagnosis Gate is approved.
- Diagnosis v2 records a high-confidence MAIN product-fidelity mismatch, an
  unsupported absolute durability claim in `APLUS03`, and a proof gap around
  stability and hinge performance. It still refuses to attribute the May-July
  decline to images without Sessions/CVR and an event timeline.
- UAE VOC is marked unavailable; US VOC is directional only.

## Remaining Gate Inputs

1. Review and approve or revise diagnosis version 2 before challenge contracts
   are created.
2. Add Seller Central Sessions and Unit Session Percentage for a clean baseline
   window when available.
3. Add dated price, coupon, ads, promotion, inventory, review, and competitor
   events around the future image publication window.

## Verification

- 15 automated tests pass, including P0/P1 regression coverage, three P2
  state-machine tests, and signature-based MIME handling for mislabeled images.
- MCP stdio exposes 34 tools and shares the production workbench database.
- JavaScript syntax validation passes.
- Desktop 1280 x 800 and mobile 390 x 844 browser checks pass with no page-level
  horizontal overflow and no console warning or error. The dense diagnosis table
  uses controlled horizontal scrolling on mobile.
- Studio and Optimize Plan tab switching passes. The image-set blocker is closed;
  the challenge queue remains unavailable only until diagnosis v2 receives human
  approval.
- All 15 PH204 project-scoped image endpoints return `200` with MIME types derived
  from their real file signatures.
