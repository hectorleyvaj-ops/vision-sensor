from abc import ABC, abstractmethod
from tools.result import ToolResult

class ToolBase(ABC):
    def __init__(self, name: str):
        self.name = name

    def run(self, **kwargs) -> ToolResult:
        try:
            output = self.process(**kwargs)

            return ToolResult(
                success=True,
                tool_name=self.name,
                data=output
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=str(e)
            )

    
    @abstractmethod
    def process(self, **kwargs):
        pass
