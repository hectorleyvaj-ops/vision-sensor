# Guía de fase 12: despliegue industrial

Después de aplicar el parche, copia el proyecto a la Raspberry y ejecuta:

    sudo ./scripts/install_raspberry.sh --installation worksurface --seed worksurface --user "$USER"

El inicio automático ocurre al abrir la siguiente sesión gráfica del usuario.
La interfaz no se ejecuta como root.

## Mantenimiento

    ./scripts/vision_service.sh status
    ./scripts/vision_service.sh logs 120
    ./scripts/vision_service.sh stop
    ./scripts/vision_service.sh start

## Estados esperados

Sin cámara o ESP32, la interfaz debe abrir y la validación normal debe decir
LISTA PARA CALIBRAR. La validación estricta devuelve código 3 mientras no haya
recetas comisionadas. PAQUETE INVALIDO sólo indica una falla estructural.

## Recuperación

El código activo se puede revertir sin borrar datos:

    sudo ./scripts/rollback_raspberry.sh /opt/vision-sensor

Antes de cualquier cambio físico importante crea un backup. Consulta
docs/industrial_deployment.md para los comandos de backup, restauración,
diagnóstico y touchscreen.
