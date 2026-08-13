# Guia de aplicacion - Fase 7: framework extensible de herramientas

## Base requerida

El parche se construyo sobre la fase 6 confirmada:

```text
6f7f6fa Add startup diagnostics and cycle traceability
```

No modifica `config/system.json`, recetas, firmware ESP32 ni ladder PLC.

## Aplicacion en VS Code/CMD

Desde la rama que contiene la fase 6 y sin cambios locales pendientes:

```cmd
git status
git switch -c feature/universal-tool-framework-phase7
git apply --check "C:\ruta\0001-Add-extensible-tool-framework.patch"
git apply --index "C:\ruta\0001-Add-extensible-tool-framework.patch"
```

Si la rama ya existe:

```cmd
git switch feature/universal-tool-framework-phase7
```

No excluyas archivos del parche. A diferencia de fases 4 y 6, esta entrega no
toca configuracion local ni JSON de recetas.

## Validacion

Con el entorno virtual activo:

```cmd
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q app core processing services tools ui vision tests
git diff --cached --check
```

Resultado esperado:

```text
Ran 59 tests
OK
```

Revision adicional del catalogo:

```cmd
python -c "from tools.registry import discover_tool_registry; r=discover_tool_registry(); print(list(r)); print(r.discovery_errors)"
```

Debe mostrar las herramientas `img_hist` y `dmtx`, seguidas por una lista de
errores vacia.

## Commit y publicacion

```cmd
git status
git diff --cached --stat
git commit -m "Add extensible tool framework"
git push -u origin feature/universal-tool-framework-phase7
```

## Prueba visual recomendada

1. Abrir el editor de configuracion.
2. Seleccionar una receta.
3. Agregar un step y confirmar que aparecen DataMatrix e histogramas.
4. Cambiar entre ambas herramientas y comprobar que el formulario se actualiza.
5. Editar un step existente y verificar que conserva ROI, imagenes y valores.
6. Intentar comisionar una receta DataMatrix sin ROI/codigo; debe rechazarse.
7. Intentar comisionar histogramas sin imagen maestra; debe rechazarse.

La prueba visual no sustituye las 59 pruebas automatizadas.

## Como agregar una herramienta despues de fase 7

1. Crear una clase concreta de `ToolBase` dentro de `tools/`.
2. Declarar `TOOL_ID`, `DISPLAY_NAME` y `PARAMETER_SCHEMA`.
3. Implementar `process(**kwargs)` y cancelacion cooperativa.
4. Agregar pruebas funcionales propias.
5. Ejecutar la suite: `test_tool_registry.py` la descubrira automaticamente.

No se debe editar `app.py`, `RecipeManager`, `ToolEditor` ni la FSM para
registrarla.

## Siguiente fase

La fase 8 construira la instalacion Worksurface externa: configuracion, mapeo
A/B/C, recetas, imagenes, ROI y enfoque. La actualizacion de firmware ESP32
permanece en la fase 9.
