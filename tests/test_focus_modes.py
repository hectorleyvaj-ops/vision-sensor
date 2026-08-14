import unittest

from core.focus_modes import FOCUS_MODE_LABELS, focus_mode_label


class FocusModeLabelTests(unittest.TestCase):
    def test_every_runtime_mode_has_a_friendly_label(self):
        self.assertEqual(
            set(FOCUS_MODE_LABELS),
            {"calibrated", "manual_fixed", "auto_continuous", "disabled"},
        )
        for value, label in FOCUS_MODE_LABELS.items():
            self.assertNotEqual(value, label)
            self.assertTrue(label)

    def test_unknown_future_mode_remains_visible(self):
        self.assertEqual(focus_mode_label("future_mode"), "future_mode")


if __name__ == "__main__":
    unittest.main()
