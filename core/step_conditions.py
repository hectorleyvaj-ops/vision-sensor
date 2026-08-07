class ConditionError(ValueError):
    """Raised when a recipe step condition is invalid."""


def _read_path(source, path):
    value = source
    for part in str(path or "").split("."):
        if not part or not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def evaluate_condition(condition, results, context):
    """Evaluate the small declarative condition language used by recipes."""
    condition = condition or {"type": "always"}
    if not isinstance(condition, dict):
        raise ConditionError("La condicion debe ser un objeto")

    condition_type = str(condition.get("type", "always")).strip().lower()

    if condition_type == "always":
        return True

    if condition_type == "step_success":
        step_id = str(condition.get("step_id", "")).strip()
        if not step_id:
            raise ConditionError("step_success requiere step_id")
        result = results.get(step_id)
        if result is None:
            return False
        expected = bool(condition.get("equals", True))
        return bool(getattr(result, "success", False)) is expected

    if condition_type == "context_equals":
        path = str(condition.get("path", "")).strip()
        if not path:
            raise ConditionError("context_equals requiere path")
        return _read_path(context, path) == condition.get("value")

    if condition_type in ("all", "any"):
        items = condition.get("conditions")
        if not isinstance(items, list) or not items:
            raise ConditionError(f"{condition_type} requiere conditions")
        values = [evaluate_condition(item, results, context) for item in items]
        return all(values) if condition_type == "all" else any(values)

    if condition_type == "not":
        if "condition" not in condition:
            raise ConditionError("not requiere condition")
        return not evaluate_condition(condition["condition"], results, context)

    raise ConditionError(f"Tipo de condicion no soportado: {condition_type}")
