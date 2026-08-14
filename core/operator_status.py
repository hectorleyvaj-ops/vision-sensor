"""Pure presentation model for the operator screen.

The UI consumes this module, but it has no Qt dependency.  Keeping status
wording here makes the production screen deterministic and testable without a
display server.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OperatorStatusView:
    headline: str
    detail: str
    level: str
    indicator_text: str
    recipe_caption: str


def _clean(value):
    return str(value or "").strip()


def build_operator_status(
    system_state,
    reason=None,
    final_result=None,
    cycle_busy=False,
    recipe_name=None,
):
    """Return the operator-facing status with safety-first precedence."""
    state = _clean(system_state).upper() or "WARNING"
    result = _clean(final_result).upper()
    recipe = _clean(recipe_name) or "SIN RECETA"
    detail = _clean(reason)

    if state == "CRITICAL":
        return OperatorStatusView(
            headline="ATENCIÓN REQUERIDA",
            detail=detail or "Existe una falla que bloquea la inspección.",
            level="critical",
            indicator_text="!",
            recipe_caption=recipe,
        )

    if state != "READY":
        return OperatorStatusView(
            headline="SISTEMA NO LISTO",
            detail=detail or "Comprobando los componentes de la estación.",
            level="warning",
            indicator_text="!",
            recipe_caption=recipe,
        )

    if cycle_busy:
        return OperatorStatusView(
            headline="INSPECCIONANDO",
            detail="Procesando el ciclo activo. Mantenga la pieza en posición.",
            level="working",
            indicator_text="…",
            recipe_caption=recipe,
        )

    if result == "OK":
        return OperatorStatusView(
            headline="RESULTADO OK",
            detail="La inspección finalizó correctamente.",
            level="ok",
            indicator_text="OK",
            recipe_caption=recipe,
        )

    if result == "NG":
        return OperatorStatusView(
            headline="RESULTADO NG",
            detail="La pieza no cumplió los criterios configurados.",
            level="ng",
            indicator_text="NG",
            recipe_caption=recipe,
        )

    if result == "ERROR":
        return OperatorStatusView(
            headline="ERROR DE CICLO",
            detail="La inspección terminó sin una decisión válida.",
            level="critical",
            indicator_text="!",
            recipe_caption=recipe,
        )

    return OperatorStatusView(
        headline="LISTO PARA INSPECCIÓN",
        detail="Esperando un ciclo válido del controlador.",
        level="ready",
        indicator_text="●",
        recipe_caption=recipe,
    )
