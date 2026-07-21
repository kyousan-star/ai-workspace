# P1 New Product MVP Status

Date: 2026-07-15
Decision: STRUCTURAL MVP PASS / REAL SKU VALIDATION PENDING

## Delivered

- Normalized `p1-intake.1` contract for Product Facts, Claims, selling points,
  product references, competitor packages, brand rules, and coverage targets.
- Deterministic input validation with separate strategy and generation readiness.
- SHA-256 reference deduplication, readable-image checks, required-view checks,
  visible-feature checks, competitor warnings, and specific capture requests.
- Gate 1 strategy model with evidence-bound selling points, Claims, category
  baselines, compliance boundaries, and visual exclusions.
- Gate 2 image sequence model with required baseline coverage.
- Reference-led Image Contracts with product and brand invariants, one explicit
  `change_only` variable, allowed Claims, Avoid rules, and acceptance criteria.
- Shared compilation into the P0 `codex_auto` or `manual_import` job queue.
- V1.3 production Gate requires a reviewed transparent real-product source for
  final Listing/A+ contracts. Exact-product jobs cannot use `codex_auto`.
- Transactional invalidation: replacing intake, strategy, sequence, or contracts
  cancels queued/manual-waiting jobs; leased work blocks revision until released.
- Launch Plan UI for coverage, Gate decisions, sequence review, contracts, and
  queue submission. Launch planning hides the result inspector until Studio is used.
- Seven P1 MCP tools and matching CLI and HTTP routes.

## Verification

- `python3 -m unittest discover -s tests -v`: 11 passed.
- `node --check workbench/static/app.js`: passed.
- P1 HTTP import and launch-workspace read: passed.
- Invalid Claim and execution mode rejection: passed.
- Re-import invalidation and queued-job cancellation: passed.
- Synthetic P1 fixture reached `coverage=passed`, Gate 1 approved, Gate 2
  approved, two contracts ready, and two `manual_import` jobs awaiting import.
- Browser: 1200-wide desktop and 390 x 844 mobile views passed visual checks.
- Browser console: 0 errors, 0 warnings.

## Runtime Demo

- Project: `prj_01KXJ9MZTS9ACYART09Q57AD0F`
- Name: `P1 Launch Planner Demo`
- Inputs: `examples/p1-*.json`
- Service: `http://127.0.0.1:8765`

The fixture uses synthetic images and facts. It verifies workflow behavior only;
it is not evidence of product-reference accuracy or generated-image quality.

## Remaining P1 Validation

1. Import one real pre-launch SKU using the existing workflow research outputs.
2. Verify Codex normalization against the real Product Facts, Claims, Listing,
   product photos, competitor images/listings, and approved brand system.
3. Exercise the missing-image response with a real capture request and re-import.
4. Generate or manually return at least one real contract result, then complete
   technical checks, product/Claim QC, and candidate nomination.
5. Keep ImageGen limited to `concept_only` or background-only preparation.
   Final product pixels remain locked and are assembled deterministically.
