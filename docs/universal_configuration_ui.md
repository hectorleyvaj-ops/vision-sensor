# Interfaz de configuracion universal

La ventana de configuracion sigue editando una sola aplicacion y una sola
instalacion. Los botones nuevos no activan perfiles ni agregan logica de una
maquina concreta.

La geometria de la interfaz tampoco pertenece a la configuracion de estacion.
Se calcula desde la pantalla activa mediante los modos `compact`, `standard` y
`wide`; consulte `docs/responsive_interface.md`.

## Sistema

`ESTACION` abre un editor por pestanas para:

- identificador y nombre de la instalacion;
- archivo de recetas y migracion automatica;
- dispositivo, resolucion, FPS y enfoque predeterminado de la camara;
- puertos por plataforma, baudrate, timeout y politicas del enlace;
- mapa entre identificadores externos y nombres de receta;
- politicas de disponibilidad, tiempo de asentamiento y timeout global de
  inspeccion.

El transporte `serial` y el protocolo `vision_controller_v1` se muestran como
contrato fijo y no pueden cambiarse desde la interfaz. Antes de guardar se
valida la estructura completa y que cada valor de `model_map` corresponda a una
receta del catalogo indicado. El guardado es atomico y conserva
`system.json.bak`.

Cambiar esta configuracion deja el motor en `NOT_READY` hasta reiniciar. Esto
evita que el archivo en disco describa una camara o controlador mientras la
sesion activa sigue usando los valores anteriores.

## Receta

`PROPIEDADES` permite revisar el ID interno y cambiar el estado de
comisionamiento.
Una receta solo puede marcarse como comisionada cuando:

- tiene al menos un step habilitado;
- todos sus IDs son unicos;
- sus herramientas estan registradas;
- sus parametros obligatorios estan completos;
- sus condiciones son validas;
- las herramientas DataMatrix tienen codigo esperado y ROI;
- las herramientas de histograma tienen imagenes maestras.

Desmarcar el comisionamiento siempre es posible y bloquea inmediatamente la
produccion con esa receta.

## Pasos y condiciones

Al agregar o editar una herramienta se separan dos grupos:

- politica del paso: `id`, `enabled`, `required` y `condition`;
- parametros propios de la herramienta, definidos en su clase y publicados por
  `ToolRegistry`.

La condicion se edita como JSON para conservar todo el lenguaje declarativo,
incluyendo condiciones anidadas `all`, `any` y `not`. Una condicion
`step_success` solo puede depender de un step anterior; las referencias a si
mismo, a pasos posteriores o a IDs inexistentes se rechazan al guardar.

Ejemplos:

```json
{"type": "always"}
```

```json
{
  "type": "step_success",
  "step_id": "code_1",
  "equals": true
}
```

```json
{
  "type": "context_equals",
  "path": "model",
  "value": "EXTERNAL_MODEL_ID"
}
```

## Incorporado en la fase 4

- ROI unica `[x1, y1, x2, y2]` para enfoque y herramientas;
- migracion de ROI heredadas al esquema de recetas v3;
- resultados `PASS`, `FAIL`, `ERROR` y `TIMEOUT`;
- comparacion DataMatrix `exact` o `prefix` y votos por intento;
- cancelacion cooperativa y timeout global de inspeccion.

## Interfaz final

La pantalla principal obtiene el nombre de la instalacion desde `system.json`,
muestra receta activa, estado, causa y resultado con texto, y mantiene el
trigger bajo autoridad del controlador. La configuracion usa objetivos tactiles
y archiva recursos retirados en `runtime/deleted_resources/`.

Consulte `docs/final_operator_interface.md` para el contrato visual completo.

## Fuera del alcance de la interfaz

- no se agregan recetas, numeros de parte ni sensores de Worksurface;
- no se crea ni modifica firmware ESP32 o PLC;
- no se recargan en caliente camara, serial o runtime;
- no se corrige desde Qt la calibracion del dispositivo touch de Linux;
- no se instala todavia el servicio de autoarranque o rollback.
