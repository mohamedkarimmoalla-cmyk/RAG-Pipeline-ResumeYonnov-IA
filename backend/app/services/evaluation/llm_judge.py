import json
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4
import logging
import fitz

from app.core.config import (
    LLM_JUDGE_MODEL,
    LLM_JUDGE_SAMPLE_MODE,
    LLM_JUDGE_MAX_PAGES,
    OLLAMA_QUALITY_NUM_CTX,
)
from ollama import chat


JUDGE_PROMPT = """
You are an expert Document Extraction Quality Auditor.

You will receive:

1. A PDF page image.
2. The Markdown extracted from that page.

Compare the image with the Markdown.

Evaluate the extraction quality.

Rules:

- quality_score must be an INTEGER between 0 and 100.
- 100 means a perfect extraction.
- 0 means the extraction is unusable.

Decision must be EXACTLY one of:

- "accept"
- "fallback"

Use:
- "accept" if quality_score >= 75
- "fallback" if quality_score < 75

The summary must contain at most two sentences.

Return ONLY valid JSON.

JSON schema:

{
    "quality_score": 0,
    "decision": "accept",
    "summary": ""
}
"""


def evaluate_page(image_path: str, markdown: str) -> Dict[str, Any]:
    """Compare one rendered PDF page with its extracted Markdown."""
    response = chat(
        model=LLM_JUDGE_MODEL,
        format="json",
        options={
            "num_ctx": OLLAMA_QUALITY_NUM_CTX,
        },
        messages=[
            {
                "role": "user",
                "content": f"""
{JUDGE_PROMPT}

Extracted Markdown

{markdown}
""",
                "images": [image_path],
            }
        ],
    )

    return json.loads(response["message"]["content"])


def select_pages(total_pages: int) -> list[int]:
    """
    Select representative pages for LLM Judge evaluation.

    Returns zero-based page indices.
    """

    if LLM_JUDGE_SAMPLE_MODE == "all":
        return list(range(total_pages))

    if total_pages <= LLM_JUDGE_MAX_PAGES:
        return list(range(total_pages))

    if LLM_JUDGE_MAX_PAGES == 1:
        return [0]

    if LLM_JUDGE_MAX_PAGES == 2:
        return [0, total_pages - 1]

    if LLM_JUDGE_MAX_PAGES == 3:
        return sorted({
            0,
            (total_pages - 1) // 2,
            total_pages - 1,
        })

    step = (total_pages - 1) / (LLM_JUDGE_MAX_PAGES - 1)

    return sorted({
        round(i * step)
        for i in range(LLM_JUDGE_MAX_PAGES)
    })


def evaluate_document_pages(
    pdf_path: str | Path,
    extracted_pages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Evaluate representative PDF pages using the notebook's visual LLM Judge.
    """

    logger = logging.getLogger(__name__)

    results: List[Dict[str, Any]] = []
    resolved_pdf_path = Path(pdf_path)
    rendered_page_paths: List[Path] = []

    try:
        with fitz.open(str(resolved_pdf_path)) as document:

            render_id = uuid4().hex

            # Select pages according to configuration
            selected_pages = select_pages(document.page_count)

            logger.info(
                "LLM Judge evaluating %d/%d pages: %s",
                len(selected_pages),
                document.page_count,
                [page + 1 for page in selected_pages],
            )

            for page_index in selected_pages:

                page = document[page_index]

                if len(extracted_pages) == document.page_count:
                    page_markdown = str(
                        extracted_pages[page_index].get("text", "")
                    )
                else:
                    # Current extractor returns aggregated text.
                    # Recreate the notebook page-level text.
                    page_markdown = page.get_text()

                image_path = resolved_pdf_path.parent / (
                    f".{resolved_pdf_path.stem}_{render_id}_page_{page_index + 1}.png"
                )

                rendered_page_paths.append(image_path)

                page.get_pixmap(dpi=200).save(str(image_path))

                result = evaluate_page(
                    str(image_path),
                    page_markdown,
                )

                result["page"] = page_index + 1

                results.append(result)

    finally:
        for image_path in rendered_page_paths:
            image_path.unlink(missing_ok=True)

    return results