# Guia fase 10 - Aceptacion integral Worksurface

## 1. Que resuelve esta fase

Esta fase convierte pruebas reales en una decision reproducible. Separa tres
cosas que no deben confundirse:

1. la validacion estructural confirma que el paquete puede calibrarse;
2. la aceptacion mide repetibilidad, errores, tiempos y seguridad;
3. el comisionamiento final autoriza una receta ya calibrada desde la interfaz.

No es necesario que los codigos DataMatrix, ROI, enfoque o umbrales
preliminares sean definitivos para instalar el codigo de esta fase. Si un valor
cambia al terminar el software, se edita desde la interfaz y la poblacion
afectada se vuelve a ejecutar.

## 2. Preparacion segura

- Mantener la salida de aprobacion al PLC aislada durante las primeras pruebas.
- Confirmar que el firmware fase 9 responde al handshake y heartbeat.
- Usar piezas o muestras cuya clasificacion real OK/NG sea conocida por un
  metodo independiente.
- No marcar recetas como comisionadas solo para completar la matriz.
- Guardar notas o identificadores de evidencia que permitan repetir cada caso.

Los limites iniciales estan en:

```text
installations/worksurface/acceptance.json
```

Actualmente exige 10 muestras OK y 10 NG por modelo, cero falsos OK, hasta 5 %
de falsos NG, cero errores de ejecucion y P95 menor o igual a 20 segundos. Son
criterios de instalacion versionados, no constantes del motor.

## 3. Crear una sesion

Desde la raiz del proyecto:

```bash
python scripts/acceptance_session.py init \
  --session runtime/acceptance/worksurface.json \
  --operator "Andy" \
  --station "Worksurface"
```

Si el archivo ya existe, el comando lo conserva. `--force` lo reemplaza de
forma explicita; normalmente conviene continuar la sesion existente.

La sesion queda vinculada por huella SHA-256 a `acceptance.json`, manifiesto,
configuracion, recetas y firmware. Si cualquiera cambia, el evaluador solicita
una sesion nueva. No se mezclan mediciones de dos calibraciones diferentes.

## 4. Registrar poblaciones

### Opcion A: importar trazabilidad

Ejecutar un lote cuya referencia completa sea OK y despues importar su archivo
o extracto JSONL:

```bash
python scripts/acceptance_session.py import-trace \
  --session runtime/acceptance/worksurface.json \
  --trace runtime/traceability/lote_a_ok.jsonl \
  --model A --expected OK
```

Repetir para NG y para cada modelo. `--expected` es la verdad de referencia del
lote, no el resultado calculado por vision. No se debe importar como un solo
lote un archivo que mezcle muestras de referencia OK y NG.

Reimportar el mismo archivo es seguro: los `cycle_id` repetidos se omiten.

### Opcion B: registro manual

```bash
python scripts/acceptance_session.py record-trial \
  --session runtime/acceptance/worksurface.json \
  --model A --expected OK --observed OK \
  --duration-ms 842 --cycle-id A-OK-001
```

`--observed` acepta `OK`, `NG`, `ERROR` o `CANCELLED`. Usar
`--output-safe yes|no|unknown` cuando la salida haya sido medida en ese ciclo.

## 5. Ejecutar escenarios fisicos

Consultar los identificadores en `acceptance.json`. Registrar cada resultado,
por ejemplo:

```bash
python scripts/acceptance_session.py record-scenario \
  --session runtime/acceptance/worksurface.json \
  --id usb_disconnect_safe --status PASS \
  --notes "GPIO32 medido en nivel seguro tras desconexion" \
  --evidence "video_prueba_usb_2026-08-14"
```

Los escenarios cubren arranque/reset, `READY=0`, bits de modelo invalidos,
NG/ERROR, timeout de vision, llave de calidad, perdida USB, reintentos,
resultado contradictorio, falta de ACK y mapeos A/B/C.

Un escenario no medido permanece `PENDING`. No debe marcarse `PASS` por
inspeccion de codigo: esta fase solicita evidencia fisica.

## 6. Evaluar

```bash
python scripts/acceptance_session.py evaluate \
  --session runtime/acceptance/worksurface.json \
  --json-out runtime/acceptance/worksurface_report.json \
  --details
echo $?
```

Codigos de salida:

| Codigo | Estado | Accion |
|---:|---|---|
| 0 | `READY_FOR_COMMISSIONING` | Revisar evidencia y calibracion final |
| 2 | `FAILED` o archivo invalido | Corregir causa y comenzar una sesion nueva |
| 3 | `PENDING` | Completar muestras o escenarios faltantes |

## 7. Cierre correcto

Cuando el reporte quede listo:

1. ajustar desde la interfaz los codigos, ROI, umbrales y enfoque definitivos;
2. crear una sesion nueva y volver a ejecutar la aceptacion con esos valores;
3. revisar el reporte y los diagnosticos de arranque;
4. usar `CONFIGURACION -> RECETA -> Comisionada -> VALIDAR Y GUARDAR`;
5. ejecutar `python scripts/validate_installation.py --require-commissioned`;
6. conectar la salida PLC solo con polaridad y estado seguro medidos.

El evaluador nunca activa `commissioned`. Esto preserva la capacidad de editar
recetas durante el desarrollo y evita que una prueba incompleta autorice
produccion accidentalmente.

## 8. Adaptacion a otra maquina

Para reutilizar el software se cambia el paquete de instalacion: manifiesto,
recetas, configuracion y plan de aceptacion. En la ESP32 se ajustan pines,
polaridades, mapeo y timeouts en `ESP32/FSM/worksurface_config.h`. El protocolo,
el motor de vision y el evaluador no deben reescribirse por cada modelo.
