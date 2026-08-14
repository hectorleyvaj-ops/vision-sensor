# Diagnostico operativo y trazabilidad

## Objetivo

Una estacion no se considera lista solo porque la interfaz abra. Antes de
publicar `READY`, el motor valida la configuracion, el catalogo, los mapeos, las
herramientas, las imagenes maestras de recetas comisionadas y el almacenamiento
de evidencia. Camara y controlador actualizan el mismo reporte al terminar sus
pruebas reales.

## Estados de diagnostico

| Estado | Significado | Efecto |
|---|---|---|
| `PASS` | Comprobacion aprobada | No bloquea produccion |
| `WARNING` | Pendiente o degradacion no concluyente | Se muestra en log; no bloquea por si sola |
| `ERROR` | Recurso o componente incorrecto | Bloquea `READY` cuando el item esta marcado como obligatorio |

Cada item tiene una clave estable. Por ejemplo, `camera.runtime` comienza como
pendiente y despues se reemplaza con el dispositivo, resolucion y FPS reales.
El reporte no crece indefinidamente.

## Comprobaciones estaticas

- `system.json` cargado con el esquema vigente;
- catalogo de recetas legible y no vacio;
- destinos de `controller.model_map` existentes;
- herramientas registradas;
- definicion, ROI y parametros de cada receta;
- existencia y lectura de imagenes maestras de `img_hist`;
- directorio de trazabilidad escribible;
- puerto correspondiente a la plataforma configurado;
- parametros solicitados de camara disponibles para la prueba dinamica.

Una receta no comisionada con recursos incompletos produce `WARNING`. La misma
falla en una receta marcada `commissioned=true` produce un `ERROR` bloqueante.

## Comprobaciones dinamicas

La camara publica el dispositivo resuelto, resolucion/FPS solicitados y reales.
Un dispositivo ausente o un worker que termina por excepcion bloquea
produccion. El controlador publica puerto y baudrate, y despues firmware y
version de protocolo cuando completa `HELLO/HELLO_ACK`.

Si `runtime.require_controller_ready=false`, una falla serial queda registrada
pero no se convierte en bloqueo por diagnostico. Esta excepcion solo es
apropiada para pruebas controladas.

## Registro de ciclos

Cada linea de `cycles.jsonl` es independiente y contiene:

- instalacion, `cycle_id`, modelo externo y receta;
- fecha UTC de inicio/fin y duracion total;
- resultado final `OK`, `NG`, `ERROR` o `CANCELLED`;
- estado del pipeline, causa y steps omitidos;
- orden, tool, estado, duracion, error y datos de cada step ejecutado;
- estado de entrega/ACK al controlador.

No se guardan frames ni imagenes de depuracion en este archivo. La escritura es
serializada, fuerza el vaciado a disco y rota antes de superar el limite
configurado. Un error al guardar evidencia nunca se convierte en `NG`.

## Recuperacion

1. Consultar el mensaje visible y `startup_diagnostics.json`.
2. Ejecutar la accion indicada por el item bloqueante.
3. Reiniciar cuando se haya cambiado hardware, puerto, configuracion o rutas.
4. Confirmar que camara y controlador pasen de pendiente/error a `PASS`.
5. No forzar `READY` ni comisionar una receta con recursos faltantes.

## Uso en aceptacion

La trazabilidad puede alimentar una sesion de aceptacion sin duplicar la
ejecucion. Cada lote importado debe tener una clasificacion de referencia OK o
NG independiente del resultado del software. El evaluador compara ambas y
calcula falsos OK, falsos NG, errores y P95.

El procedimiento completo y la diferencia entre diagnostico, aceptacion y
comisionamiento estan descritos en `docs/acceptance_framework.md`. Importar una
traza nunca edita recetas ni cambia `commissioned`.
