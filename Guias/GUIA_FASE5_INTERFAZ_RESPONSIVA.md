# Guia de aplicacion - Fase 5: interfaz responsiva

## Alcance

Esta fase detecta el area disponible del monitor y adapta la interfaz principal,
la configuracion, los dialogos, el editor de herramientas y el enfoque. No
agrega perfiles de producto, recetas Worksurface, firmware ni parametros de
pantalla a `system.json`.

El parche no modifica `config/system.json`.

## 1. Preparar la rama

Desde CMD, en la raiz del repositorio que ya contiene la fase 4:

```cmd
git status --short
git branch --show-current
git log -3 --oneline
```

El primer comando no debe mostrar cambios. Cree una rama nueva:

```cmd
git switch -c feature/universal-responsive-ui-phase5
```

## 2. Comprobar y aplicar

```cmd
git apply --check "C:\ruta\universal_responsive_ui_phase5.patch"
git apply --index "C:\ruta\universal_responsive_ui_phase5.patch"
```

Si `--check` no imprime nada, la comprobacion fue correcta. No use
`--exclude=config/system.json`: este parche no contiene ese archivo.

## 3. Validacion automatica

```cmd
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q app core processing services tools ui vision tests
git diff --cached --check
```

Resultado esperado:

```text
Ran 47 tests
OK
```

## 4. Prueba visual en PC

Active el entorno que ya usa el proyecto y ejecute:

```cmd
python main.py
```

Compruebe:

1. La ventana no queda limitada a 800x480 en un monitor grande.
2. Video, modelo, boton CONFIGURACION, indicador y log no se superponen.
3. SISTEMA abre sus cuatro pestanas y permite desplazarse.
4. RECETA, FOCUS CONFIG y el editor de herramientas caben en pantalla.
5. Los campos Ancho de captura y Alto de captura no cambian el tamano de la
   ventana.
6. Guardar sistema conserva `system.json.bak` y deja el motor en NOT_READY
   hasta reiniciar.

No es necesario conectar la maquina para revisar geometria. Si la aplicacion no
puede iniciar por una camara o puerto inexistente, registre el error: la fase de
diagnostico de inicio aun esta pendiente y se abordara despues.

## 5. Prueba obligatoria en Raspberry

En la pantalla fisica de 5 pulgadas:

1. Confirme la resolucion real del monitor con:

```bash
xrandr --current
```

2. Ejecute la aplicacion con escalado del escritorio al 100 %.
3. Anote en el log la linea `[UI] Pantalla activa: ANCHOxALTO (modo)`.
4. Abra todas las pantallas y toque cada control principal.
5. Compruebe que ningun boton queda fuera del borde y que los formularios
   largos desplazan correctamente.
6. Tome capturas de ventana principal, SISTEMA y un editor de herramienta.

Para 480x320 se espera el modo `compact`. Para 800x480 se espera `standard` y
Linux conserva la presentacion de kiosco a pantalla completa.

## 6. Commit

Despues de aprobar las pruebas:

```cmd
git status
git diff --cached --stat
git commit -m "Add responsive display adaptation"
git push -u origin feature/universal-responsive-ui-phase5
```

## 7. Si el parche no aplica

No borre archivos ni reconstruya el indice automaticamente. Comparta la salida
de:

```cmd
git status --short
git branch --show-current
git log -4 --oneline
git apply --check "C:\ruta\universal_responsive_ui_phase5.patch"
```

Si aparece otra vez `bad signature` o `index file corrupt`, detenga la aplicacion
y Git antes de reparar el indice. Ese problema pertenece al indice local, no a
este parche.

## 8. Criterio de cierre

El codigo de fase 5 esta completo cuando pasan las 47 pruebas. La fase se cierra
operativamente solo despues de aprobar visualmente PC y Raspberry. Los ajustes
esteticos que surjan deben conservar `core/display_profile.py` como unica fuente
de reglas, evitando nuevos tamanos dispersos por plataforma.
