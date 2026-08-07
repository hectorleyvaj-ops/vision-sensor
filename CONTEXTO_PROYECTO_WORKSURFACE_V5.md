# Contexto vivo - Worksurface V5

**Ultima actualizacion:** 2026-08-06  
**Responsable funcional:** Andy  
**Estado:** ladder vigente confirmado; diagnostico de fase 2 revisado; firmware exacto instalado aun sin respaldo  
**Sustituye como referencia principal a:** `CONTEXTO_PROYECTO_WORKSURFACE_V4.md`

## 1. Objetivo vigente

Actualizar Worksurface sobre el motor general de `Proyecto_vision_sensor` para obtener una estacion de inspeccion rapida, recuperable, mantenible y adecuada para una interfaz tactil de 480 x 320. El sistema debe arrancar automaticamente, seleccionar uno de tres modelos, sujetar una pieza solo cuando esta posicionada, ejecutar vision y dos comprobaciones fisicas de modelo, liberar automaticamente en `PASS` y permanecer bloqueado en `FAIL` hasta usar la llave de calidad.

El tiempo total ordinario debe ser menor de 10 s y reducirse tanto como sea posible. El primer disparo despues de arranque o cambio que invalide el foco puede tardar mas por la calibracion, pero esa condicion debe mostrarse y controlarse explicitamente; no puede aceptar triggers silenciosamente mientras el sistema no esta listo.

## 2. Arquitectura fisica confirmada

El sistema utiliza tres sensores de fibra en total, pero no los tres como entradas directas de la ESP32:

- sensor de posicion: entra al PLC como `X7` y autoriza el enclavamiento del ciclo;
- sensor de comprobacion fisica izquierdo: entra a la ESP32;
- sensor de comprobacion fisica derecho: entra a la ESP32.

Esta distribucion concuerda con el ladder vigente y con `ESP32/FSM/FSM.ino`, que declara dos sensores de evaluacion. El archivo heredado `ESP_WORKSURFACE.txt` tambien declara solo dos sensores en la ESP32. Por tanto, la frase "tres sensores en la ESP" no esta respaldada por los archivos disponibles; la interpretacion consistente es tres sensores en la maquina, repartidos uno al PLC y dos a la ESP32.

## 3. Mapa vigente del PLC

Fuente principal: `PLC_WORKSURFACE(1).pdf`, creado el 2026-08-06 a las 14:34.

### Entradas

| Direccion | Funcion confirmada |
|---|---|
| `X0` | Boton de inicio izquierdo |
| `X1` | Boton de inicio derecho |
| `X2` | Selector, modelo 1 |
| `X3` | Selector, modelo 2 |
| `X4` | Selector, modelo 3 |
| `X5` | Validacion/liberacion procedente de la ESP32 despues de inspeccion correcta |
| `X6` | Llave de calidad/desenclave |
| `X7` | Sensor de pieza en posicion para inspeccion |

### Salidas

| Direccion | Funcion confirmada |
|---|---|
| `Y0` | Primer bit de seleccion de modelo hacia la ESP32 |
| `Y1` | Segundo bit de seleccion de modelo hacia la ESP32 |
| `Y2` | Trigger de ciclo hacia la ESP32 |
| `Y3` | Clamp lateral 1 |
| `Y4` | Clamp lateral 2 |
| `Y5` | Electrovalvula del tope fisico; sigue directamente a `X2` |

### Memorias y temporizadores relevantes

| Dispositivo | Funcion observada |
|---|---|
| `M0`, `T1 K5` | Memoria temporal del boton `X0` |
| `M1`, `T2 K5` | Memoria temporal del boton `X1` |
| `M2` | Enclavamiento del ciclo |
| `M3` | Orden de desenclavamiento por `X5` o `X6` |
| `M4` | Decodificacion exclusiva del modelo 1 |
| `M5` | Decodificacion exclusiva del modelo 2 |
| `M6` | Decodificacion exclusiva del modelo 3 |

El valor `K5` se interpreta provisionalmente como una ventana aproximada de 0.5 s segun la base de tiempo configurada en el PLC. Debe comprobarse en el software del PLC antes de documentarlo como valor definitivo.

## 4. Tabla de verdad del selector

En reposo, con `M2 = 0`:

| Estado | `X2` | `X3` | `X4` | `Y0` | `Y1` | `Y5` |
|---|---:|---:|---:|---:|---:|---:|
| Inactivo | 0 | 0 | 0 | 0 | 0 | 0 |
| Modelo 1 | 1 | 0 | 0 | 1 | 0 | 1 |
| Modelo 2 | 0 | 1 | 0 | 0 | 1 | 0 |
| Modelo 3 | 0 | 0 | 1 | 1 | 1 | 0 |

Durante un ciclo enclavado, `M2 = 1` inhibe `M4`, `M5` y `M6`, por lo que `Y0` y `Y1` vuelven a 0 aunque el selector permanezca en un modelo. `Y5` no depende de `M2` y permanece activo mientras `X2` este activo.

Consecuencia obligatoria para la ESP32: debe leer, validar y guardar el modelo antes del flanco de `Y2`. No puede determinar el modelo leyendo `Y0/Y1` despues del trigger. El codigo `00` durante el ciclo no significa "modelo inactivo"; significa que las lineas de modelo fueron inhibidas por el ladder.

Debe comprobarse fisicamente que `Y0` y `Y1` llegan a los pines de ESP32 en el orden esperado. El firmware moderno interpreta `01` como A, `10` como B y `11` como C, por lo que es probable que exista un cruce intencional entre los nombres `bin_0/bin_1` y `Y0/Y1`.

## 5. Secuencia real del ladder

1. El selector activa exactamente una de `X2`, `X3` o `X4` y el PLC publica el codigo por `Y0/Y1`.
2. Para el modelo 1, `X2` activa ademas `Y5`, colocando el tope fisico.
3. Los botones `X0` y `X1` deben accionarse dentro de la ventana de `T1/T2`.
4. Si ambos botones fueron reconocidos y `X7` confirma la pieza en posicion, se enclava `M2`.
5. `M2` activa al mismo tiempo `Y2`, `Y3` y `Y4`: trigger hacia ESP32 y ambos clamps.
6. `X5` desde ESP32 o `X6` desde la llave activa `M3`, rompe el enclavamiento y desactiva `Y2/Y3/Y4`.
7. La llave de calidad libera por la ruta local del PLC aunque Raspberry o ESP32 no esten respondiendo.

`X7` solo es requisito para iniciar `M2`; despues del enclavamiento, una perdida de `X7` no libera por si sola los clamps. Esta conducta debe conservarse o cambiarse de forma consciente despues de probar el proceso.

## 6. Hallazgo de temporizacion mecanica

El ladder activa trigger y clamps simultaneamente. No existe una espera de asentamiento mecanico entre `Y3/Y4` y la captura. La nueva secuencia no debe asumir que la pieza ya esta inmovil cuando aparece `Y2`.

La ESP32 o Raspberry debe aplicar un tiempo de asentamiento configurable y medido antes de capturar, o utilizar una confirmacion fisica si se incorpora en el futuro. El valor no debe fijarse por intuicion: se medira en video y con varias piezas, presiones y temperaturas. Mientras se valida, cualquier trigger recibido durante enfoque, reconexion o receta no lista debe terminar en `NOT_READY/ERROR`, no en una inspeccion parcial.

## 7. Firmware disponible y firmware probablemente desplegado

No existe un respaldo garantizado del firmware exacto actualmente grabado.

### `ESP_WORKSURFACE.txt`

Es una version heredada con botones, selector, dos sensores y control directo de clamps desde la ESP32. No coincide con el ladder vigente, donde botones y clamps estan bajo el PLC.

### `Proyecto_vision_sensor/ESP32/FSM/FSM.ino`

Este firmware coincide mucho mejor con la instalacion actual:

- entrada de trigger;
- dos bits de modelo;
- llave de calidad;
- dos sensores de comprobacion;
- una salida de resultado hacia PLC;
- protocolo STX/ETX con `SYNC`, `ACK`, `TRIGGER`, `MODEL`, `OK`, `NG` y `RESET`.

Los registros de `vision.service` contienen exactamente frases caracteristicas de este codigo, entre ellas `[ESP] Trigger valido`, `[FSM] Reset de calidad`, `[RESULT] NG` y `SYNC_OK|MODEL`. Esto demuestra que el firmware instalado es, como minimo, una version derivada muy cercana a `FSM.ino`; no demuestra que los binarios sean identicos ni recupera los ultimos cambios.

Accion antes de reemplazarlo: conservar `FSM.ino` como referencia funcional, documentar cableado y comportamiento, construir firmware V3 con pruebas y grabarlo solo cuando exista un procedimiento de rollback. No se debe intentar extraer el fuente desde la ESP32; un binario leido de flash serviria como respaldo de recuperacion, pero no reconstruiria el codigo fuente original.

## 8. Autoridad de control acordada

| Componente | Autoridad |
|---|---|
| PLC | Botones, sensor de posicion, enclavamiento, clamps, tope y liberacion local por llave |
| ESP32 | Lectura determinista de trigger/modelo/llave/dos sensores, combinacion fisica acordada, salida de validacion, heartbeat y puente serial |
| Raspberry Pi | Camara, enfoque, recetas, herramientas, interfaz, decision de vision, trazabilidad y diagnostico |

Raspberry y ESP32 no tendran ambas control directo de las mismas electrovalvulas. La salida final de aprobacion debe exigir vision valida, patron correcto de los dos sensores y coincidencia del identificador de ciclo. Timeout, perdida de comunicacion, receta invalida o desconexion de camara nunca pueden producir `X5`.

## 9. Protocolo V3 requerido

El protocolo definitivo debe incluir:

- version de protocolo y firmware;
- `HELLO`, `READY`, `NOT_READY` y heartbeat;
- identificador monotono de ciclo;
- modelo latched antes del trigger;
- estado de ambos sensores con marca de tiempo;
- resultado de vision separado del resultado final;
- `ACK` asociado a mensaje/ciclo, no un ACK generico ambiguo;
- timeouts y reintentos limitados;
- resincronizacion despues de reconexion;
- cancelacion inmediata por llave de calidad;
- garantia de que un resultado atrasado no pueda liberar el ciclo siguiente.

El firmware actual no procesa todos los mensajes que Python ya intenta enviar (`PING`, `RPI_READY`, `RPI_NOT_READY`, `CALIBRATING`, `FOCUS_BUSY`, `RESET_FSM`) ni responde `PONG`. Ese contrato debe corregirse en ambos extremos a la vez.

## 10. Diagnostico Raspberry de fase 2

### Servicio y rendimiento

- `vision.service` esta habilitado con `Restart=always` y ejecuta `/home/worksurface/Proyecto_vision_sensor/venv/bin/python main.py`.
- En la captura de fase 2 el servicio estaba detenido de forma limpia; no habia evidencia de un crash en el ultimo cierre.
- Durante 1 h 21 min de ejecucion acumulo 1 h 42 min de CPU, aproximadamente 126 % de un nucleo en promedio.
- Con la aplicacion detenida la carga bajo y la temperatura fue 61.8 C, comparada con 79.8 C durante la primera captura.
- La lentitud se relaciona con procesamiento continuo de video y temperatura, no con RAM: la Pi tiene 8 GB.

### Tiempos observados

- Varias calibraciones de foco tardaron aproximadamente 10 a 18 s.
- Hubo triggers recibidos mientras el enfoque estaba en curso; el procesamiento quedo retrasado y algunos ciclos superaron 10 s.
- El sistema recalibro al cambiar de modelo, aunque el objetivo de produccion es calibrar en el primer disparo y conservar el foco mientras siga siendo valido.

La nueva aplicacion publicara `READY` solo cuando camara, receta, foco y ESP32 esten listos. El PLC actual no posee una entrada `READY`; por ello la ESP32 debe ignorar o rechazar el trigger de `Y2` cuando Raspberry no este lista y reportar la causa sin aprobar.

### Comunicacion serial

- Existe una ruta estable: `/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0`.
- Los logs muestran aperturas repetidas del mismo `/dev/ttyUSB0` y un error compatible con desconexion o acceso multiple.
- El nuevo adaptador serial tendra un unico propietario de puerto e hilo; ninguna otra clase abrira o leera el puerto directamente.

## 11. Diagnostico concluyente del touch

El touch ADS7846 esta registrado como `/dev/input/event0`, habilitado en Xorg y con la calibracion evdev aplicada. Sin embargo, durante la prueba interactiva de 15 s:

- no aparecio ningun evento tactil;
- el contador de interrupciones de `ads7846` permanecio en 1 antes y despues;
- Xorg mostraba coordenadas nominales 240,160 y presion 0, no movimiento real.

La falla actual ocurre por debajo de la calibracion de coordenadas. Invertir ejes o recalibrar no puede reparar un dispositivo que no genera interrupciones. Las causas prioritarias son:

1. conexion fisica parcial o floja entre panel/tarjeta/Raspberry;
2. linea IRQ del touch (GPIO 17 segun el overlay) abierta, fija o mal conectada;
3. overlay `tft35a` incompatible con la revision real de la pantalla/tarjeta;
4. falla del controlador o del panel resistivo.

Siguiente prueba de touch, con la maquina apagada y sin cambiar software:

1. fotografiar etiqueta y ambas caras de la tarjeta de pantalla;
2. verificar y reinsertar el flex del panel y la conexion de la tarjeta a los GPIO;
3. revisar pin doblado, separador que impida insercion completa o cable pellizcado;
4. encender y repetir una prueba de eventos/interrupciones;
5. solo si las interrupciones aumentan, recalibrar orientacion y coordenadas.

No reinstalar Raspberry Pi OS ni modificar `99-calibration.conf` antes de esta verificacion.

## 12. Riesgos funcionales que deben probarse

- La logica bimanual es control funcional de proceso, no un modulo de seguridad certificado.
- `Y2/Y3/Y4` simultaneos pueden iniciar vision antes de que la pieza se asiente.
- `X7` no supervisa continuamente la pieza despues de enclavar.
- Un pulso o nivel prolongado de `X5` debe liberar una sola vez y no contaminar el siguiente ciclo.
- La ESP debe conservar el modelo cuando `Y0/Y1` caen a `00` durante `M2`.
- La llave de calidad debe cancelar cualquier resultado pendiente y exigir retorno a estado normal antes del siguiente ciclo.
- Un resultado serial atrasado nunca debe activar la salida fisica de aprobacion.

## 13. Plan inmediato

1. Completar una tabla de cableado pin a pin PLC-ESP32-modulo optoacoplado.
2. Respaldar, si es posible, la flash binaria de la ESP32 antes de grabar firmware nuevo.
3. Corregir primero el motor en una rama `feature/worksurface-v3`: ROI, DataMatrix, resultados por paso, propietario serial unico y estados de error.
4. Implementar simulador de PLC/ESP32 y pruebas de contrato sin actuadores.
5. Crear firmware V3 emparejado con la misma version del protocolo.
6. Probar con relevadores desconectados y despues con aire reducido/condiciones controladas.
7. Reparar el touch desde la capa fisica/IRQ y redisenar la UI para 480 x 320.
8. Medir tiempo de asentamiento, enfoque, captura y cada herramienta antes del piloto de produccion.

## 14. Datos pendientes minimos

- fotografia legible de etiqueta y tarjeta de la pantalla;
- fotografia o tabla de terminales que muestre `Y0` a `Y5`, `X5` a `X7` y los pines de la ESP32;
- confirmacion de niveles activos de las entradas optoacopladas y de la salida de relevador hacia `X5`;
- estado seguro de cada electrovalvula sin energia;
- confirmacion de que los dos sensores de comprobacion se comportan como presencia/ausencia esperada para cada modelo;
- acceso al repositorio Git actual cuando se autorice comenzar la implementacion.

## 15. Criterios de aceptacion

- arranque automatico sin intervencion;
- touch funcional y orientado despues de 20 reinicios;
- temperatura estable bajo carga con margen respecto al throttling;
- cero triggers procesados mientras Raspberry este `NOT_READY`;
- liberacion local por llave aun con Raspberry desconectada;
- recuperacion automatica y visible de ESP32/camara;
- cero resultados atrasados aplicados a otro ciclo;
- cero falsos `PASS` en el conjunto de validacion;
- tiempo ordinario trigger-resultado menor de 10 s y medido por etapa;
- causa de `FAIL`, `ERROR`, `TIMEOUT` y liberacion por calidad visible y registrada;
- actualizacion reversible y burn-in sin congelamientos ni degradacion termica.
