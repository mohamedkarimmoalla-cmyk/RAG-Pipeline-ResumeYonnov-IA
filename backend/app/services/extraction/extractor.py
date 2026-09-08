"""Extraction orchestration for the notebook pipeline."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.services.extraction.docling_service import extract_with_docling
from app.services.extraction.pymupdf_service import extract_with_pymupdf
from app.services.extraction.quality_check import build_quality_report
from app.core.config import ENABLE_LLM_JUDGE
from app.services.evaluation.llm_judge import evaluate_document_pages

def validate_pdf_extension(filepath: str | Path) -> bool:
    """Validate the file extension exactly as the notebook does."""
    filepath = str(filepath)
    return filepath.lower().endswith(".pdf")


def validate_pdf_readable(filepath: str | Path) -> bool:
    """Validate readability of the PDF file."""
    try:
        from fitz import open as fitz_open

        document = fitz_open(str(filepath))
        document.close()
        return True
    except Exception:
        return False


def needs_ocr(pdf_path: str | Path, min_chars: int = 20) -> bool:
    """Detect whether OCR is required for the PDF."""
    from fitz import open as fitz_open

    document = fitz_open(str(pdf_path))
    total_chars = 0
    for page in document:
        text = page.get_text()
        total_chars += len(text.strip())
    document.close()
    return total_chars < min_chars


def extract_pdf_content(
    pdf_path: str | Path,
    filename: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> Tuple[List[Dict[str, str]], str, Dict[str, Any]]:
    """Run the extraction stage and return pages, markdown, and statistics."""
    pymupdf_text, pymupdf_report = extract_with_pymupdf(pdf_path)
    pages = [{"text": pymupdf_text}] if isinstance(pymupdf_text, str) else pymupdf_text

    use_docling = False
    if not pages:
        use_docling = True

    if use_docling:
        docling_payload = extract_with_docling(pdf_path)
        markdown_text = docling_payload.get("markdown", "")
    else:
        markdown_text = pymupdf_text
    
    report = {
        "Filename": str(filename or Path(str(pdf_path)).name),
        "Input PDF": str(pdf_path),
        "Output Markdown": str(markdown_path or str(pdf_path)),
        "Pages": pymupdf_report.get("page_count", 1),
        "Markdown Size (characters)": len(markdown_text),
        "Extraction Status": "Success",
        "Extraction Method": "docling" if use_docling else "pymupdf4llm",
    }
    return pages, markdown_text, report


def evaluate_extraction_quality(
    pdf_path: str | Path,
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Coordinate extraction quality evaluation and return a notebook-compatible report."""

    if not ENABLE_LLM_JUDGE:
        return {
            "status": "skipped",
            "message": "LLM Judge disabled by configuration.",
            "decision": "skipped",
            "average_score": None,
            "pages": [],
        }

    evaluated_pages = evaluate_document_pages(pdf_path, results)
    return build_quality_report(evaluated_pages)