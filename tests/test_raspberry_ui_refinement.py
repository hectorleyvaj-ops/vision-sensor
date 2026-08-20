import unittest
from pathlib import Path


class RaspberryUiRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_source = Path("ui/config_window_logic.py").read_text(
            encoding="utf-8"
        )
        cls.focus_source = Path("ui/focus_config_dialog.py").read_text(
            encoding="utf-8"
        )
        cls.responsive_source = Path("ui/responsive.py").read_text(
            encoding="utf-8"
        )
        cls.camera_source = Path("vision/camera_worker.py").read_text(
            encoding="utf-8"
        )

    def test_every_configuration_editor_uses_common_modal_execution(self):
        self.assertNotIn("configure_dialog(", self.config_source)
        self.assertEqual(self.config_source.count("exec_modal_dialog("), 6)
        self.assertIn("Qt.ApplicationModal", self.responsive_source)
        self.assertIn("QTimer.singleShot(0, dialog.showFullScreen)", self.responsive_source)

    def test_config_buttons_are_not_reset_after_theme_application(self):
        feedback = self.config_source.split(
            "    def add_button_feedback", 1
        )[1].split("    def apply_button_feedbakcs", 1)[0]
        self.assertNotIn("setStyleSheet", feedback)
        self.assertIn("application.setStyleSheet(stylesheet)", self.config_source)

    def test_manual_focus_is_an_explicit_value_not_an_automatic_sweep(self):
        self.assertIn("self.spn_manual_value", self.focus_source)
        self.assertIn('mode == "manual_fixed"', self.focus_source)
        self.assertIn('"auto_refocus_if_failed": False', self.focus_source)
        request = self.focus_source.split(
            "    def request_calibration", 1
        )[1].split("    @Slot(object)", 1)[0]
        self.assertIn('mode != "calibrated"', request)

    def test_linux_fixed_focus_cannot_be_ready_without_focus_absolute(self):
        recipe_focus = self.camera_source.split(
            "    def set_focus_from_recipe", 1
        )[1].split("    def get_focus_required_score", 1)[0]
        self.assertIn("elif self.is_linux() and has_focus_value", recipe_focus)
        self.assertIn("ready=False", recipe_focus)


if __name__ == "__main__":
    unittest.main()
