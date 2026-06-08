# schemas/tool_schemas.py

TOOL_SCHEMAS = {
    "dmtx": {
        "roi": {"type": "roi", "label": "Select ROI"},
        "video": {"type": "video", "label": "Video"},
        "expected_code": {"type": "str", "label": "Código Maestro"},
        "retries": {"type": "int", "label": "Intentos/Trigger"},
        "delay": {"type": "float", "label": "Tiempo/ciclo"},
        "show_roi": {"type": "bool", "label": "Mostrar ROI"},
        "required": {"type": "bool", "label": "Requerido"}
    },

    "img_hist": {
        "roi": {"type": "roi", "label": "Select ROI"},
        "video": {"type": "video", "label": "Video"},
        "threshold": {"type": "float"},
        "mode": {"type": "choice", "options": ["below", "above"]},
        "template_paths": {"type": "image_list"},
        "show_roi": {"type": "bool"},
        "required": {"type": "bool"}
    }
}