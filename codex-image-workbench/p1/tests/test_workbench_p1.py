import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import workbench_p1 as wb


class WorkbenchP1Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "state" / "test.sqlite"
        wb.init_db(self.db, self.root)
        self.conn = wb.connect(self.db)
        self.contract = {
            "project_id": "test-project",
            "brand": "Test Brand",
            "sku": "SKU-1",
            "kind": "listing-image",
            "slot": "PT01",
            "operation": "generate",
            "prompt": "A plain test image",
            "references": [],
            "invariants": ["one subject"],
            "avoid": ["text"],
            "acceptance": ["one subject is visible"],
        }

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def make_result(self, name="result.png", content=b"fake-png-content"):
        path = self.root / name
        path.write_bytes(content)
        return path

    def test_idempotent_create_and_complete(self):
        first, created = wb.create_job(self.conn, self.contract, "codex_auto", None, 3)
        second, created_again = wb.create_job(self.conn, self.contract, "codex_auto", None, 3)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first["job_id"], second["job_id"])

        claimed = wb.claim_job(self.conn, "worker-1", 60)
        self.assertEqual(first["job_id"], claimed["job_id"])
        completed = wb.complete_job(
            self.conn, claimed["job_id"], "worker-1", self.make_result()
        )
        self.assertEqual("succeeded", completed["status"])
        self.assertTrue(Path(completed["output_path"]).is_file())

        repeated = wb.complete_job(
            self.conn, claimed["job_id"], "worker-1", self.make_result()
        )
        self.assertEqual(completed["output_path"], repeated["output_path"])

    def test_expired_lease_is_reclaimed_by_new_worker(self):
        job, _ = wb.create_job(self.conn, self.contract, "codex_auto", "lease-test", 3)
        wb.claim_job(self.conn, "worker-old", 60)
        expired = wb.iso(wb.utcnow() - timedelta(seconds=1))
        self.conn.execute(
            "UPDATE jobs SET lease_expires_at = ? WHERE job_id = ?", (expired, job["job_id"])
        )
        self.conn.commit()

        reclaimed = wb.claim_job(self.conn, "worker-new", 60)
        self.assertEqual(job["job_id"], reclaimed["job_id"])
        self.assertEqual("worker-new", reclaimed["lease_owner"])
        self.assertEqual(2, reclaimed["attempts"])
        events = self.conn.execute(
            "SELECT event_type FROM events WHERE job_id = ? ORDER BY event_id", (job["job_id"],)
        ).fetchall()
        self.assertIn("lease.expired", [event["event_type"] for event in events])

    def test_wrong_worker_cannot_complete(self):
        job, _ = wb.create_job(self.conn, self.contract, "codex_auto", "owner-test", 3)
        wb.claim_job(self.conn, "worker-owner", 60)
        with self.assertRaises(wb.WorkbenchError):
            wb.complete_job(self.conn, job["job_id"], "worker-other", self.make_result())

    def test_manual_package_and_import_keep_lineage(self):
        contract = dict(self.contract)
        contract["parent_asset_id"] = "asset-parent-1"
        reference = self.make_result("reference.png", b"reference-bytes")
        contract["references"] = [{"path": str(reference), "role": "product-main"}]
        job, _ = wb.create_job(self.conn, contract, "manual_import", "manual-test", 3)
        package = wb.export_package(self.conn, job["job_id"], self.root / "packages")
        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(job["asset_id"], manifest["asset_id"])
        self.assertEqual("asset-parent-1", manifest["parent_asset_id"])
        self.assertEqual("PT01", manifest["slot"])
        self.assertEqual("product-main", manifest["packaged_references"][0]["role"])
        self.assertTrue(
            (package / manifest["packaged_references"][0]["package_path"]).is_file()
        )

        imported = wb.import_result(self.conn, job["job_id"], self.make_result("manual.png"))
        self.assertEqual("succeeded", imported["status"])
        self.assertEqual("asset-parent-1", imported["parent_asset_id"])
        self.assertIsNotNone(imported["output_sha256"])

    def test_failed_job_obeys_retry_limit(self):
        job, _ = wb.create_job(self.conn, self.contract, "codex_auto", "retry-test", 1)
        wb.claim_job(self.conn, "worker-1", 60)
        failed = wb.fail_job(self.conn, job["job_id"], "worker-1", "test failure", True)
        self.assertEqual("failed", failed["status"])
        self.assertEqual("test failure", failed["error"])


if __name__ == "__main__":
    unittest.main()
