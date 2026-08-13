"""Resolve recipe-owned resource directories without UI dependencies."""

from pathlib import Path


def recipe_resource_root(recipe_file):
    path = Path(str(recipe_file or ""))
    if "installations" in path.parts:
        return path.parent / "master_images"
    return Path("master_img")
