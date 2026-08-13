# Contexto vivo - Motor universal y despliegue Worksurface V11

**Ultima actualizacion:** 2026-08-11  
**Responsable funcional:** Andy  
**Estado:** fases 1 a 5 publicadas; fase 6 implementada y validada en codigo,
pendiente de aplicacion y prueba fisica por Andy  
**Sustituye como referencia principal a:**
`CONTEXTO_PROYECTO_WORKSURFACE_V10.md`

## 1. Objetivo vinculante

Crear un unico motor de vision que pueda instalarse en distintas Raspberry Pi
y configurarse externamente. El software permite definir:

- instalacion, camara, captura y enfoque;
- modelos externos y su mapeo a recetas;
- pasos, herramientas, parametros, ROI y condiciones;
- comunicacion con un controlador mediante un protocolo fijo;
- disponibilidad, tiempos, diagnostico y trazabilidad.

El motor no conoce Worksurface, modelos A/B/C, sensores ni actuadores. La
instalacion Worksurface se construira despues mediante archivos externos. El
firmware ESP32 y el ladder PLC son productos separados que deben implementar
`vision_controller_v1`.

## 2. Arquitectura vigente

```text
Motor universal
  +-- system.json de una instalacion
  +-- catalogo externo de recetas v3
  +-- registro de herramientas
  +-- pipeline y FSM
  +-- protocolo vision_controller_v1
  +-- diagnostico y trazabilidad
  +-- interfaz responsiva

Instalacion Worksurface (pendiente)
  +-- system.json propio
  +-- recetas A/B/C como datos externos
  +-- imagenes maestras, ROI y enfoque reales
  +-- firmware ESP32 separado
  +-- ladder PLC separado
```

La instalacion activa se selecciona con `VISION_SYSTEM_CONFIG`. No existen
`profiles`, `active_profile`, `general` ni `worksurface` dentro del motor.

## 3. Estado de fases

| Fase | Resultado | Estado |
|---|---|---|
| 1 | Configuracion inicial, enfoque y multiples steps | Publicada |
| Correccion universal | Retiro de perfiles y protocolo unico | Publicada |
| 3 | Editores, guardado atomico, validacion y comisionamiento | Publicada |
| 4 | ROI v3, estados, deadline, cancelacion y DataMatrix | Publicada |
| 5 | Deteccion de pantalla y layout responsivo | Publicada; pulido visual aplazado |
| 6 | Diagnostico, recursos, trazabilidad, rotacion y retencion | 53 pruebas; pendiente aplicar/probar |

## 4. Fase 6 - operacion y trazabilidad

### 4.1 Diagnostico estatico

Antes de declarar la estacion lista se comprueba:

- configuracion de instalacion valida;
- catalogo de recetas legible y no vacio;
- destinos de `model_map` existentes;
- herramientas registradas;
- definicion y recursos de cada receta;
- imagenes maestras existentes, legibles y no vacias;
- directorio de registros escribible;
- puerto correspondiente a la plataforma configurado;
- parametros solicitados de camara disponibles para comprobacion dinamica.

Una receta incompleta no comisionada genera `WARNING`. Si esta marcada como
`commissioned=true`, el mismo problema genera un `ERROR` que bloquea `READY`.

### 4.2 Diagnostico dinamico

- La camara sustituye su estado pendiente con dispositivo resuelto, resolucion
  y FPS solicitados/reales.
- El controlador informa puerto, baudrate y conexion; tras `HELLO_ACK`, tambien
  firmware y version de protocolo.
- Una desconexion actualiza el reporte y bloquea produccion cuando el
  controlador es obligatorio.
- Los mensajes incluyen una accion concreta para recuperacion.
- Una configuracion base inutilizable muestra un error grafico y termina de
  forma segura; no intenta iniciar workers con datos ambiguos.

El ultimo estado queda en
`runtime/traceability/startup_diagnostics.json`.

### 4.3 Registro de ciclos

Cada ciclo terminado o cancelado agrega una linea JSON a `cycles.jsonl` con:

- instalacion, `cycle_id`, modelo externo y receta;
- inicio/fin UTC y duracion total;
- resultado `OK`, `NG`, `ERROR` o `CANCELLED`;
- estado y causa del pipeline;
- orden, resultado, duracion, errores y datos por step;
- pasos omitidos;
- estado de entrega/ACK al controlador.

Los archivos rotan por tamano y se limitan por cantidad y antiguedad. No se
guardan frames dentro del JSONL. Una falla de escritura nunca se convierte en
un rechazo de producto `NG`.

### 4.4 Validacion

```text
Ran 53 tests
OK
COMPILE_OK
DIFF_CHECK_OK
```

El entorno no permite abrir la UI ni hardware fisico. Camara, serial, permisos,
rotacion bajo carga y tiempos deben validarse en PC/Raspberry.

## 5. Configuracion completa de `system.json`

`system.json` representa una instalacion fisica. El panel `SISTEMA` guarda de
forma atomica, conserva `system.json.bak` y exige reiniciar para aplicar
cambios de hardware, comunicacion, runtime o registros.

### 5.1 Raiz

| Parametro | Funcion | Regla |
|---|---|---|
| `schema_version` | Version del contrato de instalacion | Actualmente `2`; no editar manualmente |

### 5.2 `installation`

| Parametro | Funcion | Regla |
|---|---|---|
| `id` | Identificador tecnico estable | Obligatorio; aparece en trazabilidad |
| `name` | Nombre legible | Describe estacion/proceso sin cambiar logica |

No es un selector de perfiles. Cada JSON completo es una instalacion.

### 5.3 `recipes`

| Parametro | Funcion | Recomendacion |
|---|---|---|
| `file` | Ruta al catalogo de recetas | Relativa a la raiz del paquete cuando sea posible |
| `auto_migrate` | Migra esquemas anteriores y crea `.bak` | `true` durante migracion controlada |

El catalogo contiene modelos, enfoque, steps, condiciones, ROI y parametros.

### 5.4 `camera`

| Parametro | Funcion | Observacion |
|---|---|---|
| `device` | Indice o ruta de la camara | En Linux preferir `/dev/v4l/by-id/...` |
| `width` | Ancho solicitado | Captura, no monitor |
| `height` | Alto solicitado | Captura, no monitor |
| `capture_fps` | FPS solicitados al dispositivo | Afecta USB y CPU |
| `preview_fps` | FPS mostrados en UI | Puede ser menor para reducir carga |
| `default_focus_mode` | Modo inicial de recetas nuevas | `calibrated`, `manual_fixed`, `auto_continuous` o `disabled` |

El diagnostico registra el formato real, que puede diferir de lo solicitado.
La pantalla se detecta automaticamente y no tiene campos en este grupo.

### 5.5 `controller`

| Parametro | Funcion | Regla |
|---|---|---|
| `transport` | Medio de comunicacion | Fijo `serial` |
| `protocol` | Contrato de mensajes | Fijo `vision_controller_v1` |
| `ports` | Puerto por plataforma | `linux`, `windows` o `default` |
| `baudrate` | Velocidad del enlace | Debe coincidir con firmware |
| `timeout` | Espera por operacion serial | No es timeout de inspeccion |
| `reset_on_connect` | Pulso DTR al abrir | Solo si la secuencia de hardware lo admite |
| `heartbeat_enabled` | Supervision de enlace | Recomendado `true` en produccion |
| `ready_notifications_enabled` | Publica `READY/NOT_READY` | Recomendado `true` |
| `model_map` | ID externo a nombre de receta | Cada destino debe existir |

Los IDs externos son arbitrarios. El motor no impone A/B/C.

### 5.6 `runtime`

| Parametro | Funcion | Riesgo controlado |
|---|---|---|
| `require_controller_ready` | Exige controlador disponible | Evita triggers sin enlace |
| `require_controller_sync` | Exige `HELLO_ACK` compatible | Evita firmware incorrecto |
| `require_focus_ready` | Exige enfoque valido | Evita inspeccion borrosa |
| `max_frame_age_seconds` | Edad maxima del frame | Evita decidir con imagen vieja |
| `mechanical_settle_ms` | Espera cancelable tras trigger | Permite inmovilizar pieza/clamps |
| `inspection_timeout_seconds` | Limite total de vision | Produce TIMEOUT/ERROR, nunca NG |

Los tres `require_*` deben permanecer activos en produccion. Desactivarlos solo
es apropiado para una prueba controlada.

### 5.7 `traceability`

| Parametro | Funcion | Regla/recomendacion |
|---|---|---|
| `enabled` | Guarda evidencia por ciclo | `true` en produccion |
| `directory` | Ruta para ciclos y diagnostico | Debe ser escribible por el usuario del servicio |
| `max_file_size_mb` | Tamano antes de rotar | Positivo; base `10.0` |
| `retention_files` | Maximo total de archivos JSONL | Entero positivo; base `10` |
| `retention_days` | Antiguedad maxima de rotaciones | Entero no negativo; `0` desactiva edad |

Con la base se producen `startup_diagnostics.json`, `cycles.jsonl` y rotaciones
`cycles.N.jsonl`. El directorio `runtime/` no entra a Git.

### 5.8 Lo que no pertenece a `system.json`

- resolucion/escala del monitor;
- ROI y parametros de tools;
- patrones electricos o sensores Worksurface;
- direccionamiento PLC;
- secretos o credenciales;
- decisiones de producto codificadas en Python.

## 6. Contratos vigentes

### ROI

- `[x1,y1,x2,y2]` sobre el frame original;
- `x2/y2` exclusivos;
- migracion de formatos heredados con respaldo.

### Resultados

| Pipeline | Significado | Controlador |
|---|---|---|
| `PASS` | Producto aceptado | `OK` |
| `FAIL` | Producto rechazado | `NG` |
| `ERROR` | Falla sin decision | `ERROR` |
| `TIMEOUT` | Plazo agotado | `ERROR` |

### Ciclo

- `cycle_id` unico y opaco;
- ACK asociado a tipo/ciclo;
- `READY/NOT_READY`, heartbeat y handshake;
- cancelacion cooperativa;
- rechazo de resultados tardios;
- trazabilidad de ciclos cancelados, errores y entrega serial;
- ningun trigger aceptado en `NOT_READY`.

## 7. Estimacion de avance despues de fase 6

Es una estimacion ponderada de planeacion, no cobertura de tests ni promesa de
tiempo.

| Area | Peso | Avance del area | Contribucion |
|---|---:|---:|---:|
| Arquitectura universal/configuracion | 12 % | 100 % | 12.0 % |
| Recetas, migracion y editores | 13 % | 100 % | 13.0 % |
| Protocolo y seguridad de ciclo | 12 % | 100 % | 12.0 % |
| ROI, resultados, timeout y DataMatrix | 13 % | 100 % | 13.0 % |
| Interfaz responsiva | 8 % | 85 % | 6.8 % |
| Diagnostico, trazabilidad y recursos | 8 % | 85 % | 6.8 % |
| Framework/catalogo de herramientas | 10 % | 35 % | 3.5 % |
| Instalacion y recetas reales Worksurface | 8 % | 0 % | 0.0 % |
| Firmware, PLC y comisionamiento | 8 % | 0 % | 0.0 % |
| Empaquetado, rollback y corte | 8 % | 0 % | 0.0 % |
| **Sustitucion completa Worksurface** | **100 %** |  | **67.1 % (~67 %)** |

Tomando solo las primeras siete areas reutilizables, el motor universal esta
aproximadamente al **88 %**. Diagnostico y UI alcanzaran 100 % tras pruebas
fisicas y pulido final.

## 8. Cuantas fases faltan

Al iniciar esta entrega faltaban siete fases contando la fase 6. Una vez que
Andy aplique y pruebe esta fase, quedaran **seis fases planeadas**:

| Fase | Alcance | Salida principal |
|---:|---|---|
| 7 | Framework y catalogo extensible de herramientas | Registro/schema desacoplado, tools cancelables y documentadas |
| 8 | Instalacion Worksurface externa | `system.json`, recetas A/B/C, ROI, enfoque e imagenes reales |
| 9 | Firmware ESP32 y ajuste PLC | Implementacion separada de `vision_controller_v1` y estados seguros |
| 10 | Comisionamiento fisico | Niveles, tiempos, matriz OK/NG/ERROR/TIMEOUT y repetibilidad |
| 11 | Paquete instalable y rollback | Release Raspberry, dependencias, `systemd`, backup y restauracion |
| 12 | Pulido visual, aceptacion y corte | UI final, prueba paralela, aprobacion y sustitucion reversible |

El numero puede cambiar si la validacion fisica descubre una incompatibilidad
de camara, touch, ESP32 o PLC que merezca una fase correctiva separada.

## 9. Datos Worksurface conocidos

| Modelo | Numero de parte | Sensor izquierdo | Sensor derecho |
|---|---|---|---|
| A | `0402012XA` | OK | NG |
| B | `0402012XB` | NG | OK |
| C | `0402012XC` | OK | OK |

PLC conocido:

- entradas `X0/X1` botones, `X2/X3/X4` selector, `X5` liberacion ESP,
  `X6` llave, `X7` pieza;
- salidas `Y0/Y1` modelo, `Y2` trigger, `Y3/Y4` clamps, `Y5` tope.

La Raspberry Pi confirmada en V7 es una Pi 4 de 8 GB con pantalla SPI ILI9486
480x320 y touch ADS7846. El touch no entregaba eventos/IRQ durante el
diagnostico anterior y debe revisarse fisicamente antes del corte final.

## 10. Datos que siguen pendientes

- contenido exacto esperado en cada DataMatrix;
- niveles HIGH/LOW de sensores para A/B/C;
- estado seguro de la salida hacia PLC `X5`;
- pinout definitivo PLC/optoacopladores/ESP32;
- tiempo real desde clamps hasta pieza inmovil;
- imagenes buenas/defectuosas representativas;
- ROI, umbrales y enfoque finales;
- comportamiento medido ante desconexion y reinicio;
- permisos/rutas persistentes bajo el usuario de `systemd`;
- criterios cuantitativos de aceptacion y repetibilidad.

Nada de esto debe codificarse dentro del motor universal.

## 11. Proxima fase recomendada

Despues de aplicar fase 6 y revisar sus archivos en PC/Raspberry, continuar con
**fase 7: framework/catalogo extensible de herramientas**. Debe separar el
registro de ejecucion, schema de parametros y editor de UI, eliminar el registro
manual y definir una prueba contractual que toda nueva tool deba aprobar.

El rediseño estetico fino queda reservado para fase 12, como solicito Andy. En
fases intermedias solo deben corregirse bloqueos de uso o legibilidad.
