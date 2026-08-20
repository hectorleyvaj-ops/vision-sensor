# Contexto Worksurface V20 - Cierre visual 11.1.2

**Fecha:** 2026-08-20

**Base:** refinamiento 11.1.1 (`0aeb4f2`)

## Estado de interfaz

El feedback fisico confirma que la paleta, ventanas modales y configuracion de
enfoque funcionan correctamente en Raspberry. El cierre 11.1.2 solamente
ajusta controles de titulo, navegacion inferior y desplazamiento de eventos.

La fase de interfaz puede considerarse cerrada cuando la prueba fisica confirme
estos ultimos controles.

## Siguiente fase: industrializacion

La fase 12 debe preparar una instalacion reproducible y recuperable:

- instalador o script de aprovisionamiento;
- entorno virtual y dependencias del sistema;
- servicio `systemd` con usuario y rutas explicitas;
- arranque automatico, reinicio controlado y apagado limpio;
- variables `VISION_SYSTEM_CONFIG` y `VISION_QT_API` persistentes;
- logs mediante journal y conservacion de trazabilidad;
- inicio de interfaz en modo kiosco;
- diagnostico y reparacion del touchscreen;
- respaldo, restauracion y procedimiento de actualizacion.

No se trasladan I/O, polaridades ni secuencia de maquina al motor Python.

## Fase final: aceptacion Worksurface

Despues de industrializar se requiere configurar el hardware y producto reales,
comisionar MODELO_A/B/C desde la interfaz y ejecutar pruebas completas:

- inicio y apagado repetidos;
- combinaciones OK/NG de los tres modelos;
- desconexion y reconexion de camara y ESP32;
- cancelacion, timeout, watchdog y perdida serial;
- codigos DataMatrix e imagenes maestras definitivos;
- enfoque, ROI y umbrales por receta;
- latencia de ciclo y trazabilidad;
- tasa de falsos aceptados y falsos rechazados;
- validacion estricta y version etiquetada.

Solo al completar esa evidencia la instalacion debe pasar de
`LISTA PARA CALIBRAR` a comisionada para produccion.
