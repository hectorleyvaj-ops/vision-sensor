"""Hardware inventory for commissioning without owning machine I/O.

Discovery only proposes camera and serial endpoints. Selecting and persisting
one remains an explicit operator action, and the controller keeps ownership of
GPIO, polarities, sensors and machine sequencing.
"""

from pathlib import Path
import glob
import os
import time

from services.controller_protocol import PROTOCOL_VERSION, decode_message, encode_message


STX = b"\x02"
ETX = b"\x03"


def _unique(values):
    result = []
    seen = set()
    for value in values:
        key = str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def camera_candidate_devices(platform, configured_device=None, max_index=5):
    """Return deterministic endpoints to inspect, without opening them."""
    platform = str(platform or "other").lower()
    if platform == "linux":
        stable = sorted(glob.glob("/dev/v4l/by-id/*"))
        devices = stable or sorted(glob.glob("/dev/video*"))
        if configured_device not in (None, ""):
            devices.insert(0, configured_device)
        return _unique(devices)

    devices = list(range(max(0, int(max_index)) + 1))
    if configured_device not in (None, ""):
        devices.insert(0, configured_device)
    return _unique(devices)


def _camera_backends(platform, cv_module):
    platform = str(platform or "other").lower()
    if platform == "linux":
        return [("V4L2", getattr(cv_module, "CAP_V4L2", 200))]
    if platform == "windows":
        return [
            ("DSHOW", getattr(cv_module, "CAP_DSHOW", 700)),
            ("MSMF", getattr(cv_module, "CAP_MSMF", 1400)),
            ("AUTO", getattr(cv_module, "CAP_ANY", 0)),
        ]
    return [("AUTO", getattr(cv_module, "CAP_ANY", 0))]


def _same_camera(left, right):
    if left in (None, "") or right in (None, ""):
        return False
    if str(left) == str(right):
        return True
    try:
        return os.path.realpath(os.fspath(left)) == os.path.realpath(os.fspath(right))
    except TypeError:
        return False


def discover_cameras(
    platform,
    configured_device=None,
    active_info=None,
    max_index=5,
    capture_factory=None,
    cv_module=None,
):
    """Inspect camera candidates and return serializable status records."""
    if cv_module is None:
        try:
            import cv2 as cv_module  # type: ignore
        except ImportError:
            if capture_factory is None:
                raise

            class CameraConstants:
                CAP_ANY = 0
                CAP_V4L2 = 200
                CAP_DSHOW = 700
                CAP_MSMF = 1400
                CAP_PROP_FRAME_WIDTH = 3
                CAP_PROP_FRAME_HEIGHT = 4
                CAP_PROP_FPS = 5

            cv_module = CameraConstants()
    active_info = dict(active_info or {})
    capture_factory = capture_factory or cv_module.VideoCapture
    candidates = camera_candidate_devices(
        platform,
        configured_device=configured_device,
        max_index=max_index,
    )
    active_device = active_info.get("resolved_device")
    requested_active = active_info.get("requested_device")
    records = []

    for device in candidates:
        if active_info.get("camera_open") and (
            _same_camera(device, active_device)
            or _same_camera(device, requested_active)
        ):
            records.append({
                "device": device,
                "available": True,
                "verified": True,
                "active": True,
                "backend": active_info.get("capture_backend") or "ACTIVO",
                "width": active_info.get("actual_width"),
                "height": active_info.get("actual_height"),
                "fps": active_info.get("actual_fps"),
                "status": "Camara activa en esta sesion",
            })
            continue

        attempted = []
        record = None
        seen_backends = set()
        for backend_name, backend_id in _camera_backends(platform, cv_module):
            if backend_id in seen_backends:
                continue
            seen_backends.add(backend_id)
            attempted.append(backend_name)
            capture = None
            try:
                capture = capture_factory(device, backend_id)
                if capture is None or not capture.isOpened():
                    continue
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                record = {
                    "device": device,
                    "available": True,
                    "verified": True,
                    "active": False,
                    "backend": backend_name,
                    "width": int(capture.get(cv_module.CAP_PROP_FRAME_WIDTH) or 0),
                    "height": int(capture.get(cv_module.CAP_PROP_FRAME_HEIGHT) or 0),
                    "fps": float(capture.get(cv_module.CAP_PROP_FPS) or 0),
                    "status": "Entrega frames validos",
                }
                break
            except Exception as exc:
                record = {
                    "device": device,
                    "available": False,
                    "verified": False,
                    "active": False,
                    "backend": None,
                    "status": f"Error al probar: {exc}",
                }
            finally:
                if capture is not None:
                    try:
                        capture.release()
                    except Exception:
                        pass

        if record is None:
            record = {
                "device": device,
                "available": False,
                "verified": False,
                "active": False,
                "backend": None,
                "status": "No entrego frames validos",
            }
        record["attempted_backends"] = attempted
        records.append(record)

    return records


def serial_port_records(port_infos=None):
    """Normalize pyserial ListPortInfo objects for presentation and tests."""
    if port_infos is None:
        from serial.tools import list_ports  # type: ignore

        port_infos = list_ports.comports()
    port_infos = list(port_infos)
    records = []
    for info in port_infos:
        system_device = str(getattr(info, "device", "") or "").strip()
        if not system_device:
            continue
        device = system_device
        if system_device.startswith("/dev/"):
            for stable_path in sorted(glob.glob("/dev/serial/by-id/*")):
                try:
                    if os.path.realpath(stable_path) == os.path.realpath(system_device):
                        device = stable_path
                        break
                except OSError:
                    pass
        records.append({
            "device": device,
            "system_device": system_device,
            "description": str(getattr(info, "description", "") or "").strip(),
            "manufacturer": str(getattr(info, "manufacturer", "") or "").strip(),
            "vid": getattr(info, "vid", None),
            "pid": getattr(info, "pid", None),
            "serial_number": str(getattr(info, "serial_number", "") or "").strip(),
            "hwid": str(getattr(info, "hwid", "") or "").strip(),
            "available": True,
            "verified_controller": False,
            "active": False,
            "status": "Puerto detectado; controlador sin verificar",
        })
    return sorted(records, key=lambda item: item["device"])


def _read_framed_message(port, timeout):
    deadline = time.monotonic() + max(0.05, float(timeout))
    receiving = False
    payload = bytearray()
    while time.monotonic() < deadline:
        waiting = int(getattr(port, "in_waiting", 0) or 0)
        if waiting <= 0:
            time.sleep(0.005)
            continue
        value = port.read(1)
        if value == STX:
            receiving = True
            payload.clear()
        elif value == ETX and receiving:
            return payload.decode("utf-8", errors="replace").strip()
        elif receiving:
            payload.extend(value)
    return None


def probe_controller_port(
    device,
    baudrate=115200,
    timeout=0.55,
    serial_factory=None,
):
    """Perform an identity-only handshake without an explicit DTR reset."""
    if serial_factory is None:
        import serial  # type: ignore

        serial_factory = serial.Serial
    port = None
    try:
        port = serial_factory(
            port=device,
            baudrate=int(baudrate),
            timeout=0.05,
            write_timeout=max(0.1, float(timeout)),
        )
        hello = encode_message(
            "HELLO",
            proto=PROTOCOL_VERSION,
            role="VISION_ENGINE_DISCOVERY",
        )
        # Algunos adaptadores reinician la ESP32 al abrirse aunque discovery
        # no cambie DTR de forma explicita. Repetir HELLO permite que el
        # firmware termine de arrancar sin aumentar el timeout del runtime.
        raw = None
        for attempt in range(3):
            if attempt:
                time.sleep(0.20)
            try:
                port.reset_input_buffer()
            except Exception:
                pass
            port.write(STX + hello.encode("utf-8") + ETX)
            port.flush()
            raw = _read_framed_message(port, timeout)
            if raw:
                break
        if not raw:
            return {
                "verified_controller": False,
                "status": "Puerto accesible; sin HELLO_ACK compatible",
            }
        message = decode_message(raw)
        if message.kind != "HELLO_ACK":
            return {
                "verified_controller": False,
                "status": f"Respondio {message.kind}, no HELLO_ACK",
            }
        protocol = message.fields.get("PROTO")
        compatible = protocol == PROTOCOL_VERSION
        return {
            "verified_controller": compatible,
            "protocol": protocol,
            "firmware": message.fields.get("FW", "desconocido"),
            "status": (
                "Controlador vision_controller_v1 verificado"
                if compatible
                else f"Controlador con protocolo incompatible: {protocol}"
            ),
        }
    except Exception as exc:
        return {
            "available": False,
            "verified_controller": False,
            "status": f"No se pudo verificar: {exc}",
        }
    finally:
        if port is not None:
            try:
                port.close()
            except Exception:
                pass


def discover_serial_controllers(
    baudrate=115200,
    active_info=None,
    port_infos=None,
    serial_factory=None,
    probe=True,
):
    """Enumerate serial ports and identify compatible idle controllers."""
    active_info = dict(active_info or {})
    records = serial_port_records(port_infos=port_infos)
    active_port = str(active_info.get("port") or "")

    def matches_active(record):
        if not active_port:
            return False
        candidates = {str(record.get("device") or ""), str(record.get("system_device") or "")}
        if active_port in candidates:
            return True
        if active_port.startswith("/dev/"):
            return any(
                candidate.startswith("/dev/")
                and os.path.realpath(candidate) == os.path.realpath(active_port)
                for candidate in candidates
            )
        return False

    if active_port and not any(matches_active(item) for item in records):
        records.append({
            "device": active_port,
            "system_device": active_port,
            "description": "Puerto configurado (no enumerado)",
            "manufacturer": "",
            "vid": None,
            "pid": None,
            "serial_number": "",
            "hwid": "",
            "available": False,
            "verified_controller": False,
            "active": False,
            "status": "El puerto configurado no esta presente",
        })

    for record in records:
        if matches_active(record):
            record.update({
                "active": bool(active_info.get("connected")),
                "available": bool(active_info.get("connected", True)),
                "verified_controller": bool(active_info.get("synced")),
                "protocol": active_info.get("protocol"),
                "firmware": active_info.get("firmware"),
                "status": (
                    "Controlador activo y sincronizado"
                    if active_info.get("synced")
                    else "Puerto activo; handshake pendiente"
                ),
            })
            continue
        if probe:
            record.update(probe_controller_port(
                record["device"],
                baudrate=baudrate,
                serial_factory=serial_factory,
            ))
    return records


def format_camera_candidate(record):
    record = dict(record or {})
    device = record.get("device", "?")
    state = "ACTIVA" if record.get("active") else (
        "DISPONIBLE" if record.get("available") else "NO DISPONIBLE"
    )
    backend = record.get("backend") or "?"
    width = record.get("width") or "?"
    height = record.get("height") or "?"
    return f"{device} · {state} · {backend} · {width}x{height}"


def format_serial_candidate(record):
    record = dict(record or {})
    device = record.get("device", "?")
    description = record.get("description") or "Puerto serial"
    if record.get("verified_controller"):
        state = "CONTROLADOR VERIFICADO"
    elif record.get("available"):
        state = "DETECTADO"
    else:
        state = "NO DISPONIBLE"
    return f"{device} · {state} · {description}"
