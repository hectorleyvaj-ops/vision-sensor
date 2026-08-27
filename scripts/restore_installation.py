"""Restore a verified backup using a staging directory and atomic rename."""

import argparse
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from core.deployment_manifest import verify_manifest
from scripts.validate_installation import validate_installation


def restore_installation(backup, destination):
    backup, destination = Path(backup), Path(destination)
    manifest, errors = verify_manifest(backup)
    if errors:
        raise ValueError("; ".join(errors))
    with tempfile.TemporaryDirectory(prefix="vision-restore-", dir=str(destination.parent)) as temporary:
        staged = Path(temporary) / "installation"
        shutil.copytree(backup, staged, ignore=shutil.ignore_patterns("manifest.json"))
        report = validate_installation(staged / "commissioning.json")
        if report["errors"]:
            raise ValueError("Backup estructuralmente invalido")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        previous = destination.with_name(destination.name + ".before-restore-" + stamp)
        if destination.exists():
            destination.replace(previous)
        staged.replace(destination)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args(argv)
    restore_installation(args.backup, args.destination)
    print("Restauracion completada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
