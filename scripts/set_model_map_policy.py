"""Select whether one installation locks or configures controller model IDs."""

import argparse
import json
import os
import shutil
from pathlib import Path


POLICIES = {
    "configurable": False,
    "exact": True,
}


def set_model_map_policy(manifest_path, policy):
    path = Path(manifest_path)
    if policy not in POLICIES:
        raise ValueError(f"Politica no soportada: {policy}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"No existe commissioning.json: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"commissioning.json contiene JSON invalido: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("La raiz de commissioning.json debe ser un objeto")
    if manifest.get("schema_version") != 1:
        raise ValueError("Solo se admite commissioning.json schema_version=1")

    exact = POLICIES[policy]
    previous = manifest.get("exact_model_map") is True
    if previous == exact and "exact_model_map" in manifest:
        return {
            "changed": False,
            "policy": policy,
            "path": str(path),
            "backup": None,
        }

    backup_path = path.with_name(path.name + ".bak")
    temporary_path = path.with_name(path.name + ".tmp")
    shutil.copy2(path, backup_path)
    manifest["exact_model_map"] = exact
    try:
        temporary_path.write_text(
            json.dumps(manifest, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary_path, path.stat().st_mode)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return {
        "changed": True,
        "policy": policy,
        "path": str(path),
        "backup": str(backup_path),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Configura si los IDs externos quedan bloqueados por el manifiesto "
            "o pueden reasignarse desde system.json"
        )
    )
    parser.add_argument("manifest", help="Ruta al commissioning.json persistente")
    parser.add_argument("policy", choices=sorted(POLICIES))
    args = parser.parse_args(argv)
    try:
        result = set_model_map_policy(args.manifest, args.policy)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    state = "actualizada" if result["changed"] else "sin cambios"
    print(f"Politica {result['policy']} {state}: {result['path']}")
    if result["backup"]:
        print(f"Respaldo: {result['backup']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
