"""Read-only access to generated summary artifacts."""

import re
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.api.dependencies import sanitize_filename
from app.core.config import OUTPUT_DIR
from app.core.constants import STATUS_COMPLETED
from app.models.response_models import SummaryDetailResponse
from app.services.export.pdf_generator import (
    SummarySourceNotFoundError,
    generate_summary_pdf,
)
from app.utils.json_utils import read_json

router = APIRouter(tags=["summary"])


def _remove_temporary_file(path: Path) -> None:
    """Remove a generated response file after Starlette finishes streaming it."""
    path.unlink(missing_ok=True)


def _safe_pdf_filename(filename: str) -> str:
    """Build a portable attachment name from the safe document basename."""
    document_name = Path(filename).stem
    document_name = re.sub(r"[^\w.-]+", "_", document_name, flags=re.UNICODE)
    document_name = document_name.strip("._") or "document"
    return f"{document_name}_summary.pdf"


def _summary_artifacts(filename: str) -> tuple[str, Path, Path, Path]:
    """Resolve one document's generated artifacts without exposing their paths."""
    safe_filename = sanitize_filename(filename)
    document_directory = OUTPUT_DIR / Path(safe_filename).stem
    summary_directory = document_directory / "summary"
    markdown_path = summary_directory / "summary.md"
    json_path = summary_directory / "summary.json"
    keywords_path = document_directory / "preprocessing" / "keywords.json"

    if not all(path.is_file() for path in (markdown_path, json_path, keywords_path)):
        raise HTTPException(status_code=404, detail="Generated summary not found")

    return safe_filename, markdown_path, json_path, keywords_path


@router.get("/summary/{filename}", response_model=SummaryDetailResponse)
def get_summary(filename: str) -> SummaryDetailResponse:
    """Return generated summary content and safe download URLs."""
    safe_filename, markdown_path, json_path, keywords_path = _summary_artifacts(
        filename
    )
    summary_payload = read_json(json_path)
    keywords_payload = read_json(keywords_path)
    if isinstance(keywords_payload, dict):
        keywords = keywords_payload.get("global_keywords", [])
    elif isinstance(keywords_payload, list):
        keywords = keywords_payload
    else:
        keywords = []

    encoded_filename = quote(safe_filename, safe="")
    return SummaryDetailResponse(
        filename=safe_filename,
        metadata=summary_payload.get("metadata", {}),
        keywords=keywords,
        summary=markdown_path.read_text(encoding="utf-8"),
        status=STATUS_COMPLETED,
        generated_at=str(summary_payload.get("generated_at", "")),
        downloads={
            "markdown": f"/summary/{encoded_filename}/markdown",
            "json": f"/summary/{encoded_filename}/json",
            "pdf": f"/summary/{encoded_filename}/pdf",
        },
    )


@router.get("/summary/{filename}/markdown", response_class=FileResponse)
def download_summary_markdown(filename: str) -> FileResponse:
    """Download the generated Markdown summary."""
    _, markdown_path, _, _ = _summary_artifacts(filename)
    return FileResponse(
        markdown_path,
        media_type="text/markdown; charset=utf-8",
        filename="summary.md",
    )


@router.get("/summary/{filename}/json", response_class=FileResponse)
def download_summary_json(filename: str) -> FileResponse:
    """Download the generated JSON summary."""
    _, _, json_path, _ = _summary_artifacts(filename)
    return FileResponse(
        json_path,
        media_type="application/json",
        filename="summary.json",
    )


@router.get("/summary/{filename}/pdf", response_class=FileResponse)
def download_summary_pdf(filename: str) -> FileResponse:
    """Generate a PDF solely from the persisted final summary artifacts."""
    safe_filename = sanitize_filename(filename)
    summary_directory = OUTPUT_DIR / Path(safe_filename).stem / "summary"
    json_path = summary_directory / "summary.json"
    markdown_path = summary_directory / "summary.md"

    if not json_path.is_file() and not markdown_path.is_file():
        raise HTTPException(status_code=404, detail="Generated summary not found")

    temporary_file = tempfile.NamedTemporaryFile(
        prefix="summary_export_",
        suffix=".pdf",
        dir=summary_directory,
        delete=False,
    )
    temporary_path = Path(temporary_file.name)
    temporary_file.close()
    try:
        generate_summary_pdf(
            json_path=json_path,
            markdown_path=markdown_path,
            output_path=temporary_path,
        )
    except SummarySourceNotFoundError as exc:
        _remove_temporary_file(temporary_path)
        raise HTTPException(status_code=404, detail="Generated summary not found") from exc
    except Exception:
        _remove_temporary_file(temporary_path)
        raise

    return FileResponse(
        temporary_path,
        media_type="application/pdf",
        filename=_safe_pdf_filename(safe_filename),
        background=BackgroundTask(_remove_temporary_file, temporary_path),
    )
