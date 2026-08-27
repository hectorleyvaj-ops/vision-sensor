"""Persist a small deployment health state independently from READY."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


VALID_STATES = {"starting", "degraded", "ready", "stopped"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_runtime_health(path, state, *, version="", pid=None, diagnostic=""):
    """Atomically publish technical health.  It never authorizes production."""
    if state not in VALID_STATES:
        raise ValueError(f"Estado tecnico no soportado: {state}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "state": state,
        "version": str(version),
        "pid": os.getpid() if pid is None else int(pid),
        "updated_at": _now(),
        "diagnostic": str(diagnostic or ""),
    }
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return payload


def read_runtime_health(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
