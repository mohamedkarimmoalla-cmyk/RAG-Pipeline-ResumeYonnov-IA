"""Shared API dependencies."""

from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.folders import ensure_project_folders

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.database import SessionLocal

ensure_project_folders()

def get_db() -> Generator[Session, None, None]:
    """Provide a database session for an API request."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

def sanitize_filename(filename: str) -> str:
    """Reduce a client-supplied path to a safe basename."""
    safe_filename = Path(filename.replace("\\", "/")).name.strip()
    if not safe_filename or safe_filename in {".", ".."}:
        raise HTTPException(status_code=400, detail="Filename is required")
    return safe_filename


def validate_upload_file(file: UploadFile) -> str:
    """Validate the upload payload before saving the file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    safe_filename = sanitize_filename(file.filename)
    if Path(safe_filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    return safe_filename
