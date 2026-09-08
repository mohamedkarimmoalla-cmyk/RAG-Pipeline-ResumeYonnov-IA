"""Summarization route."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, sanitize_filename
from app.core.constants import STATUS_FAILED
from app.db.models import Document
from app.models.request_models import SummarizeRequest
from app.models.response_models import SummarizeResponse
from app.services.pipeline.document_pipeline import DocumentPipeline


router = APIRouter(tags=["summarize"])


@router.post("/summarize", response_model=SummarizeResponse)
def summarize_pdf(
    payload: SummarizeRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> SummarizeResponse:
    """Trigger the document pipeline for a previously uploaded file."""

    document = (
        db.query(Document)
        .filter(Document.id == payload.document_id)
        .first()
    )

    if document is None:
        response.status_code = status.HTTP_404_NOT_FOUND

        return SummarizeResponse(
            filename="",
            status=STATUS_FAILED,
            summary_path=None,
            metadata=None,
            message="Document not found",
        )

    safe_filename = sanitize_filename(document.filename)

    pipeline = DocumentPipeline(db=db)

    result = pipeline.run(
        document.file_path,
        document_id=payload.document_id,
        model=payload.model,
    )

    if result.get("status") == STATUS_FAILED:
        failure_stage = str(result.get("failure_stage", ""))

        if failure_stage == "validation":
            response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return SummarizeResponse(
        filename=safe_filename,
        status=result.get("status", STATUS_FAILED),
        summary_path=(
            f"/summary/{quote(safe_filename, safe='')}/markdown"
            if result.get("status") != STATUS_FAILED
            else None
        ),
        metadata=result.get("metadata"),
        message=result.get("message", "Pipeline completed"),
    )