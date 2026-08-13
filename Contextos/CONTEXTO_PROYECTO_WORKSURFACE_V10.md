# Contexto vivo - Motor universal y despliegue Worksurface V10

**Ultima actualizacion:** 2026-08-11  
**Responsable funcional:** Andy  
**Estado:** fases 1 a 4 publicadas por Andy; fase 5 implementada, validada en
codigo y pendiente de prueba visual/aplicacion por Andy  
**Sustituye como referencia principal a:**
`CONTEXTO_PROYECTO_WORKSURFACE_V9.md`

## 1. Objetivo vinculante

Crear un unico software de vision general que pueda instalarse en distintas
Raspberry Pi. La aplicacion debe permitir configurar externamente:

- instalacion y hardware;
- camara, captura y enfoque;
- modelos y mapeos externos;
- recetas, herramientas, parametros y condiciones;
- comunicacion con un controlador mediante un protocolo fijo;
- politicas de disponibilidad, ejecucion y seguridad.

El motor no conoce Worksurface, modelos A/B/C ni combinaciones de sensores.
Worksurface sera una instalacion externa construida con el mismo molde. El
firmware ESP32 y el ladder PLC se desarrollan por separado contra
`vision_controller_v1`.

## 2. Arquitectura vigente

```text
Motor universal
  +-- config/system.json de una instalacion
  +-- catalogo externo de recetas
  +-- registro de herramientas genericas
  +-- protocolo fijo vision_controller_v1
  +-- interfaz responsiva

Instalacion Worksurface (futura)
  +-- system.json propio
  +-- recetas migradas y comisionadas
  +-- imagenes maestras/ROI reales
  +-- firmware ESP32 separado
  +-- ladder PLC separado
```

La instalacion activa se selecciona mediante `VISION_SYSTEM_CONFIG`. No existen
`profiles`, `active_profile`, `general`, `worksurface` ni recetas incorporadas
al codigo del motor.

## 3. Estado de fases

| Fase | Resultado | Estado |
|---|---|---|
| 1 | Configuracion inicial, enfoque y multiples steps | Publicada |
| Correccion universal | Retiro de perfiles, recetas declarativas y protocolo unico | Publicada |
| 3 | Editor de sistema/recetas, guardado atomico, validacion y comisionamiento | Publicada |
| 4 | ROI v3, PASS/FAIL/ERROR/TIMEOUT, cancelacion, deadline y DataMatrix | Publicada por Andy |
| 5 | Deteccion de pantalla y layout responsivo | Codigo validado; prueba visual pendiente |

## 4. Fase 5 - interfaz responsiva

### 4.1 Deteccion

El motor consulta `availableGeometry()` de la pantalla activa. No usa valores
de camara ni requiere parametros en `system.json`.

| Modo | Regla | Uso esperado |
|---|---|---|
| `compact` | ancho <= 600 o alto <= 360 | Raspberry 480x320 y pantallas muy pequenas |
| `standard` | resoluciones intermedias | 800x480 y escritorios medianos |
| `wide` | ancho >= 1200 y alto >= 700 | PC y monitores grandes |

### 4.2 Comportamiento

- elimina en runtime los limites fijos heredados de 800x480;
- escala margenes, separacion, tipografia, log, indicador y video;
- conserva controles tactiles en modo compacto;
- ajusta ventana principal, configuracion, sistema, receta, enfoque y tools;
- los formularios largos permanecen desplazables;
- Linux conserva modo kiosco a pantalla completa;
- cambiar la ventana principal de monitor recalcula el perfil;
- se agregaron descripciones emergentes a los parametros de SISTEMA;
- `Ancho` y `Alto` se renombraron visualmente como `Ancho de captura` y
  `Alto de captura`.

### 4.3 Validacion

```text
Ran 47 tests
OK
COMPILE_OK
PATCH_CHECK_OK
DIFF_CHECK_OK
```

El parche se aplico sobre una segunda copia limpia de fase 4. El entorno de
desarrollo usado para construirlo no contiene PySide6/PyQt5, por lo que la
prueba visual real sigue siendo obligatoria en PC y Raspberry.

## 5. Configuracion completa de sistema

`config/system.json` describe una instalacion fisica. Los cambios guardados
desde SISTEMA son atomicos, conservan `system.json.bak` y requieren reiniciar la
aplicacion.

### 5.1 Raiz

| Parametro | Funcion | Regla |
|---|---|---|
| `schema_version` | Version del contrato de configuracion de sistema | Actualmente debe ser `2`; no editar manualmente |

### 5.2 `installation`

| Parametro | Funcion | Ejemplo/criterio |
|---|---|---|
| `id` | Identificador tecnico estable de la estacion | Obligatorio; util para despliegue y trazabilidad |
| `name` | Nombre legible de la estacion | Puede describir ubicacion o proceso |

No selecciona un perfil de producto. Cada archivo completo representa una
instalacion.

### 5.3 `recipes`

| Parametro | Funcion | Recomendacion |
|---|---|---|
| `file` | Ruta al catalogo JSON de recetas | Mantenerla relativa a la raiz del proyecto cuando sea posible |
| `auto_migrate` | Convierte recetas antiguas al esquema vigente | Mantener `true` durante la migracion; genera `.bak` |

El catalogo contiene modelos, enfoque, steps, herramientas, parametros y
condiciones. No debe confundirse con `system.json`.

### 5.4 `camera`

| Parametro | Funcion | Observacion |
|---|---|---|
| `device` | Camara utilizada | Indice `0`, `1`, etc. o ruta persistente `/dev/v4l/by-id/...` |
| `width` | Ancho solicitado del frame | Resolucion de captura, no del monitor |
| `height` | Alto solicitado del frame | Resolucion de captura, no del monitor |
| `capture_fps` | Frecuencia de adquisicion | Afecta carga USB/CPU y disponibilidad de frames |
| `preview_fps` | Frecuencia de visualizacion | Puede ser menor que captura para ahorrar recursos |
| `default_focus_mode` | Modo inicial para recetas nuevas | `calibrated`, `manual_fixed`, `auto_continuous` o `disabled` |

El driver puede entregar una resolucion distinta a la solicitada; la fase de
diagnostico de inicio debera registrar el valor real negociado.

### 5.5 `controller`

| Parametro | Funcion | Regla |
|---|---|---|
| `transport` | Medio de comunicacion | Fijo en `serial` |
| `protocol` | Contrato de mensajes | Fijo en `vision_controller_v1` |
| `ports` | Puerto por plataforma | Claves `linux`, `windows` o `default`; preferir rutas persistentes en Linux |
| `baudrate` | Velocidad serial | Debe coincidir exactamente con ESP32/controlador |
| `timeout` | Espera maxima serial | No es el timeout total de inspeccion |
| `reset_on_connect` | Reinicio al abrir puerto | Usar solo si el hardware y la secuencia de arranque lo requieren |
| `heartbeat_enabled` | Supervision de enlace | Recomendado `true` en produccion |
| `ready_notifications_enabled` | Publica READY/NOT_READY | Recomendado `true` en produccion |
| `model_map` | ID externo recibido -> nombre de receta | Cada receta destino debe existir |

`model_map` acepta IDs arbitrarios. El motor no impone A/B/C ni numeros de
parte concretos.

### 5.6 `runtime`

| Parametro | Funcion | Riesgo que controla |
|---|---|---|
| `require_controller_ready` | Exige controlador disponible | Evita triggers sin enlace operativo |
| `require_controller_sync` | Exige handshake de protocolo | Evita mezclar firmware incompatible |
| `require_focus_ready` | Exige enfoque valido | Evita inspeccion borrosa/no calibrada |
| `max_frame_age_seconds` | Antiguedad maxima del frame | Evita decidir con una imagen vieja |
| `mechanical_settle_ms` | Espera cancelable despues del trigger | Permite que pieza/clamps queden inmoviles |
| `inspection_timeout_seconds` | Limite total del ciclo de vision | Convierte una ejecucion agotada en TIMEOUT/ERROR |

Para produccion, los tres `require_*` deben permanecer en `true` salvo una
prueba controlada y documentada.

### 5.7 Lo que no pertenece a `system.json`

- resolucion o escala del monitor: se detecta automaticamente;
- ROI y parametros de herramientas: pertenecen a recetas;
- patrones de sensores Worksurface: pertenecen al firmware/configuracion de esa
  maquina;
- direccionamiento PLC: pertenece al ladder y documentacion electrica;
- secretos o credenciales: no deben guardarse aqui.

## 6. Contratos de ejecucion vigentes

### ROI

- formato unico `[x1,y1,x2,y2]` sobre el frame original;
- `x2/y2` son limites exclusivos;
- migracion v1/v2 a receta v3 con respaldo;
- histograma heredado se convierte de xywh a xyxy.

### Resultados

| Estado | Significado | Controlador |
|---|---|---|
| `PASS` | Producto aceptado | `OK` |
| `FAIL` | Producto rechazado | `NG` |
| `ERROR` | No hubo decision por falla | `ERROR` |
| `TIMEOUT` | No hubo decision dentro del plazo | `ERROR` |

### Ciclo

- identificador unico por ciclo;
- ACK vinculado al mensaje/ciclo;
- READY/NOT_READY y heartbeat;
- cancelacion cooperativa;
- rechazo de resultados tardios;
- ningun trigger se acepta en NOT_READY.

## 7. Estimacion de avance

Esta es una estimacion de planeacion ponderada, no cobertura de tests ni una
promesa de tiempo. Se separa motor universal de reemplazo completo porque el
segundo incluye hardware y despliegue.

| Area | Peso del proyecto | Avance del area | Contribucion |
|---|---:|---:|---:|
| Arquitectura universal y configuracion externa | 12 % | 100 % | 12.0 % |
| Recetas, migracion y editores | 13 % | 100 % | 13.0 % |
| Protocolo y seguridad del ciclo | 12 % | 100 % | 12.0 % |
| ROI, resultados, timeout y DataMatrix | 13 % | 100 % | 13.0 % |
| Interfaz responsiva | 8 % | 85 % | 6.8 % |
| Diagnostico, trazabilidad y recursos | 8 % | 20 % | 1.6 % |
| Framework/catalogo de herramientas | 10 % | 35 % | 3.5 % |
| Instalacion y recetas reales Worksurface | 8 % | 0 % | 0.0 % |
| Firmware, PLC y comisionamiento fisico | 8 % | 0 % | 0.0 % |
| Empaquetado, instalacion, rollback y corte | 8 % | 0 % | 0.0 % |
| **Total para sustituir Worksurface** | **100 %** |  | **61.9 % (~62 %)** |

Tomando solo las primeras siete areas de software reutilizable, el motor
universal esta aproximadamente al **81 %**. La interfaz responsiva subira de 85
a 100 % cuando pase la prueba visual/tactil real.

## 8. Datos Worksurface conocidos y pendientes

### Conocido, pero fuera del motor

| Modelo | Numero de parte | Sensor izquierdo | Sensor derecho |
|---|---|---|---|
| A | `0402012XA` | OK | NG |
| B | `0402012XB` | NG | OK |
| C | `0402012XC` | OK | OK |

### Pendiente de confirmar

- si esos numeros son el contenido exacto del DataMatrix;
- niveles HIGH/LOW reales de cada sensor;
- pinout definitivo ESP32 y tabla PLC/ESP/Raspberry;
- que `PIN_RESULT=LOW` mantenga segura/desactivada la entrada PLC X5;
- tiempo real de asentamiento tras clamps;
- imagenes representativas buenas y defectuosas de cada modelo;
- ROI, tolerancias y parametros finales de herramientas;
- comportamiento ante desconexion, reinicio y pieza retirada.

Nada de esto debe codificarse dentro del motor universal.

## 9. Ruta pendiente hasta una version descargable de reemplazo

### Paso 1 - Cerrar fase 5

- aplicar parche;
- aprobar 47 pruebas;
- revisar PC y Raspberry real;
- corregir solamente problemas visuales confirmados;
- publicar el commit.

### Paso 2 - Fase 6: operacion y trazabilidad

- validar al arranque rutas, permisos, catalogo, imagenes maestras y tools;
- diagnosticar camara/serial con valores solicitados y reales;
- registrar cada ciclo en formato estructurado con `cycle_id`, receta, tiempos,
  steps, resultado y razon;
- rotar logs y limitar almacenamiento;
- mostrar fallas accionables sin bloquear la UI;
- agregar pruebas de recuperacion y recursos faltantes.

Esta es la siguiente prioridad recomendada por V9 una vez resuelta la pantalla.

### Paso 3 - Completar el framework de herramientas

- separar descubrimiento/registro de tool y su schema de UI;
- revisar que todas las tools sean cancelables, tengan deadline y usen ROI v3;
- migrar cualquier herramienta heredada necesaria;
- documentar como agregar una tool sin modificar la FSM;
- probar parametros, errores y resultados de cada tool.

### Paso 4 - Crear la instalacion Worksurface externa

- generar su `system.json` sin agregar un perfil al motor;
- migrar recetas viejas al esquema v3;
- crear A/B/C como datos externos;
- capturar imagenes y configurar ROI/enfoque;
- comisionar cada receta solo tras validar sus recursos.

### Paso 5 - Firmware y PLC separados

- crear firmware ESP32 contra `vision_controller_v1`;
- conservar ciclo, modelo, ACK, READY/NOT_READY, heartbeat y cancelacion;
- definir estados seguros de salidas;
- adaptar/verificar ladder PLC sin incorporarlo al repositorio del motor;
- validar primero con simulador y E/S desconectadas.

### Paso 6 - Comisionamiento controlado

- medir niveles electricos y tiempos;
- probar sin actuadores, despues con actuadores aislados;
- ejecutar matriz de OK, NG, ERROR, TIMEOUT, cancelacion y desconexion;
- realizar repetibilidad por modelo y pruebas de resultados tardios;
- documentar criterios de aceptacion y evidencia.

### Paso 7 - Empaquetado descargable

- fijar dependencias compatibles con Raspberry Pi 4;
- crear paquete versionado (ZIP/release) con checksum;
- incluir instalador, entorno virtual, configuracion base y migrador;
- agregar servicio `systemd`, autoarranque y reinicio controlado;
- incluir backup/restore de configuracion y recetas;
- generar manual de instalacion, configuracion, diagnostico y rollback.

### Paso 8 - Sustitucion de la version antigua

- conservar imagen/backup completo de la Raspberry anterior;
- instalar la nueva version en paralelo o en almacenamiento de prueba;
- ejecutar prueba de aceptacion con produccion controlada;
- comparar decisiones y tiempos con el sistema anterior;
- cambiar a produccion solo con criterios aprobados;
- mantener rollback inmediato durante el periodo acordado.

La version nueva no debe reemplazar todavia a la antigua. El entregable actual
es un parche de desarrollo, no un paquete de produccion.

## 10. Criterios de salida para declarar reemplazo final

- una sola aplicacion sin perfiles de producto;
- configuracion y recetas externas como fuente de verdad;
- todas las recetas Worksurface comisionadas;
- protocolo y estados seguros aprobados con hardware real;
- cero triggers aceptados en NOT_READY;
- ERROR/TIMEOUT nunca reportados como NG;
- trazabilidad de ciclo y retencion controlada;
- arranque automatico reproducible;
- instalacion limpia documentada;
- backup y rollback probados;
- prueba de aceptacion firmada antes de retirar la version antigua.

## 11. Proxima fase recomendada

Despues de que Andy aplique y revise visualmente fase 5, continuar con **fase 6:
diagnostico de arranque, validacion de recursos y trazabilidad estructurada de
ciclos**. Esa fase reduce el riesgo de desplegar una instalacion que aparenta
estar lista pero tiene rutas, imagenes, camara o puerto incorrectos.
