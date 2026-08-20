"""Stable focus-mode IDs with operator-facing Spanish labels."""


FOCUS_MODE_LABELS = {
    "calibrated": "Automatico por receta (recomendado)",
    "manual_fixed": "Valor fijo definido por el operador",
    "auto_continuous": "Autofoco continuo de la camara",
    "disabled": "Sin gestion de enfoque",
}


FOCUS_MODE_DESCRIPTIONS = {
    "calibrated": (
        "La aplicacion recorre el rango de focus_absolute, mide la nitidez de "
        "la ROI con la varianza del Laplaciano y guarda en esta receta el mejor "
        "valor. Tambien guarda un umbral inicial del 65 % para verificar el "
        "primer ciclo y recalibrar si el enfoque se degrada."
    ),
    "manual_fixed": (
        "El operador escribe un valor focus_absolute. La aplicacion lo aplica "
        "sin barrido, sin puntuacion y sin reenfoque automatico."
    ),
    "auto_continuous": (
        "La camara mantiene activo su autofocus. El valor puede variar durante "
        "la inspeccion y no se guarda una distancia de enfoque por receta."
    ),
    "disabled": (
        "El motor no modifica el enfoque de la camara. Util para lentes fijos "
        "o dispositivos que no exponen controles de enfoque."
    ),
}


def focus_mode_label(mode):
    return FOCUS_MODE_LABELS.get(str(mode or ""), str(mode or "Desconocido"))


def focus_mode_description(mode):
    value = str(mode or "")
    return FOCUS_MODE_DESCRIPTIONS.get(
        value,
        "Modo de enfoque no reconocido.",
    )
