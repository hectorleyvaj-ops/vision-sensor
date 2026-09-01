import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.deployment_manifest import verify_manifest, write_manifest
from core.deployment_paths import DeploymentPaths, switch_release
from core.runtime_health import read_runtime_health, write_runtime_health
from scripts.prepare_installation import seed_installation
from scripts.configure_touchscreen import MATRICES, udev_rule
from scripts.validate_installation import validate_installation


class DeploymentPhase12Tests(unittest.TestCase):
    def test_paths_do_not_embed_a_user_or_hardware_endpoint(self):
        paths = DeploymentPaths.from_values("/opt/vision-sensor", "worksurface")
        self.assertEqual(paths.system_config, Path("/var/lib/vision-sensor/installations/worksurface/system.json"))
        self.assertEqual(paths.runtime, Path("/var/lib/vision-sensor/runtime/worksurface"))
        with self.assertRaises(ValueError):
            DeploymentPaths.from_values("/opt/vision-sensor", "../unsafe")

    def test_release_switch_preserves_previous_atomically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = DeploymentPaths.from_values(temp_dir, "station")
            one = paths.releases / "one"
            two = paths.releases / "two"
            one.mkdir(parents=True)
            two.mkdir(parents=True)
            switch_release(paths, one)
            previous = switch_release(paths, two)
            self.assertEqual(previous, one.resolve())
            self.assertEqual(paths.current.resolve(), two.resolve())
            self.assertEqual(paths.previous.resolve(), one.resolve())

    def test_runtime_health_is_atomic_and_not_ready_authorization(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "health.json"
            payload = write_runtime_health(path, "degraded", version="test")
            self.assertEqual(payload["state"], "degraded")
            self.assertEqual(read_runtime_health(path)["state"], "degraded")
            self.assertNotIn("READY", payload)

    def test_touchscreen_profiles_use_stable_udev_identifiers(self):
        self.assertEqual(len(MATRICES["rotate-180"]), 6)
        rule = udev_rule("1234", "abcd", "invert-x")
        self.assertIn('ENV{ID_VENDOR_ID}=="1234"', rule)
        self.assertIn("LIBINPUT_CALIBRATION_MATRIX", rule)
        self.assertNotIn("event", rule)

    def test_generic_seed_is_preserved_and_valid_for_configuration(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "station"
            self.assertTrue(seed_installation(root, destination, "generic", "station-test"))
            self.assertFalse(seed_installation(root, destination, "generic"))
            report = validate_installation(destination / "commissioning.json")
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["ready_for_commissioning"])
        self.assertEqual(report["installation"], "station-test")

    def test_service_contract_keeps_qt_in_the_graphical_user_session(self):
        root = Path(__file__).resolve().parents[1]
        service = (root / "deploy/systemd/vision-sensor.service.in").read_text(encoding="utf-8")
        autostart = (root / "deploy/autostart/vision-sensor.desktop").read_text(encoding="utf-8")
        launcher = (root / "scripts/launch_vision.sh").read_text(encoding="utf-8")
        self.assertIn("Restart=on-failure", service)
        self.assertNotIn("User=root", service)
        self.assertIn("start_graphical_service.sh", autostart)
        unit_section, service_section = service.split("[Service]", 1)
        self.assertIn("StartLimitIntervalSec=120", unit_section)
        self.assertNotIn("StartLimitIntervalSec", service_section)
        self.assertIn("La interfaz continuara", launcher)
        self.assertIn("READY productivo se valida por separado", launcher)
        self.assertIn("VISION_COMMISSIONING_VALIDATION_STATUS", launcher)
        self.assertNotIn(
            "La configuracion estructural es invalida; no se reiniciara",
            launcher,
        )

    def test_maintenance_clis_import_project_from_any_working_directory(self):
        root = Path(__file__).resolve().parents[1]
        scripts = (
            "switch_release.py",
            "backup_installation.py",
            "restore_installation.py",
            "diagnose_deployment.py",
        )
        with tempfile.TemporaryDirectory() as external_dir:
            for script in scripts:
                result = subprocess.run(
                    [sys.executable, str(root / "scripts" / script), "--help"],
                    cwd=external_dir,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_shell_scripts_are_linux_executables_and_select_dmtx_package(self):
        root = Path(__file__).resolve().parents[1]
        required = (
            "install_raspberry.sh",
            "launch_vision.sh",
            "rollback_raspberry.sh",
            "start_graphical_service.sh",
            "update_raspberry.sh",
            "vision_service.sh",
        )
        for name in required:
            path = root / "scripts" / name
            self.assertTrue(os.access(path, os.X_OK), name)
            self.assertNotIn(b"\r\n", path.read_bytes(), name)
        installer = (root / "scripts/install_raspberry.sh").read_text(encoding="utf-8")
        self.assertIn("libdmtx0t64", installer)
        self.assertIn("libdmtx0b", installer)
        self.assertIn("apt-cache show", installer)
        attributes = (root / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("*.sh text eol=lf", attributes)

    def test_named_installation_seed_is_supported(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_root = temp_root / "source"
            seed = source_root / "installations" / "custom-station"
            seed.mkdir(parents=True)
            (seed / "system.json").write_text(
                '{"schema_version":2,"installation":{"id":"custom"},"recipes":{"file":"recipes.json"},"traceability":{}}',
                encoding="utf-8",
            )
            (seed / "recipes.json").write_text(
                '{"schema_version":3,"recipes":[]}',
                encoding="utf-8",
            )
            destination = temp_root / "data" / "custom"
            self.assertTrue(
                seed_installation(source_root, destination, "custom-station", "custom")
            )
            self.assertTrue((destination / "system.json").is_file())

    def test_manifest_detects_tampered_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "system.json").write_text("{}", encoding="utf-8")
            write_manifest(root, installation_id="test", version="x")
            self.assertEqual(verify_manifest(root)[1], [])
            (root / "system.json").write_text("{broken}", encoding="utf-8")
            self.assertTrue(verify_manifest(root)[1])


if __name__ == "__main__":
    unittest.main()
