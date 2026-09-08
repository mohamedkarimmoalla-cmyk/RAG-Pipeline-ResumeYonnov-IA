"""Run the FastAPI application with configured server settings."""

import uvicorn

from app.core.config import API_HOST, API_PORT, API_RELOAD


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD,
    )
