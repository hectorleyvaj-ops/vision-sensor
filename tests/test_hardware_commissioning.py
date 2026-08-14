import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from core.recipe_manager import RecipeManager
from core.system_config import SystemConfig, SystemConfigError
from services.hardware_discovery import (
    camera_candidate_devices,
    discover_cameras,
    discover_serial_controllers,
    format_camera_candidate,
    format_serial_candidate,
    probe_controller_port,
    serial_port_records,
)


class FakeCapture:
    def __init__(self, device, backend):
        self.device = device
        self.backend = backend
        self.released = False

    def isOpened(self):
        return self.device == 2

    def read(self):
        return (True, object()) if self.isOpened() else (False, None)

    def get(self, prop):
        values = {3: 1280, 4: 720, 5: 30.0}
        return values.get(prop, 0)

    def release(self):
        self.released = True


class FakeSerial:
    def __init__(self, **_kwargs):
        self.response = bytearray(
            b"\x02HELLO_ACK|PROTO=1|FW=test-controller|READY=1\x03"
        )
        self.closed = False

    @property
    def in_waiting(self):
        return len(self.response)

    def reset_input_buffer(self):
        pass

    def write(self, payload):
        self.written = payload

    def flush(self):
        pass

    def read(self, size):
        data = bytes(self.response[:size])
        del self.response[:size]
        return data

    def close(self):
        self.closed = True


class HardwareCommissioningTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads(
            Path("config/system.json").read_text(encoding="utf-8")
        )

    def test_generic_configuration_starts_unassigned_and_safe(self):
        config = SystemConfig("config/system.json")
        self.assertTrue(config.section("installation")["commissioning_mode"])
        self.assertIsNone(config.section("camera")["device"])
        self.assertEqual(config.section("controller")["ports"], {})
        self.assertIsNone(config.controller_port("linux"))

    def test_unassigned_hardware_is_rejected_outside_commissioning(self):
        candidate = copy.deepcopy(self.base)
        candidate["installation"]["commissioning_mode"] = False
        with self.assertRaisesRegex(SystemConfigError, "camera.device"):
            SystemConfig.validate_data(candidate)

    def test_assigned_hardware_can_leave_commissioning(self):
        candidate = copy.deepcopy(self.base)
        candidate["installation"]["commissioning_mode"] = False
        candidate["camera"]["device"] = 1
        candidate["controller"]["ports"] = {"windows": "COM8"}
        validated = SystemConfig.validate_data(candidate, recipe_names=[])
        self.assertFalse(validated["installation"]["commissioning_mode"])

    def test_camera_inventory_keeps_configured_index_and_finds_frames(self):
        self.assertEqual(
            camera_candidate_devices("windows", configured_device=2, max_index=3),
            [2, 0, 1, 3],
        )
        records = discover_cameras(
            "windows",
            configured_device=2,
            max_index=3,
            capture_factory=FakeCapture,
        )
        found = next(item for item in records if item["device"] == 2)
        self.assertTrue(found["available"])
        self.assertTrue(found["verified"])
        self.assertIn("DISPONIBLE", format_camera_candidate(found))

    def test_serial_inventory_exposes_identity_fields(self):
        records = serial_port_records([
            SimpleNamespace(
                device="COM8",
                description="USB UART",
                manufacturer="Silicon Labs",
                vid=0x10C4,
                pid=0xEA60,
                serial_number="ABC",
                hwid="USB VID:PID=10C4:EA60",
            )
        ])
        self.assertEqual(records[0]["device"], "COM8")
        self.assertEqual(records[0]["serial_number"], "ABC")
        self.assertIn("COM8", format_serial_candidate(records[0]))

    def test_controller_probe_accepts_only_protocol_handshake(self):
        result = probe_controller_port("COM8", serial_factory=FakeSerial)
        self.assertTrue(result["verified_controller"])
        self.assertEqual(result["protocol"], "1")
        self.assertEqual(result["firmware"], "test-controller")

    def test_active_controller_is_not_reopened_during_discovery(self):
        def forbidden_factory(**_kwargs):
            raise AssertionError("El puerto activo no debe abrirse otra vez")

        info = SimpleNamespace(
            device="COM7",
            description="Active UART",
            manufacturer="",
            vid=None,
            pid=None,
            serial_number="",
            hwid="",
        )
        records = discover_serial_controllers(
            active_info={
                "port": "COM7",
                "connected": True,
                "synced": True,
                "protocol": "1",
                "firmware": "active-controller",
            },
            port_infos=[info],
            serial_factory=forbidden_factory,
        )
        self.assertTrue(records[0]["active"])
        self.assertTrue(records[0]["verified_controller"])

    def test_new_recipe_is_neutral_and_uses_configured_focus_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "recipes.json"
            manager = RecipeManager(
                path,
                default_focus_mode="auto_continuous",
            )
            self.assertIsNone(manager.get_selected())
            manager.create_recipe("PRODUCTO NUEVO")
            recipe = manager.get("PRODUCTO NUEVO")

        self.assertEqual(recipe["steps"], [])
        self.assertFalse(recipe["commissioned"])
        self.assertEqual(recipe["focus"]["mode"], "auto_continuous")
        self.assertTrue(recipe["focus"]["enabled"])

    def test_generic_catalog_contains_no_product_data(self):
        recipes = json.loads(
            Path("core/models/recipes.json").read_text(encoding="utf-8")
        )
        self.assertEqual(recipes, {"schema_version": 3, "recipes": []})
        serialized = json.dumps(self.base)
        self.assertNotIn("MODELO_A", serialized)
        self.assertNotIn("expected_code", serialized)

    def test_commissioning_ui_and_safe_start_are_wired(self):
        app_source = Path("app/app.py").read_text(encoding="utf-8")
        dialog_source = Path("ui/system_config_dialog.py").read_text(
            encoding="utf-8"
        )
        camera_source = Path("vision/camera_worker.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("self.open_commissioning_configuration", app_source)
        self.assertIn("Estacion en modo configuracion", app_source)
        self.assertIn("discover_cameras", dialog_source)
        self.assertIn("discover_serial_controllers", dialog_source)
        self.assertIn("Produccion abre unicamente el endpoint guardado", camera_source)


if __name__ == "__main__":
    unittest.main()
