import unittest

from core.display_profile import (
    build_display_profile,
    preferred_dialog_size,
    preferred_window_size,
)


class DisplayProfileTests(unittest.TestCase):
    def test_raspberry_touchscreen_uses_compact_profile(self):
        profile = build_display_profile(480, 320)
        self.assertEqual(profile.mode, "compact")
        self.assertEqual(preferred_window_size(profile), (480, 320))
        self.assertGreaterEqual(profile.touch_target, 38)
        self.assertLessEqual(profile.dialog_video_height, 140)

    def test_small_dimensions_are_clamped_to_safe_minimum(self):
        profile = build_display_profile(0, 0)
        self.assertEqual((profile.width, profile.height), (320, 240))

    def test_800_by_480_keeps_standard_layout(self):
        profile = build_display_profile(800, 480)
        self.assertEqual(profile.mode, "standard")
        self.assertEqual(preferred_window_size(profile), (800, 480))
        self.assertGreaterEqual(profile.touch_target, 42)
        self.assertGreaterEqual(profile.indicator_size, 70)

    def test_large_monitor_uses_wide_layout_without_unbounded_window(self):
        profile = build_display_profile(1920, 1080)
        self.assertEqual(profile.mode, "wide")
        self.assertEqual(preferred_window_size(profile), (1200, 760))

    def test_dialog_never_exceeds_available_geometry(self):
        compact = build_display_profile(480, 320)
        wide = build_display_profile(1366, 768)
        self.assertEqual(preferred_dialog_size(compact), (480, 320))
        self.assertEqual(preferred_dialog_size(wide, 1600, 900), (1318, 720))


if __name__ == "__main__":
    unittest.main()
