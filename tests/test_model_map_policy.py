import json
import tempfile
import unittest
from pathlib import Path

from scripts.set_model_map_policy import set_model_map_policy


class ModelMapPolicyTests(unittest.TestCase):
    def test_configurable_policy_is_atomic_and_preserves_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "commissioning.json"
            manifest_path.write_text(
                json.dumps({
                    "schema_version": 1,
                    "exact_model_map": True,
                    "required_models": [],
                }),
                encoding="utf-8",
            )

            result = set_model_map_policy(manifest_path, "configurable")
            updated = json.loads(manifest_path.read_text(encoding="utf-8"))
            backup = json.loads(
                Path(result["backup"]).read_text(encoding="utf-8")
            )

        self.assertTrue(result["changed"])
        self.assertFalse(updated["exact_model_map"])
        self.assertTrue(backup["exact_model_map"])

    def test_reapplying_same_policy_does_not_replace_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "commissioning.json"
            manifest_path.write_text(
                json.dumps({
                    "schema_version": 1,
                    "exact_model_map": False,
                    "required_models": [],
                }),
                encoding="utf-8",
            )

            result = set_model_map_policy(manifest_path, "configurable")

        self.assertFalse(result["changed"])
        self.assertIsNone(result["backup"])

    def test_unknown_policy_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "commissioning.json"
            manifest_path.write_text(
                '{"schema_version": 1}', encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                set_model_map_policy(manifest_path, "automatic")


if __name__ == "__main__":
    unittest.main()
