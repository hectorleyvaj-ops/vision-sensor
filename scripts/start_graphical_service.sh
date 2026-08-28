#!/usr/bin/env bash
# Called by desktop autostart after Wayland/X11 variables are available.
set -euo pipefail
session_variables=(XDG_RUNTIME_DIR XDG_SESSION_TYPE)
if [[ -n "${DISPLAY:-}" ]]; then session_variables+=(DISPLAY); fi
if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then session_variables+=(WAYLAND_DISPLAY); fi
systemctl --user import-environment "${session_variables[@]}"
systemctl --user start vision-sensor.service
