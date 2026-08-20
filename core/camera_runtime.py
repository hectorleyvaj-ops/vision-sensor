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
        detail = info.get("error") or "La camara activa no esta abierta"
        return False, f"{detail}. Revisa el dispositivo y reinicia."
    if not info.get("resolved_device"):
        return False, "No se resolvio un dispositivo /dev/video*."
    if info.get("v4l2_tool_available") is False:
        return False, (
            "Falta la utilidad v4l2-ctl. No es el driver de la camara: "
            "instala el paquete con 'sudo apt install v4l-utils' y reinicia "
            "la aplicacion."
        )
    if not info.get("v4l2_available"):
        detail = str(info.get("v4l2_error") or "").strip()
        suffix = f" Detalle: {detail}" if detail else ""
        return False, (
            "v4l2-ctl esta instalado, pero no pudo leer los controles de la "
            f"camara activa.{suffix}"
        )
    if not info.get("focus_absolute_supported"):
        return False, "La camara activa no expone el control focus_absolute."
    return True, "Camara lista para calibracion manual."


def format_camera_runtime(info):
    info = dict(info or {})
    requested = info.get("requested_device")
    if requested in (None, ""):
        requested = "sin asignar"
    resolved = info.get("resolved_device") or "sin resolver"
    width = info.get("actual_width") or "?"
    height = info.get("actual_height") or "?"
    focus = "si" if info.get("focus_absolute_supported") else "no"
    if info.get("platform") == "linux":
        tool = "si" if info.get("v4l2_tool_available") else "no"
        tool_text = f" | v4l2-ctl: {tool}"
    else:
        tool_text = ""
    state = "ABIERTA" if info.get("camera_open") else "NO DISPONIBLE"
    backend = info.get("capture_backend") or "?"
    error = str(info.get("error") or "").strip()
    error_text = f" | detalle: {error}" if error else ""
    return (
        f"Camara solicitada: {requested} | activa: {resolved} | estado: {state} | "
        f"backend: {backend} | formato: {width}x{height} | "
        f"focus_absolute: {focus}{tool_text}{error_text}"
    )
