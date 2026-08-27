# Contexto Worksurface V23 - Fase 12 implementada

La fase 12 convierte el motor en una instalación mantenible para Raspberry Pi
OS Desktop de 32 bits. No modifica firmware ESP32, PLC, pines, polaridades,
calibraciones físicas ni la aceptación estadística de producción.

## Decisiones implementadas

- El código se instala como releases inmutables bajo /opt/vision-sensor.
- Configuración, recetas, recursos e imágenes maestras se copian una sola vez
  a /var/lib/vision-sensor y sobreviven actualizaciones y rollback.
- La interfaz Qt corre como servicio de usuario. Un lanzador de autostart
  importa la sesión gráfica Wayland/X11 antes de iniciar el servicio.
- El servicio abre en estado degradado cuando falta cámara o ESP32; esto no
  autoriza producción y se conserva READY=0.
- El estado técnico se publica atómicamente en health.json y no se confunde
  con el READY enviado al controlador.
- Se incluyen preflight, diagnóstico, backup con checksums, restauración y
  rollback de código.
- El touchscreen usa perfiles de matriz libinput y reglas udev con
  identificadores estables; ninguna matriz se aplica sin selección explícita.

## Política de recetas configurable

El motor no impone DataMatrix, histograma, foco calibrado ni cantidad de pasos
por MODELO_A, MODELO_B o MODELO_C. El manifest mantiene únicamente el mapeo
externo propio de la instalación. Una receta no comisionada puede estar vacía,
incompleta o usar las herramientas que el operador decida; el resultado normal
es LISTA PARA CALIBRAR. Una receta declarada comisionada sí se valida como
ejecutable antes de permitir producción.

## Pendiente de fase 13

Seleccionar hardware definitivo, ajustar recetas con piezas reales, capturar
recursos maestros, comisionar cada receta y ejecutar las pruebas de aceptación
industrial. La fase 12 debe probarse físicamente en la Raspberry antes de
considerarse cerrada.
