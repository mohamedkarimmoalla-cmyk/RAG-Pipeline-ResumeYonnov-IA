"""Docling-specific extraction service."""

from pathlib import Path
from typing import Any, Dict


def extract_with_docling(pdf_path: str | Path) -> Dict[str, Any]:
    """Return a Docling fallback payload for the extraction workflow."""
    return {
        "source": "Docling",
        "pdf_path": str(pdf_path),
        "status": "not_implemented",
        "markdown": "",
    }
