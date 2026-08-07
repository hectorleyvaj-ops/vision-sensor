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

    def test_uncommissioned_worksurface_recipes_are_blocked(self):
        manager = RecipeManager("core/models/worksurface_recipes.json")

        for recipe in manager.get_all():
            error = manager.get_execution_error(
                recipe,
                available_tools={"dmtx", "img_hist"},
            )
            self.assertIn("no esta comisionada", error)

    def test_empty_pipeline_never_passes(self):
        response = VisionPipeline({}).run({"steps": []}, {})
        self.assertFalse(response["success"])
        self.assertIn("no contiene herramientas", response["errors"][0])


if __name__ == "__main__":
    unittest.main()
