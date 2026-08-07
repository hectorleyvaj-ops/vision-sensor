# Contexto vivo — Worksurface V3

**Última actualización:** 2026-08-06  
**Responsable funcional:** Andy  
**Estado:** diagnóstico inicial y definición de alcance  
**Propósito del archivo:** conservar objetivos, restricciones, decisiones, riesgos, preguntas abiertas y criterios de aceptación del proyecto. No deben guardarse contraseñas, tokens ni otros secretos aquí.

## 1. Objetivo del proyecto

Actualizar el Worksurface instalado en una máquina de producción. El sistema combina una Raspberry Pi 4, una cámara y una ESP32 conectada a un módulo de entradas optoacopladas y salidas por relevador. La nueva versión debe reutilizar y mejorar el motor general de ejecución de herramientas desarrollado en el proyecto `Proyecto_vision_sensor`, sin trasladar el código spaghetti del Worksurface anterior.

El resultado buscado es una plataforma de inspección y ejecución de herramientas que sea:

- rápida y predecible;
- estable ante reinicios, desconexiones y fallas de cámara/serial;
- fácil de operar mediante pantalla táctil;
- configurable mediante recetas y herramientas;
- mantenible y comprobable con pruebas automatizadas;
- desplegable de forma reproducible en Raspberry Pi;
- capaz de integrar visión, entradas físicas y salidas físicas sin mezclar la lógica de negocio con la UI o los drivers.

## 2. Material analizado

### Worksurface heredado

Archivo recibido: `Proyecto_worksurface_crudo.zip`.

Funciones observadas:

- interfaz PyQt5 diseñada para 480 × 320;
- cámara continua con dos ROI;
- lectura de DataMatrix;
- comparación de imagen por histograma;
- evaluación de dos sensores físicos;
- tres modelos A/B/C con códigos y reglas cableadas en Python;
- comunicación serial con ESP32;
- bloqueo de pieza NG y liberación mediante llave de calidad;
- configuración de ROI, umbral y un histograma maestro almacenado en `config.json`.

Limitaciones principales:

- no incluye repositorio Git ni archivo reproducible de dependencias;
- puerto serial `COM7`, modelos, códigos y reglas están cableados en el código;
- la FSM avanza cada 800 ms y puede introducir varios segundos de latencia;
- captura, procesamiento, UI, configuración y protocolo se comunican mediante numerosas banderas compartidas;
- no hay pruebas automatizadas, servicio de arranque ni procedimiento de recuperación;
- el archivo de datos de Raspberry contenía una contraseña en texto plano. Esa credencial no se copió a este contexto y debe reemplazarse.

### Motor de visión actual

Archivo recibido: `Proyecto_vision_sensor.zip`.

Estado Git observado:

- rama: `main`;
- commit: `2166fa8` (`Improve i status function`);
- remoto `origin/main` en el mismo commit;
- etiquetas de producción existentes, entre ellas `v2.1.0-production`;
- el aparente cambio de todos los archivos se debe casi por completo a finales de línea CRLF/LF; ignorando ese ruido, solo `PROJECT_CONTEXT.md` tiene cuatro líneas no confirmadas.

Capacidades relevantes:

- recetas JSON y editor dinámico de herramientas;
- registro y pipeline de herramientas;
- herramientas DataMatrix y comparación por histograma;
- CameraWorker, enfoque manual y verificación de frame reciente;
- FSM separada de la ventana principal;
- protocolo serial enmarcado con STX/ETX, ACK, reintentos y handshake;
- firmware ESP32 incluido;
- interfaz principal de 800 × 480 y configuración a pantalla completa.

## 3. Conclusión de la auditoría inicial

El motor actual es la mejor base. Sin embargo, todavía no está listo para absorber el Worksurface ni para considerarse estable en producción. La estrategia inicial recomendada es continuar en el repositorio existente, crear una rama `feature/worksurface-v3` y convertir el caso Worksurface en un perfil o producto configurable dentro del motor. No se recomienda crear otro repositorio todavía: el núcleo aún no está suficientemente desacoplado para mantenerlo como dependencia independiente sin duplicar trabajo.

Cuando los contratos de herramientas, hardware y recetas estén estabilizados, se podrá reevaluar si conviene extraer el motor como paquete separado.

## 4. Hallazgos técnicos prioritarios

### 4.1 Protocolo Raspberry–ESP32 incompatible

La aplicación envía `PING`, `RPI_READY`, `RPI_NOT_READY`, `CALIBRATING`, `FOCUS_BUSY`, `RESET_FSM` y `ESP_RESTART`, pero el firmware adjunto solo procesa `OK`, `NG`, `SYNC` y `ACK`. El firmware tampoco responde `PONG`.

Consecuencia probable: después del handshake, el watchdog de la aplicación puede declarar perdida la sincronización al pasar seis segundos sin mensajes reconocidos, aunque el enlace físico continúe conectado. Además, la variable `rpiReady` existe en el firmware, pero nunca se actualiza ni se usa para bloquear triggers.

Acción requerida: definir un protocolo versionado único, documentar cada mensaje y generar pruebas de contrato para Python y ESP32.

### 4.2 Riesgo de falso positivo en DataMatrix

Una lectura que coincide exactamente con `expected_code` se agrega una vez como coincidencia base y después se vuelve a agregar en una segunda condición. Con `min_expected_reads = 2`, una sola lectura física puede contabilizarse dos veces y aprobar.

Acción requerida: corregir el conteo y añadir pruebas con lecturas correctas, incorrectas, parciales, repetidas y ausencia de lectura.

### 4.3 Convenciones ROI incompatibles

El editor produce ROI con formato `[x1, y1, x2, y2]`. DataMatrix usa ese formato, pero la herramienta de histograma interpreta los mismos cuatro valores como `[x, y, ancho, alto]`.

Consecuencia: la comparación puede analizar un área diferente de la seleccionada y generar resultados o tiempos de proceso incorrectos.

Acción requerida: usar una sola estructura ROI validada y con nombre explícito en todo el sistema.

### 4.4 El pipeline aún no es un motor general

- Los resultados se guardan usando el nombre de la herramienta como llave; dos pasos de la misma herramienta se sobrescriben.
- La UI de producción bloquea cualquier receta que no tenga exactamente un solo paso DataMatrix.
- Las excepciones de configuración, hardware y ejecución se reducen al mismo `success = False`; no existe separación clara entre `PASS`, `FAIL`, `ERROR`, `SKIPPED` y `TIMEOUT`.
- No hay identificadores únicos de paso, política explícita de reintento, timeout general, dependencias, condiciones ni cancelación.
- La integración física aún vive en la FSM de la ESP32 y no como herramientas reutilizables del motor.

### 4.5 Riesgos de concurrencia y mantenibilidad

- `MainWindow` tiene aproximadamente 958 líneas.
- `CameraWorker` tiene aproximadamente 1352 líneas.
- `SerialComm` tiene aproximadamente 574 líneas.
- Hay llamadas bloqueantes y acceso directo a un objeto serial desde más de un hilo. El candado reduce colisiones, pero no corrige por sí solo la afinidad de hilos de Qt.
- El cierre usa `thread.terminate()` como último recurso, lo cual puede dejar recursos o archivos en un estado inconsistente.

### 4.6 Despliegue no reproducible

- `requirements.txt` no fija versiones.
- Se mantienen PySide6 y artefactos PyQt5 en paralelo.
- Varias rutas son relativas al directorio desde el que se ejecuta el programa.
- El puerto Linux está fijo en `/dev/ttyUSB0`, que puede cambiar después de reiniciar o reconectar.
- No se incluyeron pruebas automáticas; solo existe una utilidad manual de enfoque.
- No hay evidencia en los archivos recibidos de servicio `systemd`, regla `udev`, modo quiosco, watchdog del proceso, rotación de logs o procedimiento de actualización y reversión.

La sintaxis de todos los archivos Python fue validada correctamente, pero eso no comprueba su comportamiento con hardware.

## 5. Arquitectura objetivo provisional

```text
UI táctil
  └─ Application Service / Orquestador
       ├─ Motor de recetas y pasos
       │    ├─ Herramientas de visión
       │    ├─ Herramientas de entradas físicas
       │    ├─ Herramientas de salidas físicas
       │    └─ Condiciones, reintentos y timeouts
       ├─ Estado de producción y resultados
       └─ Puertos abstractos
            ├─ Cámara
            ├─ ESP32 / I/O remoto
            ├─ Persistencia de recetas
            └─ Registro y métricas
```

Estructura tentativa dentro del repositorio:

```text
engine/                 contratos, ejecutor, resultados y validación
tools/vision/           DataMatrix, histograma y futuras herramientas
tools/io/               lectura de entrada, espera de entrada y escritura de salida
adapters/camera/        captura y controles de cámara
adapters/esp32/         transporte serial y protocolo versionado
profiles/worksurface/   recetas, mapeo I/O, textos y reglas de esta máquina
firmware/esp32/         firmware emparejado por versión de protocolo
ui/                     interfaz de operación y configuración
deploy/raspberry/       systemd, udev, arranque, diagnóstico y recuperación
tests/                  unitarias, contrato serial, integración y hardware-in-loop
```

Principio pendiente de confirmar: la Raspberry puede orquestar herramientas de proceso, pero cualquier función de seguridad debe permanecer en hardware o control dedicado apropiado. Los relevadores de esta ESP32 no deben tratarse como sistema de seguridad sin una evaluación formal.

## 6. Estrategia de migración propuesta

### Fase 0 — Congelar y proteger

- rotar la contraseña expuesta y eliminar secretos de archivos versionados;
- añadir `.gitattributes` para normalizar finales de línea;
- crear rama `feature/worksurface-v3` desde un punto estable;
- respaldar la imagen actual de la Raspberry y documentar cableado/pines;
- registrar tiempos reales y comportamiento del sistema heredado como referencia.

### Fase 1 — Estabilizar el motor actual

- corregir protocolo serial, falso conteo DataMatrix y ROI;
- definir `StepResult` con estados y códigos de error;
- permitir varios pasos de la misma herramienta mediante `step_id`;
- desacoplar el pipeline de la restricción de una sola herramienta;
- agregar pruebas unitarias y de contrato antes de cambiar la UI.

### Fase 2 — Generalizar herramientas e I/O

- definir un contrato único de herramientas y esquemas;
- incorporar herramientas `read_input`, `wait_input`, `set_output` y, si aplica, `sensor_rule`;
- decidir qué FSM es autoridad del ciclo: Raspberry, ESP32 o una división explícita;
- versionar recetas y proporcionar migraciones.

### Fase 3 — Perfil Worksurface

- migrar DataMatrix, presencia/ausencia por imagen, sensores y reglas A/B/C;
- reproducir bloqueo NG, liberación por calidad y reset;
- añadir trazabilidad por ciclo: modelo, pasos, tiempos, resultado y causa NG;
- validar con un simulador de ESP32 antes de conectar actuadores.

### Fase 4 — UI táctil

- diseñar primero para la resolución física confirmada;
- separar pantalla de operador y configuración protegida;
- usar objetivos táctiles amplios, estados inequívocos y mensajes accionables;
- evitar refrescos y conversiones de imagen innecesarios;
- mostrar causa de bloqueo, estado de cámara/ESP y resultado de cada paso.

### Fase 5 — Imagen y despliegue Raspberry

- seleccionar Raspberry Pi OS y backend gráfico después del diagnóstico;
- estandarizar PySide6 o la alternativa elegida;
- usar entorno virtual, dependencias fijadas y rutas absolutas;
- instalar reglas `udev` por identidad del dispositivo, no por `/dev/ttyUSB0`;
- configurar servicio `systemd`, reinicio controlado, logs y modo quiosco;
- documentar respaldo, actualización, rollback y restauración del touch.

### Fase 6 — Validación de producción

- pruebas unitarias y de integración en cada cambio;
- pruebas hardware-in-loop con entradas y relevadores aislados;
- pruebas de desconexión de cámara/ESP, pérdida de energía y reinicios repetidos;
- prueba de carga y burn-in prolongado;
- despliegue paralelo o piloto antes de retirar la versión anterior.

## 7. Criterios de aceptación iniciales

Los valores numéricos deben confirmarse con producción.

- arranque automático sin intervención;
- touch correctamente orientado y calibrado después de al menos 20 reinicios;
- recuperación automática de cámara y ESP sin reiniciar manualmente la aplicación;
- cero triggers aceptados cuando el sistema no está listo;
- cero falsos `OK` en el conjunto de validación acordado;
- tiempo trigger–resultado medido y dentro del límite por receta;
- toda causa NG o ERROR identificable en UI y log;
- configuración validada antes de activarse;
- actualización reversible a una versión estable;
- operación continua durante el burn-in acordado sin congelamientos ni crecimiento anormal de memoria.

## 8. Información pendiente

### Hardware

- revisión exacta y RAM de Raspberry Pi 4;
- fuente de alimentación, almacenamiento y refrigeración;
- marca/modelo, interfaz y resolución de pantalla;
- marca/modelo e interfaz del touch;
- marca/modelo, interfaz y resolución de cámara;
- modelo de ESP32, firmware realmente instalado y mapeo completo de entradas/salidas;
- niveles activos, propósito y estado seguro de cada entrada y relevador.

### Proceso

- secuencia completa desde trigger hasta liberación;
- responsable del resultado final y de cada actuador;
- reglas actuales por modelo y cantidad prevista de modelos;
- tiempo máximo permitido por inspección y ritmo de producción;
- comportamiento esperado ante NG, timeout, pérdida de cámara, pérdida de ESP y reinicio.

### Operación y soporte

- significado exacto de “se desconfigura el touch”;
- forma actual de arranque de la aplicación;
- necesidad de conexión a red o funcionamiento totalmente offline;
- usuarios y permisos de configuración;
- política de actualizaciones, respaldo y mantenimiento.

## 9. Diagnóstico Raspberry

Ejecutar en la Raspberry el archivo `recopilar_diagnostico_raspberry.sh` desde una terminal. El script es de solo lectura respecto a la configuración del equipo y genera un archivo `.txt` en la carpeta actual. No recopila contraseñas ni configuración Wi‑Fi.

```bash
chmod +x recopilar_diagnostico_raspberry.sh
./recopilar_diagnostico_raspberry.sh
```

Adjuntar después el `.txt` generado junto con fotografías claras de:

- etiqueta trasera de la pantalla;
- conexiones de pantalla y touch a la Raspberry;
- cámara y su conexión;
- ESP32, módulo de I/O y cableado de terminales;
- fuente de alimentación y adaptadores USB usados.

## 10. Referencias técnicas vigentes para la futura configuración

- Raspberry Pi OS Bookworm y posteriores usan Wayland con labwc de forma predeterminada; Raspberry Pi no recomienda volver a X11 como solución permanente: <https://www.raspberrypi.com/documentation/computers/configuration.html>
- En sistemas actuales, `config.txt` se encuentra en `/boot/firmware/` y KMS se configura mediante overlays vigentes: <https://www.raspberrypi.com/documentation/computers/config_txt.html>
- La orientación de pantallas táctiles oficiales se gestiona desde la configuración de pantallas del escritorio actual: <https://www.raspberrypi.com/documentation/accessories/touch-display-2.html>

Estas referencias no sustituyen la identificación del modelo exacto de pantalla; una pantalla HDMI con touch USB, una DSI oficial y una pantalla SPI requieren configuraciones diferentes.

## 11. Registro de decisiones

| Fecha | Decisión | Estado |
|---|---|---|
| 2026-08-06 | Usar el motor actual como base y no portar directamente el Worksurface heredado. | Provisional, pendiente de confirmación de Andy |
| 2026-08-06 | Continuar inicialmente en el repositorio existente mediante una rama dedicada. | Recomendado |
| 2026-08-06 | No configurar pantalla/touch hasta identificar hardware y obtener diagnóstico. | Activo |
| 2026-08-06 | Tratar el protocolo serial, DataMatrix y ROI como bloqueadores previos a la migración. | Activo |

