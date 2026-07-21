from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT.parent / "plugins" / "codex-image-workbench"


def decode_result(result: object) -> object:
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        if isinstance(structured, dict) and "result" in structured and len(structured) == 1:
            return structured["result"]
        return structured
    content = getattr(result, "content", [])
    if not content:
        return None
    return json.loads(content[0].text)


class MCPServerTests(unittest.TestCase):
    def test_stdio_tools_share_the_workbench_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workbench_root = Path(tmp) / "workbench"
            workbench_root.mkdir()
            env = os.environ.copy()
            env["CODEX_IMAGE_WORKBENCH_ROOT"] = str(workbench_root)
            plugin_config = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
            server_config = plugin_config["mcpServers"]["codex-image-workbench"]
            server_cwd = (PLUGIN_ROOT / server_config["cwd"]).resolve()
            self.assertEqual(server_cwd, ROOT.resolve())

            async def scenario() -> None:
                params = StdioServerParameters(
                    command=server_config["command"],
                    args=server_config["args"],
                    cwd=str(server_cwd),
                    env=env,
                )
                async with stdio_client(params) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        names = {tool.name for tool in tools.tools}
                        self.assertIn("claim_generation_job", names)
                        self.assertIn("evaluate_asset", names)
                        self.assertIn("register_candidate", names)
                        self.assertIn("promote_registry_asset", names)
                        self.assertIn("reject_registry_asset", names)
                        self.assertIn("preflight_optimization_release", names)
                        self.assertIn("preflight_production_route", names)
                        self.assertIn("run_deterministic_production", names)
                        self.assertIn("record_production_failure", names)
                        self.assertEqual(40, len(names))
                        self.assertTrue(
                            {
                                "import_launch_intake",
                                "get_launch_workspace",
                                "save_launch_strategy",
                                "decide_launch_gate",
                                "save_launch_sequence",
                                "save_image_contracts",
                                "queue_image_contracts",
                            }.issubset(names)
                        )
                        self.assertTrue(
                            {
                                "import_optimization_intake",
                                "get_optimization_workspace",
                                "save_optimization_diagnosis",
                                "decide_optimization_gate",
                                "save_optimization_contracts",
                                "queue_optimization_contracts",
                                "record_optimization_release",
                                "add_optimization_observation",
                                "add_optimization_interference_event",
                                "resolve_optimization_interference_event",
                                "evaluate_optimization_release",
                            }.issubset(names)
                        )

                        health = decode_result(await session.call_tool("workbench_health"))
                        self.assertTrue(health["ok"])
                        self.assertEqual(Path(health["root"]).resolve(), workbench_root.resolve())

                        created = decode_result(
                            await session.call_tool(
                                "create_project",
                                {
                                    "name": "MCP Test",
                                    "project_mode": "launch",
                                    "brand": "VLOGARA",
                                    "sku": "MCP-1",
                                    "marketplace": "US",
                                },
                            )
                        )
                        project_id = created["project"]["project_id"]
                        job = decode_result(
                            await session.call_tool(
                                "create_generation_job",
                                {
                                    "project_id": project_id,
                                    "slot_key": "PT01",
                                    "prompt": "Create a square product image.",
                                },
                            )
                        )
                        self.assertTrue(job["created"])

                        claimed = decode_result(
                            await session.call_tool(
                                "claim_generation_job",
                                {"worker": "mcp-test-worker", "lease_seconds": 60},
                            )
                        )
                        self.assertEqual(claimed["job"]["job_id"], job["job"]["job_id"])

            anyio.run(scenario)


if __name__ == "__main__":
    unittest.main()
