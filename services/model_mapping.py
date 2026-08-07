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

    return raw_model if raw_model.startswith("MODELO_") else f"MODELO_{raw_model}"


def extract_model(message):
    marker = "MODEL:"
    if marker not in str(message or ""):
        return None
    return str(message).split(marker, 1)[1].strip().split("|", 1)[0].strip()
