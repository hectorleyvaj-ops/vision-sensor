# Hotfix fase 11 - Arranque seguro sin camara

## Objetivo

La ausencia de camara ya no es un error fatal de construccion de la interfaz.
La aplicacion inicia en modo degradado y conserva acceso a **CONFIGURAR
ESTACION**, pero permanece fuera de produccion.

En este estado:

- la interfaz muestra `CRITICAL` o `NO DISPONIBLE` con la causa;
- la ESP32 recibe `READY|STATE=0`;
- no se acepta ningun trigger ni se inicia la FSM;
- no existe un frame fresco que pueda inspeccionarse;
- se puede abrir **ESTACION** y cambiar `camera.device`;
- los cambios de camara se aplican al reiniciar.

## Aplicar sobre fase 11

Desde una rama que ya contenga el commit de fase 11:

```bash
git status --short
git am /ruta/0001-Allow-safe-startup-without-camera.patch
```

## Validacion automatica

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q app core processing services tools ui vision tests
python scripts/validate_installation.py
```

Resultado esperado:

```text
Ran 123 tests
OK
Resultado: LISTA PARA CALIBRAR
```

## Prueba manual en Windows

1. Desconectar o bloquear deliberadamente la camara configurada.
2. Iniciar con `VISION_SYSTEM_CONFIG` apuntando a Worksurface.
3. Confirmar que se abre la ventana principal y no aparece el dialogo fatal
   `Signal source has been deleted`.
4. Confirmar que el estado indica camara no disponible.
5. Confirmar que **CONFIGURAR ESTACION** permanece habilitado.
6. Abrir **ESTACION**, cambiar el indice de camara y guardar.
7. Confirmar que se solicita reiniciar y que la ESP32 permanece en `READY=0`.
8. Intentar un trigger desde el controlador y confirmar que se rechaza.
9. Reiniciar y comprobar el nuevo indice.

En Windows se intenta el indice configurado con DSHOW, MSMF y AUTO. No se
escanea ni selecciona automaticamente otro indice, para evitar usar una camara
equivocada en una estacion industrial.

## Alcance de seguridad

Este hotfix no convierte una camara opcional en produccion. Solo separa dos
conceptos:

- **interfaz/configuracion disponible**;
- **estacion lista para produccion**.

La segunda condicion continua exigiendo diagnosticos sin bloqueo, frame fresco,
receta utilizable, enfoque listo y controlador sincronizado segun `system.json`.
