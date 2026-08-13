# Auditoria de compatibilidad - Motor de vision, ESP32 y PLC Worksurface

**Fecha:** 2026-08-13  
**Responsable funcional:** Andy  
**Fuentes revisadas:** `Proyecto_vision_sensor_actual.zip`,
`CONTEXTO_PROYECTO_WORKSURFACE_V11(1).md`, `ESP_WORKSURFACE(3).txt` y
`PLC_WORKSURFACE(2).pdf`.

## 1. Conclusion ejecutiva

La version adjunta del proyecto no corresponde a una fase 11 terminada. El
historial Git termina en:

```text
6f7f6fa Add startup diagnostics and cycle traceability
```

Ese commit es la fase 6. El documento V11 es la version 11 del contexto y
expresamente deja pendientes las fases 7 a 12.

No es seguro implementar la fase 12 directamente sobre esta base, porque se
omitirian el framework de herramientas, la instalacion Worksurface real, la
actualizacion del firmware/control, el comisionamiento y el paquete de
despliegue reversible.

El firmware ESP32 actual **no es compatible** con el contrato
`vision_controller_v1` que ya exige el motor. Debe reemplazarse o actualizarse
antes de realizar pruebas integradas. El ladder PLC puede conservarse como
base, pero requiere comprobaciones electricas y funcionales antes del corte.

## 2. Estado comprobado del proyecto

| Evidencia | Resultado |
|---|---|
| Rama actual | `feature/universal-operations-phase6` |
| Commit actual | `6f7f6fa` |
| Pruebas automatizadas | 53 aprobadas |
| Cambios semanticos no confirmados | Ninguno; las diferencias del ZIP son finales de linea CRLF |
| Registro de herramientas | Todavia fijo en `app/app.py` |
| Recetas reales | Solo `MODELO_A` |
| Mapeo externo | Solo `A -> MODELO_A` |
| Firmware universal | No implementado |
| Paquete `systemd`/rollback | No presente |

Esto confirma que siguen pendientes:

1. fase 7: framework extensible de herramientas;
2. fase 8: configuracion y recetas A/B/C de Worksurface;
3. fase 9: firmware ESP32 compatible y revision del PLC;
4. fase 10: comisionamiento fisico;
5. fase 11: paquete instalable, autoarranque y rollback;
6. fase 12: pulido visual, aceptacion y sustitucion final.

## 3. Compatibilidad del firmware ESP32

| Contrato | Motor actual | Firmware adjunto | Dictamen |
|---|---|---|---|
| Transporte | STX/ETX, 115200 baud | STX/ETX, 115200 baud | Compatible |
| Sintaxis | `TIPO|CAMPO=valor` | Mensajes simples y `CAMPO: valor` | Incompatible |
| Handshake | `HELLO` / `HELLO_ACK` con protocolo y firmware | `SYNC` / `SYNC_OK` | Incompatible |
| Disponibilidad | `READY|STATE=0/1` | Variable `rpiReady` sin uso | Incompatible |
| Heartbeat | `PING|SEQ=n` / `PONG|SEQ=n` | No implementado | Incompatible |
| Trigger | Incluye `CYCLE` unico y `MODEL` retenido | Envia solo `TRIGGER` | Incompatible |
| ACK de trigger | Tipo, ciclo y estado | ACK generico | Incompatible |
| Resultado de vision | `VISION_RESULT|CYCLE=...|RESULT=...` | Recibe `OK` o `NG` | Incompatible |
| Error de vision | `RESULT=ERROR` | No soportado; equivale a NG por timeout | Incompatible y riesgoso |
| Resultado final | `FINAL_RESULT` con ciclo | Envia `OK` o `NG` | Incompatible |
| Cancelacion | `CANCEL` ligado al ciclo | Envia `RESET` sin ciclo | Incompatible |
| Resultado tardio | Debe rechazarse por `CYCLE` | No existe correlacion | Incompatible |
| Estado seguro | Salida baja en desconexion, error y cancelacion | Solo se garantiza parcialmente | Insuficiente |

### 3.1 Cambios obligatorios en la ESP32

1. Implementar `vision_controller_v1` y publicar una version de firmware.
2. Generar un identificador de ciclo unico por arranque y contador.
3. Retener el modelo antes de publicar el trigger.
4. Bloquear triggers si el motor informa `READY|STATE=0` o no existe handshake.
5. Implementar ACK tipados e idempotencia para reintentos.
6. Asociar trigger, resultado, cancelacion y resultado final al mismo `CYCLE`.
7. Responder `PONG` y pasar a estado seguro al perder comunicacion.
8. Distinguir `OK`, `NG` y `ERROR`; `ERROR` nunca debe activar la salida PLC.
9. Manejar `RESET|SCOPE=CYCLE`, `RESTART` y `FOCUS|STATE=BUSY`.
10. Forzar GPIO 32 a LOW en arranque, desconexion, cancelacion, timeout y error.
11. Corregir el retorno de `RESULT`: actualmente un NG no vuelve a `IDLE`.
12. Alinear el timeout con los 20 s del motor mas un margen comprobado. Los
    12 s actuales pueden vencer antes que la inspeccion.

### 3.2 Riesgo de mapeo A/B

El ladder activa:

- `Y0` para el selector asociado a `X2`;
- `Y1` para el selector asociado a `X3`;
- `Y0 + Y1` para `X4`.

El firmware interpreta:

- `bin_0=HIGH, bin_1=LOW` como B;
- `bin_0=LOW, bin_1=HIGH` como A;
- ambos HIGH como C.

Si `bin_0` esta cableado a `Y0` y `bin_1` a `Y1`, A y B estan intercambiados
respecto de la asignacion historica `Y0=A`, `Y1=B`. No debe corregirse por
suposicion: primero hay que documentar el pinout real y medir los niveles.

## 4. Revision del PLC

### 4.1 Comportamiento observado

- `X0/X1` forman la habilitacion bimanual mediante `M0/M1` y `T1/T2`.
- `M2` retiene el ciclo cuando existe pieza en `X7`.
- `M2` activa simultaneamente `Y2`, `Y3` y `Y4`: trigger y clamps.
- `X5` (resultado ESP32) o `X6` (llave de calidad) activan `M3` y liberan el
  ciclo.
- `Y0/Y1` codifican los tres selectores mientras `M2` esta activo.
- `Y5` sigue directamente a `X2`.

### 4.2 Cambios PLC obligatorios

No se identifica un cambio obligatorio de ladder para adoptar el protocolo
serial. El PLC no se comunica por serial con la Raspberry; esa responsabilidad
pertenece a la ESP32. Mantener `X5` como unica autorizacion automatica es una
interfaz segura por defecto siempre que la ESP garantice LOW ante cualquier
falla.

### 4.3 Verificaciones y posibles ajustes

| Punto | Accion |
|---|---|
| `Y2`, `Y3`, `Y4` simultaneos | Medir el tiempo real hasta que la pieza quede inmovil y configurarlo como `mechanical_settle_ms` |
| Caida de `Y0/Y1` al terminar M2 | La ESP debe retener el modelo durante todo el ciclo |
| `X5` | Confirmar nivel activo y que ninguna falla/reinicio produzca un pulso HIGH |
| `X6` | Confirmar que libera fisicamente y que la ESP cancela el ciclo activo |
| Codificacion A/B/C | Verificar continuidad, pinout y niveles con cada selector |
| Falla del sistema | Evaluar indicador separado; con una sola salida PLC, NG y ERROR permanecen ambos en LOW |
| Control bimanual | Tratarlo como control funcional, no como seguridad certificada |

El PLC solo debe modificarse si las mediciones contradicen estos supuestos o si
se requiere distinguir visualmente NG de una falla del sistema.

## 5. Secuencia de integracion recomendada

1. Continuar desde fase 6 con la fase 7, sin saltar directamente a fase 12.
2. Completar el registro extensible y contratos de herramientas.
3. Construir las recetas externas A/B/C y comisionarlas con imagenes reales.
4. Crear el firmware ESP32 `vision_controller_v1` y probarlo primero con E/S
   desconectadas y el simulador.
5. Medir señales PLC/ESP32 y confirmar A/B/C, estado seguro y asentamiento.
6. Ejecutar la matriz fisica OK/NG/ERROR/TIMEOUT/CANCEL/desconexion.
7. Crear el paquete Raspberry con servicio, respaldo y rollback.
8. Realizar el pulido visual y la aceptacion paralela de fase 12.

## 6. Criterio para autorizar el corte final

No debe sustituirse el software antiguo hasta comprobar como minimo:

- cero triggers aceptados en `NOT_READY`;
- cero resultados tardios aplicados a otro ciclo;
- GPIO 32 y `X5` permanecen LOW ante error, timeout, cancelacion y desconexion;
- A/B/C seleccionan la receta y patron de sensores correctos;
- la llave de calidad libera sin depender de Raspberry;
- reinicios de Raspberry/ESP32 no generan pulsos de aceptacion;
- registros de ciclo coinciden con las pruebas fisicas;
- rollback probado y documentado.
