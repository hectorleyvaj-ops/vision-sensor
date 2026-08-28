# Hotfix 12.1 - Compatibilidad y comandos de mantenimiento

Este hotfix corrige los problemas encontrados durante la primera instalación
real en Raspberry Pi OS Trixie:

- selecciona automáticamente libdmtx0t64 o libdmtx0b según APT;
- permite ejecutar los comandos Python desde cualquier directorio;
- conserva finales de línea LF y permisos ejecutables en scripts Linux;
- coloca StartLimitIntervalSec y StartLimitBurst en la sección correcta de
  systemd;
- omite de forma limpia las variables gráficas que no existan;
- permite usar cualquier semilla válida de installations, además de generic.

## Aplicación

El parche se aplica sobre el commit Fase 12. Los JSON de configuración,
recetas, imágenes maestras y archivos .bak modificados por calibración no deben
agregarse al commit del hotfix.

Después de aplicar y confirmar el parche:

    sudo ./scripts/install_raspberry.sh --installation worksurface --seed worksurface --user "$USER"

El nuevo commit produce un release diferente. La semilla ya existente bajo
/var/lib/vision-sensor se conserva y sólo cambia el enlace
/opt/vision-sensor/current.

## Comportamiento del servicio

Restart=on-failure reinicia fallos anormales. Si el operador cierra la
aplicación normalmente, el estado pasa a stopped y systemd no la reinicia hasta
una orden manual o el siguiente inicio de sesión gráfica.

La ausencia de WAYLAND_DISPLAY no es un error cuando la sesión usa X11. El
lanzador importa únicamente las variables gráficas disponibles.
