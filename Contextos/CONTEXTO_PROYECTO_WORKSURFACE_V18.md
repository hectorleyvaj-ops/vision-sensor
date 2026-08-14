# Contexto Worksurface V18 - Fase 11.1 comisionamiento seguro

**Fecha:** 2026-08-14

**Base:** fase 11 y hotfix de camara (`193e072`)

## 1. Contrato de producto

El software Python es un sensor de vision configurable. Su salida funcional es
una decision determinante `OK`, `NG` o `ERROR` asociada a un ciclo. No contiene
la secuencia general de prensa o maquina.

La ESP32 mantiene de forma separada:

- entradas y salidas fisicas;
- GPIO y polaridades;
- patrones de sensores;
- validacion fisica final;
- salida PLC;
- timeouts y recuperacion segura del controlador.

La fase 11.1 no agrega configuracion de I/O al motor Python ni modifica el
firmware Worksurface.

## 2. Primer arranque

El molde generico queda intencionalmente incompleto pero utilizable:

| Elemento | Estado inicial |
|---|---|
| Camara | Sin asignar |
| Puerto | Sin asignar |
| Recetas | Catalogo vacio |
| Modo | Configuracion |
| Produccion | Bloqueada |
| READY | `0` |

`installation.commissioning_mode=true` permite estos valores sin convertirlos
en configuracion productiva. Al iniciar se abre el editor de estacion.

## 3. Descubrimiento

`services/hardware_discovery.py` crea un inventario de endpoints:

- camaras Windows por indice y backend;
- camaras Linux con preferencia por `/dev/v4l/by-id`;
- puertos seriales con identidad USB disponible;
- verificacion de controladores por `HELLO_ACK` compatible;
- reconocimiento de la camara y controlador activos sin reabrirlos.

La busqueda corre en un hilo Python y entrega resultados a Qt mediante una
senal. No cambia campos hasta que el operador selecciona una opcion.

## 4. Neutralidad del motor

El catalogo generico ya no incluye MODELO_A ni un codigo DataMatrix concreto.
Las recetas nuevas comienzan vacias y no comisionadas. Tampoco se crea una
receta `DEFAULT` al consultar un catalogo vacio.

`camera.default_focus_mode` ahora alimenta realmente la configuracion inicial
de recetas nuevas.

Todo dato A/B/C y todo recurso fisico Worksurface permanece en
`installations/worksurface/` y `ESP32/FSM/`.

## 5. Seguridad

El modo de configuracion se comprueba antes de cualquier otra condicion de
READY. Mientras permanezca activo:

- `READY=1` es imposible;
- no se acepta trigger;
- no se ejecuta la FSM;
- no se emite una aprobacion de vision utilizable;
- la interfaz y la configuracion siguen disponibles.

Adicionalmente, produccion abre exactamente la camara guardada. En Linux se
retiro el fallback silencioso hacia `/dev/video0` a `/dev/video3`.

## 6. Persistencia

La seleccion actualiza solamente el formulario. **VALIDAR Y GUARDAR** conserva
el guardado atomico y el respaldo `.bak`. La sesion pasa a reinicio requerido.

El modo de configuracion debe retirarse explicitamente y solo puede guardarse
sin camara o puerto mientras permanece activado.

## 7. Pruebas

La suite contiene 133 pruebas. Las diez nuevas verifican:

- configuracion generica sin endpoints;
- rechazo de endpoints vacios fuera de comisionamiento;
- salida valida del modo al asignar hardware;
- inventario y apertura de camara simulada;
- metadatos seriales;
- handshake de identidad;
- no reabrir el controlador activo;
- receta neutral y enfoque predeterminado;
- ausencia de datos de producto en el molde;
- conexion del flujo visual y bloqueo de primer arranque.

La instalacion Worksurface conserva el resultado `LISTA PARA CALIBRAR`.

## 8. Puerta hacia fase 12

Antes de aprobar fase 12 se requiere feedback fisico de:

- presentacion de listas en Windows;
- seleccion y reinicio;
- inventario en Raspberry;
- legibilidad en 800x480;
- comportamiento con camara/ESP32 desconectadas;
- posibles ajustes esteticos y de vocabulario.

Fase 12 no debe comenzar hasta cerrar esos hallazgos de interfaz.
