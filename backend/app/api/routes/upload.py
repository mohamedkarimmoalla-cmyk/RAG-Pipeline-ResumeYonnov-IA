"""Upload route."""

from pathlib import Path
from uuid import UUID, uuid4
import time
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.core.config import OUTPUT_DIR, UPLOAD_DIR
from app.api.dependencies import get_db, validate_upload_file
from app.core.config import UPLOAD_DIR
from app.core.constants import STATUS_COMPLETED
from app.db.models import (
    Document,
    ExtractionResult,
    InferenceRun,
    PipelineRun,
    PreprocessingResult,
    Summary,
)
from app.models.response_models import UploadResponse


router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """Store an uploaded PDF file and create its database record."""
    start_time = time.perf_counter()
    print(">>> UPLOAD TIMER ACTIVE <<<")

    safe_filename = validate_upload_file(file)

    document_id = uuid4()

    destination_dir = UPLOAD_DIR / str(document_id)
    destination_dir.mkdir(parents=True, exist_ok=True)

    destination = destination_dir / safe_filename

    temporary_path = destination.with_name(
        f".{destination.name}.{uuid4().hex}.tmp"
    )

    document = Document(
        id=document_id,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(destination),
        status="UPLOADING",
    )

    db.add(document)

    try:
        with temporary_path.open("wb") as handle:
            content = await file.read()
            handle.write(content)

        temporary_path.replace(destination)

        document.status = STATUS_COMPLETED

        db.commit()
        db.refresh(document)

    except Exception:
        db.rollback()

        if temporary_path.exists():
            temporary_path.unlink()

        if destination.exists():
            destination.unlink()

        if destination_dir.exists() and not any(destination_dir.iterdir()):
            destination_dir.rmdir()

        raise
    upload_time = time.perf_counter() - start_time
    print(f"Timing | Upload | "
        f"{upload_time:.3f} seconds"
    )


    return UploadResponse(
        document_id=document.id,
        filename=document.filename,
        path=document.file_path,
        status=document.status,
        message="File uploaded successfully",
    )
@router.delete("/documents/{document_id}")
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a document, its pipeline executions, results, and uploaded file."""

    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # Keep the filesystem paths before deleting the DB record.
    upload_directory = UPLOAD_DIR / str(document.id)

    # Current pipeline output directory is based on PDF filename stem.
    output_directory = OUTPUT_DIR / Path(document.file_path).stem

    # Find all pipeline executions for this document.
    pipeline_runs = (
        db.query(PipelineRun)
        .filter(PipelineRun.document_id == document.id)
        .all()
    )

    pipeline_run_ids = [run.id for run in pipeline_runs]

    try:
        if pipeline_run_ids:
            db.query(Summary).filter(
                Summary.pipeline_run_id.in_(pipeline_run_ids)
            ).delete(synchronize_session=False)

            db.query(InferenceRun).filter(
                InferenceRun.pipeline_run_id.in_(pipeline_run_ids)
            ).delete(synchronize_session=False)

            db.query(PreprocessingResult).filter(
                PreprocessingResult.pipeline_run_id.in_(pipeline_run_ids)
            ).delete(synchronize_session=False)

            db.query(ExtractionResult).filter(
                ExtractionResult.pipeline_run_id.in_(pipeline_run_ids)
            ).delete(synchronize_session=False)

            db.query(PipelineRun).filter(
                PipelineRun.id.in_(pipeline_run_ids)
            ).delete(synchronize_session=False)

        db.delete(document)
        db.commit()

    except Exception:
        db.rollback()
        raise

    # Delete uploaded PDF directory.
    if upload_directory.exists():
        for path in upload_directory.iterdir():
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)

        upload_directory.rmdir()

    # Delete generated output directory.
    # Only do this when no other document uses the same filename stem.
    remaining_document = (
        db.query(Document)
        .filter(
            Document.filename == document.filename,
            Document.id != document.id,
        )
        .first()
    )

    if remaining_document is None and output_directory.exists():
        import shutil
        shutil.rmtree(output_directory)

    return {
        "document_id": str(document_id),
        "status": "deleted",
        "message": "Document and associated pipeline data deleted successfully",
    }