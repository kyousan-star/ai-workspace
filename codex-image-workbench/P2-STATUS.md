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

- Imported seven locked product facts, six readable product references, six
  competitor Listing records, five evidence sources, and ten Sorftime baseline
  periods.
- Saved the current MAIN image locally with its source URL, SHA-256, and
  403 x 500 metadata.
- Diagnosis readiness is `passed`.
- Generation readiness is `blocked` because the secondary Listing and A+ image
  sequence has not been captured.
- The diagnosis records a high-confidence candidate product-fidelity mismatch
  in MAIN and a source-resolution issue, while explicitly refusing to attribute
  the May-July performance decline to images without Sessions/CVR and an event
  timeline.
- UAE VOC is marked unavailable; US VOC is directional only.

## Remaining Gate Inputs

1. Save the full live Listing image sequence and A+ images with slot order and
   capture date under the PH204 project folder.
2. Add Seller Central Sessions and Unit Session Percentage for a clean baseline
   window when available.
3. Add dated price, coupon, ads, promotion, inventory, review, and competitor
   events around the future image publication window.
4. Review and approve or revise diagnosis version 1 before challenge contracts
   are created.

## Verification

- 14 automated tests pass, including P0/P1 regression coverage and three P2
  state-machine tests.
- MCP stdio exposes 34 tools and shares the production workbench database.
- JavaScript syntax validation passes.
- Desktop 1280 x 800 and mobile 390 x 844 browser checks pass with no page-level
  horizontal overflow and no console warning or error. The dense diagnosis table
  uses controlled horizontal scrolling on mobile.
- Studio and Optimize Plan tab switching passes; the challenge queue remains
  disabled while the current Listing image-set blocker is open.
