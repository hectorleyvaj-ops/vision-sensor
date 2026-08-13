# Contexto vivo - Motor universal y despliegue Worksurface V12

**Ultima actualizacion:** 2026-08-13

**Responsable funcional:** Andy

**Estado:** fases 1 a 6 publicadas; fase 7 implementada y validada en codigo,
pendiente de aplicacion y prueba visual por Andy

**Sustituye como referencia principal a:**
`CONTEXTO_PROYECTO_WORKSURFACE_V11.md`

## 1. Objetivo vinculante

Crear un unico motor de vision configurable para distintas Raspberry Pi. El
motor contiene UI, camara, enfoque, recetas, pipeline, herramientas, protocolo,
diagnostico y trazabilidad. No contiene modelos A/B/C, sensores, actuadores ni
secuencias codificadas de Worksurface.

Worksurface sera una instalacion externa compuesta por:

- `system.json` propio;
- catalogo de recetas A/B/C;
- imagenes maestras, ROI, codigos y enfoque reales;
- firmware ESP32 separado compatible con `vision_controller_v1`;
- ladder PLC separado;
- paquete de despliegue y rollback.

No existen perfiles `general` o `worksurface` dentro del motor.

## 2. Estado de fases

| Fase | Resultado | Estado |
|---:|---|---|
| 1 | Configuracion, enfoque y multiples steps | Publicada |
| Correccion universal | Retiro de perfiles y protocolo unico | Publicada |
| 3 | Editores, guardado atomico y comisionamiento | Publicada |
| 4 | ROI v3, estados, deadline, cancelacion y DataMatrix | Publicada |
| 5 | Interfaz responsiva por resolucion | Publicada; pulido final pendiente |
| 6 | Diagnostico y trazabilidad de ciclos | Publicada |
| 7 | Catalogo extensible y contratos de herramientas | 59 pruebas; pendiente aplicar/probar |

## 3. Fase 7 - framework de herramientas

### 3.1 Problema eliminado

Antes, una herramienta estaba registrada por separado en `app.py`,
`ui/schemas/schemas.py`, `RecipeManager` y diagnostico. Agregar una nueva
inspeccion obligaba a modificar varias capas y facilitaba divergencias.

### 3.2 Arquitectura nueva

Cada clase concreta de `ToolBase` publica:

- `TOOL_ID` estable;
- `DISPLAY_NAME`;
- `PARAMETER_SCHEMA`;
- defaults;
- reglas de comisionamiento;
- campos de recursos;
- implementacion ejecutable.

`discover_tool_registry()` descubre las clases automaticamente dentro de
`tools/`. `ToolRegistry` es la fuente unica para:

- instancias consumidas por `VisionPipeline`;
- formularios de `ToolEditor`;
- defaults y migracion en `RecipeManager`;
- validacion de comisionamiento;
- comprobacion de recursos en diagnostico.

`app.py` ya no importa ni registra manualmente DataMatrix o histogramas.

### 3.3 Contrato y seguridad

- IDs duplicados, schemas desconocidos o defaults invalidos se rechazan.
- Toda ejecucion devuelve `ToolResult`.
- Las herramientas descubiertas deben responder a cancelacion cooperativa.
- Dependencias pesadas se cargan al ejecutar, no al leer metadatos.
- Un modulo defectuoso no oculta las herramientas validas.
- Una receta comisionada con herramienta ausente o invalida bloquea `READY`.
- Parametros desconocidos se conservan al editar para compatibilidad futura.

### 3.4 Herramientas actuales

| ID | Nombre | Validacion de comisionamiento |
|---|---|---|
| `dmtx` | Lectura DataMatrix | ROI y codigo maestro obligatorios; parametros tipados |
| `img_hist` | Comparacion de histogramas | Al menos una imagen maestra legible |

### 3.5 Validacion

```text
Ran 59 tests
OK
COMPILE_OK
DIFF_CHECK_OK
```

Se conservaron las 53 pruebas previas y se agregaron seis pruebas de catalogo,
schema, recursos, pipeline, cancelacion y comisionamiento.

## 4. Configuracion completa de `system.json`

`system.json` representa una instalacion fisica completa. Se selecciona con
`VISION_SYSTEM_CONFIG`. El panel SISTEMA guarda atomicamente, crea `.bak` y
requiere reiniciar para aplicar cambios de hardware, comunicacion o runtime.

### 4.1 Raiz e instalacion

| Parametro | Funcion |
|---|---|
| `schema_version` | Version del contrato; actualmente 2, no editar manualmente |
| `installation.id` | ID tecnico estable usado en trazabilidad |
| `installation.name` | Nombre legible de la estacion |

### 4.2 Recetas

| Parametro | Funcion |
|---|---|
| `recipes.file` | Ruta del catalogo de recetas v3 |
| `recipes.auto_migrate` | Migra esquemas anteriores y conserva respaldo |

ROI, codigos, imagenes y parametros pertenecen al catalogo, no a
`system.json`.

### 4.3 Camara

| Parametro | Funcion |
|---|---|
| `camera.device` | Indice o ruta persistente del dispositivo |
| `camera.width` / `height` | Resolucion solicitada de captura, no del monitor |
| `camera.capture_fps` | FPS solicitados a la camara |
| `camera.preview_fps` | FPS mostrados; puede ser menor para ahorrar CPU |
| `camera.default_focus_mode` | Modo inicial de recetas nuevas |

La pantalla se detecta automaticamente. En Linux conviene usar una ruta
`/dev/v4l/by-id/...` cuando este disponible.

### 4.4 Controlador

| Parametro | Funcion |
|---|---|
| `controller.transport` | Fijo `serial` |
| `controller.protocol` | Fijo `vision_controller_v1` |
| `controller.ports` | Puerto por Windows/Linux |
| `controller.baudrate` | Debe coincidir con ESP32; base 115200 |
| `controller.timeout` | Espera de operacion serial |
| `controller.reset_on_connect` | Permite pulso DTR si el hardware lo admite |
| `controller.heartbeat_enabled` | Supervisa enlace con PING/PONG |
| `controller.ready_notifications_enabled` | Publica READY/NOT_READY |
| `controller.model_map` | ID externo a nombre exacto de receta |

### 4.5 Ejecucion

| Parametro | Funcion |
|---|---|
| `runtime.require_controller_ready` | Exige controlador disponible |
| `runtime.require_controller_sync` | Exige firmware/protocolo compatible |
| `runtime.require_focus_ready` | Evita inspeccionar desenfocado |
| `runtime.max_frame_age_seconds` | Evita decidir con un frame antiguo |
| `runtime.mechanical_settle_ms` | Espera cancelable para inmovilizar pieza |
| `runtime.inspection_timeout_seconds` | Limite total; timeout comunica ERROR |

Los tres `require_*` deben permanecer activos en produccion.

### 4.6 Trazabilidad

| Parametro | Funcion |
|---|---|
| `traceability.enabled` | Guarda evidencia estructurada por ciclo |
| `traceability.directory` | Ruta escribible de registros |
| `traceability.max_file_size_mb` | Tamano de rotacion |
| `traceability.retention_files` | Cantidad maxima de JSONL |
| `traceability.retention_days` | Antiguedad maxima; 0 desactiva por edad |

Produce `startup_diagnostics.json`, `cycles.jsonl` y rotaciones. No almacena
frames dentro del JSONL.

## 5. Contratos vigentes

### ROI

- `[x1,y1,x2,y2]` sobre el frame original;
- `x2/y2` exclusivos;
- migracion heredada con respaldo.

### Resultados

| Pipeline | Controlador | Significado |
|---|---|---|
| `PASS` | `OK` | Producto aceptado |
| `FAIL` | `NG` | Producto rechazado |
| `ERROR` | `ERROR` | No se obtuvo decision |
| `TIMEOUT` | `ERROR` | Plazo agotado |

### Ciclo

- `cycle_id` unico y opaco;
- handshake, READY/NOT_READY y heartbeat;
- ACK asociado a tipo y ciclo;
- un solo ciclo activo;
- cancelacion cooperativa;
- rechazo de resultados tardios;
- ningun trigger aceptado en NOT_READY.

## 6. Firmware ESP32 y PLC

La actualizacion del firmware corresponde a la **fase 9**, despues de crear las
recetas reales en fase 8. El firmware actual usa el protocolo heredado y no es
compatible con el motor universal.

Cambios obligatorios conocidos para fase 9:

- `HELLO/HELLO_ACK`, READY/NOT_READY y PING/PONG;
- IDs de ciclo y ACK tipados;
- `TRIGGER`, `VISION_RESULT`, `FINAL_RESULT` y `CANCEL` correlacionados;
- soporte de `OK`, `NG` y `ERROR`;
- rechazo de resultados tardios;
- salida GPIO 32 segura en error, timeout, cancelacion y desconexion;
- retorno a IDLE despues de NG;
- timeout alineado con el motor.

El ladder PLC puede conservarse como base. En fases 9-10 se comprobara codigo
Y0/Y1, nivel seguro X5, llave X6 y asentamiento de Y2/Y3/Y4.

## 7. Estado Worksurface conocido

| Modelo | Numero de parte | Sensor izquierdo | Sensor derecho |
|---|---|---|---|
| A | `0402012XA` | OK | NG |
| B | `0402012XB` | NG | OK |
| C | `0402012XC` | OK | OK |

PLC conocido:

- `X0/X1`: botones;
- `X2/X3/X4`: selectores;
- `X5`: liberacion desde ESP32;
- `X6`: llave de calidad;
- `X7`: pieza en posicion;
- `Y0/Y1`: codigo de modelo;
- `Y2`: trigger;
- `Y3/Y4`: clamps;
- `Y5`: tope del modelo 1.

Raspberry Pi 4 de 8 GB, pantalla ILI9486 480x320 y touch ADS7846. El touch no
producia eventos/IRQ en la revision anterior y requiere reparacion fisica antes
del corte final.

## 8. Avance despues de fase 7

Estimacion ponderada de planeacion:

| Area | Peso | Avance | Contribucion |
|---|---:|---:|---:|
| Arquitectura/configuracion | 12 % | 100 % | 12.0 % |
| Recetas, migracion y editores | 13 % | 100 % | 13.0 % |
| Protocolo y seguridad de ciclo | 12 % | 100 % | 12.0 % |
| ROI, resultados, timeout y DataMatrix | 13 % | 100 % | 13.0 % |
| Interfaz responsiva | 8 % | 85 % | 6.8 % |
| Diagnostico y trazabilidad | 8 % | 85 % | 6.8 % |
| Framework de herramientas | 10 % | 100 % | 10.0 % |
| Instalacion/recetas Worksurface | 8 % | 0 % | 0.0 % |
| Firmware, PLC y comisionamiento | 8 % | 0 % | 0.0 % |
| Empaquetado, rollback y corte | 8 % | 0 % | 0.0 % |
| **Sustitucion completa** | **100 %** |  | **73.6 % (~74 %)** |

El motor universal reutilizable esta aproximadamente al **97 %** en codigo.
No significa que Worksurface pueda sustituirse: falta la configuracion real,
firmware, pruebas fisicas, paquete y aceptacion.

## 9. Cinco fases restantes

| Fase | Objetivo | Salida |
|---:|---|---|
| 8 | Instalacion Worksurface | system.json, recetas A/B/C, ROI, codigos, enfoque e imagenes |
| 9 | Firmware ESP32 y revision PLC | `vision_controller_v1` y estados seguros |
| 10 | Comisionamiento fisico | Niveles, tiempos, matriz de fallos y repetibilidad |
| 11 | Paquete instalable | Dependencias, systemd, backup, autoarranque y rollback |
| 12 | Pulido y corte | UI final, prueba paralela, aceptacion y sustitucion reversible |

## 10. Datos pendientes para fase 8-10

- contenido exacto esperado en DataMatrix de A/B/C;
- imagenes buenas y defectuosas representativas;
- ROI, umbrales y enfoque reales;
- niveles HIGH/LOW de sensores;
- pinout Y0/Y1 a GPIO 18/19;
- estado activo/seguro de X5 y GPIO 32;
- tiempo desde clamps hasta inmovilizacion;
- comportamiento medido ante desconexion y reinicio;
- criterios cuantitativos de repetibilidad.

## 11. Proxima fase

Despues de aplicar y probar fase 7, continuar con fase 8. Debe crear una
instalacion Worksurface externa sin introducir A/B/C ni reglas de sensores en
el codigo del motor. Si faltan imagenes/codigos reales, se preparara una
plantilla no comisionada y una guia de captura; no se inventaran valores.
