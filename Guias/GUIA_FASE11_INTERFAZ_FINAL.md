# Guia fase 11 - Interfaz final

## 1. Alcance

Esta fase termina la interfaz de operador y unifica la apariencia de los
editores. No modifica recetas Worksurface, firmware, protocolo, pines ni
salidas PLC.

Cambios principales:

- nombre de instalacion obtenido desde `system.json`;
- estado y causa visibles sin depender del color;
- receta activa y resultado final claramente identificados;
- pantalla 800x480 con controles de al menos 42 px;
- nombres legibles para los modos de enfoque;
- configuracion con resumen de receta;
- confirmacion antes de borrar;
- recursos borrados archivados de forma recuperable;
- indicador visual sin funcion de trigger manual.

El touch se diagnosticara y reparara en fase 12, junto con el despliegue
industrial. Aqui se preparan tamaños y navegacion adecuados.

## 2. Aplicar el parche

Desde una copia limpia que ya contenga fase 10:

```bash
git status --short
git switch -c feature/final-interface-phase11
git am /ruta/0001-Add-final-configurable-operator-interface-phase-11.patch
```

## 3. Validacion automatica

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q app core processing services tools ui vision tests
python scripts/validate_installation.py
```

Resultado esperado:

```text
Ran 118 tests
OK
Resultado: LISTA PARA CALIBRAR
```

`LISTA PARA CALIBRAR` continua siendo correcto mientras las recetas sean
preliminares.

## 4. Revision visual en PC

Ejecutar con la instalacion activa:

```cmd
set VISION_SYSTEM_CONFIG=installations\worksurface\system.json
python main.py
```

Verificar:

1. El titulo muestra `Worksurface`, no `Summit USB`.
2. La vista de camara ocupa el panel principal.
3. La receta activa aparece aunque su nombre no sea A/B/C.
4. El estado incluye encabezado y explicacion.
5. WARNING o CRITICAL tienen prioridad sobre un OK anterior.
6. El indicador no inicia un ciclo al hacer clic.
7. CONFIGURAR ESTACION se bloquea durante una inspeccion.
8. Los eventos recientes permanecen visibles sin dominar la pantalla.
9. Los dialogos permiten scroll y no cortan sus botones.
10. Los modos de enfoque se muestran en español.

## 5. Revision en Raspberry 800x480

Esta revision es obligatoria antes de cerrar visualmente la fase:

1. Iniciar a pantalla completa.
2. Confirmar que no haya superposiciones.
3. Abrir configuracion, estacion, propiedades, enfoque y un paso.
4. Confirmar que todos los botones sean visibles.
5. Probar desplazamiento con mouse o teclado si el touch aun falla.
6. Tomar capturas de pantalla principal, configuracion y enfoque.
7. Registrar la fuente y resolucion reales si el texto se corta.

No cambiar `system.json` para corregir el tamaño de la pantalla. La geometria
pertenece a `core/display_profile.py`.

## 6. Borrado recuperable

Al borrar una receta o paso se solicita confirmacion. Los recursos se mueven a:

```text
runtime/deleted_resources/
```

No se versionan en Git. Si el borrado fue accidental, detener la aplicacion y
restaurar la carpeta antes de seguir editando. La automatizacion formal de
backup y restauracion pertenece a fase 12.

## 7. Siguiente fase

Fase 12 incluira:

- instalacion encapsulada;
- servicio `systemd`;
- inicio y cierre seguros;
- actualizacion, backup y rollback;
- diagnostico y correccion del touch en Linux;
- procedimientos operativos de recuperacion.

Fase 13 ejecutara la aceptacion integral, calibracion final, prueba paralela y
corte productivo reversible.
