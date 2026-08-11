# Referencia de configuracion de estacion

El panel `SISTEMA` describe una instalacion fisica completa. No crea perfiles
ni cambia el codigo del motor.

| Grupo | Parametro | Para que sirve |
|---|---|---|
| Instalacion | ID / nombre | Identifica la estacion en logs y despliegues. |
| Recetas | Catalogo | Ruta al JSON con modelos, steps y herramientas. |
| Recetas | Migracion | Permite convertir catalogos anteriores con respaldo. |
| Camara | Dispositivo | Indice o ruta del dispositivo de captura. |
| Camara | Ancho / alto | Resolucion real solicitada a la camara. No es el tamano de pantalla. |
| Camara | FPS captura | Ritmo de adquisicion de frames. |
| Camara | FPS preview | Ritmo visual de la interfaz; puede ser menor para reducir carga. |
| Camara | Enfoque predeterminado | Modo inicial para recetas nuevas. |
| Control | Puerto / baudrate | Enlace fisico con ESP32 u otro controlador. |
| Control | Timeout serial | Espera maxima de una operacion de comunicacion. |
| Control | Reset al conectar | Reinicia el adaptador/controlador al abrir el puerto si aplica. |
| Control | Heartbeat | Comprueba que el enlace sigue vivo. |
| Control | Publicar READY | Informa si vision puede aceptar un trigger. |
| Mapeo | ID externo / receta | Traduce el modelo opaco del controlador a una receta. |
| Ejecucion | Exigir READY | Bloquea produccion sin controlador disponible. |
| Ejecucion | Exigir handshake | Bloquea produccion hasta negociar el protocolo. |
| Ejecucion | Exigir enfoque | Bloquea produccion si el foco no esta preparado. |
| Ejecucion | Edad de frame | Evita inspeccionar una imagen demasiado antigua. |
| Ejecucion | Asentamiento | Espera entre trigger y captura para que la pieza quede inmovil. |
| Ejecucion | Timeout inspeccion | Limite total desde trigger hasta decision de vision. |

`camera.width` y `camera.height` corresponden a la imagen capturada. No controlan
el tamano de la ventana ni la resolucion del monitor. La interfaz detecta el
area disponible automaticamente y selecciona un modo compacto, estandar o
amplio; no existe un parametro de monitor en `system.json`.

Todos los cambios de este panel se validan antes de escribirse, conservan un
respaldo `system.json.bak` y requieren reiniciar la aplicacion para reconstruir
camara, enlace serial y politicas de ejecucion.
