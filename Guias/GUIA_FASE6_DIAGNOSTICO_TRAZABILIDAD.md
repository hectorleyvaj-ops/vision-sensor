# Guia de aplicacion - Fase 6

## Alcance

Esta fase agrega diagnostico de arranque y trazabilidad estructurada sin incluir
recetas, firmware, PLC ni reglas especificas de Worksurface.

Incluye:

- validacion de configuracion, catalogo, mapeos, tools e imagenes maestras;
- verificacion de escritura del directorio operativo;
- valores solicitados y reales de camara;
- puerto, baudrate, firmware y protocolo del controlador;
- bloqueo de `READY` por recursos obligatorios ausentes;
- `startup_diagnostics.json` reemplazable;
- `cycles.jsonl` con un objeto por ciclo;
- tiempos por step, causas, cancelaciones y entrega serial;
- rotacion por tamano y retencion por cantidad/dias;
- nueva pestana `Registros` dentro de `SISTEMA`;
- mensaje grafico accionable cuando la configuracion base impide iniciar.

## Base requerida

Aplicar sobre la rama que ya contiene la fase 5. Antes de iniciar:

```cmd
git status
git log -3 --oneline
```

El arbol debe estar limpio. Conserva cualquier configuracion local antes de
restaurar o reemplazar archivos.

## Aplicacion normal

```cmd
git switch -c feature/universal-operations-phase6

git apply --check "C:\ruta\0001-Add-startup-diagnostics-and-cycle-traceability.patch"
git apply --index "C:\ruta\0001-Add-startup-diagnostics-and-cycle-traceability.patch"
```

## Si `config/system.json` no coincide

El parche agrega la seccion `traceability`. Si tu archivo contiene valores
propios, conserva esos valores y excluye el JSON en ambos comandos:

```cmd
git apply --check --exclude=config/system.json "C:\ruta\0001-Add-startup-diagnostics-and-cycle-traceability.patch"
git apply --index --exclude=config/system.json "C:\ruta\0001-Add-startup-diagnostics-and-cycle-traceability.patch"
```

Luego agrega manualmente en la raiz de `config/system.json`, despues de
`runtime`:

```json
"traceability": {
    "enabled": true,
    "directory": "runtime/traceability",
    "max_file_size_mb": 10.0,
    "retention_files": 10,
    "retention_days": 30
}
```

Cuida la coma entre secciones y valida:

```cmd
python -m json.tool config\system.json > nul && echo JSON CORRECTO || echo JSON INVALIDO
git add config/system.json
```

No vuelvas a ejecutar el comando sin `--exclude`, porque intentaria aplicar por
segunda vez todos los archivos que ya fueron preparados.

## Validacion automatica

```cmd
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q app core processing services tools ui vision tests
git diff --cached --check
```

Resultado esperado:

```text
Ran 53 tests
OK
```

## Prueba funcional en PC

1. Inicia la aplicacion con la configuracion de prueba.
2. Abre `SISTEMA > Registros` y confirma los cinco parametros.
3. Revisa `runtime/traceability/startup_diagnostics.json`.
4. Confirma que `camera.runtime` muestre resolucion/FPS reales.
5. Con simulador de controlador, confirma `controller.runtime=PASS` y la
   version `vision_controller_v1`.
6. Ejecuta un ciclo OK, uno NG, uno ERROR y una cancelacion.
7. Comprueba que cada linea de `cycles.jsonl` sea JSON independiente y conserve
   el `cycle_id` correcto.

Los archivos dentro de `runtime/` estan excluidos de Git.

## Prueba obligatoria en Raspberry

- comprobar permisos del usuario del futuro servicio;
- registrar dispositivo de camara resuelto y formato realmente negociado;
- verificar la ruta persistente del puerto serial;
- desconectar/reconectar camara y controlador;
- confirmar que nunca se publica `READY` durante un error bloqueante;
- medir espacio ocupado y rotacion con varios ciclos;
- confirmar que el guardado no afecta perceptiblemente el tiempo de ciclo.

Esta prueba no autoriza todavia actuadores ni reemplazo del sistema anterior.

## Commit

```cmd
git status
git diff --cached --stat
git commit -m "Add startup diagnostics and cycle traceability"
git push -u origin feature/universal-operations-phase6
```

## Archivos generados en ejecucion

```text
runtime/traceability/startup_diagnostics.json
runtime/traceability/cycles.jsonl
runtime/traceability/cycles.1.jsonl
...
```

`startup_diagnostics.json` conserva el estado mas reciente por componente; no
es un historial infinito. `cycles.jsonl` si es evidencia append-only y se
limita mediante rotacion y retencion.
