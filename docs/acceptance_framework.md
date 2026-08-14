# Marco de aceptacion de instalaciones

## Proposito

La aceptacion comprueba que una instalacion completa se comporta de forma
repetible y segura. No calibra herramientas, no modifica recetas y no cambia
`commissioned`. Su entrada es evidencia de ciclos reales y escenarios fisicos;
su salida es un reporte determinista.

El motor generico solo conoce el esquema. Cada instalacion declara sus modelos,
limites y escenarios en su propio `acceptance.json`. Los modelos se obtienen de
`commissioning.json`, por lo que `core/acceptance.py` no contiene reglas A/B/C.

## Separacion de estados

| Estado | Pregunta que responde | Autoriza produccion |
|---|---|---|
| Validacion estructural | ¿Los archivos y contratos son coherentes? | No |
| Receta no comisionada | ¿Puede seguir editandose/calibrandose? | No |
| Aceptacion `PENDING` | ¿Falta poblacion o un escenario fisico? | No |
| Aceptacion `FAILED` | ¿Existe una medicion fuera de criterio? | No |
| `READY_FOR_COMMISSIONING` | ¿La evidencia satisface el plan? | No, habilita revision humana |
| Receta comisionada | ¿Un responsable valido y guardo la calibracion final? | Solo si el diagnostico tambien permite `READY` |

`READY_FOR_COMMISSIONING` nunca escribe en `recipes.json`. La aprobacion final
se realiza desde el editor de recetas, donde se vuelven a ejecutar las reglas
de comisionamiento vigentes.

## Archivos

- `acceptance.json`: criterios versionados de la instalacion;
- `runtime/acceptance/*.json`: sesiones y reportes locales, ignorados por Git;
- `runtime/traceability/cycles.jsonl`: ciclos producidos por el motor;
- `scripts/acceptance_session.py`: captura, importacion y evaluacion.

La sesion es reanudable, se escribe de forma atomica y conserva una copia
`.bak` al actualizarse. Un `cycle_id` existente se omite para que reimportar la
misma traza no duplique poblacion.

Al crearla se guarda una huella SHA-256 del plan y de los `evidence_files`
declarados por la instalacion. Si despues cambia una receta, configuracion o
firmware incluido, la sesion anterior se rechaza. La evidencia queda asociada
a la configuracion que realmente fue probada.

## Criterios evaluados

- minimo de muestras OK y NG por modelo;
- falsos OK absolutos;
- tasa maxima de falsos NG;
- errores o cancelaciones de ejecucion;
- percentil 95 del tiempo total de ciclo;
- evidencia de salida segura, si el plan la exige por ciclo;
- escenarios fisicos requeridos por la instalacion.

Una falla tiene prioridad sobre los pendientes. Sin fallas, cualquier muestra o
escenario faltante conserva el estado `PENDING`.

## Reutilizacion

Para otra maquina se crea un directorio de instalacion con su
`commissioning.json`, `system.json`, `recipes.json` y `acceptance.json`. Es
posible cambiar modelos, cantidades, tiempos y escenarios sin modificar el
motor. El firmware conserva sus pines, polaridades, timeouts y mapeos en su
archivo de configuracion propio.
