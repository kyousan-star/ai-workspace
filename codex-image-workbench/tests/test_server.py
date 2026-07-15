import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from workbench.core import Workbench
from workbench.server import Handler


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "app"
        root.mkdir()
        registry = Path(self.temp.name) / "registry.json"
        registry.write_text(
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
        app = Workbench(root, registry_path=registry, registryctl_path=registryctl)
        static_root = Path(__file__).resolve().parents[1] / "workbench" / "static"
        handler = type("TestHandler", (Handler,), {"app": app, "static_root": static_root})
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, path, method="GET", body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = Request(
            self.base + path,
            method=method,
            data=data,
            headers={"Content-Type": "application/json"} if data else {},
        )
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())

    def test_health_project_and_dashboard(self):
        status, health = self.request("/api/health")
        self.assertEqual(200, status)
        self.assertTrue(health["ok"])
        status, project = self.request(
            "/api/projects",
            "POST",
            {
                "name": "HTTP Test",
                "project_mode": "launch",
                "brand": "VLOGARA",
                "sku": "HTTP-1",
                "marketplace": "US",
            },
        )
        self.assertEqual(201, status)
        self.assertEqual("HTTP Test", project["project"]["name"])
        _, dashboard = self.request("/api/dashboard")
        self.assertEqual(1, dashboard["counts"]["active_projects"])


if __name__ == "__main__":
    unittest.main()
