# Contexto vivo - Motor universal y despliegue Worksurface V9

**Ultima actualizacion:** 2026-08-07  
**Responsable funcional:** Andy  
**Estado:** fases 1, correccion universal y fase 3 publicadas por Andy; fase 4 implementada y validada localmente  
**Sustituye como referencia principal a:** `CONTEXTO_PROYECTO_WORKSURFACE_V8.md`

## 1. Arquitectura vinculante

Existe un unico motor de vision general. No contiene perfiles de producto ni
logica Worksurface. Cada Raspberry selecciona un archivo completo de instalacion
mediante `VISION_SYSTEM_CONFIG` y un catalogo externo de recetas.

Worksurface sera una instalacion externa. Firmware ESP32 y ladder PLC se
desarrollan por separado contra `vision_controller_v1`.

## 2. Estado de fases

- Fase 1: configuracion inicial, enfoque y steps multiples; publicada.
- Correccion universal: perfiles retirados, receta declarativa y protocolo
  unico; publicada.
- Fase 3: editor de sistema/recetas, guardado atomico, validacion y
  comisionamiento; publicada.
- Fase 4: ROI, resultados, timeout, cancelacion y DataMatrix; implementada y
  probada, pendiente de aplicacion por Andy.

## 3. Fase 4 implementada

### ROI y recetas v3

- representacion unica `[x1,y1,x2,y2]` en pixeles del frame original;
- `x2/y2` son limites exclusivos;
- DataMatrix, histograma, enfoque, UI y overlay comparten el contrato;
- migracion v1/v2 a v3 con respaldo `.bak`;
- enfoque y DataMatrix heredados permanecen xyxy;
- `img_hist` heredado se convierte de xywh a xyxy preservando su recorte.

### Resultados

| Estado interno | Significado | Mensaje al controlador |
|---|---|---|
| `PASS` | Inspeccion aceptada | `OK` |
| `FAIL` | Pieza rechazada por una herramienta requerida | `NG` |
| `ERROR` | No hubo decision por falla de ejecucion | `ERROR` |
| `TIMEOUT` | No hubo decision dentro del plazo | `ERROR` |

Los rechazos de trigger por sistema no listo tambien se reportan como `ERROR`,
no como `NG`.

### Cancelacion y timeout

- nuevo `runtime.inspection_timeout_seconds`, base 20 s;
- deadline absoluto propagado al pipeline y herramientas;
- asentamiento mecanico interrumpible mediante evento;
- esperas DataMatrix interrumpibles;
- decoder DataMatrix siempre acotado por `decode_timeout_ms`;
- una cancelacion descarta el resultado local y no lo envia al ciclo cerrado.

### DataMatrix

- votos por intento de captura, no por objetos duplicados del decoder;
- un codigo repetido en un intento cuenta una vez;
- lecturas equivocadas tambien se cuentan por intento;
- comparacion configurable `exact` o `prefix`;
- empates sin codigo esperado no se aceptan;
- no disponer de frames validos es `ERROR`; no confirmar un codigo en frames
  validos es `FAIL`; agotar tiempo es `TIMEOUT`.

## 4. Validacion de fase 4

```text
Ran 42 tests
OK
COMPILE_OK
DIFF_CHECK_OK
```

Las pruebas cubren migracion ROI, respaldo, cuatro estados, mapeo a
OK/NG/ERROR, cancelacion interrumpible, deadline y votos DataMatrix.

## 5. Configuracion de estacion

Los campos de `SISTEMA` describen instalacion, catalogo, camara, enlace con el
controlador, mapeo de modelos y politicas runtime. `camera.width` y
`camera.height` son resolucion de captura; no son resolucion de pantalla.

La deteccion automatica del monitor y la adaptacion completa de controles a
480x320 o a otras resoluciones quedan registradas para una fase posterior.

## 6. Worksurface fuera del motor

| Modelo | Numero de parte | Sensor izquierdo | Sensor derecho |
|---|---|---|---|
| A | `0402012XA` | OK | NG |
| B | `0402012XB` | NG | OK |
| C | `0402012XC` | OK | OK |

Los niveles HIGH/LOW, salida segura X5, imagenes reales, contenido DataMatrix,
asentamiento y tabla pin a pin siguen pendientes. Estos datos no se codifican
en el motor universal.

## 7. Proximos pasos

1. Andy aplica, prueba y publica fase 4.
2. Realizar una prueba visual de fase 3/4 con PySide6 en PC.
3. Definir la siguiente fase del motor: trazabilidad, registro de ciclo y
   validacion de recursos/paths, o abordar primero interfaz responsiva segun la
   prioridad de Andy.
4. Crear despues la instalacion Worksurface desde el molde universal.
5. Crear firmware ESP32 separado compatible con `vision_controller_v1`.
6. Validar con simulador y E/S desconectadas.
7. Medir niveles, asentamiento y estados seguros.
8. Probar hardware controladamente.

## 8. Criterios vigentes

- una aplicacion sin perfiles de producto;
- configuracion y recetas como fuente de verdad;
- guardado validado, atomico y reversible;
- ROI unica y migracion sin reinterpretacion silenciosa;
- rechazo de producto distinguible de error/timeout;
- cancelacion que no publica resultados tardios;
- protocolo unico con identidad de ciclo;
- cero triggers aceptados en `NOT_READY`;
- despliegue reproducible y reversible.
