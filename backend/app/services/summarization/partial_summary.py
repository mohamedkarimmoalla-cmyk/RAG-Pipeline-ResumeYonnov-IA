"""Partial-summary generation extracted from the demonstration notebook."""

from typing import Any, Dict, List

from app.services.inference.base_engine import BaseInferenceEngine
from app.services.summarization.extractive_fallback import (
    generate_extractive_partial_summary,
)

def generate_partial_summaries(
    requests: List[Dict[str, Any]],
    engine: BaseInferenceEngine,
    keywords: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate partial summaries sequentially with notebook-compatible handling."""
    partial_summaries = []

    print(f"Generating summaries for {len(requests)} chunks...\n")

    for index, request in enumerate(requests, start=1):
        print(
            f"[{index}/{len(requests)}] "
            f"{request['section_name']}"
        )

        try:
            summary = engine.generate(request)
            partial_summaries.append(summary)

        except Exception as e:
            print(f"Error on chunk {request['chunk_id']}: {e}")
            print("Using extractive fallback.")
            fallback_summary = generate_extractive_partial_summary(
                request,
                keywords,
            )   
            partial_summaries.append({
                "chunk_id": request["chunk_id"],
                "section_name": request["section_name"],
                "priority": request["priority"],
                "summary": fallback_summary,
                "status": "fallback",
            })

    print("\nSummary generation completed.")
    print(f"Generated summaries: {len(partial_summaries)}")

    return partial_summaries

