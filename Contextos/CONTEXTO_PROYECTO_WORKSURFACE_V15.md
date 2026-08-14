# Contexto Worksurface V15 - Fase 10 aceptacion integral

**Fecha:** 2026-08-14

**Base:** fase 9 aplicada (`vision_controller_v1`)

**Rama de desarrollo:** `feature/integration-acceptance-phase10`

## 1. Objetivo vigente

El producto debe seguir siendo un motor de vision configurable y reutilizable.
Las recetas, modelos, codigos DataMatrix, ROI, umbrales, enfoque y recursos son
datos de instalacion editables. El motor no debe contener reglas A/B/C ni
valores fisicos de Worksurface.

La fase 10 agrega un marco generico que evalua evidencia real de la instalacion
antes del comisionamiento. No modifica recetas y no autoriza produccion por si
mismo.

## 2. Decision sobre la calibracion preliminar

Los codigos configurados actualmente pueden no coincidir con las piezas
definitivas. Esto no bloquea el desarrollo del codigo base. Al final se ajustan
desde la interfaz:

- codigo y politica DataMatrix;
- ROI de cada herramienta;
- imagenes maestras y umbral de histograma;
- enfoque;
- mapeo de modelos si cambia la instalacion.

Después de cualquier cambio que afecte el resultado se repite la poblacion de
aceptacion correspondiente. `commissioned` se conserva en `false` mientras
exista calibracion preliminar. Su cambio correcto es desde
`CONFIGURACION -> RECETA -> Comisionada -> VALIDAR Y GUARDAR`, no editando JSON
manualmente.

## 3. Estado de fases

| Fase | Estado | Evidencia principal |
|---:|---|---|
| 1-8 | Implementadas | Motor y paquete externo Worksurface |
| 8B | Preliminar | Recetas e imagenes presentes; valores finales pendientes |
| 9 codigo | Implementada | Firmware v1, enlace seguro e idempotencia |
| 9 fisica | Pendiente de evidencia | Carga ESP32, polaridades y matriz electrica |
| 10 codigo | Implementada | Sesiones, importacion JSONL, criterios y CLI |
| 10 fisica | Pendiente | Poblaciones y escenarios de `acceptance.json` |
| 11 | Pendiente | Servicio, autoarranque, backup y rollback |
| 12 | Pendiente | UI final, paralelo y corte reversible |

## 4. Arquitectura fase 10

Archivos principales:

```text
core/acceptance.py
scripts/acceptance_session.py
docs/acceptance_framework.md
installations/worksurface/acceptance.json
Guias/GUIA_FASE10_ACEPTACION_INTEGRAL.md
```

El nucleo carga el plan, obtiene los modelos desde `commissioning.json`, crea
sesiones, registra ciclos y escenarios, importa `cycles.jsonl` y genera un
reporte determinista.

Estados posibles:

- `PENDING`: faltan muestras o escenarios;
- `FAILED`: al menos un criterio fue violado;
- `READY_FOR_COMMISSIONING`: toda la evidencia satisface el plan.

El ultimo estado solo habilita una revision humana. No escribe
`recipes.json`, no cambia `commissioned` y no activa el GPIO PLC.

## 5. Criterios Worksurface iniciales

Por cada modelo A/B/C:

- 10 muestras de referencia OK;
- 10 muestras de referencia NG.

Limites:

- cero falsos OK;
- maximo 5 % de falsos NG;
- cero errores o cancelaciones en la poblacion;
- P95 del ciclo menor o igual a 20 segundos.

La matriz fisica cubre salida segura en arranque, NG, ERROR, timeout,
desconexion y falta de ACK; bloqueo con `READY=0`; bits de modelo invalidos;
llave de calidad; idempotencia; rechazo de resultados contradictorios; y mapeo
fisico A/B/C.

Estos criterios pertenecen a la instalacion y pueden versionarse sin cambiar
el evaluador.

## 6. Flujo operativo

Crear sesion:

```bash
python scripts/acceptance_session.py init \
  --session runtime/acceptance/worksurface.json
```

Importar lotes clasificados externamente:

```bash
python scripts/acceptance_session.py import-trace \
  --session runtime/acceptance/worksurface.json \
  --trace ruta/lote_a_ok.jsonl --model A --expected OK
```

Registrar escenarios y evaluar:

```bash
python scripts/acceptance_session.py record-scenario \
  --session runtime/acceptance/worksurface.json \
  --id usb_disconnect_safe --status PASS --evidence "referencia"

python scripts/acceptance_session.py evaluate \
  --session runtime/acceptance/worksurface.json \
  --json-out runtime/acceptance/worksurface_report.json --details
```

Los archivos bajo `runtime/` son evidencia local y permanecen fuera de Git.
Las escrituras de sesion son atomicas, conservan `.bak` y omiten `cycle_id`
duplicados. Cada sesion guarda una huella SHA-256 del plan, manifiesto,
`system.json`, `recipes.json` y firmware. Un cambio invalida la sesion anterior
y exige evidencia nueva.

## 7. Pruebas automatizadas

La suite completa contiene 103 pruebas. Las 14 nuevas verifican:

- modelos derivados del manifiesto;
- estado pendiente por defecto;
- aprobacion solo con poblacion y escenarios completos;
- fallas por falso OK, tasa de falso NG, error, salida insegura y P95;
- rechazo de sesiones manipuladas;
- importacion, filtrado y deduplicacion de JSONL;
- ciclo completo de la CLI y proteccion contra sobrescritura;
- invalidacion de evidencia cuando cambia la configuracion;
- coherencia del plan real de Worksurface.

La validacion estructural conserva el resultado esperado `LISTA PARA CALIBRAR`
mientras las recetas sean preliminares.

## 8. Firmware reutilizable

Los detalles fisicos se mantienen en:

```text
ESP32/FSM/worksurface_config.h
```

Para otra maquina normalmente se cambian pines, polaridades, combinaciones de
modelo, patrones de sensores y timeouts. El protocolo
`vision_controller_v1`, la maquina de estados segura y el evaluador de
aceptacion no se reescriben salvo que cambie el contrato funcional.

## 9. Siguiente paso

1. Aplicar el parche fase 10 y ejecutar las 103 pruebas.
2. Confirmar `LISTA PARA CALIBRAR` con el validador offline.
3. Completar cuando exista hardware la evidencia fisica pendiente de fases 9 y
   10, sin inventar resultados.
4. Mantener las recetas editables hasta que sus valores finales sean reales.
5. Continuar con fase 11: servicio de arranque, recuperacion, backup y rollback.

La mejora estetica y de distribucion de la interfaz continua reservada para la
fase final, despues de asegurar operacion y recuperacion del sistema.
