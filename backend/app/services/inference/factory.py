"""Factory for selecting an inference engine."""

from typing import Any, Mapping, Optional

from app.core.config import BACKEND_ENGINE
from app.services.inference.base_engine import BaseInferenceEngine
from app.services.inference.ollama_engine import OllamaEngine
from app.services.inference.vllm_engine import VLLMEngine


class InferenceFactory:
    """Create the configured synchronous inference engine."""

    @staticmethod
    def create_engine(
        engine_name: Optional[str] = None,
        config: Optional[Mapping[str, Any]] = None,
    ) -> BaseInferenceEngine:
        """Return an Ollama or vLLM engine based on configuration."""
        selected_engine = (engine_name or BACKEND_ENGINE).strip().lower()

        if selected_engine == "ollama":
            return OllamaEngine(config=config)

        if selected_engine == "vllm":
            return VLLMEngine(config=config)

        raise ValueError(f"Unsupported inference engine: {selected_engine}")

