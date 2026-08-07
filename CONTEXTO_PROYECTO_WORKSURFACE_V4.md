# Contexto vivo - Worksurface V4

**Ultima actualizacion:** 2026-08-06  
**Responsable funcional:** Andy  
**Estado:** auditoria de hardware y arquitectura; pendiente de confirmar cableado y firmware instalado  
**Proposito:** conservar objetivos, hechos comprobados, decisiones, riesgos, preguntas abiertas y criterios de aceptacion. No guardar contrasenas, tokens ni secretos.

## 1. Objetivo

Actualizar la estacion Worksurface para convertirla en un sistema de inspeccion industrial rapido, mantenible y recuperable. La solucion debe reutilizar el motor general del repositorio `Proyecto_vision_sensor`, incorporar el ciclo fisico de la maquina y sustituir el codigo heredado de Worksurface sin copiar su acoplamiento entre interfaz, vision, comunicacion y actuadores.

El ciclo deseado es:

1. La Raspberry y la aplicacion arrancan automaticamente.
2. El operador selecciona uno de tres modelos; la cuarta posicion es inactiva.
3. Coloca la pieza y acciona dos botones dentro de la ventana permitida.
4. En el primer ciclo del modelo o del arranque se verifica el enfoque guardado y, si es necesario, se realiza enfoque automatico con congelamiento posterior.
5. Se ejecutan las herramientas configuradas de la receta y se combinan los resultados de vision y sensores.
6. En `OK`, la interfaz indica aprobacion y los clamps liberan la pieza.
7. En `NG`, la interfaz muestra rechazo y los clamps permanecen activados.
8. La llave de calidad libera la pieza rechazada y restablece el ciclo.

El tiempo total objetivo por pieza es menor de 10 s y debe reducirse tanto como sea posible sin comprometer la confiabilidad.

## 2. Material revisado

- `Proyecto_worksurface_crudo.zip`: aplicacion heredada PyQt5 y protocolo serial de texto por lineas.
- `Proyecto_vision_sensor.zip`: motor moderno con recetas, herramientas, enfoque manual/automatico, PySide6/PyQt5 y protocolo serial STX/ETX.
- `diagnostico_raspberry_worksurface_20260806_122215.txt`: inventario real de Raspberry, pantalla, touch, camara, serial, sistema operativo y procesos.
- `PLC_WORKSURFACE.pdf`: parametros, ladder, comentarios y lista de dispositivos del PLC.
- `ESP_WORKSURFACE.txt`: firmware heredado proporcionado para la ESP32.
- Fotografias del gabinete, pantalla, neumática, PLC, ESP32, modulo de E/S, camara y superficie de inspeccion.

## 3. Hardware y software comprobados

### Raspberry Pi

- Raspberry Pi 4 Model B Rev. 1.5.
- 8 GB de RAM; no es una version de 2 GB.
- microSD de aproximadamente 64 GB, con 57 GB utiles y 15 % ocupado.
- Raspbian GNU/Linux 13 `trixie`.
- Kernel de 64 bits (`aarch64`), pero arquitectura de paquetes `armhf` de 32 bits. Esta mezcla funciona, pero complica dependencias y despliegue.
- Python 3.13.5.
- Aplicacion observada: `/home/worksurface/Proyecto_vision_sensor/venv/bin/python main.py`.
- Servicio de arranque: `vision.service`, habilitado.
- Durante el diagnostico, Python consumia aproximadamente 125 % de CPU y la temperatura era 79.8 C.
- No se reporto undervoltage ni throttling historico (`throttled=0x0`) en esa captura.

### Pantalla y touch

- La sesion activa usa Xorg y Openbox, no Wayland.
- Resolucion real del escritorio: 480 x 320.
- Pantalla SPI con framebuffer `fb_ili9486`, overlay `tft35a:rotate=270`, 16 MHz y aproximadamente 31 fps maximos reportados por el driver.
- Touch resistivo SPI `ADS7846`, detectado como `/dev/input/event0` y visible en libinput/xinput.
- Existe `/etc/X11/xorg.conf.d/99-calibration.conf` con `Option "Calibration" "3936 227 268 3880"`.
- Libinput informa matriz de calibracion identidad. Falta confirmar en el log de Xorg si se usa `libinput` o `evdev` y si la opcion anterior esta siendo ignorada.
- El kernel detecta el controlador del touch; por tanto, la falla actual no demuestra todavia un dano fisico. Deben capturarse eventos crudos mientras se toca la pantalla.

La afirmacion de que la pantalla es de 5 pulgadas debe confirmarse con la etiqueta o modelo. El overlay `tft35a` suele asociarse con pantallas SPI de otra familia/tamano y no debe usarse como prueba del tamano fisico.

### Camara

- Una camara USB `Arducam_8mp`, identificada tambien por USB como `Microdia Webcam Vitade AF` (`0c45:6366`).
- Dispositivo de captura principal: `/dev/video0`; `/dev/video1` es metadatos.
- Numero de serie reportado: `SN0001`.
- Autofoco continuo y enfoque absoluto de 1 a 1023 disponibles.
- En el momento del diagnostico estaba en 1280 x 720, YUYV, 10 fps y enfoque absoluto 500, con autofoco continuo desactivado.

### Comunicacion ESP32

- Adaptador CP2102 USB-UART (`10c4:ea60`).
- Puerto dinamico: `/dev/ttyUSB0`.
- Ruta estable disponible: `/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0`.
- El usuario `worksurface` pertenece al grupo `dialout`.
- La aplicacion no debe depender de `/dev/ttyUSB0`; debe usar la ruta `by-id` o una regla udev dedicada.

### PLC y neumática

El ladder usa:

| Direccion | Comentario | Funcion observada |
|---|---|---|
| X000 | `START_BTN_L` | Boton izquierdo |
| X001 | `START_BTN_R` | Boton derecho |
| X002 | `VALIDACION` | Finaliza el enclavamiento; probablemente resultado final externo |
| X003 | `LLAVE_DESENCLAVE` | Libera el enclavamiento de manera local |
| X004 | `SELECT_1` | Posicion/modelo 1 |
| X005 | `SELECT_2` | Posicion/modelo 2 |
| X006 | `SELECT_3` | Posicion/modelo 3 |
| Y000 | `CLAMP` | Salida asociada al primer clamp |
| Y001 | sin comentario en la lista | Salida paralela a Y000; probablemente segundo clamp |
| Y002 | `OUT_M1` | Bit/salida de modelo 1 |
| Y003 | `OUT_M2` | Bit/salida de modelo 2 |

El PLC enclava por software cada boton en M0/M1 y usa temporizadores T1/T2 con K5. El inicio M2 solo se activa si ambos botones llegan antes de que expiren los temporizadores. M2 energiza Y000/Y001. X002 o X003 energizan M3 y rompen el enclavamiento. Las tres posiciones de selector generan Y002/Y003 como 10, 01 y 11.

La llave de calidad puede liberar los clamps por logica local del PLC aunque Raspberry o ESP32 fallen. Esta independencia debe conservarse.

El PLC mostrado es un controlador convencional; esta logica no debe describirse como control bimanual de seguridad certificado. Es control funcional de proceso, sujeto a evaluacion de riesgos de la maquina.

## 4. Hallazgos de rendimiento

La lentitud no se explica por falta de RAM. Los principales sospechosos comprobables son:

1. La Raspberry estaba cerca del limite termico, a 79.8 C. Debe mejorarse la refrigeracion y medirse bajo carga prolongada.
2. `CameraWorker` solicita 1920 x 1080 a 30 fps y ejecuta un bucle de captura con pausa de 1 ms.
3. Cada frame se copia y se emite a dos consumidores.
4. `VideoWidget` usa otro temporizador de 30 ms, copia el frame, convierte BGR a RGB, redimensiona y crea pixmaps aun cuando la pantalla solo tiene 480 x 320.
5. La camara observada estaba entregando 1280 x 720 YUYV a 10 fps, por lo que la configuracion solicitada y la real pueden no coincidir.
6. El framebuffer SPI reporta alrededor de 31 fps maximos; intentar actualizar a 30 fps con conversiones de alta resolucion consume CPU sin beneficio operativo equivalente.

Accion propuesta: desacoplar FPS de captura, inspeccion y UI; capturar con formato/resolucion compatibles; conservar un frame reciente sin copias redundantes; mostrar entre 8 y 12 fps en la UI; ejecutar herramientas solo por trigger; medir tiempos por etapa.

## 5. Firmware y protocolo

### Firmware heredado `ESP_WORKSURFACE.txt`

- Protocolo de texto terminado en salto de linea.
- Responde `READY` a `PING`.
- Envia `TRIGGER`, modelo `0/1/2`, resultados de sensores y `RELEASE`.
- Recibe `OK`, `NG` y `RESET`.
- Controla directamente dos salidas denominadas `CLAMP_LEFT` y `CLAMP_RIGHT`.
- Lee dos botones, llave, tres lineas de selector y dos sensores.
- No implementa un watchdog de Raspberry ni un estado seguro por perdida de comunicacion.
- Hace eco de cada mensaje recibido, lo que puede confundirse con una respuesta valida.
- Usa `String`, `readStringUntil` y una cola de diez mensajes; puede bloquear, acumular o perder eventos.
- La llave solo envia `RELEASE`; no cambia por si sola las salidas de clamps. La liberacion depende de que Raspberry conteste `RESET`, salvo que el PLC actue por una ruta fisica independiente.

Este firmware coincide con el protocolo del Worksurface heredado, pero no con el protocolo STX/ETX del motor moderno.

### Firmware incluido en el motor moderno

- Usa STX/ETX, `SYNC`, `ACK`, reintentos y mensajes de resultado.
- Lee un trigger, dos bits de modelo, llave, dos sensores y entrega una salida final.
- Su mapa funcional se parece mas al ladder del PLC.
- Sin embargo, no procesa todos los mensajes que actualmente envia Python (`PING`, `RPI_READY`, `RPI_NOT_READY`, `CALIBRATING`, `FOCUS_BUSY`, `RESET_FSM`, entre otros) y no responde `PONG`.
- La variable `rpiReady` existe pero no gobierna los triggers.

Conclusion: ninguno de los dos contratos debe adoptarse sin cambios. Debe definirse un protocolo V3 unico, versionado y probado en Python y ESP32.

## 6. Arquitectura de control recomendada

### Responsabilidades

**PLC**

- botones y ventana bimanual funcional;
- enclavamiento fisico del ciclo;
- accionamiento de clamps y tope;
- liberacion directa por llave de calidad;
- estado seguro de salidas ante reinicio o perdida de senal;
- codificacion o lectura del selector.

**ESP32**

- E/S remota determinista entre PLC/sensores y Raspberry;
- antirrebote y captura de eventos;
- protocolo serial versionado;
- heartbeat y deteccion de perdida de Raspberry;
- rechazo de triggers cuando Raspberry no esta `READY`;
- nunca aprobar por timeout, desconexion o mensaje incompleto.

**Raspberry Pi**

- interfaz tactil;
- recetas y configuracion;
- enfoque y camara;
- ejecucion de herramientas de vision;
- combinacion de resultados segun contrato acordado;
- trazabilidad, tiempos, diagnosticos y alarmas;
- supervision de conexion con ESP32 y recuperacion automatica.

### Regla de autoridad

No se recomienda que Raspberry y ESP32 tengan simultaneamente control total sin arbitraje. Dos autoridades sobre una misma salida producen condiciones de carrera y estados imposibles de diagnosticar.

La division propuesta es:

- el PLC tiene autoridad final sobre actuadores fisicos;
- la ESP32 transmite estados y solicita/entrega validaciones;
- la Raspberry tiene autoridad sobre la decision de vision y la secuencia de receta;
- toda perdida de comunicacion se convierte en `NOT_READY/ERROR`, nunca en `OK`;
- la llave libera por la ruta local del PLC y ademas notifica a ESP/Raspberry para sincronizar sus estados.

## 7. Estados de ciclo propuestos

1. `BOOT`: salidas seguras, sin trigger aceptado.
2. `CONNECTING`: camara, ESP y receta en inicializacion.
3. `NOT_READY`: se muestra causa; PLC no debe iniciar inspeccion.
4. `READY`: modelo valido, foco aplicable, camara y enlace disponibles.
5. `CLAMPED`: pieza sujeta y trigger confirmado.
6. `FOCUS_CHECK`: solo en primer trigger o cuando la calidad de foco cae.
7. `INSPECTING`: herramientas y sensores dentro del timeout global.
8. `PASS`: se registra resultado y se solicita validacion/liberacion.
9. `FAIL_LOCKED`: pieza bloqueada y causa visible.
10. `QUALITY_RELEASE`: la llave libera fisicamente y sincroniza todos los controladores.
11. `FAULT`: camara, serial, configuracion o hardware fallaron; no permite aprobar.

## 8. Correcciones bloqueantes del motor

Antes de migrar Worksurface:

- corregir el doble conteo de DataMatrix;
- unificar ROI como estructura explicita, no una lista ambigua;
- permitir multiples instancias de la misma herramienta con `step_id`;
- eliminar la restriccion de una sola herramienta DataMatrix;
- separar `PASS`, `FAIL`, `ERROR`, `TIMEOUT`, `SKIPPED` y `CANCELLED`;
- mover todo acceso serial a un unico propietario de hilo;
- evitar `thread.terminate()` como mecanismo normal de cierre;
- fijar dependencias y usar una arquitectura de paquetes coherente;
- reducir copias y conversiones de video;
- usar el puerto serial estable por identidad;
- agregar pruebas unitarias, de contrato y simulador ESP32.

## 9. Despliegue Raspberry

No reinstalar ni cambiar drivers de pantalla hasta terminar la prueba de eventos del touch y respaldar la microSD.

La instalacion final debe incluir:

- sistema operativo y arquitectura de paquetes elegidos de forma coherente;
- entorno virtual reproducible;
- `vision.service` con directorio absoluto, usuario no root, reinicio controlado y dependencia de sesion grafica/hardware bien definida;
- regla udev o ruta `by-id` para ESP32 y camara;
- logs estructurados con rotacion;
- watchdog de proceso y heartbeat de protocolo;
- modo operador a pantalla completa;
- procedimiento de actualizacion, rollback y restauracion;
- respaldo versionado de configuracion de touch/pantalla.

## 10. Preguntas bloqueantes

1. Confirmar cual firmware esta realmente cargado en la ESP32: el contenido de `ESP_WORKSURFACE.txt`, `ESP32/FSM/FSM.ino` del motor moderno u otro.
2. Confirmar si el diagnostico se ejecuto mientras estaba corriendo la aplicacion de produccion antigua o una prueba del motor moderno.
3. Trazar el destino real de PLC Y000, Y001, Y002 y Y003.
4. Trazar el origen real de PLC X002 `VALIDACION`.
5. Identificar que salida energiza la tercera electrovalvula del tope y en que modelos debe estar activa.
6. Confirmar si la llave X003 tambien llega a una entrada de ESP32 o solo al PLC.
7. Confirmar niveles activos y estado seguro de las tres electrovalvulas al cortar energia.
8. Obtener fotografia legible de la etiqueta/modelo de la pantalla y, si existe, de su tarjeta controladora.

## 11. Pruebas de aceptacion iniciales

- arranque automatico sin intervencion;
- touch funcional y orientado despues de 20 reinicios consecutivos;
- temperatura estable bajo carga con margen respecto al throttling;
- cero triggers aceptados en `NOT_READY`, `FAULT` o durante enfoque;
- liberacion local por llave aun con Raspberry desconectada;
- desconexion de ESP/camara produce error visible y recuperacion controlada;
- cero falsos `OK` en el conjunto de validacion;
- tiempo trigger-resultado menor de 10 s por receta y medido por etapa;
- causa de cada `NG`, `ERROR` o `TIMEOUT` visible y registrada;
- actualizacion reversible a una version estable;
- burn-in continuo sin congelamiento, fuga de memoria ni degradacion termica.

## 12. Siguiente paso

Ejecutar `diagnostico_worksurface_fase2.sh` en la Raspberry sin detener la aplicacion. Durante la prueba de 15 segundos, tocar repetidamente las cuatro esquinas y el centro. Adjuntar el TXT generado y responder las preguntas bloqueantes sobre cableado/firmware. Con esos datos se podra cerrar el diagrama electrico funcional y comenzar la rama `feature/worksurface-v3` con pruebas de contrato antes de tocar actuadores.

