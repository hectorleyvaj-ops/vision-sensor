"""Offline validation for an external installation package.

This command never opens the camera or serial port and never edits recipes.
It validates the generic engine contracts plus the requirements declared by an
installation-owned ``commissioning.json`` manifest.
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.recipe_manager import RecipeManager
from core.system_config import SystemConfig, SystemConfigError
from tools.registry import discover_tool_registry


MANIFEST_SCHEMA_VERSION = 1


def _read_json(path, label):
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            value = json.load(stream)
    except FileNotFoundError as exc:
        raise ValueError(f"No existe {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON invalido en {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"La raiz de {label} debe ser un objeto")
    return value


def _resolve(base, value):
    path = Path(str(value))
    return path if path.is_absolute() else (Path(base) / path).resolve()


def _is_missing(value):
    return value is None or value == "" or value == []


def _rule_passes(actual, operator, expected):
    if operator == "eq":
        return actual == expected
    if operator == "gt":
        return actual is not None and actual > expected
    if operator == "ge":
        return actual is not None and actual >= expected
    raise ValueError(f"Operador de regla no soportado: {operator}")


def validate_installation(manifest_path):
    """Return a deterministic report without accessing physical hardware."""
    manifest_path = Path(manifest_path).resolve()
    report = {
        "manifest": str(manifest_path),
        "installation": None,
        "errors": [],
        "pending": [],
        "passes": [],
        "ready_for_commissioning": False,
        "ready_for_production": False,
    }

    def add(bucket, code, message, **details):
        item = {"code": code, "message": message}
        if details:
            item["details"] = details
        report[bucket].append(item)

    try:
        manifest = _read_json(manifest_path, "commissioning.json")
    except ValueError as exc:
        add("errors", "MANIFEST_UNREADABLE", str(exc))
        return report

    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        add(
            "errors",
            "MANIFEST_SCHEMA",
            f"schema_version de commissioning.json debe ser {MANIFEST_SCHEMA_VERSION}",
        )
        return report

    package_dir = manifest_path.parent
    project_root = _resolve(package_dir, manifest.get("project_root", "."))
    system_value = manifest.get("system_config")
    if not isinstance(system_value, str) or not system_value.strip():
        add("errors", "SYSTEM_PATH", "system_config es obligatorio en el manifiesto")
        return report
    system_path = _resolve(package_dir, system_value)

    try:
        system_config = SystemConfig(system_path)
    except (SystemConfigError, OSError) as exc:
        add("errors", "SYSTEM_CONFIG", str(exc))
        return report

    installation = system_config.section("installation")
    report["installation"] = installation.get("id")
    add(
        "passes",
        "SYSTEM_CONFIG",
        f"Configuracion valida para {installation.get('name', installation.get('id'))}",
        path=str(system_path),
    )

    recipe_path = _resolve(project_root, system_config.recipe_file)
    if not recipe_path.is_file():
        add("errors", "RECIPES_MISSING", f"No existe el catalogo: {recipe_path}")
        return report

    registry = discover_tool_registry()
    if registry.discovery_errors:
        add(
            "errors",
            "TOOL_DISCOVERY",
            "Una o mas herramientas no pudieron cargarse",
            discovery_errors=registry.discovery_errors,
        )
    elif not registry:
        add("errors", "TOOL_DISCOVERY", "No hay herramientas registradas")
    else:
        add(
            "passes",
            "TOOL_DISCOVERY",
            "Catalogo de herramientas disponible",
            tools=sorted(registry),
        )

    try:
        recipe_manager = RecipeManager(
            recipe_path,
            auto_migrate=False,
            tool_registry=registry,
        )
        recipes = recipe_manager.get_all()
    except Exception as exc:
        add("errors", "RECIPES_INVALID", f"No se pudo cargar el catalogo: {exc}")
        return report

    names = [recipe.get("name") for recipe in recipes if isinstance(recipe, dict)]
    ids = [recipe.get("id") for recipe in recipes if isinstance(recipe, dict)]
    if len(names) != len(set(names)):
        add("errors", "DUPLICATE_RECIPE_NAME", "Hay nombres de receta duplicados")
    if len(ids) != len(set(ids)):
        add("errors", "DUPLICATE_RECIPE_ID", "Hay IDs de receta duplicados")
    selected = [
        recipe.get("name")
        for recipe in recipes
        if isinstance(recipe, dict) and recipe.get("selected")
    ]
    allow_empty_recipes = manifest.get("allow_empty_recipes") is True
    if recipes and len(selected) != 1:
        add(
            "errors",
            "RECIPE_SELECTION",
            "Debe existir exactamente una receta seleccionada",
            selected=selected,
        )
    elif not recipes and not allow_empty_recipes:
        add(
            "errors",
            "RECIPE_SELECTION",
            "El catalogo no contiene recetas y el manifiesto no lo permite",
        )

    try:
        SystemConfig.validate_data(system_config.data, recipe_names=names)
    except SystemConfigError as exc:
        add("errors", "MODEL_MAP", str(exc))

    recipes_by_name = {
        recipe.get("name"): recipe
        for recipe in recipes
        if isinstance(recipe, dict) and recipe.get("name")
    }
    model_map = system_config.section("controller").get("model_map", {})
    required_models = manifest.get("required_models", [])
    required_map = {}
    for model in required_models:
        if not isinstance(model, dict):
            add("errors", "MODEL_DECLARATION", "Modelo requerido invalido")
            continue
        external_id = str(model.get("external_id", "")).strip()
        recipe_name = str(model.get("recipe", "")).strip()
        part_number = str(model.get("part_number", "")).strip()
        if not external_id or not recipe_name or not part_number:
            add(
                "errors",
                "MODEL_DECLARATION",
                "Cada modelo requiere external_id, recipe y part_number",
                model=model,
            )
            continue
        required_map[external_id] = recipe_name
        if model_map.get(external_id) != recipe_name:
            add(
                "errors",
                "MODEL_MAPPING",
                f"El modelo externo {external_id} debe apuntar a {recipe_name}",
            )
            continue
        recipe = recipes_by_name.get(recipe_name)
        if recipe is None:
            add("errors", "MODEL_RECIPE", f"No existe la receta {recipe_name}")
            continue
        machine = recipe.get("machine", {})
        if machine.get("external_model") != external_id:
            add(
                "errors",
                "MODEL_METADATA",
                f"{recipe_name} no declara external_model={external_id}",
            )
        if machine.get("part_number") != part_number:
            add(
                "errors",
                "PART_NUMBER",
                f"{recipe_name} no declara part_number={part_number}",
            )

    if manifest.get("exact_model_map") is True and model_map != required_map:
        add(
            "errors",
            "EXACT_MODEL_MAP",
            "controller.model_map no coincide exactamente con el manifiesto",
            expected=required_map,
            actual=model_map,
        )
    elif required_map:
        add(
            "passes",
            "MODEL_MAP",
            "Mapeo externo coincide con el manifiesto",
            mappings=required_map,
        )

    policy = manifest.get("recipe_policy", {})
    if not isinstance(policy, dict):
        add("errors", "RECIPE_POLICY", "recipe_policy debe ser un objeto")
        policy = {}
    required_tools = set(policy.get("required_tools", []))
    required_focus_fields = policy.get("required_focus_fields", [])
    parameter_rules = policy.get("parameter_rules", [])

    for recipe_name in required_map.values():
        recipe = recipes_by_name.get(recipe_name)
        if recipe is None:
            continue
        commissioned = recipe.get("commissioned") is True
        try:
            recipe_manager.validate(recipe)
        except ValueError as exc:
            add("errors", "RECIPE_STRUCTURE", f"{recipe_name}: {exc}")
            continue

        active_steps = [
            step for step in recipe.get("steps", [])
            if isinstance(step, dict) and step.get("enabled", True)
        ]
        active_tools = {step.get("tool") for step in active_steps}
        missing_tools = sorted(required_tools - active_tools)
        if missing_tools:
            add(
                "errors" if commissioned else "pending",
                "REQUIRED_TOOLS",
                f"{recipe_name}: faltan herramientas habilitadas",
                tools=missing_tools,
            )

        for step in active_steps:
            tool_id = step.get("tool")
            step_id = step.get("id")
            params = step.get("params", {})
            if tool_id not in registry:
                add(
                    "errors",
                    "UNKNOWN_TOOL",
                    f"{recipe_name}/{step_id}: herramienta no registrada {tool_id}",
                )
                continue
            parameter_errors = registry.validate_params(
                tool_id,
                params,
                commissioning=True,
            )
            for error in parameter_errors:
                bucket = "errors" if commissioned else "pending"
                add(
                    bucket,
                    "TOOL_COMMISSIONING",
                    f"{recipe_name}/{step_id}: {error}",
                )
            for resource in registry.resource_paths(tool_id, params):
                resource_path = _resolve(project_root, resource["path"])
                if not resource_path.is_file() or resource_path.stat().st_size <= 0:
                    bucket = "errors" if commissioned else "pending"
                    add(
                        bucket,
                        "RESOURCE_UNAVAILABLE",
                        f"{recipe_name}/{step_id}: recurso ausente o vacio",
                        path=str(resource_path),
                    )

        for rule in parameter_rules:
            if not isinstance(rule, dict):
                add("errors", "PARAMETER_RULE", "Regla de parametro invalida")
                continue
            tool_id = rule.get("tool")
            parameter = rule.get("parameter")
            operator = rule.get("operator", "eq")
            expected = rule.get("value")
            matching_steps = [step for step in active_steps if step.get("tool") == tool_id]
            for step in matching_steps:
                actual = step.get("params", {}).get(parameter)
                try:
                    valid = _rule_passes(actual, operator, expected)
                except (TypeError, ValueError) as exc:
                    add("errors", "PARAMETER_RULE", str(exc), rule=rule)
                    continue
                if not valid:
                    bucket = "errors" if commissioned else "pending"
                    add(
                        bucket,
                        "PARAMETER_RULE",
                        f"{recipe_name}/{step.get('id')}: {parameter} debe cumplir {operator} {expected}",
                        actual=actual,
                    )

        if policy.get("require_calibrated_focus") is True:
            focus = recipe.get("focus", {})
            focus_missing = [
                field for field in required_focus_fields
                if _is_missing(focus.get(field))
            ]
            focus_ready = (
                focus.get("enabled") is True
                and focus.get("mode") == "calibrated"
                and not focus_missing
            )
            if not focus_ready:
                bucket = "errors" if commissioned else "pending"
                add(
                    bucket,
                    "FOCUS_COMMISSIONING",
                    f"{recipe_name}: enfoque calibrado pendiente",
                    missing_fields=focus_missing,
                )

        commissioning_error = recipe_manager.get_commissioning_error(
            recipe,
            available_tools=registry,
        )
        if commissioned and commissioning_error:
            add(
                "errors",
                "UNSAFE_COMMISSIONED_RECIPE",
                f"{recipe_name} esta comisionada pero es incompleta: {commissioning_error}",
            )
        elif not commissioned:
            add(
                "pending",
                "RECIPE_NOT_COMMISSIONED",
                f"{recipe_name} permanece bloqueada hasta completar calibracion",
            )

    report["ready_for_commissioning"] = not report["errors"]
    report["ready_for_production"] = (
        not report["errors"]
        and not report["pending"]
        and (bool(required_map) or allow_empty_recipes)
    )
    return report


def _print_human(report):
    print(f"Instalacion: {report.get('installation') or 'desconocida'}")
    for bucket, label in (
        ("passes", "PASS"),
        ("pending", "PENDIENTE"),
        ("errors", "ERROR"),
    ):
        for item in report[bucket]:
            print(f"[{label}] {item['code']}: {item['message']}")
    print(
        "Resultado: "
        + (
            "LISTA PARA PRODUCCION"
            if report["ready_for_production"]
            else "LISTA PARA CALIBRAR"
            if report["ready_for_commissioning"]
            else "PAQUETE INVALIDO"
        )
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Valida una instalacion externa sin acceder al hardware",
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        default="installations/worksurface/commissioning.json",
        help="Ruta al commissioning.json de la instalacion",
    )
    parser.add_argument(
        "--require-commissioned",
        action="store_true",
        help="Falla si quedan calibraciones o recetas pendientes",
    )
    parser.add_argument("--json", action="store_true", help="Salida JSON")
    args = parser.parse_args(argv)

    report = validate_installation(args.manifest)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _print_human(report)

    if report["errors"]:
        return 2
    if args.require_commissioned and not report["ready_for_production"]:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
