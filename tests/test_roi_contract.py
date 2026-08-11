import json
import tempfile
import unittest
from pathlib import Path

from core.recipe_manager import RecipeManager
from core.roi import ROIError, normalize_roi


class ROIContractTests(unittest.TestCase):
    def test_canonical_roi_is_xyxy(self):
        self.assertEqual(normalize_roi([10, 20, 40, 60]), [10, 20, 40, 60])

    def test_legacy_xywh_preserves_the_same_rectangle(self):
        self.assertEqual(
            normalize_roi([10, 20, 30, 40], source_format="xywh"),
            [10, 20, 40, 60],
        )

    def test_empty_or_negative_roi_is_rejected(self):
        with self.assertRaises(ROIError):
            normalize_roi([10, 10, 10, 20])
        with self.assertRaises(ROIError):
            normalize_roi([-1, 0, 10, 20])

    def test_schema_v2_histogram_roi_is_migrated_but_dmtx_is_not(self):
        payload = {
            "schema_version": 2,
            "recipes": [{
                "id": "legacy",
                "name": "LEGACY",
                "selected": True,
                "commissioned": True,
                "focus": {"roi": [5, 6, 50, 60]},
                "steps": [
                    {
                        "id": "hist_1",
                        "tool": "img_hist",
                        "params": {"roi": [10, 20, 30, 40]},
                    },
                    {
                        "id": "dmtx_1",
                        "tool": "dmtx",
                        "params": {
                            "roi": [100, 200, 300, 400],
                            "expected_code": "ABC",
                        },
                    },
                ],
            }],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "recipes.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            recipe = RecipeManager(str(path), auto_migrate=True).get_selected()
            saved = json.loads(path.read_text(encoding="utf-8"))
            backup = json.loads(
                Path(str(path) + ".bak").read_text(encoding="utf-8")
            )

        self.assertEqual(saved["schema_version"], 3)
        self.assertEqual(backup["schema_version"], 2)
        self.assertEqual(recipe["focus"]["roi"], [5, 6, 50, 60])
        self.assertEqual(recipe["steps"][0]["params"]["roi"], [10, 20, 40, 60])
        self.assertEqual(recipe["steps"][1]["params"]["roi"], [100, 200, 300, 400])


if __name__ == "__main__":
    unittest.main()
