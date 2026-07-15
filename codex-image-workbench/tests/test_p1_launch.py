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


class P1LaunchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "codex-image-workbench"
        self.registry = self.base / "asset-registry.json"
        self.registry.write_text(
            json.dumps({"schema_version": "1.0", "updated_at": "2026-07-15", "assets": []}),
            encoding="utf-8",
        )
        registryctl = (
            Path(__file__).resolve().parents[2]
            / "skills"
            / "asset-curator"
            / "scripts"
            / "registryctl.py"
        )
        self.app = Workbench(self.root, registry_path=self.registry, registryctl_path=registryctl)
        self.project = self.app.create_project(
            {
                "name": "P1 Launch Test",
                "project_mode": "launch",
                "brand": "VLOGARA",
                "sku": "P1-TEST",
                "marketplace": "US",
            }
        )["project"]
        self.front = make_png(self.base / "front.png", (220, 220, 220))
        self.side = make_png(self.base / "side.png", (200, 220, 210))
        self.rear = make_png(self.base / "rear.png", (210, 200, 220))
        self.competitor = make_png(self.base / "competitor.png", (170, 180, 190))
        self.listing = self.base / "competitor-listing.txt"
        self.listing.write_text("Competitor listing fixture", encoding="utf-8")
        self.brand_dir = self.base / "brand-system"
        self.brand_dir.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def intake(self, complete: bool = True) -> dict:
        references = [
            {
                "reference_id": "ref-front",
                "path": str(self.front),
                "role": "product",
                "view": "front",
                "approved": True,
                "visible_features": ["front logo"],
            }
        ]
        if complete:
            references.extend(
                [
                    {
                        "reference_id": "ref-side",
                        "path": str(self.side),
                        "role": "product",
                        "view": "side",
                        "approved": True,
                        "visible_features": ["side profile"],
                    },
                    {
                        "reference_id": "ref-rear",
                        "path": str(self.rear),
                        "role": "product",
                        "view": "rear",
                        "approved": True,
                        "visible_features": ["rear label"],
                    },
                ]
            )
        return {
            "schema_version": "p1-intake.1",
            "source": {"workflow_root": str(self.base)},
            "product": {
                "name": "Ceramic Planter",
                "category": "Planters",
                "facts": [
                    {
                        "fact_id": "fact-material",
                        "label": "Material",
                        "value": "Ceramic",
                        "status": "locked" if complete else "pending",
                        "required_for_visual": True,
                        "source": "product_facts_locked.md",
                    },
                    {
                        "fact_id": "fact-color",
                        "label": "Color",
                        "value": "Matte white",
                        "status": "locked",
                        "required_for_visual": True,
                        "source": "approved references",
                    },
                ],
                "must_show": ["Single drainage opening"],
                "must_not_show": ["Extra accessories"],
            },
            "claims": [
                {
                    "claim_id": "claim-matte",
                    "text": "Matte ceramic finish",
                    "status": "allowed",
                    "evidence": "fact-material and approved product references",
                    "selected_for_images": True,
                }
            ],
            "selling_points": [
                {
                    "selling_point_id": "sp-finish",
                    "text": "Refined matte finish",
                    "status": "locked",
                    "evidence": ["approved product references"],
                    "visualizability": "high",
                },
                {
                    "selling_point_id": "sp-shape",
                    "text": "Balanced cylindrical silhouette",
                    "status": "candidate",
                    "evidence": ["front and side references"],
                    "visualizability": "high",
                },
            ],
            "references": references,
            "competitors": [
                {
                    "competitor_id": "comp-1",
                    "name": "Fixture Competitor",
                    "asin_or_url": "B000FIXTURE",
                    "role": "direct",
                    "listing_path": str(self.listing),
                    "image_paths": [str(self.competitor)],
                }
            ],
            "brand": {
                "status": "approved" if complete else "draft",
                "system_path": str(self.brand_dir),
                "invariants": ["Quiet editorial styling"],
                "avoid": ["Neon colors"],
            },
            "coverage_requirements": {
                "min_product_images": 3,
                "required_views": ["front", "side", "rear"],
                "required_visible_features": ["front logo", "side profile", "rear label"],
                "require_approved_brand": True,
                "min_competitors": 1,
            },
        }

    def strategy(self) -> dict:
        return {
            "selling_point_order": ["sp-finish", "sp-shape"],
            "claim_ids": ["claim-matte"],
            "category_baselines": [
                {
                    "baseline_id": "baseline-scale",
                    "label": "Show product scale",
                    "required": True,
                    "source": "competitor Part 1",
                }
            ],
            "rejected_techniques": ["Exploded product view"],
            "competitive_pitfalls": ["Product shown too small"],
            "compliance_boundaries": ["Do not imply plant growth performance"],
            "visual_exclusions": ["No neon colors"],
        }

    def sequence(self) -> dict:
        return {
            "slots": [
                {
                    "slot_key": "PT01",
                    "position": 1,
                    "channel": "listing",
                    "selling_point_id": "sp-finish",
                    "task": "Show the exact finish and full product shape",
                    "output_method": "reference-led studio edit",
                    "required_views": ["front"],
                    "baseline_ids": [],
                },
                {
                    "slot_key": "PT02",
                    "position": 2,
                    "channel": "listing",
                    "selling_point_id": "sp-shape",
                    "task": "Establish scale and side depth",
                    "output_method": "reference-led lifestyle composite",
                    "required_views": ["side"],
                    "baseline_ids": ["baseline-scale"],
                },
            ]
        }

    def contracts(self) -> dict:
        return {
            "contracts": [
                {
                    "slot_key": "PT01",
                    "execution_mode": "codex_auto",
                    "operation": "generate",
                    "prompt": "Create a square reference-led studio image of the exact planter.",
                    "change_only": "Replace the background with clean light gray seamless paper.",
                    "reference_ids": ["ref-front"],
                    "claim_ids": ["claim-matte"],
                    "avoid": ["Text rendered by the image model"],
                    "acceptance": ["Exact cylindrical geometry", "Matte white finish remains unchanged"],
                },
                {
                    "slot_key": "PT02",
                    "execution_mode": "manual_import",
                    "operation": "generate",
                    "prompt": "Create a square lifestyle composite that preserves the exact planter side profile.",
                    "change_only": "Add a restrained indoor shelf context and one scale cue.",
                    "reference_ids": ["ref-side"],
                    "claim_ids": [],
                    "avoid": ["Extra drainage holes"],
                    "acceptance": ["Side depth matches reference", "Product remains the visual focus"],
                },
            ]
        }

    def test_missing_inputs_return_capture_requests_and_block_gate1(self) -> None:
        workspace = self.app.import_launch_intake(self.project["project_id"], self.intake(False))
        self.assertEqual("blocked", workspace["coverage"]["strategy_status"])
        self.assertEqual("blocked", workspace["coverage"]["generation_status"])
        requested = {item["key"] for item in workspace["coverage"]["capture_requests"]}
        self.assertIn("side", requested)
        self.assertIn("rear", requested)

        workspace = self.app.save_launch_strategy(self.project["project_id"], self.strategy())
        self.assertEqual("draft", workspace["strategy"]["status"])
        with self.assertRaises(WorkbenchError):
            self.app.decide_launch_gate(self.project["project_id"], "gate1", "approved")

        malformed = self.intake(False)
        malformed["coverage_requirements"]["min_competitors"] = "not-a-number"
        with self.assertRaises(WorkbenchError):
            self.app.import_launch_intake(self.project["project_id"], malformed)

    def test_complete_launch_package_reaches_shared_generation_queue(self) -> None:
        project_id = self.project["project_id"]
        workspace = self.app.import_launch_intake(project_id, self.intake(True))
        self.assertEqual("passed", workspace["coverage"]["status"])
        workspace = self.app.save_launch_strategy(project_id, self.strategy())
        self.assertEqual("awaiting_gate1", workspace["strategy"]["status"])
        workspace = self.app.decide_launch_gate(project_id, "gate1", "approved", {"note": "approved"})
        self.assertEqual("approved", workspace["gates"]["gate1"]["status"])

        workspace = self.app.save_launch_sequence(project_id, self.sequence())
        self.assertEqual("awaiting_gate2", workspace["sequence"]["status"])
        workspace = self.app.decide_launch_gate(project_id, "gate2", "approved", {"note": "approved"})
        self.assertEqual("approved", workspace["gates"]["gate2"]["status"])

        bad = self.contracts()
        bad["contracts"][0]["claim_ids"] = ["missing-claim"]
        with self.assertRaises(WorkbenchError):
            self.app.save_image_contracts(project_id, bad)

        workspace = self.app.save_image_contracts(project_id, self.contracts())
        self.assertEqual(["ready", "ready"], sorted(item["status"] for item in workspace["contracts"]))

        invalid_mode = self.contracts()
        invalid_mode["contracts"][0]["execution_mode"] = "unknown"
        with self.assertRaises(WorkbenchError):
            self.app.save_image_contracts(project_id, invalid_mode)

        workspace = self.app.queue_image_contracts(project_id)
        statuses = sorted(job["execution_status"] for job in workspace["queued_jobs"])
        self.assertEqual(["awaiting_import", "queued"], statuses)
        self.assertTrue(all(item["status"] == "queued" for item in workspace["contracts"]))

        refreshed = self.app.import_launch_intake(project_id, self.intake(True))
        self.assertEqual("pending", refreshed["gates"]["gate1"]["status"])
        self.assertIsNone(refreshed["strategy"])
        self.assertIsNone(refreshed["sequence"])
        cancelled = sorted(job["execution_status"] for job in self.app.list_jobs(project_id))
        self.assertEqual(["cancelled", "cancelled"], cancelled)

    def test_leased_contract_job_blocks_upstream_revision(self) -> None:
        project_id = self.project["project_id"]
        self.app.import_launch_intake(project_id, self.intake(True))
        self.app.save_launch_strategy(project_id, self.strategy())
        self.app.decide_launch_gate(project_id, "gate1", "approved")
        self.app.save_launch_sequence(project_id, self.sequence())
        self.app.decide_launch_gate(project_id, "gate2", "approved")
        self.app.save_image_contracts(project_id, self.contracts())
        self.app.queue_image_contracts(project_id)

        leased = self.app.claim_job("p1-test-worker", lease_seconds=60)
        self.assertEqual("leased", leased["execution_status"])
        with self.assertRaises(WorkbenchError):
            self.app.import_launch_intake(project_id, self.intake(True))


if __name__ == "__main__":
    unittest.main()
