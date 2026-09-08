"""File helpers."""

from pathlib import Path


def ensure_parent_directory(path: str | Path) -> Path:
    """Ensure that a parent directory exists."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
