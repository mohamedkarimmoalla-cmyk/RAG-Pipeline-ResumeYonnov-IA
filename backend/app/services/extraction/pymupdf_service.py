"""PyMuPDF4LLM-specific extraction service."""

from pathlib import Path
from typing import Dict, Tuple

import fitz


def extract_with_pymupdf(pdf_path: str | Path) -> Tuple[str, Dict[str, object]]:
    """Extract PDF text using PyMuPDF4LLM-compatible logic and return a metadata report."""
    document = fitz.open(str(pdf_path))
    text_parts = []
    for page in document:
        text_parts.append(page.get_text())
    document.close()

    extracted_text = "\n\n".join(part.strip() for part in text_parts if part and part.strip())
    report = {
        "source": "PyMuPDF4LLM",
        "page_count": len(text_parts),
        "characters": len(extracted_text),
        "status": "success",
    }
    return extracted_text, report
