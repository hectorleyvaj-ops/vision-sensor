# Interfaz final de operador

## Objetivo

La pantalla principal presenta el estado operativo sin exigir que el usuario
interprete colores, logs o nombres internos. La instalacion sigue siendo un
dato de `system.json`; no existe texto Worksurface, A/B/C ni Summit dentro del
contrato visual generico.

## Jerarquia de la pantalla

1. instalacion activa, obtenida de `installation.name`;
2. vista de inspeccion con ROI de la receta;
3. receta activa;
4. estado textual y causa;
5. indicador de resultado;
6. eventos recientes;
7. acceso a configuracion.

El indicador ya no inicia ciclos con el mouse o touch. El controlador conserva
la autoridad y debe enviar un `TRIGGER` valido. Esto evita que un elemento
visual omita el contexto de ciclo, modelo o seguridad.

## Estados visibles

| Nivel | Encabezado | Uso |
|---|---|---|
| `ready` | LISTO PARA INSPECCION | Espera un trigger del controlador |
| `working` | INSPECCIONANDO | Existe un ciclo activo |
| `ok` | RESULTADO OK | Resultado final aprobado |
| `ng` | RESULTADO NG | Resultado final rechazado |
| `warning` | SISTEMA NO LISTO | Calibracion o condicion recuperable |
| `critical` | ATENCION REQUERIDA | Falla de infraestructura o ciclo |

La prioridad continua siendo seguridad, luego ciclo y finalmente resultado. Un
OK retenido nunca oculta una perdida serial o un bloqueo de diagnostico.

## Adaptacion de pantalla

`core/display_profile.py` conserva una sola politica para `compact`, `standard`
y `wide`. En 800x480 se usan objetivos tactiles de al menos 42 px, indicador de
72 px y una franja reducida de eventos. Los dialogos largos usan scroll y los
botones de configuracion ya no conservan el maximo heredado de 30 px.

La reparacion electrica o de mapeo del touch no pertenece a Qt ni a las recetas.
Se realizara en fase 12 sobre el dispositivo de entrada de Linux. Esta fase
solo deja los controles con dimensiones aptas para tocar.

## Configuracion final

La pantalla de configuracion distingue:

- recetas y su estado activa/inactiva;
- cantidad de pasos habilitados;
- calibracion o comisionamiento;
- propiedades de receta;
- estacion, camara, controlador, mapeos y runtime;
- enfoque con nombres legibles, conservando IDs estables en JSON.

Los botones de borrado solicitan confirmacion. Los recursos retirados se mueven
a `runtime/deleted_resources/` en vez de eliminarse definitivamente. El
catalogo JSON conserva sus propias escrituras atomicas y respaldos.

## Limites

- La interfaz no cambia pines, polaridades ni sensores del firmware.
- El protocolo continua siendo `vision_controller_v1`.
- Guardar configuracion de estacion requiere reiniciar la aplicacion.
- La apariencia debe revisarse en la Raspberry real porque las fuentes y el
  servidor grafico pueden variar respecto de Windows.
