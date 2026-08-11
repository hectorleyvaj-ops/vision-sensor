"""Pure mapping between internal inspection status and controller result."""

from tools.result import ToolStatus


def controller_result_for_pipeline(status):
    try:
        normalized = ToolStatus(status)
    except (TypeError, ValueError):
        return "ERROR"
    if normalized is ToolStatus.PASS:
        return "OK"
    if normalized is ToolStatus.FAIL:
        return "NG"
    return "ERROR"
