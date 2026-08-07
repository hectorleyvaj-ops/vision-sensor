# Worksurface V3 - fase 1

Esta fase integra Worksurface como un perfil del motor de vision general. No cambia el perfil activo de produccion y no modifica el firmware grabado en la ESP32.

## Activacion local

```bash
VISION_PROFILE=worksurface python main.py
```

Para un servicio `systemd`, la variable debe agregarse al servicio mediante un archivo de entorno o una directiva `Environment=VISION_PROFILE=worksurface`. No debe desplegarse todavia en la maquina: las recetas Worksurface se entregan con `commissioned=false` y sin herramientas de vision para impedir un falso `OK`.

## Modelos confirmados

| Modelo del controlador | Receta | Numero de parte | Sensor izquierdo | Sensor derecho |
|---|---|---|---|---|
| A | `MODELO_A` | `0402012XA` | `OK` | `NG` |
| B | `MODELO_B` | `0402012XB` | `NG` | `OK` |
| C | `MODELO_C` | `0402012XC` | `OK` | `OK` |

`OK/NG` describe el estado funcional esperado. La conversion a niveles electricos HIGH/LOW sigue pendiente de medicion, porque el firmware adjunto no coincide con la tabla nueva para el modelo A.

## Configuracion generalizada

`config/system.json` controla:

- perfil activo;
- archivo de recetas;
- dispositivo, resolucion y FPS de captura/vista previa;
- modo de enfoque predeterminado;
- puerto y parametros seriales;
- mapeo de modelos recibidos a recetas;
- requisitos de disponibilidad y tiempo de asentamiento mecanico.

Cada receta puede seleccionar uno de estos modos de enfoque desde la ventana de enfoque:

- `calibrated`: barrido inicial, verificacion y foco congelado;
- `manual_fixed`: valor absoluto fijo guardado en la receta;
- `auto_continuous`: autofocus continuo de la camara;
- `disabled`: la aplicacion no administra el enfoque.

## Compatibilidad con el firmware actual

El firmware confirmado procesa `SYNC`, `OK`, `NG` y `ACK`, pero no procesa `PING`, `RPI_READY` ni `RPI_NOT_READY`. Por eso el perfil mantiene deshabilitados heartbeat y avisos READY hasta desplegar una version emparejada del protocolo. Esto evita que Python declare una desconexion falsa cada seis segundos.

## Condiciones pendientes antes de comisionar

1. Configurar las herramientas y ROI de cada receta.
2. Calibrar el enfoque elegido para cada modelo.
3. Medir el tiempo de asentamiento de los clamps y configurar `mechanical_settle_ms`.
4. Medir los niveles activos reales de ambos sensores y corregir el firmware.
5. Emparejar firmware y Python con heartbeat, READY/NOT_READY e identificador de ciclo.
6. Ejecutar pruebas sin actuadores y después con aire reducido antes de habilitar `commissioned=true`.

## Verificacion de software

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m py_compile app/app.py core/*.py processing/*.py services/*.py vision/*.py
```
