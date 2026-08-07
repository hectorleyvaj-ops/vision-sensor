# Esquema universal de recetas v2

El motor guarda un catalogo con esta raiz:

```json
{
  "schema_version": 2,
  "recipes": []
}
```

Ejemplo neutral:

```json
{
  "id": "part_8472",
  "name": "PART_8472",
  "selected": true,
  "commissioned": false,
  "focus": {
    "mode": "calibrated",
    "enabled": true,
    "roi": [100, 80, 500, 360],
    "value": 420,
    "min_score": 1500,
    "median_score": 2100,
    "peak_score": 2300,
    "verify_on_first_trigger": true,
    "auto_refocus_if_failed": true
  },
  "steps": [
    {
      "id": "code_1",
      "tool": "dmtx",
      "enabled": true,
      "required": true,
      "condition": {"type": "always"},
      "params": {
        "roi": [120, 100, 440, 300],
        "expected_code": "EXPECTED-CODE"
      }
    }
  ]
}
```

## Condiciones disponibles

| Tipo | Campos | Funcion |
|---|---|---|
| `always` | ninguno | Ejecuta siempre el paso habilitado. |
| `step_success` | `step_id`, `equals` | Depende del resultado de un paso anterior. |
| `context_equals` | `path`, `value` | Compara un dato del contexto del ciclo. |
| `all` / `any` | `conditions` | Combina condiciones. |
| `not` | `condition` | Invierte una condicion. |

Un catalogo heredado sin `schema_version`, IDs de paso o metadatos se migra al
abrirlo cuando `recipes.auto_migrate=true`. Los valores existentes no se
reemplazan y el archivo anterior se conserva como `.bak`.

Las politicas `enabled`, `required` y `condition` pertenecen al paso. Los
parametros dentro de `params` pertenecen exclusivamente a la herramienta.
