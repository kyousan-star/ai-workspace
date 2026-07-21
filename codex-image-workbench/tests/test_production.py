from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from workbench.core import Workbench
from workbench.production import image_has_transparency
from workbench.util import WorkbenchError


def make_product_cutout(path: Path) -> Path:
    image = Image.new("RGBA", (80, 120), (0, 0, 0, 0))
    image.paste((35, 40, 44, 255), (10, 8, 70, 112))
    image.save(path)
    return path


class ProductionRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "workbench"
        self.registry = self.base / "asset-registry.json"
        self.registry.write_text(json.dumps({"schema_version": "1.0", "assets": []}), encoding="utf-8")
        self.app = Workbench(self.root, registry_path=self.registry)
        self.project = self.app.create_project(
            {"name": "Production Test", "project_mode": "optimize", "brand": "Test", "sku": "P-1", "marketplace": "AE"}
        )["project"]
        self.cutout = make_product_cutout(self.base / "product.png")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def payload(self) -> dict:
        return {
            "slot_key": "PT04",
            "execution_mode": "manual_import",
            "operation": "generate",
            "prompt": "Place the locked real product on white.",
            "references": [
                {
                    "reference_id": "real-product",
                    "path": str(self.cutout),
                    "role": "product",
                    "view": "front",
                    "approved": True,
                }
            ],
            "acceptance": ["Exact product pixels"],
            "expected_output": {"format": "png", "aspect_ratio": "1:1", "min_width": 512},
            "production": {
                "requested_route": "deterministic",
                "target_view": "front",
                "product_source_id": "real-product",
                "canvas": {"width": 640, "height": 640, "background": "#FFFFFF"},
            },
        }

    def test_preflight_blocks_nontransparent_product_source(self) -> None:
        rgb = self.base / "photo.png"
        Image.new("RGB", (80, 120), (220, 220, 220)).save(rgb)
        payload = self.payload()
        payload["references"][0]["path"] = str(rgb)
        result = self.app.production_preflight(self.project["project_id"], payload)
        self.assertFalse(result["ready"])
        self.assertIn("locked product source must be a transparent cutout", result["blockers"])
        self.assertFalse(image_has_transparency(rgb))

    def test_reviewed_bad_cutout_is_blocked_even_with_transparency(self) -> None:
        payload = self.payload()
        payload["production"]["source_quality"] = "insufficient"
        result = self.app.production_preflight(self.project["project_id"], payload)
        self.assertFalse(result["ready"])
        self.assertIn("product source quality is insufficient", result["blockers"])
        self.assertIn(
            "reshoot_or_recut_product_source",
            {item["action"] for item in result["production"]["capture_requests"]},
        )

    def test_locked_route_cannot_disable_exact_product_requirement(self) -> None:
        payload = self.payload()
        payload["production"]["exact_product_required"] = False
        result = self.app.production_preflight(self.project["project_id"], payload)
        self.assertFalse(result["ready"])
        self.assertIn("locked-product route requires exact_product_required=true", result["blockers"])

    def test_deterministic_runner_preserves_product_source_and_records_provenance(self) -> None:
        job, created = self.app.create_job(self.project["project_id"], self.payload())
        self.assertTrue(created)
        self.assertEqual(1, job["max_attempts"])
        result = self.app.run_deterministic_job(job["job_id"], actor="test")
        self.assertEqual("passed", result["asset"]["technical_status"])
        self.assertEqual(640, result["asset"]["width"])
        self.assertFalse(result["provenance"]["generated_product_pixels"])
        self.assertEqual(str(self.cutout.resolve()), result["provenance"]["product_source_path"])
        self.assertTrue(Path(result["provenance_path"]).is_file())

    def test_identity_failure_hard_stops_slot_and_future_concept_jobs(self) -> None:
        concept = {
            "slot_key": "PT06",
            "execution_mode": "codex_auto",
            "operation": "generate",
            "prompt": "Explore a background concept only.",
            "production": {"requested_route": "concept_only", "exact_product_required": False},
        }
        job, _ = self.app.create_job(self.project["project_id"], concept)
        failure = self.app.record_production_failure(
            self.project["project_id"],
            "PT06",
            "product_geometry",
            "Generated stand geometry changed.",
            job_id=job["job_id"],
            actor="test",
        )
        self.assertEqual(1, failure["hard_stop"])
        self.assertEqual(1, failure["cancelled_jobs"])
        self.assertEqual("cancelled", self.app.get_job(job["job_id"])["execution_status"])
        concept["prompt"] = "Try a second draw."
        with self.assertRaisesRegex(WorkbenchError, "hard-stopped"):
            self.app.create_job(self.project["project_id"], concept)

    def test_concept_only_output_cannot_enter_candidate_registry(self) -> None:
        job, _ = self.app.create_job(
            self.project["project_id"],
            {
                "slot_key": "CONCEPT-01",
                "execution_mode": "manual_import",
                "operation": "generate",
                "prompt": "Explore composition only.",
                "expected_output": {"format": "png", "aspect_ratio": "1:1"},
                "production": {"requested_route": "concept_only", "exact_product_required": False},
            },
        )
        output = self.base / "concept.png"
        Image.new("RGB", (64, 64), (220, 220, 220)).save(output)
        asset = self.app.import_result(job["job_id"], output)
        self.app.evaluate_asset(asset["asset_id"], "passed", "Concept quality passed.")
        with self.assertRaisesRegex(WorkbenchError, "cannot be registered"):
            self.app.nominate_candidate(asset["asset_id"])


if __name__ == "__main__":
    unittest.main()
