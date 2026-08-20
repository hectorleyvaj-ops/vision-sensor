# Guia de refinamiento 11.1.2 - Controles tactiles finales

## Alcance

Parche incremental sobre el refinamiento 11.1.1 (`0aeb4f2`). Atiende el ultimo
feedback visual de Raspberry antes de iniciar la industrializacion. No modifica
recetas, configuracion Worksurface, firmware ESP32, GPIO ni logica PLC.

## Cambios

- Los botones de minimizar y cerrar reducen cinco pixeles por lado respecto al
  objetivo tactil general.
- La lista de eventos oculta su scrollbar vertical nativa.
- Se agregan botones independientes `▲` y `▼`, anchos, con repeticion al
  mantenerlos presionados.
- Los controles de eventos cambian claramente a turquesa mientras se pulsan.
- Los botones inferiores de configuracion se presentan como `ESTACION` y
  `RECETA`, con ancho simetrico, texto explicito y contraste propio.
- `ESTACION` y `RECETA` muestran borde y fondo distintos durante la pulsacion.

## Aplicacion

```bash
git status --short
git log -1 --oneline
git am /ruta/0001-Refine-final-Raspberry-touch-controls-phase-11.1.2.patch
```

La base esperada es:

```text
0aeb4f2 Refine Raspberry UI and focus configuration phase 11.1.1
```

## Verificacion visual

1. Confirmar que minimizar y cerrar dejan mas aire vertical en la barra.
2. Generar suficientes eventos para permitir desplazamiento.
3. Pulsar `▲` y `▼`; cada pulsacion debe mover una entrada.
4. Mantener presionado; el desplazamiento debe repetirse.
5. Confirmar que no aparece la barra vertical angosta.
6. Confirmar texto completo y respuesta visual en `ESTACION` y `RECETA`.
7. Abrir ambos botones y comprobar que conservan su funcion original.

## Validacion automatizada

```bash
python -m unittest discover -s tests -p "test_*.py" -q
python -m compileall -q app core processing services tools ui vision tests
python scripts/validate_installation.py installations/worksurface/commissioning.json
```

Resultado esperado: 141 pruebas correctas y Worksurface `LISTA PARA CALIBRAR`.
