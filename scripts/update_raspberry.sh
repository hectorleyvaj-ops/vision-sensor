#!/usr/bin/env bash
set -euo pipefail
source_root="${1:?Uso: $0 /ruta/a/nueva_version [prefijo]}"; prefix="${2:-/opt/vision-sensor}"
if [[ "$EUID" -ne 0 ]]; then echo "Usa sudo." >&2; exit 1; fi
version="$(git -C "$source_root" rev-parse --short HEAD 2>/dev/null || date -u +%Y%m%d%H%M%S)"; target="$prefix/releases/$version"
if [[ ! -d "$target" ]]; then cp -a "$source_root" "$target"; find "$target" -name .git -type d -prune -exec rm -rf {} +; fi
python3 -m venv --system-site-packages "$target/.venv"; "$target/.venv/bin/pip" install --no-input -r "$target/requirements-rpi32.txt"
"$target/.venv/bin/python" -m compileall -q "$target/app" "$target/core" "$target/services" "$target/ui"
"$target/.venv/bin/python" "$target/scripts/switch_release.py" --prefix "$prefix" --target "$target"
echo "Release activa: $target. Los datos persistentes no fueron modificados."
