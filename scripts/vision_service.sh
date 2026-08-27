#!/usr/bin/env bash
# Human-friendly wrapper around the per-user graphical service.
set -euo pipefail
command="${1:-status}"
case "$command" in
  status|start|stop|restart|enable|disable) systemctl --user "$command" vision-sensor.service ;;
  logs) journalctl --user -u vision-sensor.service -n "${2:-120}" --no-pager ;;
  *) echo "Uso: $0 {status|start|stop|restart|logs|enable|disable}" >&2; exit 64 ;;
esac
