# Protocolo `vision_controller_v1`

Este es el unico contrato de comunicacion del motor. El firmware ESP32 y la
logica PLC se crean y versionan por separado para cada maquina.

## Transporte

- serial a 115200 baud por defecto;
- trama `STX (0x02) + UTF-8 + ETX (0x03)`;
- payload `TIPO|CAMPO=valor`;
- nombres de tipo y campo en mayusculas;
- valores escapados con percent-encoding.

## Secuencia base

1. Motor envia `HELLO|PROTO=1|ROLE=VISION_ENGINE`.
2. Controlador responde `HELLO_ACK|PROTO=1|FW=...|READY=1`.
3. Motor publica `READY|STATE=1` o `READY|STATE=0|REASON=...`.
4. Controlador envia `TRIGGER|CYCLE=...|MODEL=...`.
5. Motor responde `ACK|TYPE=TRIGGER|CYCLE=...|STATUS=OK`.
6. Motor ejecuta la receta mapeada y envia
   `VISION_RESULT|CYCLE=...|RESULT=OK` o `NG`.
7. Controlador confirma con ACK tipado y aplica su logica fisica externa.
8. Si existe resultado final de maquina, envia
   `FINAL_RESULT|CYCLE=...|RESULT=OK`, `NG` o `ERROR`.

## Mensajes obligatorios

| Direccion | Mensaje | Campos principales |
|---|---|---|
| Motor a controlador | `HELLO` | `PROTO`, `ROLE` |
| Controlador a motor | `HELLO_ACK` | `PROTO`, `FW`, `READY`, `REASON?`, `MODEL?` |
| Motor a controlador | `READY` | `STATE`, `REASON?` |
| Motor a controlador | `PING` | `SEQ` |
| Controlador a motor | `PONG` | `SEQ` |
| Controlador a motor | `MODEL` | `CODE` |
| Controlador a motor | `TRIGGER` | `CYCLE`, `MODEL` |
| Motor a controlador | `VISION_RESULT` | `CYCLE`, `RESULT` |
| Controlador a motor | `FINAL_RESULT` | `CYCLE`, `RESULT` |
| Cualquiera | `ACK` | `TYPE`, `CYCLE?`, `STATUS`, `ERROR?` |
| Controlador a motor | `CANCEL` | `CYCLE`, `REASON` |
| Cualquiera | `RESET` | `SCOPE`, `CYCLE?`, `REASON?` |
| Cualquiera | `ERROR` | `CODE`, `DETAIL?` |

`MODEL` es un identificador opaco. El motor no impone A/B/C ni interpreta
sensores. El archivo de instalacion lo mapea al nombre de una receta.

## Invariantes

- solo puede existir un ciclo activo;
- cada trigger, resultado, cancelacion y ACK de ciclo conserva el mismo
  `CYCLE`;
- un ciclo cerrado no se reutiliza;
- un resultado tardio se rechaza;
- una perdida de enlace cancela el ciclo local y elimina READY;
- un timeout o error nunca se convierte en OK;
- el controlador no debe iniciar un ciclo mientras el motor publique
  `READY|STATE=0`.

## Reintentos e idempotencia

La perdida de un ACK no debe crear ni cerrar otro ciclo:

- un `TRIGGER` repetido con el mismo `CYCLE` y `MODEL` recibe nuevamente ACK,
  pero el motor no vuelve a ejecutar la receta;
- el mismo `CYCLE` con otro `MODEL` se rechaza;
- un `VISION_RESULT` repetido con igual ciclo y resultado recibe otro ACK, sin
  volver a evaluar sensores;
- un `VISION_RESULT` contradictorio para el mismo ciclo se rechaza;
- un `FINAL_RESULT` repetido con el mismo ciclo y resultado recibe nuevamente
  ACK, pero la interfaz no duplica el resultado ni la trazabilidad;
- todo mensaje perteneciente a un ciclo anterior se rechaza como tardio.

## Heartbeat y recuperacion

El motor publica `PING|SEQ=n` cada dos segundos. El controlador devuelve el
mismo valor en `PONG|SEQ=n`. Siete segundos sin una trama valida hacen que
ambos extremos:

1. retiren `READY`;
2. cancelen el ciclo activo;
3. fuercen la salida de aprobacion a estado seguro;
4. repitan `HELLO/HELLO_ACK` antes de aceptar otro trigger.

`RESET|SCOPE=CYCLE` libera solamente el ciclo actual. `RESTART` reinicia el
ESP32 y no forma parte de la recuperacion normal.

## Implementacion Worksurface de fase 9

El firmware de `ESP32/FSM/` es especifico de Worksurface. El motor conserva el
protocolo generico y mapea los IDs opacos A/B/C mediante `system.json`.

En Worksurface, GPIO 32 solo puede activar la liberacion PLC cuando:

- vision entrega `OK` para el ciclo activo;
- los sensores fisicos coinciden con el patron del modelo retenido;
- el enlace continua sincronizado.

`NG`, `ERROR`, timeout, cancelacion, perdida de enlace y reinicio mantienen la
salida en estado seguro.
