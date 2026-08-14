# Guia fase 9 - ESP32, protocolo y revision PLC Worksurface

## 1. Alcance

Esta fase reemplaza el firmware heredado por `vision_controller_v1`, fortalece
los reintentos del enlace Python y prepara pruebas de banco sin depender de que
las recetas esten comisionadas.

No modifica el ladder PLC. Las mediciones de polaridad, pinout y tiempos se
realizan antes de decidir si el ladder necesita cambios.

## 2. Estado de `commissioned`

`commissioned` se modifica desde la interfaz:

1. abrir `CONFIGURACION`;
2. elegir un modelo;
3. pulsar `RECETA`;
4. activar `Comisionada`;
5. pulsar `VALIDAR Y GUARDAR`.

No se recomienda editar el JSON manualmente. El dialogo valida los parametros
antes de guardar. Durante fase 9 las recetas pueden permanecer en `false`: el
script de banco prueba el ESP32 sin abrir la aplicacion ni ejecutar vision.

## 3. Archivos de firmware

| Archivo | Funcion |
|---|---|
| `ESP32/FSM/FSM.ino` | FSM, tramas, ciclo, heartbeat y estado seguro |
| `ESP32/FSM/worksurface_config.h` | Pines, polaridades, A/B/C, sensores y tiempos |

Configuracion inicial:

| Señal | GPIO | Nivel funcional asumido |
|---|---:|---|
| Trigger PLC | 5 | HIGH |
| Modelo bit 0 / Y0 | 18 | HIGH |
| Modelo bit 1 / Y1 | 19 | HIGH |
| Llave de calidad | 4 | HIGH |
| Sensor izquierdo | 2 | HIGH = OK |
| Sensor derecho | 15 | HIGH = OK |
| Liberacion PLC | 32 | HIGH = pieza aprobada |

Mapeo inicial que debe medirse:

| Bit 0 | Bit 1 | Modelo |
|---:|---:|---|
| 1 | 0 | A |
| 0 | 1 | B |
| 1 | 1 | C |
| 0 | 0 | Invalido; trigger rechazado |

Patrones confirmados funcionalmente:

| Modelo | Izquierdo | Derecho |
|---|---|---|
| A | OK | NG |
| B | NG | OK |
| C | OK | OK |

Si la medicion demuestra que Y0/Y1 estan invertidos, intercambiar unicamente
`MODEL_BITS_10` y `MODEL_BITS_01` en `worksurface_config.h`.

## 4. Cargar el firmware

1. Desconectar temporalmente GPIO 32 de la entrada PLC o impedir fisicamente
   cualquier movimiento/liberacion.
2. Abrir `ESP32/FSM/FSM.ino` en Arduino IDE.
3. Verificar que `worksurface_config.h` aparezca como segunda pestaña.
4. Seleccionar la tarjeta ESP32 correcta y su puerto.
5. Pulsar **Verify** y corregir cualquier error antes de conectar E/S.
6. Pulsar **Upload**. Algunas tarjetas requieren mantener presionado BOOT
   mientras comienza la carga.

Referencias oficiales:

- https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html
- https://docs.arduino.cc/software/ide-v2/tutorials/getting-started/ide-v2-uploading-a-sketch

## 5. Prueba serial aislada

Detener completamente el software Worksurface: solo un proceso puede abrir el
puerto CP2102.

En Raspberry:

```bash
cd ~/calibration/vision-sensor
source venv-rpi32/bin/activate
```

Identificar el puerto:

```bash
ls -l /dev/serial/by-id/
```

### Solo handshake y heartbeat

```bash
python scripts/controller_protocol_smoke.py \
  --port /dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0
```

Debe mostrar `HELLO_ACK`, firmware `worksurface-controller-1.0.0` y `PONG` con
la misma secuencia.

### Ciclo seguro con ERROR

Con GPIO 32 aun desconectado del PLC:

```bash
python scripts/controller_protocol_smoke.py \
  --port /dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0 \
  --exercise-cycle \
  --result ERROR
```

Activar manualmente una combinacion A/B/C y despues el trigger. El resultado
final debe ser `ERROR` y GPIO 32 debe permanecer en estado seguro.

Repetir con `--result NG`. La prueba `OK` requiere deliberadamente:

```bash
--result OK --allow-pass-output
```

No usarla hasta medir las cinco entradas y mantener aislada la salida PLC.

## 6. Matriz minima antes de reconectar el PLC

| Prueba | Resultado obligatorio |
|---|---|
| Arranque ESP32 | GPIO 32 seguro |
| Sin handshake | Trigger ignorado; GPIO 32 seguro |
| `READY=0` | Trigger ignorado |
| Bits 00 | Ciclo rechazado |
| Resultado NG | GPIO 32 seguro |
| Resultado ERROR | GPIO 32 seguro |
| Timeout de vision | `FINAL_RESULT=ERROR`; GPIO 32 seguro |
| Llave de calidad | CANCEL/RESET y salida segura |
| Desconectar USB | En menos de 7 s, salida segura |
| Repetir TRIGGER | Un solo ciclo; ACK repetido |
| Repetir resultado igual | ACK repetido; sin segunda evaluacion |
| Resultado contradictorio | Rechazado |
| Sin ACK de resultado final | Cancelacion y GPIO 32 seguro tras 10 intentos |

## 7. Revision del PLC

No modificar el ladder por suposicion. Registrar con multimetro o entradas de
diagnostico:

1. continuidad real `Y0 -> GPIO18` y `Y1 -> GPIO19`;
2. niveles activos de trigger, selectores y sensores;
3. nivel de GPIO32 durante arranque, reset y desconexion;
4. tiempo desde Y2/Y3/Y4 hasta que la pieza queda inmovil;
5. funcionamiento independiente de X6/llave de calidad;
6. que Y0/Y1 permanezcan validos al menos durante el debounce de 80 ms.

El tiempo medido en el punto 4 se carga después en
`runtime.mechanical_settle_ms`. Si los niveles o conexiones contradicen el
header, primero se actualiza `worksurface_config.h`; el ladder solo cambia si
la secuencia fisica lo exige.

## 8. Integracion con el software

Para abrir Worksurface con su paquete externo:

```bash
env VISION_QT_API=pyqt5 \
  VISION_SYSTEM_CONFIG="$PWD/installations/worksurface/system.json" \
  python main.py
```

Mientras `commissioned=false`, el programa debe completar handshake y publicar
`READY=0` con la razon de bloqueo. Es el comportamiento correcto de fase 9.
Las pruebas automaticas de ciclo completo se reservan para fase 10, despues de
autorizar una receta probada y reconectar el PLC bajo la matriz anterior.
