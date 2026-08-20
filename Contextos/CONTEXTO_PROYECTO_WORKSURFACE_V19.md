# Contexto Worksurface V19 - Refinamiento 11.1.1

**Fecha:** 2026-08-20

**Base:** fase 11.1 limpia (`64fe994`)

## Decision

La fase 12 continua bloqueada hasta validar fisicamente este refinamiento en la
Raspberry. El motor Python sigue siendo un sensor de vision configurable que
solo entrega `OK`, `NG` o `ERROR`; la ESP32 conserva I/O y secuencia de maquina.

## Interfaz

La diferencia PySide6/PyQt5 se atiende aplicando el tema a la aplicacion,
repuliendo widgets heredados y retirando limpiezas tardias de estilos. Los
mensajes tienen contraste explicito. Los editores secundarios son modales de
aplicacion y Linux los lleva a pantalla completa una vez iniciado `exec()`.

## Enfoque

Los modos ahora tienen contratos visibles y diferentes:

- automatico por receta: barrido grueso/fino/micro, seleccion por nitidez,
  persistencia de valor y umbral, verificacion y posible recalibracion;
- valor fijo del operador: entrada numerica directa sin barrido ni reenfoque;
- autofocus continuo: autoridad de enfoque en la camara;
- sin gestion: el motor no modifica el lente.

`v4l2-ctl` se diagnostica como utilidad de `v4l-utils`, separada del driver y de
la capacidad `focus_absolute` del endpoint.

## Seguridad preservada

La ausencia de camara, utilidad V4L2 o control de foco no impide abrir la
interfaz. La configuracion permanece disponible, pero los diagnosticos y el
estado de enfoque impiden produccion cuando la politica activa lo exige.

## Puerta de salida

Antes de fase 12 deben confirmarse en Raspberry:

- tema y legibilidad 800x480;
- modales en pantalla completa;
- areas tactiles de botones y scrollbars;
- deteccion de `v4l2-ctl`;
- presencia real de `focus_absolute`;
- calibracion automatica y aplicacion del valor fijo;
- bloqueo seguro ante fallas de hardware.
