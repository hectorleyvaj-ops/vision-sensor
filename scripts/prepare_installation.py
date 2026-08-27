"""Copy a generic or project seed into mutable storage without overwriting it."""

import argparse
import json
import shutil
from pathlib import Path


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def seed_installation(source_root, destination, seed, installation_id=None):
    source_root = Path(source_root)
    destination = Path(destination)
    source = source_root / ("installations" / Path(seed) if seed != "generic" else Path("config"))
    if destination.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    config_path = destination / "system.json"
    if seed == "generic":
        shutil.copy2(source_root / "core" / "models" / "recipes.json", destination / "recipes.json")
        _write_json(
            destination / "commissioning.json",
            {
                "schema_version": 1,
                "system_config": "system.json",
                "project_root": ".",
                "allow_empty_recipes": True,
                "required_models": [],
            },
        )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if installation_id:
        config.setdefault("installation", {})["id"] = str(installation_id)
    config["recipes"]["file"] = str((destination / "recipes.json").resolve())
    trace = config.setdefault("traceability", {})
    trace["directory"] = str((destination.parent.parent / "runtime" / config["installation"]["id"] / "traceability").resolve())
    _write_json(config_path, config)
    recipes_path = destination / "recipes.json"
    if recipes_path.exists():
        payload = json.loads(recipes_path.read_text(encoding="utf-8"))
        for recipe in payload.get("recipes", []):
            for step in recipe.get("steps", []):
                params = step.get("params", {})
                paths = params.get("template_paths", [])
                resolved_paths = []
                for item in paths:
                    item_path = Path(item)
                    if item_path.is_absolute():
                        resolved_paths.append(str(item_path))
                        continue
                    source_item = (source_root / item_path).resolve()
                    try:
                        relative_to_seed = source_item.relative_to(source.resolve())
                    except ValueError:
                        resolved_paths.append(str(source_item))
                    else:
                        resolved_paths.append(str((destination / relative_to_seed).resolve()))
                params["template_paths"] = resolved_paths
        _write_json(recipes_path, payload)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--seed", choices=("generic", "worksurface"), default="generic")
    parser.add_argument("--installation-id")
    args = parser.parse_args(argv)
    print("Semilla creada" if seed_installation(args.source_root, args.destination, args.seed, args.installation_id) else "La instalacion existente se conserva")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
