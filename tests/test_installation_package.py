import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from core.acceptance import (
    evaluate_acceptance,
    load_acceptance_plan,
    new_acceptance_session,
)
from scripts.validate_installation import main, validate_installation


class InstallationPackageTests(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parents[1]
        self.package = self.project_root / "installations" / "worksurface"
        self.manifest = self.package / "commissioning.json"

    def test_preliminary_calibration_is_valid_but_not_commissioned(self):
        report = validate_installation(self.manifest)

        self.assertEqual(report["errors"], [])
        self.assertTrue(report["ready_for_commissioning"])
        self.assertFalse(report["ready_for_production"])
        pending_codes = {item["code"] for item in report["pending"]}
        self.assertIn("RECIPE_NOT_COMMISSIONED", pending_codes)
        self.assertNotIn("REQUIRED_TOOLS", pending_codes)
        self.assertNotIn("TOOL_COMMISSIONING", pending_codes)
        self.assertEqual(
            Path(report["manifest"]),
            self.manifest.resolve(),
        )

    def test_package_declares_exact_external_models_and_part_numbers(self):
        system = json.loads(
            (self.package / "system.json").read_text(encoding="utf-8")
        )
        recipes = json.loads(
            (self.package / "recipes.json").read_text(encoding="utf-8")
        )["recipes"]

        self.assertEqual(
            system["controller"]["model_map"],
            {"A": "MODELO_A", "B": "MODELO_B", "C": "MODELO_C"},
        )
        self.assertEqual(
            {
                recipe["machine"]["external_model"]:
                recipe["machine"]["part_number"]
                for recipe in recipes
            },
            {
                "A": "0402012XA",
                "B": "0402012XB",
                "C": "0402012XC",
            },
        )
        self.assertTrue(all(recipe["commissioned"] is False for recipe in recipes))
        self.assertTrue(all("steps" in recipe for recipe in recipes))

    def test_invalid_model_mapping_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            package_copy = temp_root / "worksurface"
            shutil.copytree(self.package, package_copy)
            manifest = json.loads(
                (package_copy / "commissioning.json").read_text(encoding="utf-8")
            )
            manifest["project_root"] = "."
            manifest["system_config"] = "system.json"
            (package_copy / "commissioning.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            system = json.loads(
                (package_copy / "system.json").read_text(encoding="utf-8")
            )
            system["recipes"]["file"] = "recipes.json"
            system["controller"]["model_map"]["B"] = "MODELO_A"
            (package_copy / "system.json").write_text(
                json.dumps(system), encoding="utf-8"
            )

            report = validate_installation(package_copy / "commissioning.json")

        self.assertFalse(report["ready_for_commissioning"])
        self.assertIn("MODEL_MAPPING", {item["code"] for item in report["errors"]})

    def test_cli_strict_mode_rejects_pending_calibration(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main([str(self.manifest), "--json"]), 0)
            self.assertEqual(
                main([str(self.manifest), "--require-commissioned", "--json"]),
                3,
            )

    def test_worksurface_acceptance_plan_matches_manifest_and_starts_pending(self):
        plan = load_acceptance_plan(self.package / "acceptance.json")
        report = evaluate_acceptance(new_acceptance_session(plan), plan)

        self.assertEqual(plan.models, ("A", "B", "C"))
        self.assertEqual(report["status"], "PENDING")
        self.assertEqual(plan.minimum_trials, {"OK": 10, "NG": 10})
        self.assertIn("usb_disconnect_safe", plan.scenarios)


if __name__ == "__main__":
    unittest.main()
