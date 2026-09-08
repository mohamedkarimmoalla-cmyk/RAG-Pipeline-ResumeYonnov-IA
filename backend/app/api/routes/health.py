"""Health route."""

from fastapi import APIRouter

from app.models.response_models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return the service health status."""
    return HealthResponse(status="ok", message="Backend is running")
