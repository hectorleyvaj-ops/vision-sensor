# Instalacion externa Worksurface

Este directorio contiene datos de la estacion. No forma parte del motor de
vision y no agrega reglas A/B/C a `core/`, `app/`, `processing/` ni `tools/`.

## Estado seguro inicial

Las recetas `MODELO_A`, `MODELO_B` y `MODELO_C` existen, pero comienzan con
`commissioned: false`. Los campos fisicos desconocidos se conservan vacios; no
se copiaron el codigo, ROI o enfoque de otra pieza.

El motor debe iniciarse desde la raiz del proyecto porque las rutas relativas
de `system.json` y `recipes.json` siguen el contrato vigente del motor.

## Validacion sin hardware

```bash
python scripts/validate_installation.py
```

Mientras falten mediciones, el comando termina con codigo `0` y muestra
`LISTA PARA CALIBRAR`. Esto significa que la estructura es coherente, no que la
estacion pueda producir.

El control para produccion es:

```bash
python scripts/validate_installation.py --require-commissioned
```

Este segundo comando termina con codigo `3` mientras quede cualquier receta o
calibracion pendiente. Un error estructural termina con codigo `2`.

## Directorios de imagen

- `commissioning_captures/model_*/ok`: capturas buenas representativas;
- `commissioning_captures/model_*/ng`: defectos y casos limite;
- `master_images/model_*`: maestras aprobadas que realmente usara la receta.

No se debe renombrar una captura cualquiera como imagen maestra. Primero se
evalua con poblacion OK/NG, se fija una ROI canonica `[x1,y1,x2,y2]` y se mide
un umbral que separe ambos grupos con margen.

Las rutas guardadas en `template_paths` deben comenzar con
`installations/worksurface/master_images/` para que funcionen al iniciar desde
la raiz del proyecto.

## Herramientas preparadas

Cada receta contiene:

1. un step `dmtx` requerido, pendiente de codigo exacto y ROI;
2. un step `img_hist` requerido, pendiente de ROI, umbral e imagenes maestras;
3. enfoque calibrado pendiente.

Si el estudio fisico demuestra que Worksurface no necesita comparacion por
histograma, la decision debe documentarse: se retira o deshabilita ese step y
se actualiza `recipe_policy.required_tools` en `commissioning.json`. No se debe
aprobar dejando `threshold: 0`.

## Limite con fase 9

Los patrones de sensores del manifiesto son referencia del entorno fisico para
la siguiente fase. El motor de vision no los interpreta. El firmware ESP32
actual aun debe migrarse a `vision_controller_v1`; por eso esta instalacion no
autoriza ciclos automaticos ni liberacion PLC durante fase 8.
