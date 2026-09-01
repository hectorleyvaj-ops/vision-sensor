#!/usr/bin/env bash
# Single entry point for systemd and a manual graphical start.
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
release_root="$(cd "$script_dir/.." && pwd)"
cd "$release_root"
VISION_SYSTEM_CONFIG="${VISION_SYSTEM_CONFIG:-config/system.json}"
VISION_DEPLOYMENT_RUNTIME="${VISION_DEPLOYMENT_RUNTIME:-runtime/deployment}"

if [[ ! -f "$VISION_SYSTEM_CONFIG" ]]; then
  echo "[DEPLOY][FATAL] No existe VISION_SYSTEM_CONFIG: $VISION_SYSTEM_CONFIG" >&2
  exit 20
fi
mkdir -p "$VISION_DEPLOYMENT_RUNTIME"
python_bin="$release_root/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then python_bin="python3"; fi

set +e
"$python_bin" scripts/validate_installation.py "$(dirname "$VISION_SYSTEM_CONFIG")/commissioning.json"
status="$?"
set -e
export VISION_COMMISSIONING_VALIDATION_STATUS="$status"
if [[ "$status" -ne 0 ]]; then
  echo "[DEPLOY][WARNING] La validacion de comisionamiento reporto observaciones (codigo $status)." >&2
  echo "[DEPLOY][WARNING] La interfaz continuara para permitir corregir la estacion; READY productivo se valida por separado." >&2
fi
exec "$python_bin" main.py
