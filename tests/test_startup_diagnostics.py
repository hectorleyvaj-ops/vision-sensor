import json
import tempfile
import unittest
from pathlib import Path

from core.diagnostics import DiagnosticsManager, run_static_diagnostics
from core.recipe_manager import RecipeManager
from core.system_config import SystemConfig
from core.traceability import CycleTraceWriter


class _FakeTool:
    pass


class StartupDiagnosticsTests(unittest.TestCase):
    def _write_installation(self, root, recipe_payload):
        root = Path(root)
        recipe_path = root / "recipes.json"
        recipe_path.write_text(json.dumps(recipe_payload), encoding="utf-8")
        base = json.loads(Path("config/system.json").read_text(encoding="utf-8"))
        base["recipes"]["file"] = str(recipe_path)
        base["controller"]["model_map"] = {}
        base["traceability"]["directory"] = str(root / "trace")
        config_path = root / "system.json"
        config_path.write_text(json.dumps(base), encoding="utf-8")
        return SystemConfig(config_path), RecipeManager(recipe_path)

    def test_missing_master_image_blocks_only_commissioned_recipe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            recipe = {
                "schema_version": 3,
                "recipes": [{
                    "id": "r1",
                    "name": "R1",
                    "selected": True,
                    "commissioned": True,
                    "focus": {"mode": "disabled", "enabled": False},
                    "steps": [{
                        "id": "hist_1",
                        "tool": "img_hist",
                        "enabled": True,
                        "required": True,
                        "condition": {"type": "always"},
                        "params": {
                            "roi": [0, 0, 10, 10],
                            "threshold": 80,
                            "template_paths": [str(Path(temp_dir) / "missing.png")],
                        },
                    }],
                }],
            }
            config, recipes = self._write_installation(temp_dir, recipe)
            trace = CycleTraceWriter.from_config(
                config.section("traceability"),
                installation_id="test",
            )
            manager = DiagnosticsManager(trace.diagnostics_path)
            report = run_static_diagnostics(
                manager,
                config,
                recipes,
                {"img_hist": _FakeTool()},
                trace,
                "windows",
            )
            resource = next(
                item for item in report["items"]
                if item["key"] == "recipe.resources.R1"
            )
            self.assertEqual(resource["status"], "ERROR")
            self.assertTrue(resource["blocking"])
            self.assertTrue(any(
                path.endswith("missing.png")
                for path in resource["details"]["missing_templates"]
            ))

    def test_dynamic_check_replaces_pending_state_and_persists_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "startup.json"
            manager = DiagnosticsManager(report_path)
            manager.update(
                "camera.runtime",
                "WARNING",
                "camera",
                "Pendiente",
            )
            manager.update(
                "camera.runtime",
                "PASS",
                "camera",
                "Camara lista",
                details={"actual_width": 1920},
            )
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            camera_items = [
                item for item in saved["items"]
                if item["key"] == "camera.runtime"
            ]
            self.assertEqual(len(camera_items), 1)
            self.assertEqual(camera_items[0]["status"], "PASS")
            self.assertEqual(camera_items[0]["details"]["actual_width"], 1920)


if __name__ == "__main__":
    unittest.main()
