import unittest
from pathlib import Path
from xml.etree import ElementTree

from utils.qt_backend import backend_order, normalize_qt_request


class QtBackendTests(unittest.TestCase):
    def test_auto_prefers_pyside_but_keeps_pyqt5_fallback(self):
        self.assertEqual(backend_order("auto"), ("PySide6", "PyQt5"))

    def test_backend_can_be_forced_for_raspberry(self):
        self.assertEqual(backend_order("pyqt5"), ("PyQt5",))
        self.assertEqual(normalize_qt_request("PySide6"), "PySide6")
        with self.assertRaisesRegex(ValueError, "VISION_QT_API"):
            backend_order("invented")

    def test_canonical_ui_files_contain_controls_needed_by_both_backends(self):
        required = {
            "ui/main_window.ui": {
                "centralwidget",
                "verticalLayout_3",
                "lbl_video",
                "indicator_1",
                "btn_config",
                "list_log",
                "verticalSpacer",
                "horizontalSpacer",
                "verticalSpacer_2",
            },
            "ui/config_window.ui": {
                "verticalLayout",
                "central_layout",
                "bttm_layout",
                "cmb_recipes",
                "cmb_tools",
                "btn_focus_config",
                "list_log_config",
                "horizontalSpacer_3",
            },
        }
        for filename, expected in required.items():
            root = ElementTree.parse(filename).getroot()
            names = {
                node.get("name")
                for node in root.iter()
                if node.get("name")
            }
            self.assertEqual(expected - names, set(), filename)

        generated = {
            "ui/pyqt5/ui_main_window.py": {
                "self.verticalSpacer =",
                "self.horizontalSpacer =",
                "self.verticalSpacer_2 =",
            },
            "ui/pyqt5/config_window.py": {
                "self.horizontalSpacer_3 =",
            },
        }
        for filename, expected in generated.items():
            text = Path(filename).read_text(encoding="utf-8")
            self.assertEqual(
                {token for token in expected if token not in text},
                set(),
                filename,
            )

    def test_rpi32_requirements_do_not_request_binary_qt_or_opencv_wheels(self):
        text = Path("requirements-rpi32.txt").read_text(encoding="utf-8")
        active = [
            line.strip().lower()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertFalse(any("pyside" in line for line in active))
        self.assertFalse(any("pyqt" in line for line in active))
        self.assertFalse(any("opencv" in line for line in active))


if __name__ == "__main__":
    unittest.main()
