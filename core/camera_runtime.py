"""Pure presentation and validation helpers for camera runtime state."""


def control_value_matches(requested, actual):
    if actual is None:
        return False
    try:
        return int(actual) == int(requested)
    except (TypeError, ValueError):
        return False


def manual_focus_preflight(info):
    info = dict(info or {})
    if info.get("platform") != "linux":
        return False, "La calibracion manual requiere Linux/V4L2."
    if not info.get("camera_open"):
        return False, "La camara activa no esta abierta. Revisa el dispositivo y reinicia."
    if not info.get("resolved_device"):
        return False, "No se resolvio un dispositivo /dev/video*."
    if not info.get("v4l2_available"):
        return False, "v4l2-ctl no esta disponible o no pudo leer los controles."
    if not info.get("focus_absolute_supported"):
        return False, "La camara activa no expone el control focus_absolute."
    return True, "Camara lista para calibracion manual."


def format_camera_runtime(info):
    info = dict(info or {})
    requested = info.get("requested_device", "?")
    resolved = info.get("resolved_device") or "sin resolver"
    width = info.get("actual_width") or "?"
    height = info.get("actual_height") or "?"
    focus = "si" if info.get("focus_absolute_supported") else "no"
    return (
        f"Camara solicitada: {requested} | activa: {resolved} | "
        f"formato: {width}x{height} | focus_absolute: {focus}"
    )
