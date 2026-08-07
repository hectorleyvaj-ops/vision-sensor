def normalize_model(model, model_map=None):
    raw_model = str(model or "").strip().upper()
    if not raw_model:
        return None

    normalized_map = {
        str(raw).strip().upper(): str(recipe).strip()
        for raw, recipe in (model_map or {}).items()
    }
    if normalized_map:
        return normalized_map.get(raw_model)

    return raw_model
