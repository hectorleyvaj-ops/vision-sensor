import unittest
from pathlib import Path

from core.camera_runtime import resolve_v4l2_device


class PersistentV4l2EndpointTests(unittest.TestCase):
    def test_stable_by_id_camera_resolves_to_video_node(self):
        stable_device = (
            "/dev/v4l/by-id/"
            "usb-Arducam_Technology_Co.__Ltd._Arducam_8mp_SN0001-video-index0"
        )
        self.assertEqual(
            resolve_v4l2_device(stable_device, realpath=lambda _path: "/dev/video0"),
            "/dev/video0",
        )

    def test_unresolved_stable_endpoint_reports_the_real_reason(self):
        with self.assertRaisesRegex(ValueError, "no resuelve"):
            resolve_v4l2_device(
                "/dev/v4l/by-id/camera-missing",
                realpath=lambda path: path,
            )

    def test_camera_worker_uses_resolved_node_for_detection_and_controls(self):
        source = Path("vision/camera_worker.py").read_text(encoding="utf-8")
        self.assertIn("resolved_device = resolve_v4l2_device(self.device)", source)
        self.assertIn('[v4l2_tool, "-d", self.v4l2_device, "--list-ctrls"]', source)
        self.assertIn("self.v4l2_device or resolve_v4l2_device(self.device)", source)


class CompactInterfaceRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_source = Path("app/app.py").read_text(encoding="utf-8")
        cls.responsive_source = Path("ui/responsive.py").read_text(encoding="utf-8")
        cls.theme_source = Path("ui/theme.py").read_text(encoding="utf-8")
        cls.logger_source = Path("utils/ui_logger.py").read_text(encoding="utf-8")

    def test_long_recent_events_scroll_by_pixel_and_keep_wrapping(self):
        self.assertIn("ScrollPerPixel", self.app_source)
        self.assertIn("setWordWrap(True)", self.app_source)
        self.assertIn("setUniformItemSizes(False)", self.app_source)
        self.assertIn("ScrollPerPixel", self.logger_source)
        append = self.logger_source.split(
            "    def _append_to_single_widget", 1
        )[1]
        self.assertLess(append.index("was_at_btm"), append.index("widget.addItem"))

    def test_compact_status_panel_recovers_vertical_space(self):
        self.assertIn(
            "profile.touch_target if profile.compact else profile.touch_target + 6",
            self.responsive_source,
        )
        self.assertIn(
            "profile.touch_target + (4 if profile.compact else 10)",
            self.responsive_source,
        )
        self.assertIn("profile.log_height - 18", self.app_source)

    def test_danger_buttons_have_same_border_and_visible_feedback(self):
        self.assertIn('QPushButton[buttonRole="danger"]:hover', self.theme_source)
        self.assertIn('QPushButton[buttonRole="danger"]:pressed', self.theme_source)
        self.assertIn("border: 1px solid rgb(159, 60, 72)", self.theme_source)
        self.assertIn("background-color: rgb(244, 100, 112)", self.theme_source)


if __name__ == "__main__":
    unittest.main()
