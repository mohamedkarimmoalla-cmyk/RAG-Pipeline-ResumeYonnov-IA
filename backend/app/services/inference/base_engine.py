"""Common interface for inference engines."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseInferenceEngine(ABC):
    """Define the synchronous interface shared by inference backends."""

    @abstractmethod
    def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate one partial summary from one inference request."""

