"""Protocol contract between the generic vision engine and a controller.

The module has no Qt, serial, PLC or machine-specific dependency. ESP32/PLC
software is implemented separately and must conform to this contract.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from urllib.parse import quote, unquote


PROTOCOL_NAME = "vision_controller_v1"
PROTOCOL_VERSION = "1"
VALID_RESULTS = {"OK", "NG", "ERROR"}


class ProtocolError(ValueError):
    """Raised when a framed payload violates the controller contract."""


@dataclass(frozen=True)
class ProtocolMessage:
    kind: str
    fields: Dict[str, str] = field(default_factory=dict)

    def require(self, *names: str) -> "ProtocolMessage":
        missing = [name for name in names if not self.fields.get(name)]
        if missing:
            raise ProtocolError(
                f"{self.kind} requiere campos: {', '.join(missing)}"
            )
        return self


def _clean_token(value, label: str) -> str:
    token = str(value or "").strip().upper()
    if not token:
        raise ProtocolError(f"{label} no puede estar vacio")
    if any(separator in token for separator in ("|", "=")):
        raise ProtocolError(f"{label} contiene un separador reservado")
    return token


def encode_message(kind: str, **fields) -> str:
    message_kind = _clean_token(kind, "tipo de mensaje")
    parts = [message_kind]

    for raw_key, raw_value in fields.items():
        if raw_value is None:
            continue
        key = _clean_token(raw_key, "nombre de campo")
        value = quote(str(raw_value), safe="-_.:")
        parts.append(f"{key}={value}")

    return "|".join(parts)


def decode_message(payload: str) -> ProtocolMessage:
    text = str(payload or "").strip()
    if not text:
        raise ProtocolError("Mensaje vacio")

    parts = text.split("|")
    kind = _clean_token(parts[0], "tipo de mensaje")
    fields: Dict[str, str] = {}

    for item in parts[1:]:
        if "=" not in item:
            raise ProtocolError(f"Campo sin '=' en {kind}: {item}")
        raw_key, raw_value = item.split("=", 1)
        key = _clean_token(raw_key, "nombre de campo")
        if key in fields:
            raise ProtocolError(f"Campo duplicado en {kind}: {key}")
        fields[key] = unquote(raw_value)

    return ProtocolMessage(kind=kind, fields=fields)


def validate_external_model(value: str) -> str:
    """Return an opaque controller model ID without imposing A/B/C semantics."""
    return _clean_token(value, "modelo externo")


def validate_result(value: str) -> str:
    result = _clean_token(value, "resultado")
    if result not in VALID_RESULTS:
        raise ProtocolError(f"Resultado no soportado: {result}")
    return result


@dataclass
class CycleGuard:
    """Reject stale, duplicate and cross-cycle controller messages."""

    active_cycle_id: Optional[str] = None
    active_model: Optional[str] = None
    last_closed_cycle_id: Optional[str] = None

    def begin(self, cycle_id: str, model: str) -> Dict[str, str]:
        cycle = str(cycle_id or "").strip()
        if not cycle:
            raise ProtocolError("TRIGGER sin CYCLE")
        selected_model = validate_external_model(model)

        if cycle == self.last_closed_cycle_id:
            raise ProtocolError(f"Ciclo ya cerrado: {cycle}")
        if self.active_cycle_id == cycle:
            raise ProtocolError(f"Trigger duplicado: {cycle}")
        if self.active_cycle_id is not None:
            raise ProtocolError(
                f"Ya existe un ciclo activo: {self.active_cycle_id}"
            )

        self.active_cycle_id = cycle
        self.active_model = selected_model
        return {"cycle_id": cycle, "model": selected_model}

    def require_active(self, cycle_id: str) -> str:
        cycle = str(cycle_id or "").strip()
        if not cycle:
            raise ProtocolError("Mensaje sin CYCLE")
        if self.active_cycle_id is None:
            raise ProtocolError(f"No existe ciclo activo para {cycle}")
        if cycle != self.active_cycle_id:
            raise ProtocolError(
                f"Ciclo fuera de secuencia: {cycle}; activo={self.active_cycle_id}"
            )
        return cycle

    def close(self, cycle_id: str) -> str:
        cycle = self.require_active(cycle_id)
        self.last_closed_cycle_id = cycle
        self.active_cycle_id = None
        self.active_model = None
        return cycle

    def cancel(self, cycle_id: Optional[str] = None) -> Optional[str]:
        if self.active_cycle_id is None:
            return None
        if cycle_id:
            self.require_active(cycle_id)
        cycle = self.active_cycle_id
        self.last_closed_cycle_id = cycle
        self.active_cycle_id = None
        self.active_model = None
        return cycle
