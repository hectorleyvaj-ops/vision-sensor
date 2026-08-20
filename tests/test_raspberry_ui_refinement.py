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
        cls.app_source = Path("app/app.py").read_text(encoding="utf-8")
        cls.theme_source = Path("ui/theme.py").read_text(encoding="utf-8")

    def test_every_configuration_editor_uses_common_modal_execution(self):
        self.assertNotIn("configure_dialog(", self.config_source)
        self.assertEqual(self.config_source.count("exec_modal_dialog("), 6)
        self.assertIn("Qt.ApplicationModal", self.responsive_source)
        self.assertIn("QTimer.singleShot(0, dialog.showFullScreen)", self.responsive_source)
        self.assertIn("int(profile.touch_target) - 5", self.responsive_source)

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

    def test_recent_events_use_large_touch_buttons_instead_of_native_scrollbar(self):
        self.assertIn("setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)", self.app_source)
        self.assertIn("native_scrollbar.setFixedWidth(0)", self.app_source)
        self.assertIn("native_scrollbar.hide()", self.app_source)
        self.assertIn("setViewportMargins(0, 0, 0, 0)", self.app_source)
        self.assertIn("log_height - 17", self.app_source)
        self.assertIn('QPushButton("▲")', self.app_source)
        self.assertIn('QPushButton("▼")', self.app_source)
        self.assertIn("setAutoRepeat(True)", self.app_source)
        self.assertIn('buttonRole="logScroll"', self.theme_source)

    def test_station_and_recipe_buttons_have_explicit_press_feedback(self):
        self.assertIn('QPushButton("ESTACION")', self.config_source)
        self.assertIn('QPushButton("RECETA")', self.config_source)
        self.assertEqual(self.config_source.count('setProperty("buttonRole", "navigation")'), 2)
        self.assertIn('buttonRole="navigation"]:pressed', self.theme_source)

    def test_activate_and_save_buttons_are_readable_and_have_press_feedback(self):
        self.assertEqual(
            self.config_source.count('setProperty("buttonRole", "commit")'), 2
        )
        self.assertIn('buttonRole="commit"] {', self.theme_source)
        self.assertIn('buttonRole="commit"]:pressed', self.theme_source)


if __name__ == "__main__":
    unittest.main()
