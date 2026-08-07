import json
import tempfile
import unittest
from pathlib import Path

from core.system_config import SystemConfig, SystemConfigError


class SystemConfigTests(unittest.TestCase):
    def setUp(self):
        self.config_path = Path("config/system.json")

    def test_base_config_is_one_complete_installation(self):
        config = SystemConfig(self.config_path)

        self.assertNotIn("profiles", config.data)
        self.assertNotIn("active_profile", config.data)
        self.assertEqual(config.recipe_file, "core/models/recipes.json")
        self.assertEqual(
            config.section("controller")["protocol"],
            "vision_controller_v1",
        )

    def test_profile_configuration_is_rejected(self):
        invalid = {
            "active_profile": "machine_a",
            "profiles": {"machine_a": {}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "system.json"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(SystemConfigError):
                SystemConfig(path)

    def test_invalid_focus_mode_is_rejected(self):
        invalid = json.loads(self.config_path.read_text(encoding="utf-8"))
        invalid["camera"]["default_focus_mode"] = "invented"

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "system.json"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(SystemConfigError):
                SystemConfig(path)

    def test_controller_protocol_cannot_be_switched_by_config(self):
        invalid = json.loads(self.config_path.read_text(encoding="utf-8"))
        invalid["controller"]["protocol"] = "machine_specific_protocol"

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "system.json"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(SystemConfigError):
                SystemConfig(path)


if __name__ == "__main__":
    unittest.main()
