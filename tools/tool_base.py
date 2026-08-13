from abc import ABC, abstractmethod
from copy import deepcopy

from core.roi import ROIError, normalize_roi
from tools.result import ToolExecutionError, ToolResult, ToolStatus

class ToolBase(ABC):
    TOOL_ID = ""
    DISPLAY_NAME = ""
    PARAMETER_SCHEMA = {}
    SUPPORTED_PARAMETER_TYPES = {
        "str", "float", "int", "bool", "choice", "roi", "image_list", "video"
    }

    def __init__(self, name=None):
        self.name = str(name or self.tool_id())

    @classmethod
    def tool_id(cls):
        return str(cls.TOOL_ID or "").strip()

    @classmethod
    def display_name(cls):
        return str(cls.DISPLAY_NAME or cls.tool_id()).strip()

    @classmethod
    def parameter_schema(cls):
        return deepcopy(cls.PARAMETER_SCHEMA)

    @classmethod
    def default_params(cls):
        defaults = {}
        for key, config in cls.PARAMETER_SCHEMA.items():
            if config.get("persist", True) and "default" in config:
                defaults[key] = deepcopy(config["default"])
        return defaults

    @classmethod
    def validate_contract(cls):
        tool_id = cls.tool_id()
        if not tool_id or tool_id.lower() != tool_id:
            raise ValueError(
                f"{cls.__name__}.TOOL_ID debe ser un ID estable en minusculas"
            )
        if any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_" for char in tool_id):
            raise ValueError(f"TOOL_ID invalido: {tool_id}")
        if not cls.display_name():
            raise ValueError(f"{tool_id} no tiene nombre visible")
        if not isinstance(cls.PARAMETER_SCHEMA, dict):
            raise ValueError(f"{tool_id}.PARAMETER_SCHEMA debe ser un objeto")

        for key, config in cls.PARAMETER_SCHEMA.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"{tool_id} contiene un parametro sin nombre")
            if not isinstance(config, dict):
                raise ValueError(f"Schema invalido en {tool_id}.{key}")
            param_type = config.get("type")
            if param_type not in cls.SUPPORTED_PARAMETER_TYPES:
                raise ValueError(
                    f"Tipo no soportado en {tool_id}.{key}: {param_type}"
                )
            if param_type == "choice":
                options = config.get("options")
                if not isinstance(options, list) or not options:
                    raise ValueError(f"{tool_id}.{key} requiere options")

        default_errors = cls.validate_params(cls.default_params())
        if default_errors:
            raise ValueError(
                f"Defaults invalidos en {tool_id}: {'; '.join(default_errors)}"
            )
        return True

    @classmethod
    def validate_params(cls, params, commissioning=False):
        if not isinstance(params, dict):
            return ["params debe ser un objeto"]

        errors = []
        for key, config in cls.PARAMETER_SCHEMA.items():
            if not config.get("persist", True):
                continue
            value = params.get(key)
            if commissioning and config.get("commissioning_required"):
                if value is None or value == "" or value == []:
                    errors.append(f"Falta parametro obligatorio: {key}")
                    continue
            if value is None:
                continue

            param_type = config["type"]
            valid_type = True
            if param_type == "str":
                valid_type = isinstance(value, str)
            elif param_type == "bool":
                valid_type = isinstance(value, bool)
            elif param_type == "int":
                valid_type = isinstance(value, int) and not isinstance(value, bool)
            elif param_type == "float":
                valid_type = isinstance(value, (int, float)) and not isinstance(value, bool)
            elif param_type == "choice":
                valid_type = value in config.get("options", [])
            elif param_type == "image_list":
                valid_type = isinstance(value, list) and all(
                    isinstance(item, str) and item.strip() for item in value
                )
            elif param_type == "roi":
                try:
                    normalize_roi(value, allow_none=False)
                except ROIError:
                    valid_type = False

            if not valid_type:
                errors.append(f"Valor invalido para {key}")
                continue
            if param_type in ("int", "float"):
                if "min" in config and value < config["min"]:
                    errors.append(f"{key} debe ser >= {config['min']}")
                if "max" in config and value > config["max"]:
                    errors.append(f"{key} debe ser <= {config['max']}")
        return errors

    @classmethod
    def resource_paths(cls, params):
        if not isinstance(params, dict):
            return []
        resources = []
        for key, config in cls.PARAMETER_SCHEMA.items():
            if not config.get("resource"):
                continue
            value = params.get(key)
            values = value if isinstance(value, list) else [value]
            for path in values:
                if isinstance(path, str) and path.strip():
                    resources.append({"parameter": key, "path": path})
        return resources

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
