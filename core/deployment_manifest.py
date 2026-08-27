"""Checksum manifests used by backup and restore maintenance commands."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(root, *, installation_id, version=""):
    root = Path(root)
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        files.append({
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        })
    return {
        "schema_version": 1,
        "installation_id": str(installation_id),
        "version": str(version),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": files,
    }


def write_manifest(root, **values):
    manifest = build_manifest(root, **values)
    path = Path(root) / "manifest.json"
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return manifest


def verify_manifest(root):
    root = Path(root)
    manifest_path = root / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    for record in payload.get("files", []):
        path = root / record["path"]
        if not path.is_file():
            errors.append(f"Falta {record['path']}")
        elif path.stat().st_size != record["size"] or sha256_file(path) != record["sha256"]:
            errors.append(f"Checksum invalido: {record['path']}")
    return payload, errors
