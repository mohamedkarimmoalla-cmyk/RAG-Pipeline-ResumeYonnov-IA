"""JSON helpers."""

import json
from pathlib import Path
from typing import Any


def write_json(path: str | Path, payload: Any) -> None:
    """Write a JSON payload to disk."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4, ensure_ascii=False)


def read_json(path: str | Path) -> Any:
    """Read a UTF-8 JSON payload from disk."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)
