"""Read-only retrieval of persisted document pipeline executions."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.db.models import (
    ExtractionResult,
    InferenceRun,
    PipelineRun,
    PreprocessingResult,
    Summary,
)
from app.models.response_models import (
    ExtractionResultResponse,
    InferenceRunResponse,
    PipelineRunDetailResponse,
    PipelineRunListItemResponse,
    PipelineSummaryResponse,
    PreprocessingResultResponse,
    DeletePipelineRunResponse,
)


router = APIRouter(tags=["pipeline-runs"])
def sanitize_extraction_report(
    report: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Remove internal filesystem paths from the public API response."""
    if not report:
        return report

    sanitized = dict(report)

    extraction = sanitized.get("extraction")

    if isinstance(extraction, dict):
        extraction = dict(extraction)
        extraction.pop("Input PDF", None)
        extraction.pop("Output Markdown", None)
        sanitized["extraction"] = extraction

    # Also protect against paths stored at the top level.
    sanitized.pop("Input PDF", None)
    sanitized.pop("Output Markdown", None)

    return sanitized

@router.get(
    "/documents/{document_id}/pipeline-runs",
    response_model=list[PipelineRunListItemResponse],
)
def list_document_pipeline_runs(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> list[PipelineRunListItemResponse]:
    """Return pipeline execution history for one document."""

    pipeline_runs = (
        db.query(PipelineRun)
        .filter(PipelineRun.document_id == document_id)
        .order_by(PipelineRun.created_at.desc())
        .all()
    )

    return [
        PipelineRunListItemResponse(
            pipeline_run_id=run.id,
            document_id=run.document_id,
            status=run.status,
            model=run.model,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_ms=run.duration_ms,
            failure_stage=run.failure_stage,
        )
        for run in pipeline_runs
    ]


@router.get("/pipeline-runs/{pipeline_run_id}", response_model=PipelineRunDetailResponse)
def get_pipeline_run(
    pipeline_run_id: UUID,
    db: Session = Depends(get_db),
) -> PipelineRunDetailResponse:
    """Return one pipeline run and all persisted stage results."""
    pipeline_run = db.query(PipelineRun).filter(PipelineRun.id == pipeline_run_id).first()

    if pipeline_run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    extraction = (
        db.query(ExtractionResult)
        .filter(ExtractionResult.pipeline_run_id == pipeline_run.id)
        .first()
    )
    preprocessing = (
        db.query(PreprocessingResult)
        .filter(PreprocessingResult.pipeline_run_id == pipeline_run.id)
        .first()
    )
    inference = (
        db.query(InferenceRun)
        .filter(InferenceRun.pipeline_run_id == pipeline_run.id)
        .first()
    )
    summary = db.query(Summary).filter(Summary.pipeline_run_id == pipeline_run.id).first()

    return PipelineRunDetailResponse(
        pipeline_run_id=pipeline_run.id,
        document_id=pipeline_run.document_id,
        status=pipeline_run.status,
        model=pipeline_run.model,
        started_at=pipeline_run.started_at,
        completed_at=pipeline_run.completed_at,
        duration_ms=pipeline_run.duration_ms,
        failure_stage=pipeline_run.failure_stage,
        error_message=pipeline_run.error_message,
        extraction=(
            ExtractionResultResponse(
                extraction_method=extraction.extraction_method,
                quality_score=extraction.quality_score,
                decision=extraction.decision,
                page_count=extraction.page_count,
                extraction_report=sanitize_extraction_report(
                    extraction.extraction_report
                )
                
            )
            if extraction
            else None
        ),
        preprocessing=(
            PreprocessingResultResponse(
                article_metadata=preprocessing.article_metadata,
                article_keywords=preprocessing.article_keywords,
                sections=preprocessing.sections,
                missing_sections=preprocessing.missing_sections,
                selected_sections=preprocessing.selected_sections,
                filtered_sections=preprocessing.filtered_sections,
                chunked_sections=preprocessing.chunked_sections,
                cleaning_report=preprocessing.cleaning_report,
            )
            if preprocessing
            else None
        ),
        inference=(
            InferenceRunResponse(
                model=inference.model,
                status=inference.status,
                request_count=inference.request_count,
                completed_count=inference.completed_count,
                failed_count=inference.failed_count,
                started_at=inference.started_at,
                completed_at=inference.completed_at,
                duration_ms=inference.duration_ms,
                inference_config=inference.inference_config,
                result_metadata=inference.result_metadata,
                error_message=inference.error_message,
            )
            if inference
            else None
        ),
        summary=(
            PipelineSummaryResponse(
                summary_text=summary.summary_text,
                summary_json=summary.summary_json,
                created_at=summary.created_at,
                updated_at=summary.updated_at,
            )
            if summary
            else None
        ),
    )
@router.get(
    "/pipeline-runs",
    response_model=list[PipelineRunListItemResponse],
)
def list_pipeline_runs(
    db: Session = Depends(get_db),
) -> list[PipelineRunListItemResponse]:
    """Return lightweight pipeline execution history."""
    pipeline_runs = (
        db.query(PipelineRun)
        .order_by(PipelineRun.created_at.desc())
        .all()
    )

    return [
        PipelineRunListItemResponse(
            pipeline_run_id=run.id,
            document_id=run.document_id,
            status=run.status,
            model=run.model,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_ms=run.duration_ms,
            failure_stage=run.failure_stage,
        )
        for run in pipeline_runs
    ]
@router.delete(
    "/pipeline-runs/{pipeline_run_id}",
    response_model=DeletePipelineRunResponse,
)
def delete_pipeline_run(
    pipeline_run_id: UUID,
    db: Session = Depends(get_db),
) -> DeletePipelineRunResponse:
    """Delete one pipeline execution and its persisted stage results."""

    pipeline_run = (
        db.query(PipelineRun)
        .filter(PipelineRun.id == pipeline_run_id)
        .first()
    )

    if pipeline_run is None:
        raise HTTPException(
            status_code=404,
            detail="Pipeline run not found",
        )

    try:
        # Delete child stage records first because the foreign keys
        # currently do not use ON DELETE CASCADE.
        db.query(ExtractionResult).filter(
            ExtractionResult.pipeline_run_id == pipeline_run.id
        ).delete(synchronize_session=False)

        db.query(PreprocessingResult).filter(
            PreprocessingResult.pipeline_run_id == pipeline_run.id
        ).delete(synchronize_session=False)

        db.query(InferenceRun).filter(
            InferenceRun.pipeline_run_id == pipeline_run.id
        ).delete(synchronize_session=False)

        db.query(Summary).filter(
            Summary.pipeline_run_id == pipeline_run.id
        ).delete(synchronize_session=False)

        db.delete(pipeline_run)

        db.commit()

    except Exception:
        db.rollback()
        raise

    return DeletePipelineRunResponse(
        pipeline_run_id=pipeline_run_id,
        status="deleted",
        message="Pipeline run deleted successfully",
    )