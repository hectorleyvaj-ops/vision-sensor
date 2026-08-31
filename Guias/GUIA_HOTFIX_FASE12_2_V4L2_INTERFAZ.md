# Hotfix 12.2 - Enfoque V4L2 e interfaz compacta

Este hotfix corrige la deteccion de controles de camara cuando la estacion usa
un endpoint persistente `/dev/v4l/by-id/*` y reúne los ajustes visuales
confirmados en la pantalla Worksurface de 480x320.

## Cambios incluidos

- conserva la ruta estable configurada para identificar la Arducam;
- resuelve internamente esa ruta al nodo canonico `/dev/videoN`;
- consulta y aplica `focus_absolute` y
  `focus_automatic_continuous` sobre el nodo resuelto;
- publica el endpoint de controles en el diagnostico runtime;
- recupera espacio vertical para el mensaje de estado en modo compacto;
- reduce ligeramente los botones de desplazamiento de eventos;
- desplaza mensajes largos por pixeles para no saltar texto envuelto;
- conserva el seguimiento automatico del evento mas reciente;
- unifica el grosor de bordes y agrega feedback hover/pressed a botones de
  borrado;
- restaura LF y permiso ejecutable en los scripts Linux de Fase 12.

No cambia recetas, valores de enfoque guardados, firmware ESP32, PLC, pines,
protocolos ni datos persistentes de la instalacion.

## Aplicar en la copia de desarrollo

Desde la raiz de una copia limpia del proyecto:

```bash
git status --short
git apply --check fase12_2_v4l2_ui_hotfix.patch
git apply fase12_2_v4l2_ui_hotfix.patch
python -m unittest discover -s tests -p "test_*.py"
git status --short
```

Revisa los cambios y crea un commit. El commit es obligatorio antes de usar
`update_raspberry.sh`, porque el hash del commit identifica el nuevo release:

```bash
git add app core scripts tests ui utils vision Guias Contextos
git commit -m "Fix V4L2 persistent camera focus and compact UI"
git push
```

No agregues `system.json`, `recipes.json`, recursos maestros ni archivos
`.bak` modificados por calibracion.

## Actualizar una Raspberry que ya tiene Fase 12

No ejecutes otra vez `install_raspberry.sh`. La instalacion existente ya tiene
servicio, autostart y directorios persistentes. En la copia Git de la Raspberry:

```bash
cd /ruta/a/Proyecto_vision_sensor
git pull --ff-only
git status --short
python3 -m unittest discover -s tests -p "test_*.py"
sudo ./scripts/update_raspberry.sh "$(pwd)" /opt/vision-sensor
./scripts/vision_service.sh restart
./scripts/vision_service.sh status
./scripts/vision_service.sh logs 160
```

`git status --short` debe quedar vacio antes de actualizar. El script crea un
nuevo release bajo `/opt/vision-sensor/releases`, mueve atómicamente
`/opt/vision-sensor/current` y conserva:

```text
/var/lib/vision-sensor/installations/worksurface
/var/lib/vision-sensor/runtime/worksurface
```

Por ello no es necesario volver a seleccionar hardware, rehacer recetas ni
recalibrar el enfoque si el valor almacenado sigue siendo opticamente valido.

## Verificacion en Raspberry

```bash
readlink -f /opt/vision-sensor/current
grep '^VISION_SYSTEM_CONFIG=' /etc/vision-sensor/vision-sensor.env
./scripts/vision_service.sh logs 200 | grep -iE \
  'Endpoint V4L2|Controles v4l2|focus_absolute|Rango focus|ERROR'
```

Se espera un registro equivalente a:

```text
[CAMERA] Endpoint V4L2 de controles: /dev/v4l/by-id/... -> /dev/video0
[CAMERA] Controles v4l2 detectados: [..., 'focus_absolute', ...]
[CAMERA] Rango focus_absolute: min=1, max=1023, step=1
```

En **CONFIGURAR ESTACION > CONFIGURAR ENFOQUE** debe aparecer
`focus_absolute: si` y el rango `1-1023`. Verifica ademas que el texto de
atencion y los eventos largos puedan recorrerse completos.

## Recuperacion

Si el nuevo release no inicia:

```bash
sudo ./scripts/rollback_raspberry.sh /opt/vision-sensor
./scripts/vision_service.sh restart
./scripts/vision_service.sh status
```

## EXE de Windows

El EXE no participa en el despliegue de Raspberry: Fase 12 ejecuta Python desde
el entorno virtual del release. Solo reconstruye el EXE una vez, despues de
aplicar este parche, si tambien distribuyes una version Windows. Esta copia del
proyecto no contiene un archivo `.spec` ni un script de PyInstaller, por lo que
el comando exacto debe recuperarse del procedimiento usado para construir el
EXE anterior.
