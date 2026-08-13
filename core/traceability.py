import json
import os
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


def _utc_iso(timestamp=None):
    value = time.time() if timestamp is None else float(timestamp)
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="milliseconds")


def _json_safe(value):
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _json_safe(value.to_dict())
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class CycleTraceWriter:
    """Append-only JSONL cycle evidence with bounded local retention."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        directory="runtime/traceability",
        installation_id="vision-station",
        enabled=True,
        max_file_size_mb=10.0,
        retention_files=10,
        retention_days=30,
        max_file_size_bytes=None,
    ):
        self.directory = Path(directory)
        self.installation_id = str(installation_id)
        self.enabled = bool(enabled)
        self.max_file_size_bytes = (
            max(1, int(max_file_size_bytes))
            if max_file_size_bytes is not None
            else max(1024, int(float(max_file_size_mb) * 1024 * 1024))
        )
        self.retention_files = max(1, int(retention_files))
        self.retention_days = max(0, int(retention_days))
        self.active_path = self.directory / "cycles.jsonl"
        self.diagnostics_path = self.directory / "startup_diagnostics.json"
        self._lock = threading.RLock()

    @classmethod
    def from_config(cls, config, installation_id):
        values = dict(config or {})
        return cls(
            directory=values.get("directory", "runtime/traceability"),
            installation_id=installation_id,
            enabled=values.get("enabled", True),
            max_file_size_mb=values.get("max_file_size_mb", 10.0),
            retention_files=values.get("retention_files", 10),
            retention_days=values.get("retention_days", 30),
        )

    def check_storage(self):
        details = {
            "enabled": self.enabled,
            "directory": str(self.directory),
            "max_file_size_bytes": self.max_file_size_bytes,
            "retention_files": self.retention_files,
            "retention_days": self.retention_days,
        }
        if not self.enabled:
            return details
        self.directory.mkdir(parents=True, exist_ok=True)
        probe = self.directory / ".write_probe.tmp"
        try:
            with probe.open("w", encoding="utf-8") as stream:
                stream.write("ok")
            probe.unlink()
        finally:
            if probe.exists():
                probe.unlink()
        return details

    def record_cycle(
        self,
        context,
        recipe_name,
        final_result,
        pipeline_result=None,
        communication=None,
        reason=None,
    ):
        if not self.enabled:
            return None
        context = dict(context or {})
        now_wall = time.time()
        started_wall = float(context.get("started_at_wall", now_wall))
        started_monotonic = context.get("started_at")
        if started_monotonic is None:
            duration_ms = max(0.0, (now_wall - started_wall) * 1000.0)
        else:
            duration_ms = max(0.0, (time.monotonic() - float(started_monotonic)) * 1000.0)

        pipeline = _json_safe(pipeline_result or {})
        raw_results = pipeline.get("results", {}) if isinstance(pipeline, dict) else {}
        step_durations = pipeline.get("step_durations_ms", {}) if isinstance(pipeline, dict) else {}
        steps = []
        for step_id in pipeline.get("execution_order", []) if isinstance(pipeline, dict) else []:
            result = raw_results.get(step_id, {})
            steps.append({
                "step_id": step_id,
                "tool": result.get("tool"),
                "status": result.get("status"),
                "duration_ms": step_durations.get(step_id),
                "error_code": result.get("error_code"),
                "error": result.get("error"),
                "data": result.get("data"),
            })

        record = {
            "schema_version": self.SCHEMA_VERSION,
            "record_type": "vision_cycle",
            "installation_id": self.installation_id,
            "cycle_id": context.get("cycle_id"),
            "external_model": context.get("model"),
            "recipe": recipe_name,
            "started_at": _utc_iso(started_wall),
            "finished_at": _utc_iso(now_wall),
            "duration_ms": round(duration_ms, 3),
            "final_result": str(final_result or "ERROR"),
            "pipeline_status": pipeline.get("status") if isinstance(pipeline, dict) else None,
            "reason": reason,
            "execution_order": pipeline.get("execution_order", []) if isinstance(pipeline, dict) else [],
            "skipped_steps": pipeline.get("skipped_steps", []) if isinstance(pipeline, dict) else [],
            "steps": steps,
            "communication": _json_safe(communication or {}),
        }
        self._append(record)
        return record

    def _append(self, record):
        encoded = json.dumps(_json_safe(record), ensure_ascii=False, separators=(",", ":")) + "\n"
        payload = encoded.encode("utf-8")
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._prune_by_age()
            if self.active_path.exists() and self.active_path.stat().st_size + len(payload) > self.max_file_size_bytes:
                self._rotate()
            with self.active_path.open("ab") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())

    def _rotate(self):
        if self.retention_files <= 1:
            if self.active_path.exists():
                self.active_path.unlink()
            return
        oldest = self.directory / f"cycles.{self.retention_files - 1}.jsonl"
        if oldest.exists():
            oldest.unlink()
        for index in range(self.retention_files - 2, 0, -1):
            source = self.directory / f"cycles.{index}.jsonl"
            target = self.directory / f"cycles.{index + 1}.jsonl"
            if source.exists():
                os.replace(source, target)
        if self.active_path.exists():
            os.replace(self.active_path, self.directory / "cycles.1.jsonl")

    def _prune_by_age(self):
        if self.retention_days <= 0:
            return
        cutoff = time.time() - self.retention_days * 86400
        for path in self.directory.glob("cycles.*.jsonl"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except FileNotFoundError:
                pass
