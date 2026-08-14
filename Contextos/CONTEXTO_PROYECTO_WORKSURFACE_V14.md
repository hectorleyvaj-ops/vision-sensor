# Contexto Worksurface V14 - Fase 9 ESP32 y protocolo

**Fecha:** 2026-08-13

**Base recibida:** `f18c61c Save preliminary worksurface calibration`

**Rama de desarrollo:** `feature/worksurface-controller-phase9`

## 1. Objetivo vigente

El proyecto es un motor de vision universal con una instalacion externa
Worksurface. El motor conserva herramientas, recetas, configuracion,
trazabilidad y comunicación genericas. El firmware ESP32, el ladder PLC y los
datos fisicos pertenecen a la instalacion.

La fase 9 crea un controlador ESP32 compatible con
`vision_controller_v1`, fortalece el enlace Python y deja una ruta de prueba de
banco independiente del comisionamiento de recetas.

## 2. Estado de fases

| Fase | Estado | Evidencia principal |
|---:|---|---|
| 1-7 | Terminadas | Motor, configuracion, UI adaptable, operaciones y herramientas |
| 8 | Implementada | Paquete externo A/B/C y validador |
| 8B | Preliminar | ROI, DataMatrix, histogramas e imagenes capturados; falta aceptacion final |
| 9 | Implementada en codigo | Firmware v1, enlace idempotente y prueba de banco |
| 9 física | Pendiente | Carga ESP32 y matriz electrica/PLC |
| 10 | Pendiente | Pruebas integrales y repetibilidad |
| 11 | Pendiente | Servicio, autoarranque, backup y rollback |
| 12 | Pendiente | UI final, paralelo y corte reversible |

## 3. Calibracion preliminar recibida

El paquete activo es:

```text
installations/worksurface/system.json
installations/worksurface/recipes.json
installations/worksurface/master_images/
```

Las recetas A/B/C contienen ROI y cinco imagenes maestras de histograma por
modelo. Permanecen con:

```json
"commissioned": false
```

Este valor se cambia desde `CONFIGURACION -> RECETA -> Comisionada -> VALIDAR
Y GUARDAR`. No debe editarse manualmente en JSON porque el dialogo ejecuta las
reglas de comisionamiento.

El estado `false` es correcto para fase 9. El programa puede completar el
handshake y publicar `READY=0`; el script de banco prueba el protocolo sin
ejecutar recetas.

Datos que requieren confirmacion antes de fase 10:

- MODELO_B declara DataMatrix esperado `0402010XB` aunque su numero de parte es
  `0402012XB`;
- MODELO_C declara `0402009XB` aunque su numero de parte es `0402012XC`;
- MODELO_B aun no contiene enfoque;
- A y C usan `manual_fixed`, mientras el manifiesto estricto pide enfoque
  `calibrated`;
- el umbral de histograma 80 es preliminar y necesita poblaciones OK/NG.

Los codigos no se corrigen por suposicion: pueden ser contenidos fisicos reales
distintos del numero de parte.

## 4. Firmware fase 9

Archivos:

```text
ESP32/FSM/FSM.ino
ESP32/FSM/worksurface_config.h
```

Implementa:

- STX/ETX a 115200 baud;
- `HELLO/HELLO_ACK` con version de protocolo y firmware;
- `READY=0/1`;
- `PING/PONG` y watchdog de 7 segundos;
- `MODEL`, `TRIGGER`, `VISION_RESULT`, `FINAL_RESULT` y `CANCEL` ligados al
  mismo ID de ciclo;
- ACK tipados;
- reintentos idempotentes;
- resultados separados `OK`, `NG` y `ERROR`;
- reset de ciclo y reinicio explicito;
- timeout de vision seguro;
- retencion del modelo durante el ciclo;
- rechazo de bits de modelo `00` al momento del trigger;
- GPIO 32 seguro en arranque, NG, ERROR, timeout, cancelacion y perdida de
  enlace.
- cancelacion segura si falta el ACK final despues de diez reintentos.

Version declarada:

```text
worksurface-controller-1.0.0
```

## 5. Configuracion fisica inicial

| Funcion | GPIO |
|---|---:|
| Trigger | 5 |
| Modelo bit 0 | 18 |
| Modelo bit 1 | 19 |
| Llave calidad | 4 |
| Sensor izquierdo | 2 |
| Sensor derecho | 15 |
| Pass hacia PLC | 32 |

Se asumen señales activas en HIGH. Deben medirse antes de reconectar GPIO 32 a
la entrada PLC.

Mapeo inicial:

- `10 -> A`;
- `01 -> B`;
- `11 -> C`;
- `00 -> invalido`.

Patrones:

- A: izquierda OK, derecha NG;
- B: izquierda NG, derecha OK;
- C: izquierda OK, derecha OK.

## 6. Cambios del motor Python

Se corrigieron dos casos de reintento:

1. un TRIGGER identico recibe otro ACK sin iniciar ni cancelar otro ciclo;
2. un FINAL_RESULT identico recibe otro ACK sin duplicar indicador ni registro.

Un mensaje contradictorio con el mismo ciclo sigue rechazandose. El watchdog
ahora cancela el contexto local y exige otro handshake, aunque el dispositivo
serial permanezca abierto.

Python tambien acepta `RESET` remoto para que la llave de calidad limpie la UI
aun cuando no exista ciclo activo.

## 7. Pruebas y herramientas

La suite completa contiene 89 pruebas y pasa en la base limpia. Incluye nuevas
pruebas para:

- idempotencia de trigger y resultado;
- rechazo de reintentos contradictorios;
- cancelacion por heartbeat vencido;
- mensajes obligatorios del firmware;
- salida GPIO segura;
- mapeo A/B/C y rechazo de bits 00;
- proteccion del script de banco contra un OK accidental.

El script:

```text
scripts/controller_protocol_smoke.py
```

permite comprobar handshake y PING/PONG sin Qt, camara ni recetas
comisionadas. El modo de ciclo usa `ERROR` por defecto. Enviar `OK` requiere
`--allow-pass-output`.

El sketch paso una comprobacion de sintaxis C++11 con stubs de Arduino. Este
entorno no contiene Arduino CLI ni el core ESP32, por lo que la compilacion
nativa definitiva debe realizarse con Arduino IDE antes de cargarlo.

## 8. PLC

El ladder no cambia en fase 9. Primero se verifica:

- continuidad Y0/Y1 a GPIO18/GPIO19;
- polaridades reales;
- GPIO32 siempre seguro durante reinicios y fallas;
- llave X6 independiente;
- tiempo desde Y2/Y3/Y4 hasta inmovilizacion;
- permanencia de bits A/B/C durante al menos 80 ms.

Solo una medicion que contradiga el contrato justifica modificar el ladder.
El tiempo de asentamiento medido se guarda en
`runtime.mechanical_settle_ms`.

## 9. Siguiente paso

1. Aplicar el parche de fase 9 sobre `f18c61c`.
2. Verificar y cargar `ESP32/FSM/FSM.ino` con Arduino IDE.
3. Mantener GPIO32 desconectado del PLC.
4. Ejecutar handshake y heartbeat con el script de banco.
5. Ejecutar la matriz ERROR/NG, cancelacion, timeout y desconexion.
6. Medir A/B/C, sensores y polaridades.
7. Probar OK unicamente con salida PLC aislada.
8. Registrar resultados para cerrar la verificacion fisica de fase 9.
9. Continuar a fase 10 con recetas autorizadas de manera controlada.

La mejora estetica observada en las capturas sigue pendiente. La legibilidad,
superposiciones y barra inferior se trataran antes de la aceptacion integral;
no forman parte del firmware de esta fase.
