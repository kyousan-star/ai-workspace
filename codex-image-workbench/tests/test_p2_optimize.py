from __future__ import annotations

import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from workbench.core import Workbench
from workbench.util import WorkbenchError


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def make_png(path: Path, rgb: tuple[int, int, int]) -> Path:
    width = height = 64
    raw = (b"\x00" + bytes(rgb) * width) * height
    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(raw))
    payload += png_chunk(b"IEND", b"")
    path.write_bytes(payload)
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

    def test_release_records_publish_time_and_inconclusive_evaluation(self) -> None:
        project_id = self.project["project_id"]
        self.approve_diagnosis(True)
        self.app.save_optimization_contracts(project_id, self.contracts())
        workspace = self.app.queue_optimization_contracts(project_id)
        job = workspace["queued_jobs"][0]
        asset = self.app.import_result(job["job_id"], self.current)
        self.app.evaluate_asset(asset["asset_id"], "passed", "Matches the approved challenge contract.")
        workspace = self.app.record_optimization_release(
            project_id,
            {
                "optimization_contract_id": workspace["contracts"][0]["optimization_contract_id"],
                "asset_id": asset["asset_id"],
                "published_at": "2026-07-20T13:30:00+04:00",
                "note": "MAIN only",
            },
        )
        release = workspace["releases"][0]
        self.assertEqual("2026-07-20T13:30:00+04:00", release["published_at"])
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

    def test_leased_challenge_blocks_snapshot_revision(self) -> None:
        project_id = self.project["project_id"]
        self.approve_diagnosis(True)
        self.app.save_optimization_contracts(project_id, self.contracts("codex_auto"))
        self.app.queue_optimization_contracts(project_id)
        leased = self.app.claim_job("p2-test-worker", lease_seconds=60)
        self.assertEqual("leased", leased["execution_status"])
        with self.assertRaises(WorkbenchError):
            self.app.import_optimization_intake(project_id, self.intake(True))


if __name__ == "__main__":
    unittest.main()
