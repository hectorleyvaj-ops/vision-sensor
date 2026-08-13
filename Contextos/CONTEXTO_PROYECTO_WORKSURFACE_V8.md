# Contexto vivo - Motor universal y despliegue Worksurface V8

**Ultima actualizacion:** 2026-08-07  
**Responsable funcional:** Andy  
**Estado:** fase 3 implementada y validada; pendiente de aplicacion por Andy  
**Sustituye como referencia principal a:** `CONTEXTO_PROYECTO_WORKSURFACE_V7.md`

## 1. Decision arquitectonica vinculante

Existe un unico motor de vision general. No contiene perfiles de producto o de
maquina. Cada Raspberry selecciona datos de una instalacion mediante
`VISION_SYSTEM_CONFIG` y un catalogo externo de recetas.

Worksurface es una instalacion futura del motor, no una rama de ejecucion, un
perfil o un modulo dentro del codigo. Su firmware ESP32 y su programa PLC son
productos separados que implementaran el contrato fijo del motor.

## 2. Separacion de productos

| Producto | Contenido | Excluye |
|---|---|---|
| Motor universal | UI, configuracion, recetas, pipeline, herramientas, camara, enfoque, protocolo y trazabilidad | Numeros de parte, sensores, actuadores y secuencias Worksurface |
| Instalacion | `system.json`, catalogo de recetas, recursos de herramientas y tiempos | Ramas de codigo y protocolos alternativos |
| Control de maquina | Firmware ESP32, E/S fisicas y ladder PLC | Herramientas de vision y reglas internas de UI |

## 3. Estado de las fases

### Fase 1

Andy aplico, probo, confirmo y publico la preparacion inicial del motor:

- configuracion de camara y enfoque;
- recetas con multiples herramientas;
- IDs de step;
- bloqueo de recetas no comisionadas;
- migracion inicial compatible.

### Correccion universal

Andy aplico y publico la correccion que elimino los perfiles internos y dejo:

- un archivo completo de instalacion;
- recetas universales v2;
- condiciones declarativas;
- protocolo fijo `vision_controller_v1`;
- modelo externo opaco;
- firmware y PLC fuera del motor.

### Fase 3 - Interfaz universal

Implementada y probada localmente sobre una base limpia equivalente a los dos
commits anteriores. Agrega:

- editor por pestanas de instalacion, camara, controlador, runtime y mapa de
  modelos;
- guardado atomico de `system.json` con respaldo `.bak`;
- validacion de tipos, puertos, protocolo y referencias hacia recetas;
- editor de ID, habilitado, requerido y condicion por step;
- editor de ID y comisionamiento de receta;
- validacion antes de comisionar;
- bloqueo `NOT_READY` despues de cambiar configuracion hasta reiniciar;
- rechazo de IDs de receta o step duplicados;
- rechazo de `step_success` hacia si mismo, un paso posterior o uno inexistente.

Validacion de fase 3:

```text
Ran 26 tests
OK
COMPILE_OK
PATCH_CHECK_OK
```

El parche se comprobo con la secuencia:

```text
commit base -> fase 1 -> correccion universal -> fase 3 -> 26 pruebas
```

## 4. Configuracion universal vigente

Cada instalacion contiene:

- `schema_version`;
- `installation`;
- `recipes`;
- `camera`;
- `controller`;
- `runtime`.

`VISION_SYSTEM_CONFIG` selecciona un archivo completo. Cambia datos, no
comportamiento ni protocolo. El motor conserva y valida campos desconocidos
para no eliminar extensiones futuras al guardar desde la interfaz.

El transporte sigue siendo serial y el protocolo no es seleccionable:
`vision_controller_v1`.

## 5. Recetas y steps

La receta v2 contiene:

- `id`, `name`, `selected`, `commissioned`;
- configuracion de enfoque;
- lista ordenada de steps.

Cada step contiene:

- `id` unico;
- `tool`;
- `enabled`;
- `required`;
- `condition`;
- `params` de la herramienta.

La UI separa las politicas del step de los parametros propios de la
herramienta. Las condiciones siguen siendo `always`, `step_success`,
`context_equals`, `all`, `any` y `not`.

Una receta solo puede comisionarse desde la interfaz cuando tiene steps
habilitados, herramientas disponibles y parametros obligatorios completos. El
runtime vuelve a validar antes de cada ciclo; editar el JSON no omite el
bloqueo de produccion.

## 6. Protocolo universal

Propiedades vigentes de `vision_controller_v1`:

- STX/ETX;
- `HELLO/HELLO_ACK` y version;
- `READY/NOT_READY`;
- heartbeat `PING/PONG`;
- ciclo opaco y unico;
- modelo externo arbitrario;
- ACK tipado;
- `VISION_RESULT` separado de `FINAL_RESULT`;
- cancelacion;
- rechazo de ciclos paralelos y resultados tardios;
- recuperacion tras perdida de enlace.

La interfaz solo edita transporte fisico, puerto, baudrate, timeout, politicas
del enlace y mapa identificador-receta. No puede cambiar el protocolo.

## 7. Worksurface como instalacion futura

Datos conservados fuera del motor:

| Modelo | Numero de parte | Sensor izquierdo | Sensor derecho |
|---|---|---|---|
| A | `0402012XA` | OK | NG |
| B | `0402012XB` | NG | OK |
| C | `0402012XC` | OK | OK |

La traduccion de OK/NG a HIGH/LOW sigue pendiente de medicion.

### PLC confirmado

| Entrada | Funcion |
|---|---|
| `X0`, `X1` | Botones de inicio |
| `X2`, `X3`, `X4` | Selectores de modelos 1, 2 y 3 |
| `X5` | Liberacion procedente de ESP32 |
| `X6` | Llave de calidad |
| `X7` | Pieza en posicion |

| Salida | Funcion |
|---|---|
| `Y0`, `Y1` | Codigo de modelo hacia ESP32 |
| `Y2` | Trigger hacia ESP32 |
| `Y3`, `Y4` | Clamps laterales |
| `Y5` | Tope fisico del modelo 1 |

El PLC conserva autoridad sobre botones, clamps, tope y liberacion local por
llave. La ESP32 retiene el modelo, interpreta sensores y aplica la secuencia
fisica. La Raspberry decide solamente la vision.

## 8. Riesgos de maquina pendientes

- `Y2`, `Y3` y `Y4` se activan simultaneamente; falta medir asentamiento.
- `Y0/Y1` desaparecen durante el ciclo; la ESP32 debe retener el modelo.
- la llave debe liberar con Raspberry desconectada;
- un resultado tardio no puede activar `X5` en otro ciclo;
- falta medir el estado seguro de `X5` y niveles activos de sensores;
- la logica bimanual actual no es seguridad certificada.

## 9. Raspberry y touch

- Raspberry Pi 4 de 8 GB;
- pantalla SPI ILI9486 de 480 x 320;
- touch ADS7846 por SPI/Xorg;
- no hubo eventos ni incremento de IRQ durante el diagnostico;
- revisar primero conexion fisica, flex, tarjeta y GPIO IRQ;
- vista previa objetivo: 8 a 12 FPS;
- inspeccion: frame completo bajo trigger.

La fase 3 agrega controles funcionales, pero no declara terminada la adaptacion
tactil de 480 x 320.

## 10. Siguiente fase del motor

Corregir bloqueadores generales antes de crear la instalacion Worksurface:

1. definir una representacion unica de ROI para todas las herramientas;
2. migrar ROI heredadas sin cambiar su region real;
3. modelar resultados como `PASS`, `FAIL`, `ERROR` y `TIMEOUT`;
4. hacer cancelacion y timeouts no bloqueantes;
5. corregir conteo y politica de lecturas DataMatrix;
6. agregar pruebas de contrato de herramientas y cancelacion.

Despues:

1. crear archivos externos de instalacion y recetas Worksurface;
2. incorporar imagenes reales y ROIs;
3. crear firmware ESP32 separado contra `vision_controller_v1`;
4. validar con simulador y E/S desconectadas;
5. medir niveles, asentamiento y estados seguros;
6. probar hardware controladamente;
7. reparar touch y adaptar completamente la UI a 480 x 320.

## 11. Datos pendientes para Worksurface

- niveles HIGH/LOW de ambos sensores para A, B y C;
- estado seguro de la salida PLC `X5`;
- imagenes representativas de cada modelo;
- contenido exacto esperado en DataMatrix;
- tiempo medido de asentamiento;
- tabla pin a pin de PLC, optoacopladores y ESP32;
- revision fisica de pantalla y touch.

## 12. Criterios de aceptacion vigentes

- una aplicacion sin perfiles de producto;
- instalacion creada solo con configuracion y recetas;
- edicion desde UI y JSON sobre la misma fuente de verdad;
- guardado validado, atomico y reversible;
- recetas heredadas migradas con respaldo;
- steps repetidos sin sobrescritura;
- condiciones reproducibles y sin referencias futuras;
- camara y enfoque configurables;
- protocolo unico probado sin hardware;
- cero triggers en `NOT_READY`;
- cero resultados tardios aplicados a otro ciclo;
- fallos distinguibles de rechazos de producto;
- despliegue reproducible y reversible.
