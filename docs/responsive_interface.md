# Interfaz responsiva y deteccion de pantalla

La interfaz no toma el tamano del monitor desde `system.json`. El motor consulta
el area disponible de la pantalla activa al iniciar y cuando la ventana cambia
de monitor. La resolucion de captura de la camara permanece independiente.

## Perfiles calculados

| Modo | Regla principal | Comportamiento |
|---|---|---|
| `compact` | ancho <= 600 o alto <= 360 | Pensado para 480x320: margenes reducidos, log compacto, controles tactiles y dialogos a pantalla completa. |
| `standard` | resoluciones intermedias | Conserva una composicion cercana a 800x480 sin limites fijos. |
| `wide` | ancho >= 1200 y alto >= 700 | Aumenta tipografia, separacion y area de video sin expandir la ventana indefinidamente. |

`core/display_profile.py` contiene la politica pura y comprobable.
`ui/responsive.py` aplica esa politica a las ventanas Qt y elimina en tiempo de
ejecucion los limites rigidos heredados de los archivos generados por Qt
Designer.

## Criterios

- el area de video siempre puede contraerse y crecer;
- los botones principales conservan un objetivo tactil minimo;
- los editores modales nunca exceden la pantalla disponible;
- los formularios largos usan desplazamiento;
- en modo compacto se ocultan etiquetas redundantes y el log de configuracion;
- cambiar de monitor vuelve a calcular el layout de la ventana principal;
- `camera.width` y `camera.height` nunca modifican el layout.

## Limite de validacion

Las reglas y el codigo pueden probarse sin hardware. La aprobacion visual final
requiere ejecutar la aplicacion con PySide6 en 480x320 real, revisar el tactil y
confirmar que el escalado del sistema operativo sea 100 %. Esa prueba puede
producir ajustes esteticos, pero no debe cambiar el contrato de configuracion.
