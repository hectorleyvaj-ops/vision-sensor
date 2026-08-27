"""Paths and atomic release switches for an installed vision sensor."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeploymentPaths:
    """Keep code releases separate from mutable station data."""

    prefix: Path
    installation_id: str

    @classmethod
    def from_values(cls, prefix="/opt/vision-sensor", installation_id="vision-station"):
        installation_id = str(installation_id or "").strip()
        if not installation_id or "/" in installation_id or ".." in installation_id:
            raise ValueError("installation_id invalido")
        return cls(Path(prefix), installation_id)

    @property
    def releases(self):
        return self.prefix / "releases"

    @property
    def current(self):
        return self.prefix / "current"

    @property
    def previous(self):
        return self.prefix / "previous"

    @property
    def data_root(self):
        return Path("/var/lib/vision-sensor")

    @property
    def installation(self):
        return self.data_root / "installations" / self.installation_id

    @property
    def runtime(self):
        return self.data_root / "runtime" / self.installation_id

    @property
    def backups(self):
        return Path("/var/backups/vision-sensor") / self.installation_id

    @property
    def environment_file(self):
        return Path("/etc/vision-sensor/vision-sensor.env")

    @property
    def system_config(self):
        return self.installation / "system.json"

    def mutable_directories(self):
        return (self.installation, self.runtime, self.backups)

    def ensure_runtime_layout(self):
        for path in (self.installation, self.runtime):
            path.mkdir(parents=True, exist_ok=True)


def atomic_replace_symlink(link, target):
    """Replace *link* atomically without following an existing symlink."""
    link = Path(link)
    target = Path(target)
    if not target.exists():
        raise FileNotFoundError(f"No existe el release destino: {target}")
    link.parent.mkdir(parents=True, exist_ok=True)
    temporary = link.with_name(link.name + ".new")
    if temporary.exists() or temporary.is_symlink():
        temporary.unlink()
    temporary.symlink_to(target)
    os.replace(temporary, link)


def switch_release(paths, target):
    """Point current at *target*, preserving the prior current release."""
    target = Path(target).resolve()
    previous_target = None
    if paths.current.is_symlink():
        previous_target = paths.current.resolve()
    if previous_target and previous_target != target:
        atomic_replace_symlink(paths.previous, previous_target)
    atomic_replace_symlink(paths.current, target)
    return previous_target
