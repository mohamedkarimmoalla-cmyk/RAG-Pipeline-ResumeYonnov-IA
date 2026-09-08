"""Placeholder vLLM inference engine."""

from typing import Any, Dict, Mapping, Optional

from app.services.inference.base_engine import BaseInferenceEngine


class VLLMEngine(BaseInferenceEngine):
    """Reserve the common inference interface for a future vLLM backend."""

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        self.config = dict(config) if config is not None else {}

    def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Indicate that vLLM inference is intentionally unavailable."""
        raise NotImplementedError("VLLM inference is not implemented yet")

