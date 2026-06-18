# schemas/tool_schemas.py

TOOL_SCHEMAS = {
    "dmtx": {
        "roi": {"type": "roi", "label": "Select ROI"},
        "video": {"type": "video", "label": "Video"},

        "expected_code": {
            "type": "str", 
            "label": "Código Maestro", 
            "default": ""
            },

        "retries": {
            "type": "int", 
            "label": "Intentos/Trigger", 
            "min": 1, 
            "max": 20, 
            "default": 5
            },

        "delay": {
            "type": "float", 
            "label": "Tiempo/ciclo", 
            "min": 0.0, 
            "max": 5.0, 
            "decimals": 2, 
            "default": 0.1
            },

        "min_expected_reads": {
            "type": "int", 
            "label": "Lecturas OK mínimas", 
            "min": 1, 
            "max": 20, 
            "default": 2
            },

        "max_wrong_reads": {
            "type": "int", 
            "label": "Lecturas erróneas máximas", 
            "min": 0, 
            "max": 20, 
            "default": 0
            },

        "roi_padding": {
            "type": "int",
            "label": "Margen extra ROI",
            "min": 0,
            "max": 100,
            "default": 12
            },

        "preprocess": {
            "type": "bool",
            "label": "Mejorar imagen",
            "default": True
            },

        "upscale": {
            "type": "float",
            "label": "Escalado imagen",
            "min": 1.0,
            "max": 4.0,
            "decimals": 1,
            "step": 0.1,
            "default": 2.0
            },

        "decode_timeout_ms": {
            "type": "int",
            "label": "Timeout decode ms",
            "min": 50,
            "max": 2000,
            "step": 50,
            "default": 250
            },

        "max_total_time": {
            "type": "float",
            "label": "Tiempo máximo total",
            "min": 1.0,
            "max": 30.0,
            "decimals": 1,
            "step": 0.5,
            "default": 15.0
            },

        "show_roi": {
            "type": "bool", 
            "label": "Mostrar ROI", 
            "default": True
            },

        "required": {
            "type": "bool", 
            "label": "Requerido", 
            "default": True
            }
    },

    "img_hist": {
        "roi": {
            "type": "roi", 
            "label": "Select ROI"
            },

        "video": {
            "type": "video", 
            "label": "Video"
            },

        "threshold": {
            "type": "float", 
            "default": 0.0
            },

        "mode": {
            "type": "choice", 
            "options": ["below", "above"], 
            "default": "below"
            },

        "template_paths": {"type": "image_list"},

        "show_roi": {"type": "bool", "default": True},
        
        "required": {"type": "bool", "default": True}
    }
}
