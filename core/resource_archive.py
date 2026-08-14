"""Recoverable archive for resources removed from the configuration UI."""

import shutil
import uuid
from pathlib import Path


def archive_resource_path(source, archive_root="runtime/deleted_resources", token=None):
    source = Path(source)
    if not source.exists():
        return None
    archive_root = Path(archive_root)
    archive_root.mkdir(parents=True, exist_ok=True)
    suffix = str(token or uuid.uuid4().hex[:8]).strip()
    target = archive_root / f"{source.name}-{suffix}"
    if target.exists():
        raise FileExistsError(f"El destino de archivo ya existe: {target}")
    shutil.move(str(source), str(target))
    return target
