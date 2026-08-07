import copy
import json
import tempfile
import unittest
from pathlib import Path

from core.editor_models import (
    EditorValueError,
    build_model_map,
    parse_camera_device,
    parse_condition_text,
)
from core.system_config import SystemConfig, SystemConfigError


class ConfigurationEditorTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads(
            Path("config/system.json").read_text(encoding="utf-8")
        )

    def test_camera_device_accepts_index_or_path(self):
        self.assertEqual(parse_camera_device("2"), 2)
        self.assertEqual(parse_camera_device("/dev/video-camera"), "/dev/video-camera")
        with self.assertRaises(EditorValueError):
            parse_camera_device("  ")

    def test_model_map_rejects_duplicate_external_ids(self):
        with self.assertRaises(EditorValueError):
            build_model_map([
                ("SKU", "RECIPE_A"),
                ("SKU", "RECIPE_B"),
            ])

    def test_condition_editor_rejects_forward_step_reference(self):
        with self.assertRaises(EditorValueError):
            parse_condition_text(
                '{"type":"step_success","step_id":"future"}',
                available_step_ids=["previous"],
            )

    def test_system_config_save_is_atomic_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "system.json"
            path.write_text(json.dumps(self.base), encoding="utf-8")
            config = SystemConfig(path)
            updated = copy.deepcopy(config.data)
            updated["installation"]["name"] = "Station updated"
            updated["controller"]["model_map"] = {"SKU": "RECIPE_A"}

            config.save(updated, recipe_names=["RECIPE_A"])

            saved = json.loads(path.read_text(encoding="utf-8"))
            backup = json.loads(
                Path(str(path) + ".bak").read_text(encoding="utf-8")
            )
            self.assertEqual(saved["installation"]["name"], "Station updated")
            self.assertEqual(
                backup["installation"]["name"],
                self.base["installation"]["name"],
            )

    def test_unknown_recipe_mapping_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "system.json"
            original_text = json.dumps(self.base)
            path.write_text(original_text, encoding="utf-8")
            config = SystemConfig(path)
            updated = copy.deepcopy(config.data)
            updated["controller"]["model_map"] = {"SKU": "MISSING"}

            with self.assertRaises(SystemConfigError):
                config.save(updated, recipe_names=["RECIPE_A"])

            self.assertEqual(path.read_text(encoding="utf-8"), original_text)
            self.assertFalse(Path(str(path) + ".tmp").exists())


if __name__ == "__main__":
    unittest.main()
