import unittest
from pathlib import Path

from core.camera_runtime import format_camera_runtime, manual_focus_preflight


class DegradedCameraStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_source = Path("app/app.py").read_text(encoding="utf-8")
        cls.camera_source = Path("vision/camera_worker.py").read_text(
            encoding="utf-8"
        )

    def test_runtime_is_fully_wired_before_any_worker_starts(self):
        constructor = self.app_source.split("    def setup_ui_logger", 1)[0]
        self.assertLess(
            constructor.index("self.setup_state_manager()"),
            constructor.index("self.start_runtime_workers()"),
        )

        setup_camera = self.app_source.split("    def setup_camera", 1)[1].split(
            "    def update_frame", 1
        )[0]
        setup_serial = self.app_source.split("    def setup_serial", 1)[1].split(
            "    def on_serial_connection_lost", 1
        )[0]
        self.assertNotIn("self.camera_thread.start()", setup_camera)
        self.assertNotIn("self.serial_thread.start()", setup_serial)

    def test_camera_failure_keeps_worker_available_for_configuration(self):
        setup_camera = self.app_source.split("    def setup_camera", 1)[1].split(
            "    def update_frame", 1
        )[0]
        self.assertNotIn("camera_worker.deleteLater", setup_camera)

        start_method = self.camera_source.split("    def start(self):", 1)[1].split(
            "    def stop(self):", 1
        )[0]
        self.assertEqual(start_method.count("self.finished.emit()"), 1)

    def test_windows_retries_backends_without_changing_camera_index(self):
        open_camera = self.camera_source.split("    def open_camera", 1)[1].split(
            "    def configure_resolution", 1
        )[0]
        for backend in ('"DSHOW"', '"MSMF"', '"AUTO"'):
            self.assertIn(backend, open_camera)
        self.assertIn("cv2.VideoCapture(self.device, backend_id)", open_camera)

    def test_missing_camera_is_a_blocking_diagnostic_not_a_fatal_startup(self):
        open_camera = self.camera_source.split("    def open_camera", 1)[1].split(
            "    def configure_resolution", 1
        )[0]
        self.assertIn("blocking=True", open_camera)
        self.assertIn("self.diagnostics.blocking_reason()", self.app_source)
        self.assertIn("self.ui.btn_config.setEnabled", self.app_source)

    def test_configuration_explains_camera_unavailable_reason(self):
        info = {
            "platform": "windows",
            "requested_device": 2,
            "resolved_device": 2,
            "camera_open": False,
            "capture_backend": None,
            "error": "No se pudo abrir la camara 2",
        }
        text = format_camera_runtime(info)
        self.assertIn("NO DISPONIBLE", text)
        self.assertIn("No se pudo abrir la camara 2", text)

        ok, message = manual_focus_preflight(info)
        self.assertFalse(ok)
        self.assertIn("Linux/V4L2", message)


if __name__ == "__main__":
    unittest.main()
