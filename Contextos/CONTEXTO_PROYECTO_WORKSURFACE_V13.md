# Contexto vivo - Motor universal y despliegue Worksurface V13

**Ultima actualizacion:** 2026-08-13

**Responsable funcional:** Andy

**Estado:** fases 1 a 7 instaladas y verificadas; fase 8 implementada en codigo
y lista para calibracion fisica, aun no autorizada para produccion

**Sustituye como referencia principal a:**
`CONTEXTO_PROYECTO_WORKSURFACE_V12.md`

## 1. Objetivo vinculante

Existe un solo motor de vision universal y reutilizable. El motor contiene UI,
camara, enfoque, recetas, pipeline, herramientas, protocolo, diagnostico y
trazabilidad. No contiene modelos A/B/C, patrones de sensores, actuadores ni
secuencias particulares de Worksurface.

Worksurface es una instalacion externa compuesta por configuracion, recetas,
recursos, firmware ESP32, ladder PLC y datos de comisionamiento propios.

No se reintroducen perfiles `general`/`worksurface` en el motor y no se copia
logica del producto a `core/`, `app/`, `processing/` o `tools/`.

## 2. Estado de fases

| Fase | Resultado | Estado |
|---:|---|---|
| 1 | Configuracion, enfoque y multiples steps | Instalada |
| Correccion universal | Retiro de perfiles y protocolo unico | Instalada |
| 3 | Editores, guardado atomico y comisionamiento | Instalada |
| 4 | ROI v3, estados, deadline, cancelacion y DataMatrix | Instalada |
| 5 | Interfaz responsiva | Instalada; pulido final en fase 12 |
| 6 | Diagnostico y trazabilidad | Instalada |
| 7 | Catalogo extensible y contratos de herramientas | Instalada y verificada |
| 8 | Paquete externo Worksurface A/B/C | Implementado; calibracion fisica pendiente |
| 9 | Firmware ESP32 y revision PLC | Pendiente |
| 10 | Comisionamiento fisico integral | Pendiente |
| 11 | Paquete instalable y rollback | Pendiente |
| 12 | Pulido, aceptacion y corte | Pendiente |

## 3. Resultado de fase 8

### 3.1 Paquete externo

`installations/worksurface/` contiene:

| Archivo/directorio | Funcion |
|---|---|
| `system.json` | Configuracion completa de la estacion |
| `recipes.json` | Catalogo schema v3 con `MODELO_A/B/C` |
| `commissioning.json` | Identidad, reglas de validacion y pendientes fisicos |
| `commissioning_captures/` | Poblaciones OK/NG por modelo |
| `master_images/` | Imagenes maestras aprobadas por modelo |
| `README.md` | Contrato operativo local del paquete |

No se alteraron la configuracion ni la receta predeterminadas del motor.
Worksurface se activa explicitamente con:

```text
VISION_SYSTEM_CONFIG=installations/worksurface/system.json
```

El proceso debe tener como directorio de trabajo la raiz del proyecto, igual
que el contrato de rutas vigente desde fases anteriores.

### 3.2 Mapeo confirmado

| Modelo externo | Receta | Numero de parte | Sensor izquierdo | Sensor derecho |
|---|---|---|---|---|
| A | `MODELO_A` | `0402012XA` | OK | NG |
| B | `MODELO_B` | `0402012XB` | NG | OK |
| C | `MODELO_C` | `0402012XC` | OK | OK |

`controller.model_map` solo traduce el ID opaco A/B/C al nombre de receta. Los
patrones de sensores permanecen como metadatos externos para firmware/PLC; el
pipeline de vision no los evalua.

### 3.3 Plantillas de receta

Cada receta declara dos pasos requeridos:

1. `dmtx_1`: DataMatrix, pendiente de ROI y contenido exacto;
2. `img_hist_1`: comparacion visual, pendiente de ROI, umbral e imagenes.

Cada receta tambien contiene el bloque completo de enfoque calibrado, aun sin
valores. Todos los campos desconocidos son `null`, cadena/lista vacia o cero de
plantilla. No se reutilizo el codigo, ROI o enfoque historico de otra pieza.

Si el estudio fisico concluye que la comparacion por histograma no corresponde
a Worksurface, el step y la politica externa deben actualizarse mediante una
decision documentada. Un umbral cero no es criterio de aceptacion.

### 3.4 Bloqueo de seguridad

Las tres recetas usan `commissioned: false`. Esta condicion es intencional:

- permite instalar y editar el paquete;
- impide ejecutar una receta incompleta;
- hace visibles los pendientes en diagnostico;
- evita presentar una plantilla como configuracion productiva.

El valor `mechanical_settle_ms` sigue en `0` como pendiente de medicion, no como
confirmacion de que no se requiere asentamiento.

### 3.5 Compatibilidad Raspberry Pi OS de 32 bits

El backend grafico ya no queda fijado indirectamente a PySide6. La seleccion
centralizada acepta `VISION_QT_API=auto|pyside6|pyqt5`; en modo automatico
prefiere PySide6 y usa PyQt5 como alternativa. Tanto la ventana principal como
la de configuracion seleccionan su clase UI de acuerdo con el backend real.

Para `armhf/armv7l` se agrego `requirements-rpi32.txt`. PyQt5, OpenCV y NumPy
se instalan mediante APT y el entorno se crea con `--system-site-packages`.
La guia detallada esta en `docs/raspberry_pi_32bit_runtime.md`.

## 4. Validador offline

`scripts/validate_installation.py` valida el paquete sin abrir camara ni serial
y sin modificar recetas.

Modo estructural:

```bash
python scripts/validate_installation.py
```

Estado inicial esperado: `LISTA PARA CALIBRAR`, codigo `0`, sin errores y con
pendientes explicitamente enumerados.

Modo estricto:

```bash
python scripts/validate_installation.py --require-commissioned
```

Codigos:

| Codigo | Significado |
|---:|---|
| 0 | Paquete estructural valido; con `--require-commissioned`, listo para produccion |
| 2 | Configuracion, catalogo, mapeo o recurso invalido |
| 3 | Estructura valida, pero calibracion/comisionamiento pendiente |

El manifiesto permite que la validacion siga siendo generica y dirigida por
datos externos. Comprueba:

- schema de sistema y recetas;
- un solo modelo seleccionado;
- nombres e IDs de receta unicos;
- mapeo externo exacto;
- numeros de parte;
- herramientas requeridas y sus contratos;
- recursos existentes y no vacios;
- umbral de histograma mayor que cero;
- enfoque calibrado completo;
- estado de comisionamiento coherente.

Una receta marcada `commissioned: true` con datos incompletos pasa a ser un
error, no una advertencia.

## 5. Validacion automatizada

Resultado despues de fase 8 y la compatibilidad Raspberry Pi de 32 bits:

```text
Ran 67 tests
OK
```

Se conservaron las 59 pruebas de fase 7. Las cuatro pruebas originales de fase
8 cubren:

- paquete valido pero deliberadamente no comisionado;
- mapeo y numeros de parte A/B/C;
- rechazo de mapeo incorrecto;
- rechazo estricto de calibracion pendiente.

Otras cuatro pruebas cubren seleccion forzada/automatica de Qt, paridad de los
controles UI y la separacion de dependencias binarias en Raspberry Pi 32 bits.

Tambien se verificara `compileall`, validez JSON y aplicacion aislada del parche
antes de publicar la entrega.

## 6. Datos aun pendientes de fase 8

Se deben medir en el hardware final, por modelo:

- contenido exacto del DataMatrix y politica `exact`/`prefix`;
- ROI DataMatrix `[x1,y1,x2,y2]` sobre 1920x1080;
- caracteristica visual, ROI y umbral de histograma;
- poblaciones OK/NG e imagenes maestras aprobadas;
- ROI, posicion y scores de enfoque;
- tiempo real de asentamiento mecanico;
- ruta persistente de camara;
- puerto serial definitivo en Raspberry Pi.

No se debe marcar una receta comisionada hasta que el validador estricto pase y
la evidencia fisica del modelo haya sido revisada.

## 7. Firmware ESP32 y PLC

La actualizacion del firmware permanece en la **fase 9**. La fase 8 no modifica
`ESP32/FSM/FSM.ino` ni el ladder PLC.

El firmware actual usa el protocolo heredado y no es compatible con el motor
universal. Cambios obligatorios ya identificados:

- `HELLO/HELLO_ACK`, READY/NOT_READY y PING/PONG;
- IDs de ciclo y ACK tipados;
- `TRIGGER`, `VISION_RESULT`, `FINAL_RESULT` y `CANCEL` correlacionados;
- soporte separado de `OK`, `NG` y `ERROR`;
- rechazo de resultados tardios;
- salida GPIO 32 segura ante error, timeout, cancelacion y desconexion;
- retorno a IDLE despues de NG;
- timeout alineado con vision.

El PLC puede conservarse como base, sujeto a verificar Y0/Y1, X5, X6,
Y2/Y3/Y4, polaridades y tiempos. Durante fase 8 no se autoriza liberar PLC ni
aceptar triggers automaticos con el firmware antiguo.

## 8. Fases restantes

| Fase | Objetivo | Criterio principal |
|---:|---|---|
| 8B | Completar calibracion Worksurface | Validador estricto en codigo 0 |
| 9 | Firmware ESP32 y revision PLC | Protocolo v1 y estados seguros |
| 10 | Pruebas fisicas integrales | Matriz de fallas y repetibilidad |
| 11 | Despliegue | Servicio, backup, autoarranque y rollback |
| 12 | Corte | UI final, paralelo, aceptacion y sustitucion reversible |

La fase 9 puede desarrollarse en paralelo documentalmente, pero Worksurface no
queda autorizada para produccion hasta cerrar 8B, 9 y 10.

## 9. Proximo paso

1. Aplicar el parche de fase 8 sobre fase 7 confirmada.
2. Ejecutar las 67 pruebas y el validador estructural.
3. Capturar y medir A/B/C siguiendo
   `GUIA_FASE8_INSTALACION_WORKSURFACE.md`.
4. Ejecutar el validador estricto hasta codigo 0.
5. Continuar con fase 9 para firmware ESP32 y revision PLC.
