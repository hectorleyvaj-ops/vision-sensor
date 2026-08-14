# Contexto Worksurface V16 - Fase 11 interfaz final

**Fecha:** 2026-08-14

**Base:** fase 10 aplicada

**Rama:** `feature/final-interface-phase11`

## 1. Objetivo vigente

El sistema es un motor de vision configurable y descentralizado. La Raspberry
ejecuta recetas y herramientas; el controlador externo conserva trigger,
modelo, sincronizacion y logica fisica segura. La interfaz debe permitir editar
la instalacion y las recetas sin introducir reglas Worksurface en el motor.

El orden final de trabajo se cambio por decision del proyecto:

| Fase | Alcance |
|---:|---|
| 11 | Interfaz final, estetica, adaptable y amigable |
| 12 | Despliegue industrial, servicio, backup/rollback y reparacion del touch |
| 13 | Pruebas integrales, calibracion, aceptacion y corte reversible |

No se planea una fase 14. Los hallazgos posteriores se trataran como defectos de
la version candidata, no como ampliacion automatica del alcance.

## 2. Estado de fases

| Fase | Estado |
|---:|---|
| 1-10 codigo | Implementadas |
| 9 fisica | Evidencia electrica pendiente |
| 10 fisica | Poblaciones y escenarios pendientes |
| 11 codigo | Implementada |
| 11 visual | Pendiente de revisar en PC y Raspberry real |
| 12 | Pendiente |
| 13 | Pendiente |

## 3. Interfaz principal

Se elimino el texto heredado `SUMMIT USB`. El encabezado ahora usa
`installation.name` de `system.json`, por lo que otra instalacion cambia su
identidad sin modificar Python o archivos `.ui`.

La pantalla muestra:

- instalacion activa;
- vista de camara y ROI;
- receta activa;
- estado textual;
- causa de bloqueo;
- resultado OK/NG/ERROR;
- eventos recientes;
- acceso a configuracion.

Los estados se construyen en `core/operator_status.py`, sin Qt, y respetan esta
prioridad:

1. falla critica;
2. no listo;
3. ciclo en ejecucion;
4. resultado final;
5. espera de trigger.

Un OK retenido no puede ocultar una desconexion o diagnostico bloqueante.

## 4. Autoridad del controlador

El indicador dejo de estar conectado a `run_fsm`. Es un indicador, no un boton
de trigger. El ciclo productivo solo empieza con un evento valido del
controlador que incluya ciclo y modelo.

Este cambio conserva la arquitectura descentralizada:

```text
PLC/sensores -> ESP32 -> vision_controller_v1 -> motor -> receta
```

La interfaz no conoce pines o patrones de sensores. Worksurface continua
requiriendo la ESP32 porque `require_controller_ready` y
`require_controller_sync` estan activos.

## 5. Sistema visual

`ui/theme.py` contiene una paleta industrial unica para operador y editores:

- fondo azul oscuro;
- tarjetas con borde discreto;
- acento cian;
- verde para OK;
- rojo para NG/falla;
- ambar para no listo;
- azul para ciclo en proceso.

El estado siempre se comunica con texto y color. Se agregaron nombres
accesibles y tooltips a los elementos principales.

En 800x480:

- objetivo tactil minimo: 42 px;
- indicador: 72 px;
- encabezado: 48 px;
- eventos: 64 px.

Los maximos heredados de 30 px se eliminan de los botones de configuracion.

## 6. Configuracion

La ventana usa vocabulario de operador:

- NUEVA, BORRAR y ACTIVAR receta;
- AGREGAR, EDITAR y BORRAR PASO;
- ESTACION y PROPIEDADES;
- CAMARA Y ENFOQUE;
- GUARDAR y VOLVER.

Cada receta muestra un resumen:

```text
ACTIVA · 2 PASOS · EN CALIBRACION
```

Los IDs internos de enfoque continúan estables en JSON, pero la interfaz
muestra nombres en español. La seleccion de receta refresca inmediatamente la
pantalla principal y sus ROI.

## 7. Borrado recuperable

Borrar una receta o paso requiere confirmacion. Los recursos asociados se
mueven a:

```text
runtime/deleted_resources/
```

No se usa `rmtree` en ese flujo. El archivado evita sobrescribir un destino
existente y puede restaurarse manualmente. La politica completa de backups y
rollback se implementara en fase 12.

## 8. Configurabilidad y limites

Desde la interfaz ya se editan:

- nombre e ID de instalacion;
- catalogo de recetas;
- camara, resolucion y FPS;
- enfoque predeterminado;
- puerto, baudrate y timeouts;
- heartbeat y READY;
- mapeo de IDs externos a recetas;
- condiciones de disponibilidad;
- asentamiento mecanico y timeout de inspeccion;
- trazabilidad;
- recetas, pasos, herramientas, ROI, imagenes y enfoque.

No se editan desde Python los pines, polaridades o patrones de sensores de la
ESP32. Esos valores siguen en el firmware de cada instalacion. Tampoco se
implementan transportes hipoteticos que Worksurface no usa.

## 9. Pruebas

La suite contiene 118 pruebas y pasa completa. Las 15 nuevas verifican:

- prioridad y textos del estado de operador;
- receta sin nombre y estados OK/NG;
- perfiles tactiles 480x320 y 800x480;
- seis niveles semanticos de color;
- ausencia de Summit y modelo A en la interfaz generica;
- consistencia PyQt5/PySide6;
- controlador como unica autoridad del trigger;
- protecciones de borrado;
- archivado recuperable sin sobrescritura;
- nombres legibles para todos los modos de enfoque.

El entorno de construccion no tiene Qt instalado, por lo que no se genero una
captura real. La sintaxis Python, XML, contratos estaticos y logica pura estan
validados. La revision visual en la Raspberry sigue siendo obligatoria.

El validador de instalacion conserva:

```text
Resultado: LISTA PARA CALIBRAR
```

## 10. Siguiente paso

1. Aplicar el parche de fase 11.
2. Ejecutar las 118 pruebas.
3. Revisar visualmente en PC.
4. Copiar a Raspberry y tomar capturas en 800x480.
5. Ajustar solamente defectos visuales comprobados.
6. Continuar fase 12 con servicio, encapsulamiento, backup, rollback y touch.
7. Ejecutar fase 13 con aceptacion completa y hardware real.
