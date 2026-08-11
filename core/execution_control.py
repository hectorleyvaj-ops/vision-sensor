"""Cooperative cancellation and deadline helpers for inspection workers."""

import time

from tools.result import ToolCancelled, ToolTimeout


def check_execution(cancel_event=None, deadline=None):
    if cancel_event is not None and cancel_event.is_set():
        raise ToolCancelled("Inspeccion cancelada por el controlador")
    if deadline is not None and time.monotonic() >= float(deadline):
        raise ToolTimeout("Tiempo maximo de inspeccion agotado")


def wait_interruptibly(seconds, cancel_event=None, deadline=None):
    """Wait without hiding a cancellation for the complete sleep interval."""
    check_execution(cancel_event=cancel_event, deadline=deadline)
    duration = max(0.0, float(seconds or 0.0))
    if deadline is not None:
        duration = min(duration, max(0.0, float(deadline) - time.monotonic()))

    if cancel_event is not None:
        if cancel_event.wait(duration):
            raise ToolCancelled("Inspeccion cancelada por el controlador")
    elif duration:
        time.sleep(duration)

    check_execution(cancel_event=cancel_event, deadline=deadline)
