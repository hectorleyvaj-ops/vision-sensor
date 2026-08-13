# Contexto vivo - Motor universal y despliegue Worksurface V7

**Ultima actualizacion:** 2026-08-07  
**Responsable funcional:** Andy  
**Estado:** arquitectura corregida; fase 1 publicada por Andy; correccion universal implementada y probada localmente  
**Sustituye como referencia principal a:** `CONTEXTO_PROYECTO_WORKSURFACE_V6.md`

## 1. Decision arquitectonica vinculante

El objetivo principal no es crear una aplicacion Worksurface dentro del motor de
vision. El objetivo es crear un unico software de vision general que pueda
instalarse en distintas Raspberry Pi y configurarse sin modificar el codigo.

El motor debe permitir configurar mediante interfaz y archivos:

- camara, resolucion, FPS y dispositivo;
- enfoque automatico, calibrado, manual fijo o deshabilitado;
- catalogo de modelos/recetas;
- varias herramientas por receta;
- parametros, ROI, obligatoriedad y condiciones por herramienta;
- mapeo entre identificadores externos y recetas;
- tiempos y politicas de ejecucion;
- trazabilidad y estados de resultado.

No habra perfiles internos `general` y `worksurface`. Worksurface sera solamente
una instalacion concreta formada por archivos de configuracion y recetas.

El firmware ESP32 y el programa PLC son productos separados. Se desarrollan
para cada maquina usando el protocolo unico y predefinido por el motor, pero no
se insertan como logica de producto dentro del software de vision.

## 2. Separacion de productos

| Producto | Contenido | No debe contener |
|---|---|---|
| Motor de vision | UI, recetas, pipeline, herramientas, camara, enfoque, protocolo y trazabilidad | Numeros de parte, sensores o actuadores de Worksurface |
| Configuracion de instalacion | Camara, puerto, mapa de modelos, recetas y tiempos | Ramas de codigo o protocolos alternativos |
| Firmware/control | ESP32, E/S fisicas, secuencia de maquina y ladder PLC | Herramientas de vision o reglas internas de UI |

El repositorio actual sigue siendo la base del motor. En una etapa posterior se
decidira si firmware y configuraciones de maquina se alojan en repositorios
separados o en paquetes de despliegue independientes.

## 3. Configuracion universal acordada

Cada instalacion utiliza un archivo completo con estas secciones:

- `installation`;
- `recipes`;
- `camera`;
- `controller`;
- `runtime`.

La ruta se selecciona con `VISION_SYSTEM_CONFIG`. Esa variable elige datos de
una instalacion; no habilita perfiles ni cambia el comportamiento del motor.

El archivo base es `config/system.json`. El catalogo heredado
`core/models/recipes.json` se migra automaticamente al esquema v2 cuando
`recipes.auto_migrate=true`. Antes de reemplazarlo se genera `.bak`.

## 4. Molde universal de receta v2

La raiz contiene `schema_version=2` y una lista `recipes`. Cada receta incluye:

- `id`, `name`, `selected` y `commissioned`;
- configuracion de enfoque;
- lista ordenada de pasos.

Cada paso incluye:

- `id` unico;
- `tool`;
- `enabled`;
- `required`;
- `condition`;
- `params` propios de la herramienta.

Condiciones iniciales soportadas: `always`, `step_success`, `context_equals`,
`all`, `any` y `not`. El motor ya permite repetir una herramienta sin
sobrescribir resultados.

## 5. Protocolo universal del controlador

Nombre: `vision_controller_v1`. No es seleccionable por perfil.

Propiedades conservadas de la fase 2:

- trama STX/ETX;
- `HELLO/HELLO_ACK` con version;
- `READY/NOT_READY`;
- heartbeat `PING/PONG`;
- identificador opaco y unico de ciclo;
- modelo externo retenido antes del trigger;
- ACK tipado por mensaje y ciclo;
- resultado de vision separado del resultado final de maquina;
- cancelacion;
- rechazo de ciclos paralelos y resultados tardios;
- recuperacion despues de desconexion.

El identificador de modelo es arbitrario. El motor no impone A/B/C ni interpreta
sensores. La configuracion lo mapea a una receta. El firmware de cada maquina
implementa el mismo contrato y decide su logica fisica fuera del motor.

## 6. Estado de la correccion sobre la fase 1

La fase 1 ya fue aplicada, probada, confirmada y publicada por Andy. La
correccion debe aplicarse encima de ese commit y:

- elimina `active_profile`, `profiles` y `VISION_PROFILE`;
- elimina `core/models/worksurface_recipes.json`;
- elimina la documentacion que presentaba Worksurface como perfil;
- deja un solo archivo de instalacion;
- agrega migracion de recetas heredadas;
- agrega condiciones de pasos;
- generaliza el protocolo de ciclo;
- no incluye ni modifica firmware ESP32/PLC.

Validacion local de la correccion:

- 19 pruebas unitarias y de contrato aprobadas;
- compilacion sintactica completa aprobada;
- `git diff --check` sin errores.

## 7. Worksurface como futura instalacion

Estos datos se conservan para crear despues sus archivos, no para codificarlos
en el motor:

| Modelo | Numero de parte | Sensor izquierdo | Sensor derecho |
|---|---|---|---|
| A | `0402012XA` | OK | NG |
| B | `0402012XB` | NG | OK |
| C | `0402012XC` | OK | OK |

La traduccion de OK/NG a HIGH/LOW sigue pendiente de medicion. Las reglas de
sensores pertenecen al firmware/control de Worksurface, no a las recetas del
motor de vision salvo que en el futuro se expongan como una herramienta de E/S
generica deliberada.

### PLC confirmado

| Entrada | Funcion |
|---|---|
| `X0`, `X1` | Botones de inicio |
| `X2`, `X3`, `X4` | Selector de modelos 1, 2 y 3 |
| `X5` | Liberacion procedente de ESP32 |
| `X6` | Llave de calidad |
| `X7` | Pieza en posicion |

| Salida | Funcion |
|---|---|
| `Y0`, `Y1` | Codigo de modelo hacia ESP32 |
| `Y2` | Trigger hacia ESP32 |
| `Y3`, `Y4` | Clamps laterales |
| `Y5` | Tope fisico del modelo 1 |

El PLC mantiene autoridad sobre botones, clamps, tope y liberacion local por
llave. La ESP32 lee trigger/modelo/llave/sensores y publica la validacion. La
Raspberry decide solamente la vision.

## 8. Riesgos de maquina que permanecen

- `Y2`, `Y3` y `Y4` se activan simultaneamente; debe medirse el asentamiento.
- `Y0/Y1` desaparecen durante el ciclo; la ESP32 debe retener el modelo antes
  del trigger.
- la llave debe liberar aun con Raspberry desconectada.
- un resultado tardio nunca puede activar `X5` en otro ciclo.
- la salida segura hacia `X5` y niveles activos de sensores deben medirse.
- la logica bimanual actual es control funcional, no seguridad certificada.

## 9. Raspberry y touch

Hallazgos vigentes:

- Raspberry Pi 4 de 8 GB;
- pantalla SPI ILI9486 de 480 x 320;
- touch ADS7846 por SPI/Xorg;
- durante la prueba no hubo eventos ni incremento de IRQ;
- antes de recalibrar debe revisarse conexion fisica, flex, tarjeta y GPIO IRQ;
- la carga y temperatura se relacionan con captura/procesamiento continuo, no
  con falta de RAM;
- la vista previa debe limitarse aproximadamente a 8-12 FPS y la inspeccion usar
  el frame completo por trigger.

## 10. Plan corregido

1. Aplicar la correccion universal encima del commit de fase 1.
2. Integrar en la UI los campos universales que hoy solo estan disponibles en
   JSON: camara, pasos habilitados, condiciones y mapa externo-receta.
3. Corregir bloqueadores generales restantes: ROI unificado, conteo DataMatrix,
   resultados PASS/FAIL/ERROR/TIMEOUT y cancelacion no bloqueante.
4. Crear desde el molde una configuracion Worksurface externa y sus recetas con
   imagenes reales.
5. Crear por separado el firmware ESP32 Worksurface compatible con
   `vision_controller_v1`.
6. Validar firmware con simulador y E/S desconectadas.
7. Medir niveles electricos, asentamiento y estados seguros.
8. Probar hardware de forma controlada y despues desplegar en Raspberry.
9. Reparar touch y adaptar la UI a 480 x 320.

## 11. Datos pendientes para Worksurface

- niveles HIGH/LOW de los dos sensores para A, B y C;
- estado seguro de la salida hacia PLC `X5`;
- imagenes representativas de cada modelo;
- contenido exacto esperado en DataMatrix;
- tiempo medido de asentamiento;
- fotografias o tabla pin a pin de PLC, optoacopladores y ESP32;
- identificacion y revision fisica de la tarjeta de pantalla/touch.

## 12. Criterios de aceptacion del motor

- una sola aplicacion sin perfiles de producto;
- nueva instalacion creada solo con archivos de configuracion y recetas;
- recetas heredadas migradas sin perder valores y con respaldo;
- varias herramientas iguales sin sobrescritura;
- condiciones de paso reproducibles y validadas;
- camara y enfoque configurables;
- protocolo unico documentado y probado sin hardware;
- cero triggers aceptados cuando el motor esta NOT_READY;
- cero resultados tardios aplicados a otro ciclo;
- fallos distinguibles de rechazos de producto;
- despliegue reproducible y reversible.
