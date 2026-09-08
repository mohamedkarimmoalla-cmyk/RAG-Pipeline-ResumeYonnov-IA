"""Ollama inference engine."""

from typing import Any, Dict, Mapping, Optional

import ollama

from app.core.config import (
    SUMMARY_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TEMPERATURE,
    OLLAMA_TOP_P,
)
from app.services.inference.base_engine import BaseInferenceEngine


OLLAMA_CONFIG = {
    "model": SUMMARY_MODEL,
    "temperature": OLLAMA_TEMPERATURE,
    "top_p": OLLAMA_TOP_P,
    "num_predict": OLLAMA_NUM_PREDICT,
    "num_ctx": OLLAMA_NUM_CTX,
}


class OllamaEngine(BaseInferenceEngine):
    """Generate summaries through Ollama."""

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        self.config = (
            dict(config)
            if config is not None
            else OLLAMA_CONFIG.copy()
        )

    def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate one summary using Ollama."""

        response = ollama.chat(
            model=self.config["model"],
            messages=[
                {
                    "role": "user",
                    "content": request["prompt"],
                }
            ],
            options={
                "temperature": self.config["temperature"],
                "top_p": self.config["top_p"],
                "num_predict": self.config["num_predict"],
                "num_ctx": self.config["num_ctx"],
            },
        )

        # ---------------------------------------------------------
        # Diagnostic information
        # ---------------------------------------------------------
        print("\n" + "=" * 80)
        print("OLLAMA RESPONSE METADATA")
        print("=" * 80)

        print(f"Model:           {self.config['model']}")
        print(f"Temperature:     {self.config['temperature']}")
        print(f"Top-p:           {self.config['top_p']}")
        print(f"Num predict:     {self.config['num_predict']}")
        print(f"Num context:     {self.config['num_ctx']}")

        print("-" * 80)

        # Print useful Ollama response metadata if available.
        print(f"Done:            {response.get('done')}")
        print(f"Done reason:     {response.get('done_reason')}")

        print(
            f"Prompt eval:     "
            f"{response.get('prompt_eval_count')}"
        )

        print(
            f"Generated tokens:"
            f" {response.get('eval_count')}"
        )

        print(
            f"Prompt duration: "
            f"{response.get('prompt_eval_duration')}"
        )

        print(
            f"Generation duration:"
            f" {response.get('eval_duration')}"
        )

        print("-" * 80)

        generated_text = response["message"]["content"].strip()

        print(f"Generated chars: {len(generated_text)}")

        print(
            f"Generated words:"
            f" {len(generated_text.split())}"
        )

        print("-" * 80)

        print("LAST 500 CHARACTERS OF RESPONSE:")
        print(generated_text[-500:])

        print("=" * 80)

        # ---------------------------------------------------------
        # Return the same structure used by the existing pipeline
        # ---------------------------------------------------------
        return {
            "chunk_id": request["chunk_id"],
            "section_name": request["section_name"],
            "priority": request["priority"],
            "summary": generated_text,
        }