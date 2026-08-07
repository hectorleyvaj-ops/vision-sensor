import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.system_config import SystemConfig, SystemConfigError


class SystemConfigTests(unittest.TestCase):
    def setUp(self):
        self.config_path = Path("config/system.json")

    def test_worksurface_profile_contains_all_model_mappings(self):
        config = SystemConfig(self.config_path, profile_name="worksurface")
        model_map = config.section("serial")["model_map"]

        self.assertEqual(
            model_map,
            {"A": "MODELO_A", "B": "MODELO_B", "C": "MODELO_C"},
        )
        self.assertEqual(config.recipe_file, "core/models/worksurface_recipes.json")

    def test_environment_can_select_profile(self):
        with patch.dict(os.environ, {"VISION_PROFILE": "worksurface"}):
            config = SystemConfig(self.config_path)

        self.assertEqual(config.profile_name, "worksurface")

    def test_invalid_focus_mode_is_rejected(self):
        invalid = {
            "active_profile": "bad",
            "profiles": {
                "bad": {
                    "recipe_file": "recipes.json",
                    "camera": {
                        "width": 1,
                        "height": 1,
                        "capture_fps": 1,
                        "preview_fps": 1,
                        "default_focus_mode": "invented",
                    },
                    "serial": {
                        "model_map": {"A": "MODEL_A"},
                    },
                }
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "system.json"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(SystemConfigError):
                SystemConfig(path)


if __name__ == "__main__":
    unittest.main()
