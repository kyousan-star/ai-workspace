from __future__ import annotations

import argparse
import json
from pathlib import Path

from workbench.production import compose_locked_product, normalize_production_spec


DEFAULT_VISUAL_LAB = Path("/Users/lihuan/ai-workspace/visual-lab")


def reference(reference_id: str, path: Path, view: str) -> dict:
    return {
        "reference_id": reference_id,
        "path": str(path.resolve()),
        "role": "product",
        "view": view,
        "approved": True,
        "exists": path.is_file(),
        "readable_image": path.is_file(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify PH204 V1.3 production route gates")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_VISUAL_LAB / "tmp" / "ph204-production-v1.3",
    )
    args = parser.parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pt04_source = DEFAULT_VISUAL_LAB / "tmp" / "PT04_package_v1" / "source" / "ph204-pt04-product-cutout-refined.png"
    pt06_source = DEFAULT_VISUAL_LAB / "tmp" / "ph204-pt06-folded-side-cutout-final.png"
    pt04_ref = reference("ph204-pt04-approved-cutout", pt04_source, "front")
    pt06_ref = reference("ph204-pt06-rejected-cutout", pt06_source, "side")

    pt04 = normalize_production_spec(
        {
            "requested_route": "deterministic",
            "target_view": "front",
            "product_source_id": pt04_ref["reference_id"],
            "source_quality": "approved",
            "canvas": {"width": 1254, "height": 1254, "background": "#FFFFFF"},
            "placement": {"max_width_ratio": 0.72, "max_height_ratio": 0.82, "anchor": "center"},
        },
        {pt04_ref["reference_id"]: pt04_ref},
        [pt04_ref["reference_id"]],
        ["front"],
    )
    pt04_output = output_dir / "PT04-deterministic-proof.png"
    pt04_provenance = compose_locked_product(pt04, pt04_output)

    pt06 = normalize_production_spec(
        {
            "requested_route": "deterministic",
            "target_view": "side",
            "product_source_id": pt06_ref["reference_id"],
            "source_quality": "insufficient",
        },
        {pt06_ref["reference_id"]: pt06_ref},
        [pt06_ref["reference_id"]],
        ["side"],
    )
    report = {
        "schema_version": "ph204-production-regression.1",
        "pt04": {
            "expected": "deterministic",
            "actual": pt04["route"],
            "ready": not pt04["blockers"],
            "production": pt04,
            "output_path": str(pt04_output),
            "provenance": pt04_provenance,
        },
        "pt06": {
            "expected": "blocked",
            "actual": pt06["route"],
            "ready": not pt06["blockers"],
            "production": pt06,
        },
    }
    report_path = output_dir / "PH204-PRODUCTION-REGRESSION.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if pt04["route"] == "deterministic" and pt06["route"] == "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
