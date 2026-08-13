# SE ENCARGA DE MANEJAR LAS HERRAMIENTAS REQUERIDAS POR LAS RECETAS Y
# CONSERVAR LA DIFERENCIA ENTRE RECHAZO DE PRODUCTO Y FALLA DE EJECUCION.

from core.execution_control import check_execution
from core.step_conditions import ConditionError, evaluate_condition
import time
from tools.result import (
    ToolCancelled,
    ToolResult,
    ToolStatus,
    ToolTimeout,
)


class VisionPipeline:
    def __init__(self, tool_registry: dict):
        self.tool_registry = tool_registry

    def run(self, recipe: dict, contex: dict):
        results = {}
        execution_order = []
        skipped_steps = []
        errors = []
        step_durations_ms = {}
        contex.setdefault("outputs", {})
        contex.setdefault("outputs_by_tool", {})
        contex.setdefault("debug_images", [])

        steps = recipe.get("steps", []) if isinstance(recipe, dict) else []
        if not steps:
            return self._build_response(
                ToolStatus.ERROR,
                results,
                ["La receta no contiene herramientas ejecutables"],
                execution_order,
                skipped_steps,
                step_durations_ms,
                error_code="EMPTY_RECIPE",
            )

        for index, step in enumerate(steps):
            tool_name = step["tool"]
            step_id = step.get("id") or f"{tool_name}_{index + 1}"
            params = step.get("params", {})
            required = step.get("required", params.get("required", True))

            if not step.get("enabled", True):
                skipped_steps.append(step_id)
                continue

            control_error = self._execution_control_result(contex)
            if control_error:
                return self._build_response(
                    control_error.status,
                    results,
                    [control_error.error],
                    execution_order,
                    skipped_steps,
                    step_durations_ms,
                    error_code=control_error.error_code,
                )

            try:
                should_run = evaluate_condition(
                    step.get("condition"),
                    results,
                    contex,
                )
            except ConditionError as exc:
                errors.append(f"Condicion invalida en {step_id}: {exc}")
                return self._build_response(
                    ToolStatus.ERROR,
                    results,
                    errors,
                    execution_order,
                    skipped_steps,
                    step_durations_ms,
                    error_code="INVALID_CONDITION",
                )

            if not should_run:
                skipped_steps.append(step_id)
                continue

            if step_id in results:
                errors.append(f"Step id duplicado durante ejecucion: {step_id}")
                return self._build_response(
                    ToolStatus.ERROR,
                    results,
                    errors,
                    execution_order,
                    skipped_steps,
                    step_durations_ms,
                    error_code="DUPLICATE_STEP_ID",
                )

            tool = self.tool_registry.get(tool_name)
            if not tool:
                error_msg = f"Tool '{tool_name}' no encontrada"
                errors.append(error_msg)
                if required:
                    print(f"[ERROR] {error_msg}")
                    return self._build_response(
                        ToolStatus.ERROR,
                        results,
                        errors,
                        execution_order,
                        skipped_steps,
                        step_durations_ms,
                        error_code="TOOL_NOT_FOUND",
                    )
                skipped_steps.append(step_id)
                continue

            print(f"[PIPELINE] Ejecutando {step_id} ({tool_name})")
            inputs = {**contex, **params}
            step_started = time.monotonic()

            try:
                result = tool.run(**inputs)
            except Exception as exc:
                result = ToolResult(
                    status=ToolStatus.ERROR,
                    tool_name=tool_name,
                    error=str(exc),
                    error_code="UNCAUGHT_TOOL_EXCEPTION",
                )
            finally:
                step_durations_ms[step_id] = round(
                    (time.monotonic() - step_started) * 1000.0,
                    3,
                )

            if not isinstance(result, ToolResult):
                result = ToolResult(
                    status=ToolStatus.ERROR,
                    tool_name=tool_name,
                    error="La herramienta no devolvio ToolResult",
                    error_code="INVALID_TOOL_RESULT",
                )

            results[step_id] = result
            execution_order.append(step_id)
            print(
                f"[PIPELINE] Estado: {result.status.value}; "
                f"resultado: {result.data}"
            )

            if result.status is ToolStatus.PASS:
                if result.data is not None:
                    contex["outputs"][step_id] = result.data
                    contex["outputs_by_tool"].setdefault(tool_name, []).append(
                        result.data
                    )
                continue

            errors.append(result.error or f"{step_id}: {result.status.value}")
            if required:
                print(
                    f"[PIPELINE] Step requerido {step_id}: "
                    f"{result.status.value} - {result.error}"
                )
                return self._build_response(
                    result.status,
                    results,
                    errors,
                    execution_order,
                    skipped_steps,
                    step_durations_ms,
                    error_code=result.error_code,
                )

        if not execution_order:
            return self._build_response(
                ToolStatus.ERROR,
                results,
                ["Ninguna herramienta cumplio su condicion de ejecucion"],
                execution_order,
                skipped_steps,
                step_durations_ms,
                error_code="NO_EXECUTED_STEPS",
            )

        return self._build_response(
            ToolStatus.PASS,
            results,
            errors,
            execution_order,
            skipped_steps,
            step_durations_ms,
        )

    @staticmethod
    def _execution_control_result(context):
        try:
            check_execution(
                cancel_event=context.get("cancel_event"),
                deadline=context.get("deadline"),
            )
        except (ToolCancelled, ToolTimeout) as exc:
            return ToolResult(
                status=exc.status,
                tool_name="pipeline",
                error=str(exc),
                error_code=exc.code,
            )
        return None

    def _build_response(
        self,
        status,
        results,
        errors,
        execution_order,
        skipped_steps,
        step_durations_ms,
        error_code=None,
    ):
        status = ToolStatus(status)
        return {
            "status": status.value,
            "success": status is ToolStatus.PASS,
            "results": results,
            "errors": errors,
            "error_code": error_code,
            "execution_order": execution_order,
            "skipped_steps": skipped_steps,
            "step_durations_ms": step_durations_ms,
        }
