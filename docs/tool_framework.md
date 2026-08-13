# Framework extensible de herramientas

## Objetivo

Una herramienta de vision debe poder agregarse sin editar `app.py`, la FSM,
`RecipeManager`, el diagnostico ni una tabla global de UI. Cada clase concreta
de `ToolBase` es la fuente autoritativa de:

- ID tecnico estable;
- nombre visible;
- esquema y valores predeterminados;
- validacion de parametros y comisionamiento;
- recursos externos utilizados;
- ejecucion y resultado tipado.

`discover_tool_registry()` recorre el paquete `tools`, importa sus modulos y
registra automaticamente las subclases concretas. `ToolRegistry` implementa
`Mapping`, por lo que el pipeline sigue consumiendo `registry[tool_id]` sin
conocer la implementacion concreta.

## Contrato minimo

```python
from tools.tool_base import ToolBase


class PresenceTool(ToolBase):
    TOOL_ID = "presence"
    DISPLAY_NAME = "Presencia de componente"
    PARAMETER_SCHEMA = {
        "roi": {
            "type": "roi",
            "label": "Region de inspeccion",
            "default": None,
            "commissioning_required": True,
        },
        "threshold": {
            "type": "float",
            "label": "Umbral",
            "min": 0.0,
            "max": 1.0,
            "default": 0.5,
        },
    }

    def process(self, **kwargs):
        # Debe consultar cancel_event/deadline durante trabajo prolongado.
        return {"result": "PASS"}
```

El archivo puede llamarse `tools/presence_tool.py`. No se agrega un import a
`app.py`: el catalogo lo descubre al reiniciar.

## Tipos de parametros

| Tipo | Persistido | Editor |
|---|---|---|
| `str` | Si | Texto |
| `int` | Si | Control numerico entero |
| `float` | Si | Control numerico decimal |
| `bool` | Si | Casilla |
| `choice` | Si | Lista de opciones |
| `roi` | Si | Seleccion sobre video |
| `image_list` | Si | Lista/captura de imagenes |
| `video` | No, usar `persist=False` | Vista auxiliar |

Campos relevantes del schema:

- `default`: valor agregado a recetas nuevas o migradas;
- `min`, `max`, `options`: validacion generica;
- `commissioning_required`: bloquea comisionamiento si falta;
- `resource`: identifica rutas que debe verificar el diagnostico;
- `persist=False`: elemento auxiliar de UI que no es parametro de receta.

Los parametros desconocidos se conservan al editar. Esto permite abrir recetas
creadas por una version posterior sin borrar datos, aunque una herramienta no
debe depender de un parametro que no declare.

## Resultados y cancelacion

Toda ejecucion sale de `ToolBase.run()` como `ToolResult`:

- `PASS`: inspeccion aceptada;
- `FAIL`: defecto de producto;
- `ERROR`: no se obtuvo una decision;
- `TIMEOUT`: vencio el plazo.

Una herramienta prolongada debe llamar `check_execution()` entre operaciones y
usar `wait_interruptibly()` en vez de pausas bloqueantes. `cancel_event` y
`deadline` llegan dentro de `kwargs`.

Las dependencias pesadas, como OpenCV o un decoder opcional, se importan al
ejecutar y no al leer el manifiesto. Asi los metadatos pueden validarse sin
inicializar hardware; cualquier modulo que aun falle al importarse queda
registrado sin ocultar las demas herramientas.

## Prueba contractual

`tests/test_tool_registry.py` recorre automaticamente las herramientas
descubiertas y comprueba:

1. IDs estables y no duplicados;
2. schemas y defaults validos;
3. construccion sin argumentos;
4. salida `ToolResult` aun ante error;
5. cancelacion cooperativa previa;
6. compatibilidad directa con `VisionPipeline`;
7. validacion de comisionamiento y recursos desde el catalogo.

Toda herramienta nueva debe pasar esta prueba junto con pruebas funcionales
propias de su algoritmo.
