import copy
import json
import os
from pathlib import Path


class SystemConfigError(ValueError):
    """Raised when the runtime configuration cannot be used safely."""


class SystemConfig:
    VALID_FOCUS_MODES = {
        "calibrated",
        "manual_fixed",
        "auto_continuous",
        "disabled",
    }

    def __init__(self, path="config/system.json", profile_name=None):
        self.path = Path(path)
        self.data = self._load()
        self.profile_name = (
            profile_name
            or os.getenv("VISION_PROFILE")
            or self.data.get("active_profile")
        )

        profiles = self.data.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            raise SystemConfigError("La configuracion no contiene perfiles")

        if self.profile_name not in profiles:
            available = ", ".join(sorted(profiles))
            raise SystemConfigError(
                f"Perfil '{self.profile_name}' inexistente. Disponibles: {available}"
            )

        self.profile = copy.deepcopy(profiles[self.profile_name])
        self._validate_profile()

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

        return data

    def _validate_profile(self):
        recipe_file = self.profile.get("recipe_file")
        if not isinstance(recipe_file, str) or not recipe_file.strip():
            raise SystemConfigError("El perfil requiere recipe_file")

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

        serial = self.section("serial")
        model_map = serial.get("model_map", {})
        if not isinstance(model_map, dict):
            raise SystemConfigError("serial.model_map debe ser un objeto")

        for raw_model, recipe_name in model_map.items():
            if not str(raw_model).strip() or not str(recipe_name).strip():
                raise SystemConfigError("serial.model_map contiene una entrada vacia")

    def section(self, name):
        section = self.profile.get(name, {})
        if not isinstance(section, dict):
            raise SystemConfigError(f"La seccion '{name}' debe ser un objeto")
        return copy.deepcopy(section)

    @property
    def recipe_file(self):
        return self.profile["recipe_file"]

    def serial_port(self, platform):
        serial = self.section("serial")
        ports = serial.get("ports", {})
        if not isinstance(ports, dict):
            raise SystemConfigError("serial.ports debe ser un objeto")

        port = ports.get(platform) or ports.get("default")
        if port is None:
            raise SystemConfigError(
                f"No hay puerto serial configurado para plataforma '{platform}'"
            )
        return port
