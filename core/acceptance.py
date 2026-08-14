"""Installation-owned acceptance sessions and deterministic evaluation.

The engine never changes recipe parameters or ``commissioned`` from here.
Acceptance consumes traceability and physical-test evidence, then reports
whether an installation is ready for a human to commission from the UI.
"""

import copy
import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PLAN_SCHEMA_VERSION = 1
SESSION_SCHEMA_VERSION = 1
VALID_OBSERVED_RESULTS = {"OK", "NG", "ERROR", "CANCELLED"}
VALID_SCENARIO_STATES = {"PASS", "FAIL", "PENDING"}


class AcceptanceError(ValueError):
    """Raised when a plan, session or evidence record is invalid."""


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _read_json(path, label):
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
    except FileNotFoundError as exc:
        raise AcceptanceError(f"No existe {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AcceptanceError(f"JSON invalido en {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AcceptanceError(f"La raiz de {label} debe ser un objeto")
    return value


def _bounded_rate(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AcceptanceError(f"{label} debe ser numerico")
    result = float(value)
    if result < 0.0 or result > 1.0:
        raise AcceptanceError(f"{label} debe estar entre 0 y 1")
    return result


def _non_negative_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AcceptanceError(f"{label} debe ser entero no negativo")
    return value


def _positive_number(value, label):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value <= 0
    ):
        raise AcceptanceError(f"{label} debe ser mayor que cero")
    return float(value)


def _non_negative_number(value, label):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value < 0
    ):
        raise AcceptanceError(f"{label} debe ser mayor o igual que cero")
    return float(value)


def _canonical_from(values, requested, label):
    text = str(requested or "").strip()
    matches = {str(value).upper(): str(value) for value in values}
    canonical = matches.get(text.upper())
    if canonical is None:
        raise AcceptanceError(
            f"{label} no configurado: {text or '<vacio>'}; "
            f"permitidos={', '.join(str(value) for value in values)}"
        )
    return canonical


@dataclass(frozen=True)
class AcceptancePlan:
    path: Path
    installation_id: str
    models: tuple
    trial_classes: tuple
    minimum_trials: dict
    max_false_accepts: int
    max_false_reject_rate: float
    max_execution_errors: int
    max_p95_cycle_ms: float
    require_safe_output_for_non_ok: bool
    scenarios: dict
    evidence_files: tuple
    configuration_fingerprint: str


def _configuration_fingerprint(plan_path, evidence_values):
    hasher = hashlib.sha256()
    resolved_files = []
    entries = [("acceptance.json", Path(plan_path))]
    for value in evidence_values:
        if not isinstance(value, str) or not value.strip():
            raise AcceptanceError("Cada evidence_file debe ser una ruta no vacia")
        evidence_path = Path(value)
        if not evidence_path.is_absolute():
            evidence_path = (Path(plan_path).parent / evidence_path).resolve()
        entries.append((value, evidence_path))
    for label, evidence_path in entries:
        if not evidence_path.is_file():
            raise AcceptanceError(f"No existe evidence_file: {evidence_path}")
        hasher.update(label.encode("utf-8"))
        hasher.update(b"\0")
        with evidence_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(65536), b""):
                hasher.update(chunk)
        hasher.update(b"\0")
        if label != "acceptance.json":
            resolved_files.append(str(evidence_path))
    return tuple(resolved_files), hasher.hexdigest()


def load_acceptance_plan(path):
    path = Path(path).resolve()
    data = _read_json(path, "plan de aceptacion")
    if data.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise AcceptanceError(
            f"schema_version del plan debe ser {PLAN_SCHEMA_VERSION}"
        )

    installation_id = str(data.get("installation_id", "")).strip()
    if not installation_id:
        raise AcceptanceError("installation_id es obligatorio")

    manifest_value = data.get("installation_manifest")
    if not isinstance(manifest_value, str) or not manifest_value.strip():
        raise AcceptanceError("installation_manifest es obligatorio")
    manifest_path = Path(manifest_value)
    if not manifest_path.is_absolute():
        manifest_path = (path.parent / manifest_path).resolve()
    manifest = _read_json(manifest_path, "commissioning.json")

    models = []
    for item in manifest.get("required_models", []):
        if not isinstance(item, dict):
            continue
        external_id = str(item.get("external_id", "")).strip()
        if external_id and external_id not in models:
            models.append(external_id)
    if not models:
        raise AcceptanceError("El manifiesto no declara modelos requeridos")

    criteria = data.get("criteria")
    if not isinstance(criteria, dict):
        raise AcceptanceError("criteria debe ser un objeto")

    minimum_raw = criteria.get("minimum_trials_per_model", {})
    if not isinstance(minimum_raw, dict) or not minimum_raw:
        raise AcceptanceError("minimum_trials_per_model debe ser un objeto")
    minimum_trials = {}
    for raw_class, raw_count in minimum_raw.items():
        trial_class = str(raw_class).strip().upper()
        if trial_class not in {"OK", "NG"}:
            raise AcceptanceError(
                f"Clase de prueba no soportada: {trial_class}"
            )
        count = _non_negative_int(
            raw_count,
            f"minimum_trials_per_model.{trial_class}",
        )
        if count == 0:
            raise AcceptanceError(
                f"minimum_trials_per_model.{trial_class} debe ser mayor que cero"
            )
        minimum_trials[trial_class] = count
    if set(minimum_trials) != {"OK", "NG"}:
        raise AcceptanceError(
            "minimum_trials_per_model debe declarar poblaciones OK y NG"
        )

    raw_scenarios = data.get("required_scenarios", [])
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise AcceptanceError("required_scenarios debe ser una lista no vacia")
    scenarios = {}
    for item in raw_scenarios:
        if not isinstance(item, dict):
            raise AcceptanceError("Escenario de aceptacion invalido")
        scenario_id = str(item.get("id", "")).strip()
        description = str(item.get("description", "")).strip()
        if not scenario_id or not description:
            raise AcceptanceError("Cada escenario requiere id y description")
        if scenario_id in scenarios:
            raise AcceptanceError(f"Escenario duplicado: {scenario_id}")
        scenarios[scenario_id] = copy.deepcopy(item)

    require_safe = criteria.get("require_safe_output_for_non_ok", False)
    if not isinstance(require_safe, bool):
        raise AcceptanceError(
            "criteria.require_safe_output_for_non_ok debe ser booleano"
        )

    evidence_values = data.get("evidence_files")
    if not isinstance(evidence_values, list) or not evidence_values:
        raise AcceptanceError("evidence_files debe ser una lista no vacia")
    evidence_files, fingerprint = _configuration_fingerprint(
        path,
        evidence_values,
    )

    return AcceptancePlan(
        path=path,
        installation_id=installation_id,
        models=tuple(models),
        trial_classes=tuple(minimum_trials),
        minimum_trials=minimum_trials,
        max_false_accepts=_non_negative_int(
            criteria.get("max_false_accepts", 0),
            "criteria.max_false_accepts",
        ),
        max_false_reject_rate=_bounded_rate(
            criteria.get("max_false_reject_rate", 0.0),
            "criteria.max_false_reject_rate",
        ),
        max_execution_errors=_non_negative_int(
            criteria.get("max_execution_errors", 0),
            "criteria.max_execution_errors",
        ),
        max_p95_cycle_ms=_positive_number(
            criteria.get("max_p95_cycle_ms"),
            "criteria.max_p95_cycle_ms",
        ),
        require_safe_output_for_non_ok=require_safe,
        scenarios=scenarios,
        evidence_files=evidence_files,
        configuration_fingerprint=fingerprint,
    )


def new_acceptance_session(plan, operator="", station="", notes=""):
    return {
        "schema_version": SESSION_SCHEMA_VERSION,
        "record_type": "acceptance_session",
        "session_id": uuid.uuid4().hex,
        "installation_id": plan.installation_id,
        "plan": plan.path.name,
        "configuration_fingerprint": plan.configuration_fingerprint,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "metadata": {
            "operator": str(operator).strip(),
            "station": str(station).strip(),
            "notes": str(notes).strip(),
        },
        "trials": [],
        "scenarios": {
            scenario_id: {
                "status": "PENDING",
                "observed_at": None,
                "notes": "",
                "evidence": [],
            }
            for scenario_id in plan.scenarios
        },
    }


def validate_session(session, plan):
    if not isinstance(session, dict):
        raise AcceptanceError("La sesion debe ser un objeto")
    if session.get("schema_version") != SESSION_SCHEMA_VERSION:
        raise AcceptanceError(
            f"schema_version de la sesion debe ser {SESSION_SCHEMA_VERSION}"
        )
    if session.get("record_type") != "acceptance_session":
        raise AcceptanceError("record_type de la sesion es invalido")
    if session.get("installation_id") != plan.installation_id:
        raise AcceptanceError(
            "La sesion pertenece a otra instalacion: "
            f"{session.get('installation_id')}"
        )
    if session.get("configuration_fingerprint") != plan.configuration_fingerprint:
        raise AcceptanceError(
            "La configuracion cambio desde que se creo la sesion; "
            "cree una sesion nueva y repita la evidencia"
        )
    if not isinstance(session.get("trials"), list):
        raise AcceptanceError("trials debe ser una lista")
    if not isinstance(session.get("scenarios"), dict):
        raise AcceptanceError("scenarios debe ser un objeto")
    seen_cycles = set()
    for index, trial in enumerate(session["trials"], start=1):
        label = f"trials[{index}]"
        if not isinstance(trial, dict):
            raise AcceptanceError(f"{label} debe ser un objeto")
        _canonical_from(plan.models, trial.get("model"), f"{label}.model")
        _canonical_from(
            plan.trial_classes,
            trial.get("expected_result"),
            f"{label}.expected_result",
        )
        observed = str(trial.get("observed_result", "")).strip().upper()
        if observed not in VALID_OBSERVED_RESULTS:
            raise AcceptanceError(f"{label}.observed_result es invalido")
        _non_negative_number(trial.get("duration_ms"), f"{label}.duration_ms")
        output_safe = trial.get("output_safe")
        if output_safe is not None and not isinstance(output_safe, bool):
            raise AcceptanceError(f"{label}.output_safe debe ser booleano o null")
        cycle_id = str(trial.get("cycle_id") or "").strip()
        if cycle_id:
            if cycle_id in seen_cycles:
                raise AcceptanceError(f"cycle_id duplicado en la sesion: {cycle_id}")
            seen_cycles.add(cycle_id)
    for scenario_id in session["scenarios"]:
        _canonical_from(plan.scenarios, scenario_id, "Escenario de sesion")
    for scenario_id in plan.scenarios:
        evidence = session["scenarios"].get(scenario_id)
        if not isinstance(evidence, dict):
            raise AcceptanceError(f"Falta el escenario requerido: {scenario_id}")
        state = str(evidence.get("status", "")).strip().upper()
        if state not in VALID_SCENARIO_STATES:
            raise AcceptanceError(
                f"Estado invalido para escenario {scenario_id}: {state}"
            )
    return session


def load_acceptance_session(path, plan):
    return validate_session(_read_json(path, "sesion de aceptacion"), plan)


def save_acceptance_session(path, session, plan):
    validate_session(session, plan)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = copy.deepcopy(session)
    candidate["updated_at"] = _utc_now()
    tmp_path = path.with_name(path.name + ".tmp")
    bak_path = path.with_name(path.name + ".bak")
    if path.exists():
        with path.open("rb") as source, bak_path.open("wb") as backup:
            backup.write(source.read())
    try:
        with tmp_path.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(candidate, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    session.clear()
    session.update(candidate)


def add_trial(
    session,
    plan,
    model,
    expected_result,
    observed_result,
    duration_ms,
    cycle_id="",
    output_safe=None,
    notes="",
    source="manual",
):
    validate_session(session, plan)
    canonical_model = _canonical_from(plan.models, model, "Modelo")
    expected = _canonical_from(
        plan.trial_classes,
        expected_result,
        "Resultado esperado",
    )
    observed = str(observed_result or "").strip().upper()
    if observed not in VALID_OBSERVED_RESULTS:
        raise AcceptanceError(f"Resultado observado no soportado: {observed}")
    duration = _non_negative_number(duration_ms, "duration_ms")
    if output_safe is not None and not isinstance(output_safe, bool):
        raise AcceptanceError("output_safe debe ser booleano o null")

    cycle = str(cycle_id or "").strip()
    if cycle and any(
        str(item.get("cycle_id", "")).strip() == cycle
        for item in session["trials"]
        if isinstance(item, dict)
    ):
        return False

    session["trials"].append(
        {
            "trial_id": uuid.uuid4().hex,
            "recorded_at": _utc_now(),
            "model": canonical_model,
            "expected_result": expected,
            "observed_result": observed,
            "duration_ms": round(duration, 3),
            "cycle_id": cycle or None,
            "output_safe": output_safe,
            "source": str(source or "manual"),
            "notes": str(notes or "").strip(),
        }
    )
    return True


def set_scenario(session, plan, scenario_id, status, notes="", evidence=None):
    validate_session(session, plan)
    scenario = _canonical_from(plan.scenarios, scenario_id, "Escenario")
    state = str(status or "").strip().upper()
    if state not in VALID_SCENARIO_STATES:
        raise AcceptanceError(f"Estado de escenario no soportado: {state}")
    evidence_values = []
    for value in evidence or []:
        text = str(value).strip()
        if text:
            evidence_values.append(text)
    session["scenarios"][scenario] = {
        "status": state,
        "observed_at": _utc_now() if state != "PENDING" else None,
        "notes": str(notes or "").strip(),
        "evidence": evidence_values,
    }


def import_trace_jsonl(
    session,
    plan,
    trace_path,
    expected_result,
    model=None,
    output_safe=None,
):
    trace_path = Path(trace_path)
    if not trace_path.is_file():
        raise AcceptanceError(f"No existe trazabilidad: {trace_path}")
    model_filter = (
        _canonical_from(plan.models, model, "Modelo") if model else None
    )
    imported = 0
    skipped = 0
    with trace_path.open("r", encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            text = raw_line.strip()
            if not text:
                continue
            try:
                record = json.loads(text)
            except json.JSONDecodeError as exc:
                raise AcceptanceError(
                    f"JSONL invalido en {trace_path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(record, dict) or record.get("record_type") != "vision_cycle":
                skipped += 1
                continue
            record_model = str(record.get("external_model", "")).strip()
            try:
                canonical_model = _canonical_from(
                    plan.models,
                    record_model,
                    "Modelo de trazabilidad",
                )
            except AcceptanceError:
                skipped += 1
                continue
            if model_filter and canonical_model != model_filter:
                skipped += 1
                continue
            observed = str(record.get("final_result", "")).strip().upper()
            if observed not in VALID_OBSERVED_RESULTS:
                skipped += 1
                continue
            try:
                added = add_trial(
                    session,
                    plan,
                    model=canonical_model,
                    expected_result=expected_result,
                    observed_result=observed,
                    duration_ms=record.get("duration_ms"),
                    cycle_id=record.get("cycle_id"),
                    output_safe=output_safe,
                    notes=f"Importado de {trace_path.name}:{line_number}",
                    source=str(trace_path),
                )
            except AcceptanceError:
                skipped += 1
                continue
            if added:
                imported += 1
            else:
                skipped += 1
    return {"imported": imported, "skipped": skipped}


def _nearest_rank_percentile(values, percentile):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    rank = max(1, int((percentile * len(ordered) + 0.999999)))
    return ordered[min(rank, len(ordered)) - 1]


def evaluate_acceptance(session, plan):
    validate_session(session, plan)
    failures = []
    pending = []
    passes = []

    trials = [item for item in session["trials"] if isinstance(item, dict)]
    by_model = {}
    for model in plan.models:
        by_model[model] = {}
        for trial_class in plan.trial_classes:
            matching = [
                item
                for item in trials
                if item.get("model") == model
                and item.get("expected_result") == trial_class
            ]
            by_model[model][trial_class] = len(matching)
            required = plan.minimum_trials[trial_class]
            if len(matching) < required:
                pending.append(
                    {
                        "code": "TRIAL_COUNT",
                        "message": (
                            f"{model}/{trial_class}: {len(matching)}/{required} "
                            "pruebas"
                        ),
                    }
                )

    false_accepts = [
        item
        for item in trials
        if item.get("expected_result") == "NG"
        and item.get("observed_result") == "OK"
    ]
    if len(false_accepts) > plan.max_false_accepts:
        failures.append(
            {
                "code": "FALSE_ACCEPT",
                "message": (
                    f"Falsos OK: {len(false_accepts)}; "
                    f"maximo={plan.max_false_accepts}"
                ),
            }
        )
    else:
        passes.append({"code": "FALSE_ACCEPT", "message": "Sin falsos OK"})

    expected_ok = [item for item in trials if item.get("expected_result") == "OK"]
    false_rejects = [
        item for item in expected_ok if item.get("observed_result") == "NG"
    ]
    false_reject_rate = (
        len(false_rejects) / len(expected_ok) if expected_ok else 0.0
    )
    if false_reject_rate > plan.max_false_reject_rate:
        failures.append(
            {
                "code": "FALSE_REJECT_RATE",
                "message": (
                    f"Tasa de falsos NG: {false_reject_rate:.3%}; "
                    f"maximo={plan.max_false_reject_rate:.3%}"
                ),
            }
        )
    elif expected_ok:
        passes.append(
            {
                "code": "FALSE_REJECT_RATE",
                "message": f"Tasa de falsos NG: {false_reject_rate:.3%}",
            }
        )

    execution_errors = [
        item
        for item in trials
        if item.get("observed_result") in {"ERROR", "CANCELLED"}
    ]
    if len(execution_errors) > plan.max_execution_errors:
        failures.append(
            {
                "code": "EXECUTION_ERROR",
                "message": (
                    f"Errores/cancelaciones: {len(execution_errors)}; "
                    f"maximo={plan.max_execution_errors}"
                ),
            }
        )
    else:
        passes.append(
            {
                "code": "EXECUTION_ERROR",
                "message": "Sin errores de ejecucion en la poblacion",
            }
        )

    if plan.require_safe_output_for_non_ok:
        for item in trials:
            if item.get("observed_result") == "OK":
                continue
            if item.get("output_safe") is False:
                failures.append(
                    {
                        "code": "UNSAFE_OUTPUT",
                        "message": (
                            f"Salida insegura en ciclo "
                            f"{item.get('cycle_id') or item.get('trial_id')}"
                        ),
                    }
                )
            elif item.get("output_safe") is not True:
                pending.append(
                    {
                        "code": "SAFE_OUTPUT_EVIDENCE",
                        "message": (
                            "Falta confirmar salida segura en ciclo "
                            f"{item.get('cycle_id') or item.get('trial_id')}"
                        ),
                    }
                )

    durations = [
        item.get("duration_ms")
        for item in trials
        if isinstance(item.get("duration_ms"), (int, float))
    ]
    p95_cycle_ms = _nearest_rank_percentile(durations, 0.95)
    if p95_cycle_ms is not None:
        if p95_cycle_ms > plan.max_p95_cycle_ms:
            failures.append(
                {
                    "code": "CYCLE_P95",
                    "message": (
                        f"P95={p95_cycle_ms:.3f} ms; "
                        f"maximo={plan.max_p95_cycle_ms:.3f} ms"
                    ),
                }
            )
        else:
            passes.append(
                {
                    "code": "CYCLE_P95",
                    "message": f"P95={p95_cycle_ms:.3f} ms",
                }
            )

    scenario_metrics = {}
    for scenario_id, definition in plan.scenarios.items():
        evidence = session["scenarios"].get(scenario_id, {})
        status = str(evidence.get("status", "PENDING")).upper()
        scenario_metrics[scenario_id] = status
        message = definition.get("description", scenario_id)
        if status == "PASS":
            passes.append({"code": "SCENARIO", "message": message})
        elif status == "FAIL":
            failures.append({"code": "SCENARIO", "message": message})
        else:
            pending.append({"code": "SCENARIO", "message": message})

    status = "FAILED" if failures else "PENDING" if pending else "READY_FOR_COMMISSIONING"
    return {
        "schema_version": 1,
        "record_type": "acceptance_report",
        "generated_at": _utc_now(),
        "installation_id": plan.installation_id,
        "session_id": session.get("session_id"),
        "status": status,
        "failures": failures,
        "pending": pending,
        "passes": passes,
        "metrics": {
            "trials_total": len(trials),
            "trials_by_model": by_model,
            "false_accepts": len(false_accepts),
            "false_rejects": len(false_rejects),
            "false_reject_rate": false_reject_rate,
            "execution_errors": len(execution_errors),
            "p95_cycle_ms": p95_cycle_ms,
            "scenarios": scenario_metrics,
        },
    }
