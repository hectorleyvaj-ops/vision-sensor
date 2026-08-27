# Despliegue industrial en Raspberry Pi

Esta fase instala el motor de visión sin mezclar el código con los datos que
el operador modifica. El programa gráfico siempre corre con el usuario de
escritorio, nunca como root.

## Instalación

En una copia limpia del proyecto, desde Raspberry Pi OS Desktop de 32 bits:

    sudo ./scripts/install_raspberry.sh --installation worksurface --seed worksurface --user "$USER"
    systemctl --user enable --now vision-sensor.service

La sesión gráfica debe iniciar automáticamente para ese usuario. El instalador
no cambia esa opción ni contraseñas: actívala explícitamente desde raspi-config
si todavía no está configurada.

Código: /opt/vision-sensor/current. Datos configurables:
/var/lib/vision-sensor/installations/worksurface. Una actualización no
sobrescribe recetas, imágenes maestras, configuración ni trazabilidad.

## Operación

    ./scripts/vision_service.sh status
    ./scripts/vision_service.sh logs 120
    ./scripts/vision_service.sh stop
    ./scripts/vision_service.sh start

Para obtener un diagnóstico sin modificar el equipo:

    python3 scripts/diagnose_deployment.py --config /var/lib/vision-sensor/installations/worksurface/system.json --runtime-health /var/lib/vision-sensor/runtime/worksurface/health.json

## Actualización, rollback y respaldo

    sudo ./scripts/update_raspberry.sh /ruta/nueva/version /opt/vision-sensor
    sudo ./scripts/rollback_raspberry.sh /opt/vision-sensor
    python3 scripts/backup_installation.py --source /var/lib/vision-sensor/installations/worksurface --destination /var/backups/vision-sensor/worksurface --installation worksurface

El rollback cambia únicamente el código. La restauración valida checksums antes
de sustituir una instalación.

## Touchscreen

Primero identifica por teclado, SSH o VNC los IDs estables del touch. Genera la
regla sin escribirla para revisarla:

    python3 scripts/configure_touchscreen.py --vendor 1234 --product abcd --profile rotate-180

Solo después de confirmar, aplícala con --apply. La recuperación es:

    sudo python3 scripts/configure_touchscreen.py --rollback

Reinicia o desconecta/reconecta el dispositivo después de modificar reglas
udev. No se usan nombres variables como /dev/input/eventN.
