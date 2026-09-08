"""Response models for the API."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    message: str


class UploadResponse(BaseModel):
    """Upload response model."""
    document_id: UUID
    filename: str
    path: str
    status: str
    message: str


class SummarizeResponse(BaseModel):
    """Summarization response model."""

    filename: str
    status: str
    summary_path: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    message: str


class SummaryDetailResponse(BaseModel):
    """Generated summary content exposed without filesystem paths."""

    filename: str
    metadata: dict[str, Any]
    keywords: list[Any]
    summary: str
    status: str
    generated_at: str
    downloads: dict[str, str]


class ExtractionResultResponse(BaseModel):
    """Persisted extraction stage data for a pipeline run."""

    extraction_method: str
    quality_score: Optional[float] = None
    decision: Optional[str] = None
    page_count: Optional[int] = None
    extraction_report: Optional[dict[str, Any]] = None

class DocumentListItemResponse(BaseModel):
    """Lightweight document information for retrieval."""

    document_id: UUID
    filename: str
    original_filename: str
    status: str
    created_at: datetime
    updated_at: datetime

class PreprocessingResultResponse(BaseModel):
    """Persisted preprocessing stage data for a pipeline run."""

    article_metadata: Optional[dict[str, Any]] = None
    article_keywords: Optional[dict[str, Any] | list[Any]] = None
    sections: Optional[list[Any]] = None
    missing_sections: Optional[list[Any]] = None
    selected_sections: Optional[list[Any]] = None
    filtered_sections: Optional[list[Any]] = None
    chunked_sections: Optional[list[Any]] = None
    cleaning_report: Optional[dict[str, Any]] = None


class InferenceRunResponse(BaseModel):
    """Persisted inference stage data for a pipeline run."""

    model: Optional[str] = None
    status: str
    request_count: int
    completed_count: int
    failed_count: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    inference_config: Optional[dict[str, Any]] = None
    result_metadata: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None


class PipelineSummaryResponse(BaseModel):
    """Persisted final summary data for a pipeline run."""

    summary_text: str
    summary_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PipelineRunDetailResponse(BaseModel):
    """Complete persisted execution history for one pipeline run."""

    pipeline_run_id: UUID
    document_id: UUID
    status: str
    model: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    failure_stage: Optional[str] = None
    error_message: Optional[str] = None
    extraction: Optional[ExtractionResultResponse] = None
    preprocessing: Optional[PreprocessingResultResponse] = None
    inference: Optional[InferenceRunResponse] = None
    summary: Optional[PipelineSummaryResponse] = None

class PipelineRunListItemResponse(BaseModel):
    """Lightweight pipeline run information for execution history."""

    pipeline_run_id: UUID
    document_id: UUID
    status: str
    model: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    failure_stage: Optional[str] = None
class DocumentListItemResponse(BaseModel):
    """Lightweight document information for retrieval."""

    document_id: UUID
    filename: str
    original_filename: str
    status: str
    created_at: datetime
    updated_at: datetime
class DeletePipelineRunResponse(BaseModel):
    """Response returned after deleting one pipeline execution."""

    pipeline_run_id: UUID
    status: str
    message: str