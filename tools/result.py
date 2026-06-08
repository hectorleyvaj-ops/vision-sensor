class ToolResult:
    def __init__(self, success:bool, tool_name:str, data=None, error=None):
        self.success = success
        self.tool_name = tool_name
        self.data = data
        self.error = error

    def to_dict(self):
        return {
            "tool": self.tool_name,
            "success": self.success,
            "data": self.data,
            "error": self.error
        }