# Guia de refinamiento 11.1.1 - Interfaz Raspberry y enfoque

## 1. Alcance

Este parche es incremental sobre la fase 11.1 limpia (`64fe994`). Corrige la
presentacion PyQt5 observada en Raspberry, conserva el arranque seguro sin
hardware y aclara el contrato de enfoque. No cambia recetas Worksurface,
firmware ESP32, GPIO, polaridades ni logica PLC.

## 2. Aplicacion

Con el arbol limpio y la fase 11.1 ya aplicada:

```bash
git status --short
git am /ruta/0001-Refine-Raspberry-UI-and-focus-configuration-phase-11.1.1.patch
```

Si `git status --short` muestra cambios propios, guardarlos en un commit antes
de aplicar el parche.

## 3. Cambios de interfaz

- El tema se instala tambien a nivel de `QApplication`, para que PyQt5 aplique
  colores coherentes a ventanas superiores y `QMessageBox`.
- Los textos y botones de `QMessageBox` tienen reglas explicitas de contraste.
- Ya no se limpia el estilo de los botones despues de aplicar el tema.
- `ESTACION`, `PROPIEDADES`, `GUARDAR` y `VOLVER` tienen anchos y alturas
  tactiles acotados.
- Los editores secundarios se ejecutan como modales de aplicacion.
- En Linux pasan a pantalla completa despues de que `exec()` inicia su bucle;
  esto evita que PyQt5 descarte el estado y bloquea la ventana inferior.
- Las barras de desplazamiento conservan una zona tactil ancha y no muestran
  botones de flecha estrechos.

## 4. `v4l2-ctl` no es el driver

`v4l2-ctl` es una utilidad de diagnostico y control proporcionada por el
paquete `v4l-utils`. La camara puede entregar video mediante el driver V4L2 y,
aun asi, faltar este ejecutable. En ese caso solo queda deshabilitado el control
avanzado de enfoque.

Instalacion y comprobacion:

```bash
sudo apt update
sudo apt install -y v4l-utils
which v4l2-ctl
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-ctrls
```

Usar en el ultimo comando el endpoint seleccionado en la estacion. Para los
modos por receta o fijo, la lista debe incluir `focus_absolute`. Si no aparece,
la camara o ese endpoint no permiten control manual; no se corrige instalando
otro driver al azar.

## 5. Modos de enfoque

### Automatico por receta (recomendado)

1. El operador selecciona una ROI con detalle relevante o usa el frame entero.
2. **BUSCAR MEJOR ENFOQUE** recorre el rango `focus_absolute` en tres barridos:
   grueso, fino y micro.
3. Para cada valor calcula la varianza del Laplaciano en varios frames y
   compara la mediana para reducir ruido.
4. Guarda el mejor valor, la mediana, el pico y un umbral recomendado del 65 %
   de la mediana final.
5. Antes del primer ciclo aplica y verifica el valor. Si el detalle queda bajo
   el umbral, puede recalibrar automaticamente.

El valor no se decide por nombre de receta ni por el codigo DataMatrix: se
calcula con la imagen fisica y queda almacenado dentro de esa receta.

### Valor fijo definido por el operador

El operador escribe directamente `focus_absolute`. Al guardar se aplica ese
valor sin barrido, sin puntuacion de nitidez y sin reenfoque automatico. Sirve
cuando la distancia y el lente ya estan caracterizados o cuando se desea un
valor impuesto externamente.

### Autofoco continuo

Se deja a la camara ajustar el lente continuamente. No existe un valor fijo por
receta y puede variar durante la inspeccion.

### Sin gestion de enfoque

El motor no modifica controles de enfoque. Es apropiado para lentes mecanicos
fijos o camaras sin `focus_absolute`.

## 6. Prueba en Raspberry

```bash
export VISION_QT_API=pyqt5
export VISION_SYSTEM_CONFIG=installations/worksurface/system.json
python main.py
```

Comprobar:

1. Texto claro y botones tematicos en la configuracion principal.
2. `QMessageBox` legible.
3. Estacion, propiedades, enfoque y editores ocupan la pantalla y bloquean la
   ventana inferior.
4. La ausencia de `v4l2-ctl` menciona `v4l-utils`, no un driver faltante.
5. El modo fijo muestra un campo numerico y oculta la busqueda automatica.
6. El modo por receta muestra la ROI y **BUSCAR MEJOR ENFOQUE**.
7. Una falla de camara o foco mantiene accesible configuracion, con produccion
   y triggers bloqueados.

## 7. Validacion automatica

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q app core processing services tools ui vision tests
python scripts/validate_installation.py installations/worksurface/commissioning.json
```

La validacion fisica de color, tacto, pantalla completa y controles V4L2 sigue
requiriendo la Raspberry real.
