"""Create a verified, portable backup of one mutable installation."""

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

from core.deployment_manifest import write_manifest


def backup_installation(source, destination_root, installation_id, version="", include_traceability=False):
    source = Path(source)
    destination_root = Path(destination_root)
    if not source.is_dir():
        raise ValueError(f"No existe la instalacion: {source}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = destination_root / (stamp + "-" + str(installation_id))
    target.mkdir(parents=True, exist_ok=False)
    for item in source.iterdir():
        if item.name == "traceability" and not include_traceability:
            continue
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)
    write_manifest(target, installation_id=installation_id, version=version)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--installation", required=True)
    parser.add_argument("--version", default="")
    parser.add_argument("--include-traceability", action="store_true")
    args = parser.parse_args(argv)
    print(backup_installation(args.source, args.destination, args.installation, args.version, args.include_traceability))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
