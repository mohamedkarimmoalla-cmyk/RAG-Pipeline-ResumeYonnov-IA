from app.core.config import OUTPUT_DIR, UPLOAD_DIR


def ensure_project_folders() -> None:
    """Create the upload and output folders if they do not exist."""
    for folder in (UPLOAD_DIR, OUTPUT_DIR):
        folder.mkdir(parents=True, exist_ok=True)

    (OUTPUT_DIR / "logs").mkdir(parents=True, exist_ok=True)
