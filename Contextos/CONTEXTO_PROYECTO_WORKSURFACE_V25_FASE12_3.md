# Contexto V25 - Fase 12.3

## Problema confirmado

El servicio industrial ejecutaba `validate_installation.py` antes de abrir la
interfaz y convertia cualquier error del manifiesto en `exit 20`. Una
reasignacion valida de `controller.model_map` podia no coincidir con el mapa
duplicado en `commissioning.json`; la aplicacion quedaba bloqueada sin permitir
corregirla desde su propia interfaz.

La comparacion nunca dependio del orden JSON. El conflicto real era que el
manifiesto Worksurface fijaba `A -> MODELO_A`, `B -> MODELO_B` y
`C -> MODELO_C` mediante `exact_model_map: true`.

## Decision de arquitectura

- El orden de recetas es presentacion y no tiene semantica de control.
- `controller.model_map` traduce IDs externos configurables a recetas.
- El manifiesto puede optar por politica configurable o exacta.
- En politica configurable se exige cobertura de recetas requeridas, no IDs
  externos ni orden especificos.
- Un manifiesto invalido bloquea `READY`, pero no bloquea la interfaz.
- La configuracion generica permanece libre de modelos Worksurface.

## Cambios

- `scripts/validate_installation.py`: valida cobertura por receta cuando
  `exact_model_map` es falso y conserva la validacion estricta opcional.
- `installations/worksurface/commissioning.json`: politica configurable por
  defecto.
- `scripts/launch_vision.sh`: la validacion de comisionamiento es recuperable.
- `app/app.py`: propaga el fallo como diagnostico bloqueante de `READY`.
- `scripts/set_model_map_policy.py`: migracion atomica con respaldo para datos
  persistentes.
- `ui/system_config_dialog.py`: aclara que la tabla no ordena recetas.
- Pruebas para mapeos intercambiados, politica exacta, migracion y arranque
  degradado.

## Validacion

- 165 pruebas unitarias aprobadas.
- `compileall` aprobado.
- Sintaxis de scripts Bash aprobada.
- `git diff --check` aprobado.
