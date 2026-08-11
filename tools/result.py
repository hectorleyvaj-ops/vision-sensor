from enum import Enum


class ToolStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"


class ToolExecutionError(RuntimeError):
    """Base exception used by tools to return a typed non-PASS result."""

    status = ToolStatus.ERROR
    code = "TOOL_ERROR"

    def __init__(self, message, data=None, code=None):
        super().__init__(message)
        self.data = data
        if code:
            self.code = str(code)


class ToolFailure(ToolExecutionError):
    """The inspection ran correctly and rejected the product."""

    status = ToolStatus.FAIL
    code = "INSPECTION_FAILED"


class ToolTimeout(ToolExecutionError):
    """The inspection did not complete inside its configured deadline."""

    status = ToolStatus.TIMEOUT
    code = "INSPECTION_TIMEOUT"


class ToolCancelled(ToolExecutionError):
    """A controller/user cancellation interrupted the inspection safely."""

    status = ToolStatus.ERROR
    code = "CANCELLED"


class ToolResult:
    """Stable result contract shared by every vision tool.

    ``success`` remains accepted for legacy tools/tests, but new code should use
    one of the four explicit statuses.  FAIL is a valid inspection rejection;
    ERROR and TIMEOUT indicate that no product decision was obtained.
    """

    def __init__(
        self,
        success=None,
        tool_name="",
        data=None,
        error=None,
        status=None,
        error_code=None,
    ):
        if status is None:
            if success is True:
                status = ToolStatus.PASS
            elif success is False:
                # Compatibilidad con herramientas antiguas: success=False era
                # el unico modo de expresar un rechazo de inspeccion.
                status = ToolStatus.FAIL
            else:
                status = ToolStatus.ERROR
        try:
            self.status = ToolStatus(status)
        except ValueError as exc:
            raise ValueError(f"Estado de herramienta no soportado: {status}") from exc

        self.tool_name = tool_name
        self.data = data
        self.error = error
        self.error_code = error_code

    @property
    def success(self):
        return self.status is ToolStatus.PASS

    def to_dict(self):
        return {
            "tool": self.tool_name,
            "status": self.status.value,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
        }
