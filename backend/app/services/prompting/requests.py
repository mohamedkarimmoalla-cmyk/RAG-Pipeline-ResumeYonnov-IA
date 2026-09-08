"""Inference request generation helpers for the prompting stage."""

from typing import Any, Dict, List

from app.services.prompting.builder import build_prompt


def build_inference_requests(chunked_sections: List[Dict[str, Any]], shared_prefix: str) -> List[Dict[str, Any]]:
    """Create inference requests from chunked sections."""
    requests: List[Dict[str, Any]] = []
    for chunk in chunked_sections:
        if str(chunk.get("section_name", "")).lower() == "title":
            continue
        requests.append({
            "chunk_id": chunk["chunk_id"],
            "section_name": chunk["section_name"],
            "priority": chunk["priority"],
            "content": chunk["content"],
            "prompt": build_prompt(chunk, shared_prefix),
        })
    return requests
