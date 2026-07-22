from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

from workbench.core import Workbench
from workbench.util import WorkbenchError


def make_png(path: Path, rgb: tuple[int, int, int]) -> Path:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    image.paste((*rgb, 255), (4, 4, 60, 60))
    image.save(path)
    return path


class P2OptimizeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "codex-image-workbench"
        self.registry = self.base / "asset-registry.json"
        self.registry.write_text(json.dumps({"schema_version": "1.0", "assets": []}), encoding="utf-8")
        registryctl = Path(__file__).resolve().parents[2] / "skills" / "asset-curator" / "scripts" / "registryctl.py"
        self.app = Workbench(self.root, registry_path=self.registry, registryctl_path=registryctl)
        self.project = self.app.create_project(
            {
                "name": "P2 Optimize Test",
                "project_mode": "optimize",
                "brand": "Halorient",
                "sku": "PH204",
                "marketplace": "AE",
            }
        )["project"]
        self.current = make_png(self.base / "current-main.png", (240, 240, 240))
        self.front = make_png(self.base / "product-front.png", (30, 35, 40))
        self.side = make_png(self.base / "product-side.png", (40, 45, 50))
        self.voc = self.base / "voc.md"
        self.voc.write_text("Stability and compatibility are recurring review themes.", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def intake(self, complete: bool = True) -> dict:
        listing_image = {
            "slot_key": "MAIN",
            "path": str(self.current) if complete else "",
            "url": "https://example.com/current-main.jpg",
            "source": "listing-capture",
            "captured_at": "2026-07-15",
        }
        return {
            "schema_version": "p2-intake.1",
            "source": {"workflow_root": str(self.base), "snapshot_source": "fixture"},
            "listing": {
                "asin": "B0FM7HMMZW",
                "url": "https://www.amazon.ae/dp/B0FM7HMMZW",
                "marketplace": "AE",
                "launched_at": "2025-10-08",
                "captured_at": "2026-07-15",
                "title": "Carbon Steel Phone Stand for Desk",
                "bullets": ["900g load capacity", "Three pivots"],
                "description": "Foldable desktop holder.",
                "image_set_complete": complete,
                "images": [listing_image],
            },
            "product": {
                "name": "Desktop phone stand",
                "category": "Cell phone stands",
                "facts": [
                    {
                        "fact_id": "fact-load",
                        "label": "Load capacity",
                        "value": "900g",
                        "status": "locked",
                        "required_for_visual": True,
                        "source": "product facts",
                    },
                    {
                        "fact_id": "fact-material",
                        "label": "Material",
                        "value": "Carbon steel and silicone",
                        "status": "locked",
                        "required_for_visual": True,
                        "source": "product facts",
                    },
                ],
                "must_show": ["Three rotation points"],
                "must_not_show": ["Invented accessories"],
            },
            "claims": [
                {
                    "claim_id": "claim-load",
                    "text": "Supports up to 900g",
                    "status": "allowed",
                    "evidence": "fact-load",
                }
            ],
            "references": [
                {
                    "reference_id": "ref-front",
                    "path": str(self.front),
                    "role": "product",
                    "view": "front",
                    "approved": True,
                },
                {
                    "reference_id": "ref-side",
                    "path": str(self.side),
                    "role": "product",
                    "view": "side",
                    "approved": True,
                },
            ],
            "evidence_sources": [
                {
                    "source_id": "voc-us",
                    "type": "VOC",
                    "status": "directional",
                    "market": "US",
                    "path": str(self.voc),
                    "note": "Directional only for UAE.",
                }
            ],
            "competitors": [
                {
                    "competitor_id": "comp-1",
                    "name": "Competitor",
                    "asin_or_url": "B000COMP",
                    "image_paths": [],
                }
            ],
            "baseline": {
                "observations": [
                    {
                        "observation_key": "sorftime-2026-05",
                        "period_start": "2026-05-01",
                        "period_end": "2026-05-31",
                        "source": "sorftime",
                        "source_class": "external_estimate",
                        "metrics": {"sales": 5, "price": 33.64, "rank": 6686},
                    },
                    {
                        "observation_key": "sorftime-2026-06",
                        "period_start": "2026-06-01",
                        "period_end": "2026-06-30",
                        "source": "sorftime",
                        "source_class": "external_estimate",
                        "metrics": {"sales": 5, "price": 32.54, "rank": 12508},
                    },
                ],
                "events": [],
            },
            "requirements": {
                "require_complete_listing_images": True,
                "min_product_references": 2,
                "min_baseline_periods": 2,
            },
        }

    def diagnosis(self) -> dict:
        return {
            "issues": [
                {
                    "issue_id": "issue-main-accuracy",
                    "area": "image",
                    "severity": "high",
                    "confidence": "medium",
                    "finding": "Current MAIN may not clearly match the verified product geometry.",
                    "hypothesis": "A more accurate and larger product rendering can improve qualified clicks.",
                    "evidence_refs": ["listing:MAIN", "ref-front", "fact-material"],
                    "target_metrics": ["cvr", "sales"],
                }
            ],
            "priority_issue_ids": ["issue-main-accuracy"],
            "non_image_risks": ["Traffic decline may also affect sales."],
            "confounders": ["Price and coupon changes."],
            "evidence_limitations": ["US VOC is directional for UAE."],
        }

    def contracts(self, mode: str = "manual_import") -> dict:
        return {
            "contracts": [
                {
                    "challenge_key": "main-accuracy-v1",
                    "issue_id": "issue-main-accuracy",
                    "slot_key": "MAIN",
                    "baseline_slot_key": "MAIN",
                    "execution_mode": mode,
                    "operation": "generate",
                    "prompt": "Create a white-background MAIN image using the exact PH204 product references.",
                    "change_only": "Increase product scale and correct the product geometry.",
                    "reference_ids": ["ref-front", "ref-side"],
                    "claim_ids": [],
                    "acceptance": ["Exact stand geometry", "Pure white background", "No added accessories"],
                    "target_metrics": ["sales", "cvr"],
                    "observation_days": 14,
                    "production": {
                        "requested_route": "deterministic",
                        "target_view": "front",
                        "product_source_id": "ref-front",
                    },
                }
            ]
        }

    def approve_diagnosis(self, complete: bool = True) -> dict:
        project_id = self.project["project_id"]
        self.app.import_optimization_intake(project_id, self.intake(complete))
        self.app.save_optimization_diagnosis(project_id, self.diagnosis())
        return self.app.decide_optimization_gate(project_id, "approved", {"note": "approved"})

    def test_incomplete_listing_set_allows_diagnosis_but_blocks_queue(self) -> None:
        workspace = self.approve_diagnosis(False)
        self.assertEqual("passed", workspace["readiness"]["diagnosis_status"])
        self.assertEqual("blocked", workspace["readiness"]["generation_status"])
        workspace = self.app.save_optimization_contracts(self.project["project_id"], self.contracts())
        self.assertEqual("blocked", workspace["contracts"][0]["status"])
        with self.assertRaises(WorkbenchError):
            self.app.queue_optimization_contracts(self.project["project_id"])

        complete_project = self.app.create_project(
            {
                "name": "P2 Listing Media Test",
                "project_mode": "optimize",
                "brand": "Halorient",
                "sku": "PH204-MEDIA",
                "marketplace": "AE",
            }
        )["project"]
        self.app.import_optimization_intake(complete_project["project_id"], self.intake(True))
        self.assertEqual(
            self.current.resolve(),
            self.app.get_optimization_listing_image_path(complete_project["project_id"], "main").resolve(),
        )

    def test_baseline_observation_is_idempotent_and_preserves_open_contract(self) -> None:
        project_id = self.project["project_id"]
        self.approve_diagnosis(True)
        self.app.save_optimization_contracts(project_id, self.contracts())
        workspace = self.app.queue_optimization_contracts(project_id)
        listing_version_id = workspace["listing_version"]["listing_version_id"]
        contract_id = workspace["contracts"][0]["optimization_contract_id"]
        payload = {
            "period_start": "2026-07-01",
            "period_end": "2026-07-21",
            "source": "sorftime",
            "source_class": "external_estimate",
            "metrics": {"sales": 5, "price": 27.44, "rank": 10910},
            "note": "Partial month snapshot through 2026-07-21.",
        }

        self.app.add_optimization_baseline_observation(project_id, payload)
        workspace = self.app.add_optimization_baseline_observation(project_id, payload)
        matching = [
            item
            for item in workspace["observations"]
            if item["period_end"] == "2026-07-21" and item["source"] == "sorftime"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("before", matching[0]["phase"])
        self.assertEqual(3, workspace["readiness"]["metrics"]["baseline_periods"])
        self.assertEqual(listing_version_id, workspace["listing_version"]["listing_version_id"])
        contract = next(item for item in workspace["contracts"] if item["optimization_contract_id"] == contract_id)
        self.assertEqual("queued", contract["status"])

        conflicting = dict(payload)
        conflicting["metrics"] = {"sales": 6, "price": 27.44, "rank": 10910}
        with self.assertRaisesRegex(WorkbenchError, "different evidence"):
            self.app.add_optimization_baseline_observation(project_id, conflicting)

    def test_release_records_publish_time_and_inconclusive_evaluation(self) -> None:
        project_id = self.project["project_id"]
        self.approve_diagnosis(True)
        self.app.save_optimization_contracts(project_id, self.contracts())
        workspace = self.app.queue_optimization_contracts(project_id)
        job = workspace["queued_jobs"][0]
        asset = self.app.import_result(job["job_id"], self.current)
        published_at = datetime.fromisoformat(asset["created_at"]).astimezone(
            timezone(timedelta(hours=4))
        ).isoformat()
        self.app.evaluate_asset(asset["asset_id"], "passed", "Matches the approved challenge contract.")
        preflight = self.app.get_optimization_release_preflight(
            project_id,
            workspace["contracts"][0]["optimization_contract_id"],
            asset["asset_id"],
        )
        self.assertFalse(preflight["ready"])
        with self.assertRaisesRegex(WorkbenchError, "approved in the central Registry"):
            self.app.record_optimization_release(
                project_id,
                {
                    "optimization_contract_id": workspace["contracts"][0]["optimization_contract_id"],
                    "asset_id": asset["asset_id"],
                    "published_at": published_at,
                },
            )
        self.app.nominate_candidate(asset["asset_id"])
        self.app.promote_registry_asset(
            asset["asset_id"],
            "approved",
            "user",
            "2026-07-20",
            "decisions/test-release.md",
        )
        preflight = self.app.get_optimization_release_preflight(
            project_id,
            workspace["contracts"][0]["optimization_contract_id"],
            asset["asset_id"],
        )
        self.assertTrue(preflight["ready"])
        self.assertEqual("MAIN", preflight["rollback_target"]["slot_key"])
        with self.assertRaisesRegex(WorkbenchError, "explicit timezone"):
            self.app.record_optimization_release(
                project_id,
                {
                    "optimization_contract_id": workspace["contracts"][0]["optimization_contract_id"],
                    "asset_id": asset["asset_id"],
                    "published_at": published_at[:19],
                },
            )
        workspace = self.app.record_optimization_release(
            project_id,
            {
                "optimization_contract_id": workspace["contracts"][0]["optimization_contract_id"],
                "asset_id": asset["asset_id"],
                "published_at": published_at,
                "note": "MAIN only",
            },
        )
        release = workspace["releases"][0]
        self.assertEqual(published_at, release["published_at"])
        self.app.add_optimization_observation(
            project_id,
            release["release_id"],
            {
                "period_start": "2026-07-21",
                "period_end": "2026-08-03",
                "source": "sorftime",
                "source_class": "external_estimate",
                "metrics": {"sales": 8, "price": 26.99, "rank": 9000},
            },
        )
        workspace = self.app.add_optimization_interference_event(
            project_id,
            {
                "release_id": release["release_id"],
                "event_type": "coupon",
                "status": "open",
                "started_at": "2026-07-25",
                "description": "Coupon changed during observation window.",
                "source": "manual",
            },
        )
        with self.assertRaises(WorkbenchError):
            self.app.evaluate_optimization_release(
                project_id,
                release["release_id"],
                {"decision": "keep", "rationale": "Sales increased."},
            )
        workspace = self.app.evaluate_optimization_release(
            project_id,
            release["release_id"],
            {"decision": "inconclusive", "rationale": "Coupon change prevents attribution."},
        )
        self.assertEqual("inconclusive", workspace["evaluations"][0]["decision"])
        event_id = workspace["interference_events"][0]["interference_event_id"]
        self.app.resolve_optimization_interference_event(
            project_id, event_id, "2026-08-03", actor="test"
        )
        workspace = self.app.evaluate_optimization_release(
            project_id,
            release["release_id"],
            {"decision": "keep", "rationale": "The event is closed and comparable sales improved."},
        )
        self.assertEqual("kept", workspace["releases"][0]["status"])
        self.assertEqual(3, len(workspace["evaluations"][0]["evidence"]["comparable_metrics"]))

    def test_open_challenge_is_cancelled_by_snapshot_revision(self) -> None:
        project_id = self.project["project_id"]
        self.approve_diagnosis(True)
        self.app.save_optimization_contracts(project_id, self.contracts("manual_import"))
        self.app.queue_optimization_contracts(project_id)
        self.app.import_optimization_intake(project_id, self.intake(True))
        self.assertEqual("cancelled", self.app.list_jobs(project_id)[0]["execution_status"])


if __name__ == "__main__":
    unittest.main()
