"""Request models for the API."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    """Summarization payload model."""

    document_id: UUID
    model: Optional[str] = None
