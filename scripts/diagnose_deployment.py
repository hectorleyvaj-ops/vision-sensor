"""Read-only deployment diagnosis; safe to run before hardware is configured."""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.runtime_health import read_runtime_health


def _item(status, code, message, **details):
    return {"status": status, "code": code, "message": message, "details": details}


def diagnose(config_path, runtime_path=None):
    config_path = Path(config_path)
    items = []
    items.append(_item("PASS" if config_path.is_file() else "ERROR", "SYSTEM_CONFIG", str(config_path)))
    for command in ("v4l2-ctl", "python3"):
        items.append(_item("PASS" if shutil.which(command) else "WARNING", "COMMAND_" + command.replace("-", "_").upper(), command))
    for module in ("cv2", "numpy", "serial"):
        try:
            __import__(module)
            items.append(_item("PASS", "PYTHON_" + module.upper(), module))
        except ImportError:
            items.append(_item("WARNING", "PYTHON_" + module.upper(), module + " no disponible"))
    camera_links = sorted(str(path) for path in Path("/dev/v4l/by-id").glob("*")) if Path("/dev/v4l/by-id").exists() else []
    serial_links = sorted(str(path) for path in Path("/dev/serial/by-id").glob("*")) if Path("/dev/serial/by-id").exists() else []
    items.append(_item("PASS" if camera_links else "WARNING", "CAMERAS", "Camaras persistentes", devices=camera_links))
    items.append(_item("PASS" if serial_links else "WARNING", "SERIAL", "Puertos persistentes", devices=serial_links))
    runtime = read_runtime_health(runtime_path) if runtime_path else None
    if runtime:
        items.append(_item("PASS", "RUNTIME_HEALTH", runtime.get("state", "unknown"), health=runtime))
    return {
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "user": os.getenv("USER", ""),
        "session_type": os.getenv("XDG_SESSION_TYPE", "unknown"),
        "qt_api": os.getenv("VISION_QT_API", "auto"),
        "items": items,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--runtime-health")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = diagnose(args.config, args.runtime_health)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for item in report["items"]:
            print("[{}] {}: {}".format(item["status"], item["code"], item["message"]))
    return 2 if any(item["status"] == "ERROR" for item in report["items"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
