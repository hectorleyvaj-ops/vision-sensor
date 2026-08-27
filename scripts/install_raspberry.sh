#!/usr/bin/env bash
# Provision one Raspberry Pi OS Desktop station. Run only with sudo.
set -euo pipefail
if [[ "$EUID" -ne 0 ]]; then echo "Ejecuta este instalador con sudo." >&2; exit 1; fi

installation="vision-station"; seed="generic"; operator="$SUDO_USER"; prefix="/opt/vision-sensor"
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --installation) installation="$2"; shift 2 ;;
    --seed) seed="$2"; shift 2 ;;
    --user) operator="$2"; shift 2 ;;
    --prefix) prefix="$2"; shift 2 ;;
    *) echo "Opcion no reconocida: $1" >&2; exit 64 ;;
  esac
done
if [[ -z "$operator" || "$operator" == "root" ]]; then echo "Indica el usuario de escritorio con --user." >&2; exit 64; fi
if [[ "$seed" != "generic" && "$seed" != "worksurface" ]]; then echo "--seed debe ser generic o worksurface" >&2; exit 64; fi
if [[ "$(uname -m)" != armv7l && "$(dpkg --print-architecture)" != armhf ]]; then echo "Se requiere Raspberry Pi OS de 32 bits (armhf)." >&2; exit 65; fi

script_dir="$(cd "$(dirname "$0")" && pwd)"; release_root="$(cd "$script_dir/.." && pwd)"
version="$(git -C "$release_root" rev-parse --short HEAD 2>/dev/null || date -u +%Y%m%d%H%M%S)"
release="$prefix/releases/$version"; data_root="/var/lib/vision-sensor"
install_root="$data_root/installations/$installation"; runtime_root="$data_root/runtime/$installation"; env_file="/etc/vision-sensor/vision-sensor.env"
apt-get update
apt-get install -y python3-venv python3-pyqt5 python3-opencv python3-numpy libdmtx0b v4l-utils
install -d -m 0755 "$prefix/releases" "$data_root/installations" "$data_root/runtime" /etc/vision-sensor
if [[ ! -d "$release" ]]; then cp -a "$release_root" "$release"; find "$release" -name .git -type d -prune -exec rm -rf {} +; fi
python3 -m venv --system-site-packages "$release/.venv"
"$release/.venv/bin/pip" install --no-input -r "$release/requirements-rpi32.txt"
usermod -aG video,dialout "$operator"
"$release/.venv/bin/python" "$release/scripts/prepare_installation.py" --source-root "$release" --destination "$install_root" --seed "$seed" --installation-id "$installation"
install -d -o "$operator" -g "$operator" "$install_root" "$runtime_root"; chown -R "$operator:$operator" "$install_root" "$runtime_root"
if [[ ! -f "$env_file" ]]; then install -m 0644 "$release/deploy/vision-sensor.env.example" "$env_file"; fi
sed -i -e "s|^VISION_SYSTEM_CONFIG=.*|VISION_SYSTEM_CONFIG=$install_root/system.json|" -e "s|^VISION_DEPLOYMENT_RUNTIME=.*|VISION_DEPLOYMENT_RUNTIME=$runtime_root|" -e "s|^VISION_RELEASE_VERSION=.*|VISION_RELEASE_VERSION=$version|" "$env_file"
install -d -m 0755 "/home/$operator/.config/systemd/user"
sed -e "s|@CURRENT_RELEASE@|$prefix/current|g" -e "s|@ENVIRONMENT_FILE@|$env_file|g" "$release/deploy/systemd/vision-sensor.service.in" > "/home/$operator/.config/systemd/user/vision-sensor.service"
chown "$operator:$operator" "/home/$operator/.config/systemd/user/vision-sensor.service"
install -d -m 0755 "/home/$operator/.config/autostart"
sed "s|/opt/vision-sensor/current|$prefix/current|g" "$release/deploy/autostart/vision-sensor.desktop" > "/home/$operator/.config/autostart/vision-sensor.desktop"
chown "$operator:$operator" "/home/$operator/.config/autostart/vision-sensor.desktop"
previous=""; if [[ -L "$prefix/current" ]]; then previous="$(readlink -f "$prefix/current")"; fi
"$release/.venv/bin/python" "$release/scripts/switch_release.py" --prefix "$prefix" --installation "$installation" --target "$release"
echo "Instalacion lista. El autostart iniciara el servicio tras la proxima sesion grafica de $operator."
echo "Datos persistentes: $install_root"
