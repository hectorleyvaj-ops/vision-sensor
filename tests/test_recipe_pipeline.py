import json
import tempfile
import unittest
from pathlib import Path

from core.recipe_manager import RecipeManager
from processing.pipeline import VisionPipeline
from tools.result import ToolResult


class SuccessfulTool:
    def __init__(self):
        self.calls = 0

    def run(self, **kwargs):
        self.calls += 1
        return ToolResult(
            success=True,
            tool_name="fake",
            data={"call": self.calls},
        )


class RecipeAndPipelineTests(unittest.TestCase):
    def test_legacy_duplicate_tools_receive_unique_step_ids(self):
        payload = {
            "recipes": [
                {
                    "name": "LEGACY",
                    "selected": True,
                    "steps": [
                        {"tool": "fake", "params": {}},
                        {"tool": "fake", "params": {}},
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "recipes.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            manager = RecipeManager(str(path))
            recipe = manager.get_selected()

        self.assertEqual(
            [step["id"] for step in recipe["steps"]],
            ["fake_1", "fake_2"],
        )

        pipeline = VisionPipeline({"fake": SuccessfulTool()})
        context = {}
        response = pipeline.run(recipe, context)

        self.assertTrue(response["success"])
        self.assertEqual(response["execution_order"], ["fake_1", "fake_2"])
        self.assertEqual(set(response["results"]), {"fake_1", "fake_2"})
        self.assertEqual(len(context["outputs_by_tool"]["fake"]), 2)

    def test_legacy_recipe_is_migrated_to_universal_schema(self):
        payload = {
            "recipes": [
                {
                    "name": "LEGACY",
                    "selected": True,
                    "steps": [
                        {
                            "tool": "fake",
                            "params": {"required": False},
                        }
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "recipes.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            manager = RecipeManager(str(path), auto_migrate=True)
            recipe = manager.get_selected()
            migrated = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(migrated["schema_version"], 3)
        self.assertEqual(recipe["id"], "legacy")
        self.assertEqual(recipe["steps"][0]["id"], "fake_1")
        self.assertFalse(recipe["steps"][0]["required"])
        self.assertEqual(
            recipe["steps"][0]["condition"],
            {"type": "always"},
        )
        self.assertNotIn("required", recipe["steps"][0]["params"])

    def test_empty_pipeline_never_passes(self):
        response = VisionPipeline({}).run({"steps": []}, {})
        self.assertFalse(response["success"])
        self.assertIn("no contiene herramientas", response["errors"][0])

    def test_step_condition_can_skip_a_tool(self):
        recipe = {
            "steps": [
                {
                    "id": "only_model_b",
                    "tool": "fake",
                    "enabled": True,
                    "required": True,
                    "condition": {
                        "type": "context_equals",
                        "path": "model",
                        "value": "B",
                    },
                    "params": {},
                }
            ]
        }

        response = VisionPipeline({"fake": SuccessfulTool()}).run(
            recipe,
            {"model": "A"},
        )

        self.assertFalse(response["success"])
        self.assertEqual(response["skipped_steps"], ["only_model_b"])

    def test_step_success_must_reference_a_previous_step(self):
        recipe = {
            "id": "bad_order",
            "name": "BAD_ORDER",
            "selected": False,
            "commissioned": False,
            "steps": [
                {
                    "id": "first",
                    "tool": "fake",
                    "enabled": True,
                    "required": True,
                    "condition": {
                        "type": "step_success",
                        "step_id": "second",
                    },
                    "params": {},
                },
                {
                    "id": "second",
                    "tool": "fake",
                    "enabled": True,
                    "required": True,
                    "condition": {"type": "always"},
                    "params": {},
                },
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = RecipeManager(str(Path(temp_dir) / "recipes.json"))
            with self.assertRaisesRegex(ValueError, "step anterior inexistente"):
                manager.save(recipe)

    def test_recipe_ids_are_unique(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = RecipeManager(str(Path(temp_dir) / "recipes.json"))
            manager.save({
                "id": "same_id",
                "name": "ONE",
                "selected": True,
                "commissioned": False,
                "steps": [],
            })
            with self.assertRaisesRegex(ValueError, "Recipe id duplicado"):
                manager.save({
                    "id": "same_id",
                    "name": "TWO",
                    "selected": False,
                    "commissioned": False,
                    "steps": [],
                })


if __name__ == "__main__":
    unittest.main()
