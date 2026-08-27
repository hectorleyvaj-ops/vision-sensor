#!/usr/bin/env bash
# Called by desktop autostart after Wayland/X11 variables are available.
set -euo pipefail
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR XDG_SESSION_TYPE
systemctl --user start vision-sensor.service
