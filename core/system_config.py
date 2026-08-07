import copy
import json
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
        self._validate()

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

    def _validate(self):
        if self.data.get("schema_version") != self.SCHEMA_VERSION:
            raise SystemConfigError(
                f"schema_version debe ser {self.SCHEMA_VERSION}"
            )

        installation = self.section("installation")
        if not str(installation.get("id", "")).strip():
            raise SystemConfigError("installation.id es obligatorio")

        recipes = self.section("recipes")
        recipe_file = recipes.get("file")
        if not isinstance(recipe_file, str) or not recipe_file.strip():
            raise SystemConfigError("recipes.file es obligatorio")

        camera = self.section("camera")
        for key in ("width", "height", "capture_fps", "preview_fps"):
            value = camera.get(key)
            if not isinstance(value, (int, float)) or value <= 0:
                raise SystemConfigError(f"camera.{key} debe ser mayor que cero")

        focus_mode = camera.get("default_focus_mode", "calibrated")
        if focus_mode not in self.VALID_FOCUS_MODES:
            raise SystemConfigError(
                f"Modo de enfoque no soportado: {focus_mode}"
            )

        controller = self.section("controller")
        if controller.get("transport") != "serial":
            raise SystemConfigError("controller.transport debe ser 'serial'")
        if controller.get("protocol") != self.CONTROLLER_PROTOCOL:
            raise SystemConfigError(
                "El motor solo implementa el protocolo predefinido "
                f"{self.CONTROLLER_PROTOCOL}"
            )
        model_map = controller.get("model_map", {})
        if not isinstance(model_map, dict):
            raise SystemConfigError("controller.model_map debe ser un objeto")
        for external_id, recipe_name in model_map.items():
            if not str(external_id).strip() or not str(recipe_name).strip():
                raise SystemConfigError(
                    "controller.model_map contiene una entrada vacia"
                )

        self.section("runtime")

    def section(self, name):
        section = self.data.get(name, {})
        if not isinstance(section, dict):
            raise SystemConfigError(f"La seccion '{name}' debe ser un objeto")
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
