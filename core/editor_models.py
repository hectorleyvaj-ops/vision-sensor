import json

from core.step_conditions import ConditionError, validate_condition


class EditorValueError(ValueError):
    """Raised when a UI value cannot be converted to universal config data."""


def parse_camera_device(value):
    text = str(value or "").strip()
    if not text:
        raise EditorValueError("El dispositivo de camara es obligatorio")
    if text.isdigit():
        return int(text)
    return text


def build_model_map(rows):
    """Convert editable rows into a unique external-model mapping."""
    model_map = {}
    for external_id, recipe_name in rows:
        external_id = str(external_id or "").strip()
        recipe_name = str(recipe_name or "").strip()
        if not external_id and not recipe_name:
            continue
        if not external_id or not recipe_name:
            raise EditorValueError(
                "Cada mapeo requiere identificador externo y receta"
            )
        if external_id in model_map:
            raise EditorValueError(
                f"Identificador externo duplicado: {external_id}"
            )
        model_map[external_id] = recipe_name
    return model_map


def parse_condition_text(text, available_step_ids=None):
    raw = str(text or "").strip()
    if not raw:
        return {"type": "always"}
    try:
        condition = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EditorValueError(
            f"JSON de condicion invalido: {exc.msg} (linea {exc.lineno})"
        ) from exc
    try:
        validate_condition(
            condition,
            available_step_ids=available_step_ids,
        )
    except ConditionError as exc:
        raise EditorValueError(str(exc)) from exc
    return condition


def format_condition(condition):
    return json.dumps(
        condition or {"type": "always"},
        indent=2,
        ensure_ascii=False,
    )
