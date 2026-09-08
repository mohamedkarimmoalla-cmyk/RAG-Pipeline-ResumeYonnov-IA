"""Centralized configuration for the backend."""

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def _resolve_directory(variable_name: str, default: str) -> Path:
    """Resolve a configured directory relative to the backend root."""
    configured_path = Path(os.getenv(variable_name, default)).expanduser()
    if not configured_path.is_absolute():
        configured_path = BASE_DIR / configured_path
    return configured_path


def _read_bool(variable_name: str, default: bool) -> bool:
    """Read a boolean environment variable using conventional values."""
    raw_value = os.getenv(variable_name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _read_list(variable_name: str, default: str = "") -> list[str]:
    """Read a comma-separated configuration value."""
    raw_value = os.getenv(variable_name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


APP_NAME = os.getenv("APP_NAME", "PDF Summarization Backend")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_RELOAD = _read_bool("API_RELOAD", True)
CORS_ORIGINS = _read_list(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:8080,http://127.0.0.1:8080",
)

UPLOAD_DIR = _resolve_directory("UPLOAD_DIR", "uploads")
OUTPUT_DIR = _resolve_directory("OUTPUT_DIR", "outputs")

BACKEND_ENGINE = os.getenv("BACKEND_ENGINE", "ollama").strip().lower()

ENABLE_LLM_JUDGE = _read_bool("ENABLE_LLM_JUDGE", False)

SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "qwen2.5:3b")

LLM_JUDGE_MODEL = os.getenv("LLM_JUDGE_MODEL", "qwen2.5vl:7b")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.9"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "2000"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_QUALITY_NUM_CTX = int(os.getenv("OLLAMA_QUALITY_NUM_CTX", "8192"))

LLM_JUDGE_SAMPLE_MODE = os.getenv(
    "LLM_JUDGE_SAMPLE_MODE",
    "representative",
).strip().lower()

LLM_JUDGE_MAX_PAGES = int(
    os.getenv("LLM_JUDGE_MAX_PAGES", "3")
)
SUMMARY_JUDGE_MODEL = os.getenv(
    "SUMMARY_JUDGE_MODEL",
    "qwen2.5:3b",
)
DATABASE_URL = os.getenv("DATABASE_URL")