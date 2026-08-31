# Contexto Worksurface V24 - Hotfix Fase 12.2

## Resultado

Se corrigio la falsa ausencia de `focus_absolute` en Raspberry. La Arducam se
configura mediante una ruta persistente `/dev/v4l/by-id/*`, mientras que la
logica anterior solo aceptaba cadenas que comenzaran literalmente por
`/dev/video`. OpenCV podia abrir el enlace y mostrar video, pero la consulta de
controles terminaba antes de ejecutar `v4l2-ctl`.

El runtime conserva el endpoint estable como identidad, lo resuelve mediante
`realpath` y valida que su destino sea `/dev/videoN`. La deteccion, lectura y
escritura de controles usan ese nodo canonico. Un endpoint roto informa ahora
la ruta configurada y su destino fallido.

## Evidencia fisica

La Arducam 8MP SN0001 publico en Raspberry:

- driver `uvcvideo`;
- video en `/dev/video0`;
- `focus_absolute` con rango `1-1023` y paso `1`;
- `focus_automatic_continuous`;
- escritura y lectura correctas de `focus_absolute`.

Por tanto, el mensaje `focus_absolute: no` era una falla de integracion y no
una ausencia del control en la camara.

## Refinamiento visual incluido

- mas altura util para el estado en la pantalla compacta 480x320;
- controles de eventos 3 px mas bajos;
- mensajes largos envueltos y desplazamiento por pixel;
- seguimiento correcto del ultimo evento;
- bordes uniformes y feedback visible para botones destructivos.

## Despliegue

Una estacion con Fase 12 instalada se actualiza como nuevo release mediante
`scripts/update_raspberry.sh`; no se repite el aprovisionamiento. Configuracion,
recetas, calibraciones, imagenes maestras y trazabilidad permanecen bajo
`/var/lib/vision-sensor`. El EXE de Windows es independiente del runtime de la
Raspberry.

## Validacion automatizada

La suite completa contiene 158 pruebas correctas, incluidas regresiones para
rutas persistentes V4L2 y contratos visuales compactos. Tambien se validaron la
compilacion Python y la sintaxis de los scripts Bash.
