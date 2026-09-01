# Hotfix Fase 12.3: mapeo configurable y arranque recuperable

## Objetivo

Separar el orden visual de las recetas del mapeo recibido por el controlador.
`controller.model_map` es la fuente de verdad para traducir IDs externos a
recetas y el orden de sus filas no establece prioridad.

El manifiesto admite dos politicas:

- `exact_model_map: false`: los IDs externos son configurables. La validacion
  solo exige que todas las recetas requeridas tengan algun ID asignado.
- `exact_model_map: true`: conserva el contrato estricto para instalaciones
  que deban bloquear IDs y recetas concretas.

Una discrepancia de comisionamiento ya no impide abrir la interfaz. El runtime
arranca en estado degradado y bloquea `READY` hasta corregir la estacion.

## Aplicar en el repositorio de desarrollo

```bash
git status --short
git apply --check Patchs/fase12_3_model_map_configurable.patch
git apply Patchs/fase12_3_model_map_configurable.patch
python -m unittest discover -s tests -p "test_*.py"
git add app installations scripts tests ui Guias Contextos
git commit -m "Make controller model mapping configurable"
git push origin feature/industrial-installation-phase12
```

## Actualizar Raspberry

```bash
cd /home/worksurface/calibration/vision-sensor
git status --short
git pull --ff-only
python3 -m unittest discover -s tests -p "test_*.py"
sudo ./scripts/update_raspberry.sh "$(pwd)" /opt/vision-sensor
```

No se debe restaurar el `stash` de calibracion dentro del repositorio antes de
crear el release.

## Migrar la politica de la instalacion persistente

El actualizador conserva `/var/lib`, por lo que la instalacion existente debe
cambiarse una sola vez a politica configurable:

```bash
/opt/vision-sensor/current/.venv/bin/python \
  /opt/vision-sensor/current/scripts/set_model_map_policy.py \
  /var/lib/vision-sensor/installations/worksurface/commissioning.json \
  configurable
```

El comando crea `commissioning.json.bak` antes de escribir.

## Validar y reactivar servicio

```bash
/opt/vision-sensor/current/.venv/bin/python \
  /opt/vision-sensor/current/scripts/validate_installation.py \
  /var/lib/vision-sensor/installations/worksurface/commissioning.json

systemctl --user daemon-reload
systemctl --user reset-failed vision-sensor.service
systemctl --user enable --now vision-sensor.service
systemctl --user status vision-sensor.service --full --no-pager
journalctl --user -u vision-sensor.service -n 160 --no-pager -o cat
```

Si faltara una receta requerida en los valores de `controller.model_map`, la
interfaz abrira para corregir el mapeo, pero produccion permanecera en
`NOT_READY`.

## Volver a politica exacta

Solo para una estacion que deba fijar IDs externos especificos:

```bash
/opt/vision-sensor/current/.venv/bin/python \
  /opt/vision-sensor/current/scripts/set_model_map_policy.py \
  /var/lib/vision-sensor/installations/worksurface/commissioning.json \
  exact
```
