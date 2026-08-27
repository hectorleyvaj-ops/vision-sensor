#!/usr/bin/env bash
set -euo pipefail
prefix="${1:-/opt/vision-sensor}"
if [[ "$EUID" -ne 0 ]]; then echo "Usa sudo." >&2; exit 1; fi
if [[ ! -L "$prefix/previous" ]]; then echo "No hay release anterior recuperable." >&2; exit 2; fi
current="$(readlink -f "$prefix/current")"; previous="$(readlink -f "$prefix/previous")"
python3 "$(dirname "$0")/switch_release.py" --prefix "$prefix" --target "$previous"
echo "Rollback de codigo completado. Los datos persistentes no fueron modificados."
