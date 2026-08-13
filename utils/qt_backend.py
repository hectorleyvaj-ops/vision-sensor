"""Pure selection policy for the supported Qt bindings."""


def normalize_qt_request(value):
    normalized = str(value or "auto").strip().lower()
    aliases = {
        "auto": "auto",
        "pyside6": "PySide6",
        "pyqt5": "PyQt5",
    }
    if normalized not in aliases:
        raise ValueError(
            "VISION_QT_API debe ser auto, pyside6 o pyqt5; "
            f"valor recibido: {normalized!r}"
        )
    return aliases[normalized]


def backend_order(requested="auto"):
    selected = normalize_qt_request(requested)
    if selected == "auto":
        return ("PySide6", "PyQt5")
    return (selected,)
