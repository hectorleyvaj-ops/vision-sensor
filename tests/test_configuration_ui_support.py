import unittest
from pathlib import Path

from core.camera_runtime import (
    control_value_matches,
    format_camera_runtime,
    manual_focus_preflight,
)
from core.display_profile import build_display_profile
from core.resource_paths import recipe_resource_root
from ui.theme import interface_stylesheet, operator_stylesheet


class ConfigurationUiSupportTests(unittest.TestCase):
    def test_manual_focus_preflight_identifies_missing_v4l2_control(self):
        ok, message = manual_focus_preflight({
            "platform": "linux",
            "camera_open": True,
            "resolved_device": "/dev/video2",
            "v4l2_available": True,
            "focus_absolute_supported": False,
        })
        self.assertFalse(ok)
        self.assertIn("focus_absolute", message)

    def test_manual_focus_preflight_accepts_ready_camera(self):
        ok, _message = manual_focus_preflight({
            "platform": "linux",
            "camera_open": True,
            "resolved_device": "/dev/video1",
            "v4l2_available": True,
            "focus_absolute_supported": True,
        })
        self.assertTrue(ok)

    def test_missing_v4l2_tool_is_not_reported_as_a_driver_failure(self):
        ok, message = manual_focus_preflight({
            "platform": "linux",
            "camera_open": True,
            "resolved_device": "/dev/video0",
            "v4l2_tool_available": False,
            "v4l2_available": False,
        })
        self.assertFalse(ok)
        self.assertIn("v4l-utils", message)
        self.assertIn("No es el driver", message)

    def test_focus_control_readback_must_match_requested_value(self):
        self.assertTrue(control_value_matches(320, 320))
        self.assertFalse(control_value_matches(320, 319))
        self.assertFalse(control_value_matches(320, None))

    def test_camera_runtime_text_exposes_resolved_device_and_format(self):
        text = format_camera_runtime({
            "requested_device": 0,
            "resolved_device": "/dev/video1",
            "actual_width": 1920,
            "actual_height": 1080,
            "focus_absolute_supported": True,
        })
        self.assertIn("solicitada: 0", text)
        self.assertIn("activa: /dev/video1", text)
        self.assertIn("1920x1080", text)

    def test_external_catalog_owns_its_master_image_directory(self):
        self.assertEqual(
            recipe_resource_root("installations/worksurface/recipes.json"),
            Path("installations/worksurface/master_images"),
        )
        self.assertEqual(recipe_resource_root("recipes.json"), Path("master_img"))
        self.assertEqual(
            recipe_resource_root("core/models/recipes.json"), Path("master_img")
        )

    def test_theme_covers_text_editors_tables_popups_and_scrollbars(self):
        stylesheet = interface_stylesheet(build_display_profile(800, 480))
        for selector in (
            "QPlainTextEdit",
            "QTableWidget",
            "QComboBox QAbstractItemView",
            "QScrollBar:vertical",
            "QMessageBox",
            "QMessageBox QLabel",
            "QMessageBox QPushButton",
        ):
            self.assertIn(selector, stylesheet)

    def test_operator_theme_has_semantic_ready_warning_and_result_states(self):
        stylesheet = operator_stylesheet(build_display_profile(800, 480))
        for state in ("ready", "working", "ok", "ng", "warning", "critical"):
            self.assertIn(f'statusLevel="{state}"', stylesheet)
        self.assertIn("QPushButton#btn_config", stylesheet)
        self.assertIn("QLabel#lbl_model", stylesheet)

    def test_rpi_instructions_install_v4l2_tools(self):
        requirements = Path("requirements-rpi32.txt").read_text(encoding="utf-8")
        guide = Path("docs/raspberry_pi_32bit_runtime.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("v4l-utils", requirements)
        self.assertIn("v4l-utils", guide)


if __name__ == "__main__":
    unittest.main()
