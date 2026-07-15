import hashlib
import json
import struct
import tempfile
import unittest
import zlib
from datetime import timedelta
from pathlib import Path

from workbench.core import Workbench
from workbench.util import WorkbenchError, iso, utcnow


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def make_png(path: Path, width: int, height: int, rgb=(230, 230, 230)) -> Path:
    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(raw))
    payload += png_chunk(b"IEND", b"")
    path.write_bytes(payload)
    return path


class WorkbenchCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "codex-image-workbench"
        self.root.mkdir()
        self.registry = Path(self.temp.name) / "asset-registry.json"
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
        self.app = Workbench(
            self.root,
            registry_path=self.registry,
            registryctl_path=registryctl,
        )
        self.project = self.app.create_project(
            {
                "name": "P0 Test",
                "project_mode": "launch",
                "brand": "VLOGARA",
                "sku": "TEST-1",
                "marketplace": "US",
            }
        )["project"]

    def tearDown(self):
        self.temp.cleanup()

    def job_payload(self, mode="manual_import", operation="generate", parent=None):
        return {
            "slot_key": "PT01",
            "execution_mode": mode,
            "operation": operation,
            "parent_asset_id": parent,
            "prompt": "One test object on white",
            "invariants": ["one object"],
            "avoid": ["text"],
            "acceptance": ["square image"],
            "expected_output": {"format": "png", "aspect_ratio": "1:1"},
        }

    def test_manual_import_qc_candidate_and_parent_version(self):
        job, created = self.app.create_job(self.project["project_id"], self.job_payload())
        self.assertTrue(created)
        source = make_png(Path(self.temp.name) / "square.png", 64, 64)
        asset = self.app.import_result(job["job_id"], source)
        self.assertEqual("passed", asset["technical_status"])
        self.assertEqual("not_run", asset["qc_status"])

        asset = self.app.evaluate_asset(asset["asset_id"], "passed", "fixture accepted")
        self.assertEqual("passed", asset["qc_status"])
        asset = self.app.nominate_candidate(asset["asset_id"])
        self.assertEqual("candidate", asset["registry_status"])

        registry = json.loads(self.registry.read_text(encoding="utf-8"))
        self.assertEqual(asset["asset_id"], registry["assets"][0]["asset_id"])
        self.assertEqual("candidate", registry["assets"][0]["status"])

        edit_payload = self.job_payload("manual_import", "edit", asset["asset_id"])
        edit_payload["prompt"] = "Change only the background"
        edit_job, _ = self.app.create_job(self.project["project_id"], edit_payload)
        self.assertEqual(asset["asset_id"], edit_job["parent_asset_id"])

    def test_technical_failure_cannot_pass_qc(self):
        job, _ = self.app.create_job(self.project["project_id"], self.job_payload())
        source = make_png(Path(self.temp.name) / "wide.png", 80, 40)
        asset = self.app.import_result(job["job_id"], source)
        self.assertEqual("failed", asset["technical_status"])
        with self.assertRaises(WorkbenchError):
            self.app.evaluate_asset(asset["asset_id"], "passed", "should fail")

    def test_auto_job_lease_recovery_and_completion(self):
        payload = self.job_payload("codex_auto")
        job, _ = self.app.create_job(self.project["project_id"], payload)
        claimed = self.app.claim_job("worker-a", 60)
        self.assertEqual(job["job_id"], claimed["job_id"])
        with self.app.connect() as conn:
            conn.execute(
                "UPDATE jobs SET lease_expires_at = ? WHERE job_id = ?",
                (iso(utcnow() - timedelta(seconds=1)), job["job_id"]),
            )
        reclaimed = self.app.claim_job("worker-b", 60)
        self.assertEqual("worker-b", reclaimed["lease_owner"])
        self.assertEqual(2, reclaimed["attempts"])
        source = make_png(Path(self.temp.name) / "auto.png", 64, 64, (20, 120, 80))
        asset = self.app.complete_job(job["job_id"], "worker-b", source)
        self.assertEqual("passed", asset["technical_status"])
        self.assertEqual("succeeded", self.app.get_job(job["job_id"])["execution_status"])

    def test_idempotent_job_creation(self):
        first, created = self.app.create_job(self.project["project_id"], self.job_payload())
        second, created_again = self.app.create_job(self.project["project_id"], self.job_payload())
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first["job_id"], second["job_id"])


if __name__ == "__main__":
    unittest.main()
