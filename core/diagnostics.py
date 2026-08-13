import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


VALID_DIAGNOSTIC_STATUSES = {"PASS", "WARNING", "ERROR"}


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class DiagnosticsManager:
    """Thread-safe, persisted health report for one installation.

    Checks are keyed so camera/serial workers can replace their startup state
    instead of appending an unbounded history.  Only ERROR items explicitly
    marked as blocking prevent READY.
    """

    SCHEMA_VERSION = 1

    def __init__(self, report_path):
        self.report_path = Path(report_path)
        self._items = {}
        self._lock = threading.RLock()
        self.last_persist_error = None

    def update(
        self,
        key,
        status,
        component,
        message,
        action="",
        details=None,
        blocking=False,
    ):
        normalized_status = str(status or "").strip().upper()
        if normalized_status not in VALID_DIAGNOSTIC_STATUSES:
            raise ValueError(f"Estado de diagnostico no soportado: {status}")
        item = {
            "key": str(key),
            "status": normalized_status,
            "component": str(component),
            "message": str(message),
            "action": str(action or ""),
            "blocking": bool(blocking and normalized_status == "ERROR"),
            "details": dict(details or {}),
            "updated_at": utc_now_iso(),
        }
        with self._lock:
            self._items[item["key"]] = item
            try:
                self._persist_locked()
                self.last_persist_error = None
            except OSError as exc:
                # Runtime health must remain available in memory even when the
                # storage failure being diagnosed prevents report persistence.
                self.last_persist_error = str(exc)
        return dict(item)

    def snapshot(self):
        with self._lock:
            items = [dict(item) for item in self._items.values()]
        items.sort(key=lambda item: item["key"])
        if any(item["status"] == "ERROR" for item in items):
            overall = "ERROR"
        elif any(item["status"] == "WARNING" for item in items):
            overall = "WARNING"
        else:
            overall = "PASS"
        return {
            "schema_version": self.SCHEMA_VERSION,
            "generated_at": utc_now_iso(),
            "overall_status": overall,
            "blocking": any(item["blocking"] for item in items),
            "items": items,
        }

    def blocking_reason(self):
        with self._lock:
            blocking = [
                item for item in self._items.values()
                if item.get("blocking")
            ]
        if not blocking:
            return None
        blocking.sort(key=lambda item: item["key"])
        item = blocking[0]
        if item.get("action"):
            return f"{item['message']}. Accion: {item['action']}"
        return item["message"]

    def _persist_locked(self):
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.report_path.with_name(self.report_path.name + ".tmp")
        payload = self.snapshot()
        try:
            with tmp_path.open("w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
            os.replace(tmp_path, self.report_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


def run_static_diagnostics(
    manager,
    system_config,
    recipe_manager,
    tool_registry,
    trace_writer,
    platform,
):
    """Validate files and declarative resources before production starts."""
    config_path = Path(system_config.path)
    manager.update(
        "config.system",
        "PASS",
        "configuration",
        f"Configuracion valida: {config_path}",
        details={"path": str(config_path), "schema_version": system_config.SCHEMA_VERSION},
    )

    recipe_path = Path(recipe_manager.path)
    try:
        recipes = recipe_manager.get_all()
        manager.update(
            "recipes.catalog",
            "PASS",
            "recipes",
            f"Catalogo de recetas legible: {recipe_path}",
            details={"path": str(recipe_path), "recipes": len(recipes)},
        )
    except Exception as exc:
        recipes = []
        manager.update(
            "recipes.catalog",
            "ERROR",
            "recipes",
            f"No se pudo cargar el catalogo de recetas: {exc}",
            action="Restaura el JSON o su respaldo .bak y reinicia la aplicacion",
            details={"path": str(recipe_path)},
            blocking=True,
        )

    recipe_names = {
        recipe.get("name") for recipe in recipes
        if isinstance(recipe, dict) and recipe.get("name")
    }
    if not recipes:
        manager.update(
            "recipes.available",
            "ERROR",
            "recipes",
            "El catalogo no contiene recetas",
            action="Crea o importa al menos una receta antes de producir",
            blocking=True,
        )
    else:
        manager.update(
            "recipes.available",
            "PASS",
            "recipes",
            f"Catalogo con {len(recipes)} receta(s)",
            details={"recipes": sorted(recipe_names)},
        )
    model_map = system_config.section("controller").get("model_map", {})
    missing_targets = sorted({
        recipe_name for recipe_name in model_map.values()
        if recipe_name not in recipe_names
    })
    if missing_targets:
        manager.update(
            "recipes.model_map",
            "ERROR",
            "recipes",
            "El mapeo del controlador apunta a recetas inexistentes",
            action="Corrige controller.model_map o crea las recetas indicadas",
            details={"missing_recipes": missing_targets},
            blocking=True,
        )
    else:
        manager.update(
            "recipes.model_map",
            "PASS",
            "recipes",
            "Todos los modelos externos apuntan a recetas existentes",
            details={"mappings": len(model_map)},
        )

    available_tools = set(tool_registry)
    manager.update(
        "tools.registry",
        "PASS" if available_tools else "ERROR",
        "tools",
        f"Herramientas registradas: {', '.join(sorted(available_tools)) or 'ninguna'}",
        action="Registra al menos una herramienta antes de producir",
        details={"tools": sorted(available_tools)},
        blocking=not available_tools,
    )

    for recipe in recipes:
        if not isinstance(recipe, dict):
            continue
        recipe_name = str(recipe.get("name") or "sin_nombre")
        commissioned = recipe.get("commissioned") is True
        commissioning_error = recipe_manager.get_commissioning_error(
            recipe,
            available_tools=available_tools,
        )
        missing_tools = []
        missing_templates = []
        unreadable_templates = []
        for step in recipe.get("steps", []):
            if not isinstance(step, dict) or not step.get("enabled", True):
                continue
            tool_name = step.get("tool")
            if tool_name not in available_tools:
                missing_tools.append({"step": step.get("id"), "tool": tool_name})
            if tool_name != "img_hist":
                continue
            for raw_path in step.get("params", {}).get("template_paths", []):
                template_path = Path(str(raw_path))
                if not template_path.is_file():
                    missing_templates.append(str(template_path))
                elif not os.access(template_path, os.R_OK) or template_path.stat().st_size <= 0:
                    unreadable_templates.append(str(template_path))

        problems = []
        if missing_tools:
            problems.append("herramientas no registradas")
        if missing_templates:
            problems.append("imagenes maestras inexistentes")
        if unreadable_templates:
            problems.append("imagenes maestras no legibles")
        if commissioning_error:
            problems.append("definicion de receta incompleta")
        if problems:
            manager.update(
                f"recipe.resources.{recipe_name}",
                "ERROR" if commissioned else "WARNING",
                "recipes",
                f"Receta {recipe_name}: {', '.join(problems)}",
                action="Corrige los recursos y vuelve a comisionar la receta",
                details={
                    "commissioned": commissioned,
                    "missing_tools": missing_tools,
                    "missing_templates": missing_templates,
                    "unreadable_templates": unreadable_templates,
                    "commissioning_error": commissioning_error,
                },
                blocking=commissioned,
            )
        else:
            manager.update(
                f"recipe.resources.{recipe_name}",
                "PASS",
                "recipes",
                f"Recursos disponibles para la receta {recipe_name}",
                details={"commissioned": commissioned},
            )

    try:
        storage_details = trace_writer.check_storage()
        manager.update(
            "traceability.storage",
            "PASS" if trace_writer.enabled else "WARNING",
            "traceability",
            "Almacenamiento de trazabilidad disponible"
            if trace_writer.enabled else "Trazabilidad de ciclos deshabilitada",
            action="Habilita traceability.enabled para conservar evidencia de produccion",
            details=storage_details,
        )
    except OSError as exc:
        manager.update(
            "traceability.storage",
            "ERROR",
            "traceability",
            f"No se puede escribir la trazabilidad: {exc}",
            action="Corrige la ruta o los permisos del directorio de trazabilidad",
            details={"directory": str(trace_writer.directory)},
            blocking=trace_writer.enabled,
        )

    controller = system_config.section("controller")
    try:
        port = system_config.controller_port(platform)
        manager.update(
            "controller.configuration",
            "WARNING",
            "controller",
            f"Controlador configurado en {port}; conexion pendiente",
            details={
                "port": port,
                "baudrate": controller.get("baudrate"),
                "protocol": controller.get("protocol"),
            },
        )
    except Exception as exc:
        manager.update(
            "controller.configuration",
            "ERROR",
            "controller",
            str(exc),
            action=f"Agrega un puerto para la plataforma {platform}",
            blocking=True,
        )

    camera = system_config.section("camera")
    manager.update(
        "camera.runtime",
        "WARNING",
        "camera",
        "Camara configurada; apertura y formato real pendientes",
        details={
            "requested_device": camera.get("device"),
            "requested_width": camera.get("width"),
            "requested_height": camera.get("height"),
            "requested_fps": camera.get("capture_fps"),
        },
    )
    return manager.snapshot()
