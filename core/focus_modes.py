"""Stable focus-mode IDs with operator-facing Spanish labels."""


FOCUS_MODE_LABELS = {
    "calibrated": "Calibrado por receta",
    "manual_fixed": "Valor manual fijo",
    "auto_continuous": "Enfoque automático continuo",
    "disabled": "Sin control de enfoque",
}


def focus_mode_label(mode):
    return FOCUS_MODE_LABELS.get(str(mode or ""), str(mode or "Desconocido"))
