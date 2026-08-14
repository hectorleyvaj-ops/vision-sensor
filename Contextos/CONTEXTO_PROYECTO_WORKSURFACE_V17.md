# Contexto Worksurface V17 - Hotfix de arranque degradado

**Fecha:** 2026-08-14

**Base:** fase 11 aplicada (`017552a`)

## Decision

La camara es obligatoria para inspeccionar, pero su ausencia no debe impedir
entrar a la interfaz. El motor adopta un arranque degradado seguro:

| Capacidad | Camara ausente |
|---|---|
| Abrir interfaz | Permitido |
| Consultar eventos y estado | Permitido |
| Editar configuracion | Permitido |
| Cambiar indice de camara | Permitido; requiere reinicio |
| Publicar `READY=1` | Bloqueado |
| Aceptar trigger | Bloqueado |
| Ejecutar inspeccion | Bloqueado |
| Autorizar resultado PLC | Bloqueado |

## Causa corregida

Antes, el hilo de camara arrancaba antes de crear `Camera` y `StateManager`.
En Windows, el constructor serial podia permanecer ocupado durante el reset
DTR. Si la camara fallaba en ese intervalo, `CameraWorker` emitia `finished`
dos veces y era eliminado. La conexion posterior de `frame_ready` intentaba
usar un objeto Qt ya destruido y producia:

```text
Signal source has been deleted
QThread: Destroyed while thread is still running
```

Ahora se construyen y conectan camara, serial y FSM antes de iniciar cualquier
hilo. El fallo de apertura emite una sola finalizacion, el worker permanece
consultable desde configuracion y un arranque parcial se cierra limpiamente si
ocurre una excepcion realmente fatal.

## Apertura de camara en Windows

El indice definido en `camera.device` se prueba con los backends DSHOW, MSMF y
AUTO. Todos usan exactamente el mismo indice. No se buscan indices alternos de
forma automatica porque eso podria asociar la estacion a la camara incorrecta.

## Barreras de produccion conservadas

La camara ausente genera un diagnostico bloqueante. Ademas, no existe frame
fresco. `get_system_ready_error()` mantiene `READY=0`, `run_fsm()` rechaza el
trigger y el controlador conserva las salidas seguras.

El boton de configuracion no depende de READY: solo se deshabilita durante una
FSM o una comprobacion de enfoque. Esto permite reparar el indice sin permitir
produccion.

## Validacion

- compilacion Python correcta;
- 123 pruebas automatizadas correctas;
- cinco contratos nuevos para arranque degradado;
- instalacion Worksurface valida y todavia lista para calibrar;
- prueba fisica pendiente en Windows con camara desconectada e indice erroneo.

La planificacion no cambia: fase 12 cubre despliegue industrial/touch y fase 13
las pruebas integrales con hardware real.
