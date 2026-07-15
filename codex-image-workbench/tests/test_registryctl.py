import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REGISTRYCTL_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "asset-curator"
    / "scripts"
    / "registryctl.py"
)
SPEC = importlib.util.spec_from_file_location("registryctl", REGISTRYCTL_PATH)
registryctl = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(registryctl)


class RegistryCtlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / "registry.json"
        self.registry.write_text(
            json.dumps({"schema_version": "1.0", "updated_at": "2026-07-15", "assets": []}),
            encoding="utf-8",
        )
        self.source = self.root / "asset.png"
        self.source.write_bytes(b"registry-fixture")
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "asset_id": "wb-test-asset-001",
                    "kind": "listing-image",
                    "status": "candidate",
                    "source_path": str(self.source),
                    "sha256": registryctl.sha256_file(self.source),
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_atomic_candidate_and_promotion(self):
        result = registryctl.register_candidate(self.registry, self.manifest)
        self.assertTrue(result["created"])
        repeat = registryctl.register_candidate(self.registry, self.manifest)
        self.assertFalse(repeat["created"])
        promoted = registryctl.promote(
            self.registry,
            "wb-test-asset-001",
            "approved",
            "user",
            "2026-07-15",
            "decisions/test.md",
        )
        self.assertEqual("approved", promoted["to"])
        self.assertEqual([], registryctl.validate(registryctl.load_registry(self.registry), True))

    def test_hash_mismatch_is_rejected(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["sha256"] = "0" * 64
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(registryctl.RegistryError):
            registryctl.register_candidate(self.registry, self.manifest)


if __name__ == "__main__":
    unittest.main()
