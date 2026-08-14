# Guia fase 11.1 - Primer arranque y descubrimiento de hardware

## 1. Objetivo

La fase 11.1 convierte el molde generico en un sensor de vision instalable que
puede abrirse sin camara, controlador o recetas. En ese estado permite
configurar el motor, pero no puede producir ni aceptar triggers.

La separacion de responsabilidades permanece fija:

- el motor de vision ejecuta recetas y entrega `OK`, `NG` o `ERROR`;
- la ESP32 conserva GPIO, polaridades, sensores, actuadores y secuencia de la
  maquina;
- `vision_controller_v1` es el contrato entre ambos;
- la busqueda solo identifica endpoints y nunca modifica firmware o I/O.

## 2. Aplicar el parche

El parche es incremental y requiere fase 11 mas el hotfix de camara, cuyo
ultimo commit base es `193e072`.

```bash
git status --short
git am /ruta/0001-Add-safe-first-run-and-hardware-discovery-phase-11.1.patch
```

No se modifican `installations/worksurface/recipes.json`, imagenes maestras,
firmware ESP32 ni configuracion Worksurface. Solo se neutraliza el molde
generico `config/system.json` y su catalogo base.

## 3. Primer arranque generico

Ejecutar sin seleccionar una instalacion existente:

```bash
python main.py
```

El molde generico inicia con:

```text
camera.device = sin asignar
controller.ports = vacio
recipes = vacio
commissioning_mode = true
READY = 0
```

La aplicacion abre automaticamente la configuracion de la estacion. La busqueda
se ejecuta en segundo plano y no bloquea la interfaz.

## 4. Camaras

La lista muestra dispositivo, disponibilidad, backend y formato observado.

- Windows prueba indices `0` a `5` con DSHOW, MSMF y AUTO.
- Linux prioriza rutas persistentes `/dev/v4l/by-id/*`.
- Si no existen rutas persistentes, muestra `/dev/video*`.
- La camara activa no se vuelve a abrir durante el inventario.
- Seleccionar una opcion copia el endpoint al campo editable.
- Guardar no cambia la sesion activa; se aplica al reiniciar.

En produccion solo se abre el endpoint guardado. El runtime no sustituye una
camara ausente por otro indice silenciosamente.

## 5. Controladores seriales

La lista usa `pyserial` para mostrar los puertos del sistema. Cuando el puerto
no pertenece a la sesion activa, intenta un `HELLO/HELLO_ACK` de identidad con
el baudrate visible en la pantalla.

Estados posibles:

- controlador compatible verificado;
- puerto detectado sin respuesta compatible;
- puerto ocupado o no disponible;
- controlador activo y sincronizado;
- puerto configurado que ya no esta presente.

El puerto activo no se abre por segunda vez. En Linux se prefiere
`/dev/serial/by-id/*` cuando existe una ruta persistente equivalente.

La verificacion no envia configuraciones, resultados ni comandos de I/O. Un
adaptador serial desconocido puede abrirse brevemente durante la busqueda; por
eso el inventario se ejecuta desde configuracion y no durante produccion.

## 6. Recetas neutrales

El catalogo generico comienza vacio. Ya no se crea `DEFAULT` ni se agrega
DataMatrix automaticamente.

Una receta nueva:

- recibe ID estable;
- comienza sin comisionar;
- no contiene pasos;
- usa `camera.default_focus_mode`;
- permanece bloqueada hasta agregar y validar herramientas.

Worksurface conserva MODELO_A, MODELO_B, MODELO_C y sus recursos dentro de su
paquete de instalacion.

## 7. Flujo recomendado

1. Iniciar en modo de configuracion.
2. Elegir camara y controlador detectados.
3. Ajustar baudrate, resolucion, FPS, timeouts y politicas.
4. Guardar y reiniciar para activar el hardware.
5. Crear recetas, pasos, ROI, recursos y enfoque.
6. Mapear IDs externos del controlador a las recetas.
7. Validar y comisionar cada receta.
8. Desmarcar **Modo de configuracion**.
9. Guardar y reiniciar.
10. Confirmar handshake, frame fresco, receta valida y `READY=1`.

Para recetas que necesitan capturar ROI o imagenes maestras son necesarios dos
reinicios: uno para activar la camara elegida y otro para salir del modo de
configuracion. Esto evita recargar drivers o hilos a mitad de una edicion.

## 8. Prueba sobre Worksurface

Ejecutar con su configuracion habitual:

```cmd
set VISION_SYSTEM_CONFIG=installations\worksurface\system.json
python main.py
```

Abrir **CONFIGURAR ESTACION > ESTACION** y revisar:

1. La camara activa aparece como activa o disponible.
2. COM7 aparece como controlador activo si ya existe handshake.
3. **BUSCAR HARDWARE** no cambia los valores guardados por si solo.
4. Elegir otra opcion solo la propone y solicita reiniciar.
5. Cancelar no modifica `system.json`.
6. Guardar crea `system.json.bak` y mantiene `READY=0` hasta reiniciar.
7. Desconectar camara o ESP32 mantiene acceso a configuracion.
8. Ningun clic en la interfaz inicia un ciclo productivo.

## 9. Validacion automatica

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q app core processing services tools ui vision tests
python scripts/validate_installation.py
```

Resultado esperado:

```text
Ran 133 tests
OK
Resultado: LISTA PARA CALIBRAR
```

La revision visual y el inventario real de dispositivos deben probarse en
Windows y Raspberry. La suite automatizada usa hardware simulado.
