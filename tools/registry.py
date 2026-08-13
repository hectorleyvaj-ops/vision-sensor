"""Discovery and metadata catalog for generic vision tools.

Tools are self-describing: the execution class owns its stable ID, parameter
schema, defaults and commissioning rules.  The engine consumes this mapping
without importing product-specific tools in ``app.py``.
"""

from collections.abc import Mapping
from copy import deepcopy
import importlib
import inspect
import pkgutil

from tools.tool_base import ToolBase


class ToolContractError(ValueError):
    """Raised when a tool cannot safely join the execution catalog."""


class ToolRegistry(Mapping):
    """Read-only mapping of stable tool IDs to executable instances."""

    def __init__(self, tool_classes=None, discovery_errors=None):
        self._instances = {}
        self._classes = {}
        self.discovery_errors = list(discovery_errors or [])
        for tool_class in tool_classes or []:
            self.register(tool_class)

    def register(self, tool_class):
        if not inspect.isclass(tool_class) or not issubclass(tool_class, ToolBase):
            raise ToolContractError("La herramienta debe heredar ToolBase")
        if inspect.isabstract(tool_class):
            raise ToolContractError(
                f"La herramienta {tool_class.__name__} no puede ser abstracta"
            )

        tool_class.validate_contract()
        tool_id = tool_class.tool_id()
        if tool_id in self._classes:
            other = self._classes[tool_id]
            raise ToolContractError(
                f"ID de herramienta duplicado '{tool_id}': "
                f"{other.__name__} y {tool_class.__name__}"
            )

        try:
            instance = tool_class()
        except Exception as exc:
            raise ToolContractError(
                f"No se pudo construir {tool_id}: {exc}"
            ) from exc
        if instance.name != tool_id:
            raise ToolContractError(
                f"{tool_id} construyo una instancia con nombre '{instance.name}'"
            )

        self._classes[tool_id] = tool_class
        self._instances[tool_id] = instance
        return instance

    def __getitem__(self, tool_id):
        return self._instances[tool_id]

    def __iter__(self):
        return iter(self._instances)

    def __len__(self):
        return len(self._instances)

    def tool_class(self, tool_id):
        return self._classes.get(str(tool_id or "").strip())

    def schema(self, tool_id):
        tool_class = self.tool_class(tool_id)
        return tool_class.parameter_schema() if tool_class else None

    def schemas(self):
        return {
            tool_id: tool_class.parameter_schema()
            for tool_id, tool_class in self._classes.items()
        }

    def default_params(self, tool_id):
        tool_class = self.tool_class(tool_id)
        return tool_class.default_params() if tool_class else {}

    def validate_params(self, tool_id, params, commissioning=False):
        tool_class = self.tool_class(tool_id)
        if tool_class is None:
            return [f"Herramienta no registrada: {tool_id}"]
        return tool_class.validate_params(
            params,
            commissioning=commissioning,
        )

    def resource_paths(self, tool_id, params):
        tool_class = self.tool_class(tool_id)
        if tool_class is None:
            return []
        return tool_class.resource_paths(params)

    def manifest(self):
        return {
            tool_id: {
                "id": tool_id,
                "name": tool_class.display_name(),
                "schema": tool_class.parameter_schema(),
                "defaults": tool_class.default_params(),
            }
            for tool_id, tool_class in self._classes.items()
        }


def discover_tool_registry(package_name="tools"):
    """Import tool modules and register every concrete ToolBase subclass.

    A broken optional module is reported through ``discovery_errors`` instead
    of hiding all other valid tools.  Commissioned recipes using the missing
    tool are then blocked by startup diagnostics.
    """

    package = importlib.import_module(package_name)
    classes = []
    errors = []
    prefix = package.__name__ + "."

    for module_info in pkgutil.iter_modules(package.__path__, prefix):
        module_name = module_info.name
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            errors.append({"module": module_name, "error": str(exc)})
            continue

        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate is ToolBase:
                continue
            if candidate.__module__ != module.__name__:
                continue
            if issubclass(candidate, ToolBase) and not inspect.isabstract(candidate):
                classes.append(candidate)

    return ToolRegistry(classes, discovery_errors=errors)


def copy_schema(schema):
    """Compatibility helper for consumers that need a mutable UI copy."""
    return deepcopy(schema or {})
