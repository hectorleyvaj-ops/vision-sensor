# Guia de cierre 11.1.3 - Interfaz Raspberry

## Alcance

Parche incremental sobre la version 11.1.2 (`7e38381`). Corrige exclusivamente
los ultimos hallazgos visuales confirmados en Raspberry. No modifica recetas,
configuracion Worksurface, camara, firmware ESP32, GPIO ni logica PLC.

## Cambios

- La barra vertical nativa de eventos se oculta tambien a nivel de widget y se
  fija a ancho cero; los botones tactiles siguen controlando el desplazamiento.
- Los botones `▲` y `▼` reducen aproximadamente cinco pixeles su altura.
- `ACTIVAR` y `GUARDAR` usan un estilo de accion explicita con texto blanco y
  contraste estable en Raspberry.
- Al presionar `ACTIVAR` o `GUARDAR`, el fondo cambia a turquesa claro, el texto
  cambia a oscuro y el contenido se desplaza levemente para confirmar el toque.

## Aplicacion

Desde una copia limpia que ya contenga la version 11.1.2:

```bash
git status --short
git log -1 --oneline
git am /ruta/0001-Close-Raspberry-interface-phase-11.1.3.patch
```

La referencia de desarrollo es:

```text
7e38381 Refine final Raspberry touch controls phase 11.1.2
```

Si la 11.1.2 se instalo mediante `git am`, el hash local puede ser diferente;
es correcto siempre que el ultimo commit tenga ese titulo y el arbol este
limpio.

Si `git status --short` muestra cambios locales, no aplique el parche hasta
guardarlos o confirmarlos.

## Verificacion visual en Raspberry

1. Abrir la ventana principal y generar suficientes eventos para desplazarse.
2. Confirmar que no queda una linea o canal de scrollbar entre la lista y `▲`.
3. Confirmar que `▲` y `▼` conservan un area tactil comoda con menor altura.
4. Abrir la configuracion del motor y verificar texto blanco legible en
   `ACTIVAR` y `GUARDAR`.
5. Mantener presionado cada boton y confirmar la inversion visible de color.
6. Confirmar que `ACTIVAR` selecciona la receta y que `GUARDAR` conserva su
   funcion original.

## Validacion automatizada

```bash
python -m unittest discover -s tests -p "test_*.py" -q
python -m compileall -q app core processing services tools ui vision tests
python scripts/validate_installation.py installations/worksurface/commissioning.json
```

Resultado esperado: 142 pruebas correctas y Worksurface `LISTA PARA CALIBRAR`.
