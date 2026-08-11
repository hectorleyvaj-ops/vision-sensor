from abc import ABC, abstractmethod
from tools.result import ToolExecutionError, ToolResult, ToolStatus

class ToolBase(ABC):
    def __init__(self, name: str):
        self.name = name

    def run(self, **kwargs) -> ToolResult:
        try:
            output = self.process(**kwargs)

            return ToolResult(
                status=ToolStatus.PASS,
                tool_name=self.name,
                data=output
            )
        except ToolExecutionError as exc:
            return ToolResult(
                status=exc.status,
                tool_name=self.name,
                data=exc.data,
                error=str(exc),
                error_code=exc.code,
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                tool_name=self.name,
                error=str(e),
                error_code="UNEXPECTED_EXCEPTION",
            )

    
    @abstractmethod
    def process(self, **kwargs):
        pass
