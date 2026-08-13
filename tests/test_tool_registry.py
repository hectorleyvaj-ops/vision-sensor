import tempfile
import threading
import unittest
from pathlib import Path

from core.recipe_manager import RecipeManager
from processing.pipeline import VisionPipeline
from tools.registry import (
    ToolContractError,
    ToolRegistry,
    discover_tool_registry,
)
from tools.result import ToolResult, ToolStatus
from tools.tool_base import ToolBase


class ContractTool(ToolBase):
    TOOL_ID = "contract_tool"
    DISPLAY_NAME = "Contract tool"
    PARAMETER_SCHEMA = {
        "limit": {
            "type": "int",
            "min": 1,
            "max": 10,
            "default": 3,
        },
        "resource": {
            "type": "image_list",
            "default": [],
            "resource": True,
        },
    }

    def process(self, **kwargs):
        return {"limit": kwargs.get("limit", 3)}


class DuplicateContractTool(ContractTool):
    pass


class InvalidSchemaTool(ToolBase):
    TOOL_ID = "invalid_schema"
    PARAMETER_SCHEMA = {"value": {"type": "mystery"}}

    def process(self, **kwargs):
        return None


class ToolRegistryTests(unittest.TestCase):
    def test_builtin_tools_are_discovered_without_loading_runtime_dependencies(self):
        registry = discover_tool_registry()

        self.assertEqual(set(registry), {"dmtx", "img_hist"})
        self.assertEqual(registry.discovery_errors, [])
        self.assertEqual(registry["dmtx"].name, "dmtx")
        self.assertEqual(registry["img_hist"].name, "img_hist")

    def test_every_builtin_satisfies_structural_and_result_contracts(self):
        registry = discover_tool_registry()

        for tool_id in registry:
            with self.subTest(tool_id=tool_id):
                tool_class = registry.tool_class(tool_id)
                self.assertTrue(tool_class.validate_contract())
                result = registry[tool_id].run()
                self.assertIsInstance(result, ToolResult)
                self.assertEqual(result.tool_name, tool_id)
                self.assertIn(result.status, set(ToolStatus))

                cancel_event = threading.Event()
                cancel_event.set()
                cancelled = registry[tool_id].run(cancel_event=cancel_event)
                self.assertEqual(cancelled.error_code, "CANCELLED")

    def test_duplicate_ids_and_invalid_schemas_are_rejected(self):
        registry = ToolRegistry([ContractTool])
        with self.assertRaises(ToolContractError):
            registry.register(DuplicateContractTool)
        with self.assertRaises(ValueError):
            ToolRegistry([InvalidSchemaTool])

    def test_schema_drives_defaults_validation_and_resources(self):
        registry = ToolRegistry([ContractTool])

        self.assertEqual(
            registry.default_params("contract_tool"),
            {"limit": 3, "resource": []},
        )
        self.assertEqual(
            registry.validate_params("contract_tool", {"limit": 11}),
            ["limit debe ser <= 10"],
        )
        self.assertEqual(
            registry.resource_paths(
                "contract_tool",
                {"resource": ["one.png", "two.png"]},
            ),
            [
                {"parameter": "resource", "path": "one.png"},
                {"parameter": "resource", "path": "two.png"},
            ],
        )

    def test_registry_is_directly_consumable_by_pipeline(self):
        registry = ToolRegistry([ContractTool])
        response = VisionPipeline(registry).run(
            {
                "steps": [{
                    "id": "contract_1",
                    "tool": "contract_tool",
                    "enabled": True,
                    "required": True,
                    "condition": {"type": "always"},
                    "params": {"limit": 4},
                }]
            },
            {},
        )

        self.assertEqual(response["status"], "PASS")
        self.assertEqual(response["results"]["contract_1"].data["limit"], 4)

    def test_recipe_commissioning_uses_tool_owned_rules(self):
        registry = discover_tool_registry()
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = RecipeManager(
                Path(temp_dir) / "recipes.json",
                tool_registry=registry,
            )
            recipe = {
                "id": "part",
                "name": "PART",
                "selected": True,
                "commissioned": True,
                "focus": manager.default_focus_config(),
                "steps": [{
                    "id": "dmtx_1",
                    "tool": "dmtx",
                    "enabled": True,
                    "required": True,
                    "condition": {"type": "always"},
                    "params": registry.default_params("dmtx"),
                }],
            }
            recipe["steps"][0]["params"]["roi"] = [0, 0, 10, 10]

            error = manager.get_commissioning_error(recipe)
            self.assertIn("expected_code", error)


if __name__ == "__main__":
    unittest.main()
