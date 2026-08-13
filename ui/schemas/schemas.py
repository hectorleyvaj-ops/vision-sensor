"""UI adapters for schemas owned by the tool catalog.

This module intentionally contains no tool definitions.  It returns mutable
copies for Qt while the authoritative schema remains beside each tool.
"""

from tools.registry import copy_schema


def tool_schemas(tool_registry):
    if tool_registry is None:
        return {}
    return {
        tool_id: copy_schema(tool_registry.schema(tool_id))
        for tool_id in tool_registry
    }
