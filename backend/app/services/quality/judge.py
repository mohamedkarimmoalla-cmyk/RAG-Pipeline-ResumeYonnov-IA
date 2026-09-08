"""LLM-based quality Judge for generated scientific summaries."""

import json
from typing import Any, Dict, Mapping, Optional
import time
import ollama

from app.services.quality.judge_prompt import build_judge_prompt
from app.services.quality.quality_schema import validate_quality_report
import os

from app.core.config import SUMMARY_JUDGE_MODEL

DEFAULT_SUMMARY_JUDGE_MODEL = SUMMARY_JUDGE_MODEL

DEFAULT_JUDGE_CONFIG = {
    "temperature": 0.1,
    "top_p": 0.9,
    "num_predict": 1500,
    "num_ctx": 16384,
}


class SummaryQualityJudge:
    """Evaluate a generated summary against source information."""

    def __init__(
        self,
        model: str = DEFAULT_SUMMARY_JUDGE_MODEL,
        config: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.model = model
        self.config = {
            **DEFAULT_JUDGE_CONFIG,
            **(dict(config) if config is not None else {}),
        }

    def evaluate(
        self,
        source: Dict[str, Any],
        summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate the summary using the Judge LLM."""

        prompt = build_judge_prompt(
            source=source,
            summary=summary,
        )
        print("\n===== JUDGE CONFIG =====")
        print(f"Model: {self.model}")   
        print(f"Temperature: {self.config['temperature']}")
        print(f"Top-p: {self.config['top_p']}")
        print(f"Num predict: {self.config['num_predict']}")
        print(f"Num context: {self.config['num_ctx']}")
        print(f"Prompt characters: {len(prompt)}")
        print(f"Prompt words: {len(prompt.split())}")
        print("========================\n")
        start_time = time.perf_counter()

        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "temperature": self.config["temperature"],
                "top_p": self.config["top_p"],
                "num_predict": self.config["num_predict"],
                "num_ctx": self.config["num_ctx"],
            },
        )
        judge_time = time.perf_counter() - start_time
        print(
            f"Timing | Judge LLM | "
            f"{judge_time:.3f} seconds" 
        )



        content = response["message"]["content"].strip()
        print("\n===== JUDGE RAW RESPONSE =====")
        print(content)
        print("===== END JUDGE RAW RESPONSE =====\n")

        
        report = self._parse_json_response(content)
        report.setdefault("critical_errors", [])
        report.setdefault("recommendations", [])


        report.pop("overall_score", None)
        report.pop("decision", None)


        return validate_quality_report(report)

    @staticmethod
    def _parse_json_response(content: str) -> Dict[str, Any]:
        """Parse the Judge response as JSON."""
        content = content.strip()
        if content.startswith("```"):
            content = content[len("```json"):].strip()
        elif content.startswith("```"):
            content = content[len("```"):].strip()
        start = content.find("{")
        if start == -1:
            raise ValueError("Judge LLM returned no JSON object.")

        decoder = json.JSONDecoder()

        
        try:
            parsed, _ = decoder.raw_decode(content[start:])
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Judge LLM returned invalid JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "Judge LLM response must be a JSON object."
            )

        return parsed