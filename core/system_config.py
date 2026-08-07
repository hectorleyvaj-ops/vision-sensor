import copy
import json
import os
import shutil
from pathlib import Path


class SystemConfigError(ValueError):
    """Raised when a station configuration cannot be used safely."""


class SystemConfig:
    """Load one complete vision-station configuration.

    The application has no product or machine profiles. A deployment selects a
    complete config file with ``VISION_SYSTEM_CONFIG`` and every recipe remains
    data outside the engine.
    """

    SCHEMA_VERSION = 2
    CONTROLLER_PROTOCOL = "vision_controller_v1"
    VALID_FOCUS_MODES = {
        "calibrated",
        "manual_fixed",
        "auto_continuous",
        "disabled",
    }

    def __init__(self, path="config/system.json"):
        self.path = Path(path)
        self.data = self._load()
        self.validate_data(self.data)

    def _load(self):
        try:
            with self.path.open("r", encoding="utf-8") as config_file:
                data = json.load(config_file)
        except FileNotFoundError as exc:
            raise SystemConfigError(
                f"No existe el archivo de configuracion: {self.path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise SystemConfigError(
                f"JSON de configuracion invalido en {self.path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise SystemConfigError("La raiz de system.json debe ser un objeto")
        if "profiles" in data or "active_profile" in data:
            raise SystemConfigError(
                "La configuracion por perfiles fue retirada. Use un archivo "
                "completo por instalacion mediante VISION_SYSTEM_CONFIG"
            )
        return data

    @classmethod
    def _section_from(cls, data, name):
        section = data.get(name, {})
        if not isinstance(section, dict):
            raise SystemConfigError(f"La seccion '{name}' debe ser un objeto")
        return section

    @staticmethod
    def _is_positive_number(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value > 0
        )

    @classmethod
    def validate_data(cls, data, recipe_names=None):
        """Validate a complete installation before it reaches disk/runtime."""
        if not isinstance(data, dict):
            raise SystemConfigError("La configuracion debe ser un objeto")
        if "profiles" in data or "active_profile" in data:
            raise SystemConfigError(
                "La configuracion por perfiles fue retirada. Use un archivo "
                "completo por instalacion mediante VISION_SYSTEM_CONFIG"
            )
        if data.get("schema_version") != cls.SCHEMA_VERSION:
            raise SystemConfigError(
                f"schema_version debe ser {cls.SCHEMA_VERSION}"
            )

        installation = cls._section_from(data, "installation")
        if not str(installation.get("id", "")).strip():
            raise SystemConfigError("installation.id es obligatorio")

        recipes = cls._section_from(data, "recipes")
        recipe_file = recipes.get("file")
        if not isinstance(recipe_file, str) or not recipe_file.strip():
            raise SystemConfigError("recipes.file es obligatorio")
        if not isinstance(recipes.get("auto_migrate", True), bool):
            raise SystemConfigError("recipes.auto_migrate debe ser booleano")

        camera = cls._section_from(data, "camera")
        device = camera.get("device")
        valid_device = (
            isinstance(device, int)
            and not isinstance(device, bool)
            and device >= 0
        ) or (isinstance(device, str) and bool(device.strip()))
        if not valid_device:
            raise SystemConfigError(
                "camera.device debe ser un indice no negativo o una ruta"
            )
        for key in ("width", "height", "capture_fps", "preview_fps"):
            value = camera.get(key)
            if not cls._is_positive_number(value):
                raise SystemConfigError(f"camera.{key} debe ser mayor que cero")

        focus_mode = camera.get("default_focus_mode", "calibrated")
        if focus_mode not in cls.VALID_FOCUS_MODES:
            raise SystemConfigError(
                f"Modo de enfoque no soportado: {focus_mode}"
            )

        controller = cls._section_from(data, "controller")
        if controller.get("transport") != "serial":
            raise SystemConfigError("controller.transport debe ser 'serial'")
        if controller.get("protocol") != cls.CONTROLLER_PROTOCOL:
            raise SystemConfigError(
                "El motor solo implementa el protocolo predefinido "
                f"{cls.CONTROLLER_PROTOCOL}"
            )
        ports = controller.get("ports")
        if not isinstance(ports, dict) or not ports:
            raise SystemConfigError("controller.ports debe contener al menos un puerto")
        for platform, port in ports.items():
            if not str(platform).strip() or not str(port).strip():
                raise SystemConfigError("controller.ports contiene una entrada vacia")
        baudrate = controller.get("baudrate")
        if (
            not isinstance(baudrate, int)
            or isinstance(baudrate, bool)
            or baudrate <= 0
        ):
            raise SystemConfigError("controller.baudrate debe ser un entero positivo")
        if not cls._is_positive_number(controller.get("timeout")):
            raise SystemConfigError("controller.timeout debe ser mayor que cero")
        for key in (
            "reset_on_connect",
            "heartbeat_enabled",
            "ready_notifications_enabled",
        ):
            if not isinstance(controller.get(key), bool):
                raise SystemConfigError(f"controller.{key} debe ser booleano")

        model_map = controller.get("model_map", {})
        if not isinstance(model_map, dict):
            raise SystemConfigError("controller.model_map debe ser un objeto")
        for external_id, recipe_name in model_map.items():
            if not str(external_id).strip() or not str(recipe_name).strip():
                raise SystemConfigError(
                    "controller.model_map contiene una entrada vacia"
                )
        if recipe_names is not None:
            known = {str(name).strip() for name in recipe_names}
            unknown = sorted(
                str(name) for name in model_map.values()
                if str(name).strip() not in known
            )
            if unknown:
                raise SystemConfigError(
                    "controller.model_map referencia recetas inexistentes: "
                    + ", ".join(unknown)
                )

        runtime = cls._section_from(data, "runtime")
        for key in (
            "require_controller_ready",
            "require_controller_sync",
            "require_focus_ready",
        ):
            if not isinstance(runtime.get(key), bool):
                raise SystemConfigError(f"runtime.{key} debe ser booleano")
        if not cls._is_positive_number(runtime.get("max_frame_age_seconds")):
            raise SystemConfigError(
                "runtime.max_frame_age_seconds debe ser mayor que cero"
            )
        settle_ms = runtime.get("mechanical_settle_ms")
        if (
            not isinstance(settle_ms, int)
            or isinstance(settle_ms, bool)
            or settle_ms < 0
        ):
            raise SystemConfigError(
                "runtime.mechanical_settle_ms debe ser un entero no negativo"
            )

        return copy.deepcopy(data)

    def save(self, data, recipe_names=None):
        """Atomically persist a validated installation and keep one backup."""
        candidate = self.validate_data(data, recipe_names=recipe_names)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        bak_path = self.path.with_name(self.path.name + ".bak")

        if self.path.exists():
            shutil.copy2(self.path, bak_path)

        try:
            with tmp_path.open("w", encoding="utf-8", newline="\n") as config_file:
                json.dump(candidate, config_file, indent=4, ensure_ascii=False)
                config_file.write("\n")
            os.replace(tmp_path, self.path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        self.data = candidate
        return copy.deepcopy(candidate)

    def section(self, name):
        section = self._section_from(self.data, name)
        return copy.deepcopy(section)

    @property
    def recipe_file(self):
        return self.section("recipes")["file"]

    @property
    def auto_migrate_recipes(self):
        return bool(self.section("recipes").get("auto_migrate", True))

    def controller_port(self, platform):
        controller = self.section("controller")
        ports = controller.get("ports", {})
        if not isinstance(ports, dict):
            raise SystemConfigError("controller.ports debe ser un objeto")

        port = ports.get(platform) or ports.get("default")
        if port is None:
            raise SystemConfigError(
                f"No hay puerto del controlador para plataforma '{platform}'"
            )
        return port

    # Alias temporal para llamadas de la fase 1. No representa otro protocolo.
    def serial_port(self, platform):
        return self.controller_port(platform)
