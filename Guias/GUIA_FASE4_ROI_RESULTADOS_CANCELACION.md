# Guia de aplicacion - Fase 4

Esta fase se aplica sobre la rama que ya contiene el commit de la interfaz
universal de fase 3. No contiene recetas Worksurface ni firmware ESP32/PLC.

## 1. Preparar una rama

Desde la terminal CMD de VS Code:

```cmd
git status
git branch --show-current
git switch -c feature/universal-engine-phase4
```

El primer comando debe mostrar un arbol de trabajo limpio.

## 2. Comprobar y aplicar

```cmd
git apply --check "C:\ruta\universal_engine_hardening_phase4.patch"
git apply --index "C:\ruta\universal_engine_hardening_phase4.patch"
```

Si `--check` no imprime nada, el parche es compatible. Si muestra
`patch does not apply`, no fuerces la aplicacion.

## 3. Validar

```cmd
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q app core processing services tools ui vision tests
git diff --cached --check
```

Resultado esperado:

```text
Ran 42 tests
OK
```

`compileall` y `git diff --cached --check` no muestran salida cuando todo esta
correcto.

## 4. Confirmar y publicar

```cmd
git status
git diff --cached --stat
git commit -m "Harden universal inspection execution"
git push -u origin feature/universal-engine-phase4
```

## Cambios de datos al primer arranque

El catalogo de recetas sube de esquema v2 a v3. Si
`recipes.auto_migrate=true`, el motor:

1. crea `recipes.json.bak`;
2. conserva ROI de enfoque y DataMatrix como `[x1,y1,x2,y2]`;
3. convierte ROI heredadas de `img_hist` desde `[x,y,ancho,alto]`;
4. agrega `match_mode="exact"` a DataMatrix si no existe;
5. guarda el catalogo como esquema v3.

No cambies manualmente `schema_version` antes de abrir el programa; hacerlo
saltaria la migracion de ROI de histograma.

## Parametros nuevos o aclarados

- `runtime.inspection_timeout_seconds`: limite total de un ciclo de vision.
- `dmtx.match_mode=exact`: todo el texto debe coincidir.
- `dmtx.match_mode=prefix`: el texto debe comenzar con el codigo esperado.
- `camera.width` y `camera.height`: resolucion de la camara, no de la pantalla.

La interfaz responsiva y la deteccion automatica del monitor quedan para una
fase posterior.

## Restricciones de despliegue

- Probar primero en PC con el catalogo respaldado.
- No desplegar aun en la maquina Worksurface.
- No crear todavia firmware Worksurface a partir de esta rama.
- No modificar el PLC en esta fase.
