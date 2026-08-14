"""Create and evaluate installation acceptance evidence without editing recipes."""

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.acceptance import (
    AcceptanceError,
    add_trial,
    evaluate_acceptance,
    import_trace_jsonl,
    load_acceptance_plan,
    load_acceptance_session,
    new_acceptance_session,
    save_acceptance_session,
    set_scenario,
)

DEFAULT_PLAN = PROJECT_ROOT / "installations" / "worksurface" / "acceptance.json"


def _output_safe(value):
    if value == "yes":
        return True
    if value == "no":
        return False
    return None


def _write_json_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _parser():
    parser = argparse.ArgumentParser(
        description=(
            "Registra evidencia de aceptacion fisica sin cambiar recipes.json "
            "ni el estado commissioned."
        )
    )
    parser.add_argument("--plan", default=str(DEFAULT_PLAN))
    subparsers = parser.add_subparsers(dest="command", required=True)

    initialize = subparsers.add_parser("init", help="Crear una sesion vacia")
    initialize.add_argument("--session", required=True)
    initialize.add_argument("--operator", default="")
    initialize.add_argument("--station", default="")
    initialize.add_argument("--notes", default="")
    initialize.add_argument("--force", action="store_true")

    trial = subparsers.add_parser("record-trial", help="Agregar un ciclo manual")
    trial.add_argument("--session", required=True)
    trial.add_argument("--model", required=True)
    trial.add_argument("--expected", choices=("OK", "NG"), required=True)
    trial.add_argument(
        "--observed",
        choices=("OK", "NG", "ERROR", "CANCELLED"),
        required=True,
    )
    trial.add_argument("--duration-ms", type=float, required=True)
    trial.add_argument("--cycle-id", default="")
    trial.add_argument(
        "--output-safe",
        choices=("yes", "no", "unknown"),
        default="unknown",
    )
    trial.add_argument("--notes", default="")

    trace = subparsers.add_parser("import-trace", help="Importar ciclos JSONL")
    trace.add_argument("--session", required=True)
    trace.add_argument("--trace", required=True)
    trace.add_argument("--expected", choices=("OK", "NG"), required=True)
    trace.add_argument("--model")
    trace.add_argument(
        "--output-safe",
        choices=("yes", "no", "unknown"),
        default="unknown",
    )

    scenario = subparsers.add_parser(
        "record-scenario",
        help="Registrar una prueba de falla, seguridad o mapeo",
    )
    scenario.add_argument("--session", required=True)
    scenario.add_argument("--id", required=True)
    scenario.add_argument(
        "--status",
        choices=("PASS", "FAIL", "PENDING"),
        required=True,
    )
    scenario.add_argument("--notes", default="")
    scenario.add_argument("--evidence", action="append", default=[])

    evaluate = subparsers.add_parser("evaluate", help="Evaluar una sesion")
    evaluate.add_argument("--session", required=True)
    evaluate.add_argument("--json-out")
    evaluate.add_argument("--details", action="store_true")
    return parser


def _print_report(report, details=False):
    metrics = report["metrics"]
    print(f"ACEPTACION: {report['status']}")
    print(f"Ciclos: {metrics['trials_total']} | P95: {metrics['p95_cycle_ms']} ms")
    print(
        "Falsos OK: "
        f"{metrics['false_accepts']} | Falsos NG: {metrics['false_rejects']} | "
        f"Errores: {metrics['execution_errors']}"
    )
    print(
        f"Fallas: {len(report['failures'])} | "
        f"Pendientes: {len(report['pending'])}"
    )
    if details:
        for bucket, title in (("failures", "FALLA"), ("pending", "PENDIENTE")):
            for item in report[bucket]:
                print(f"[{title}] {item['code']}: {item['message']}")


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        plan = load_acceptance_plan(args.plan)
        if args.command == "init":
            session_path = Path(args.session)
            if session_path.exists() and not args.force:
                raise AcceptanceError(
                    f"La sesion ya existe: {session_path}; use --force para reemplazarla"
                )
            session = new_acceptance_session(
                plan,
                operator=args.operator,
                station=args.station,
                notes=args.notes,
            )
            save_acceptance_session(session_path, session, plan)
            print(f"Sesion creada: {session_path}")
            return 0

        session = load_acceptance_session(args.session, plan)
        if args.command == "record-trial":
            added = add_trial(
                session,
                plan,
                model=args.model,
                expected_result=args.expected,
                observed_result=args.observed,
                duration_ms=args.duration_ms,
                cycle_id=args.cycle_id,
                output_safe=_output_safe(args.output_safe),
                notes=args.notes,
            )
            if not added:
                print(f"Ciclo ya registrado, sin cambios: {args.cycle_id}")
                return 0
            save_acceptance_session(args.session, session, plan)
            print("Ciclo registrado")
            return 0

        if args.command == "import-trace":
            result = import_trace_jsonl(
                session,
                plan,
                trace_path=args.trace,
                expected_result=args.expected,
                model=args.model,
                output_safe=_output_safe(args.output_safe),
            )
            save_acceptance_session(args.session, session, plan)
            print(
                f"Importados: {result['imported']} | "
                f"Omitidos/duplicados: {result['skipped']}"
            )
            return 0

        if args.command == "record-scenario":
            set_scenario(
                session,
                plan,
                scenario_id=args.id,
                status=args.status,
                notes=args.notes,
                evidence=args.evidence,
            )
            save_acceptance_session(args.session, session, plan)
            print(f"Escenario actualizado: {args.id}={args.status}")
            return 0

        report = evaluate_acceptance(session, plan)
        _print_report(report, details=args.details)
        if args.json_out:
            _write_json_atomic(args.json_out, report)
            print(f"Reporte JSON: {args.json_out}")
        return {"READY_FOR_COMMISSIONING": 0, "FAILED": 2, "PENDING": 3}[report["status"]]
    except (AcceptanceError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
