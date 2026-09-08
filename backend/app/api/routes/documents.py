"""Document retrieval routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.db.models import Document, PipelineRun
from app.models.response_models import DocumentListItemResponse


router = APIRouter(tags=["documents"])


@router.get(
    "/documents",
    response_model=list[DocumentListItemResponse],
)
def list_documents(
    db: Session = Depends(get_db),
) -> list[DocumentListItemResponse]:
    """Return persisted documents without exposing filesystem paths."""

    documents = (
        db.query(Document)
        .join(PipelineRun, PipelineRun.document_id == Document.id)
        .distinct()
        .order_by(Document.created_at.desc())
        .all()
    )

    return [
        DocumentListItemResponse(
            document_id=document.id,
            filename=document.filename,
            original_filename=document.original_filename,
            status=document.status,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        for document in documents
    ]