from app.services.quality.judge import SummaryQualityJudge


source = {
    "metadata": {
        "title": "Test Scientific Paper",
        "authors": ["Author One"],
        "year": 2025,
        "source": "Example Journal",
        "doi": None,
        "page_count": 5,
    },
    "keywords": [
        "document conversion",
        "OCR",
        "GPU",
    ],
    "sections": {
        "main_topic": """
        The paper presents a document conversion system designed
        to improve document processing performance.
        """,
        "problem_statement": """
        Document processing can be computationally expensive,
        especially when OCR is involved.
        """,
        "objectives": """
        The objective is to evaluate document conversion performance
        using GPU acceleration.
        """,
        "methodology": """
        The system was evaluated using an NVIDIA A40 GPU.
        """,
        "main_results": """
        OCR processing achieved an 8x speedup.
        """,
        "scientific_contributions": """
        The paper presents a GPU-accelerated document conversion
        approach.
        """,
        "limitations": """
        No explicit limitations were identified in the source.
        """,
        "future_work": """
        No explicit future work was identified in the source.
        """,
    },
}


summary = {
    "metadata": {
        "title": "Test Scientific Paper",
        "authors": ["Author One"],
        "year": 2025,
        "source": "Example Journal",
        "doi": None,
        "page_count": 5,
    },
    "main_topic": (
        "The paper presents a document conversion system "
        "designed to improve document processing performance."
    ),
    "problem_statement": (
        "Document processing can be computationally expensive, "
        "especially when OCR is involved."
    ),
    "objectives": (
        "The objective is to evaluate document conversion "
        "performance using GPU acceleration."
    ),
    "methodology": (
        "The system was evaluated using an NVIDIA A40 GPU."
    ),
    "main_results": (
        "OCR processing achieved an 8x speedup."
    ),
    "scientific_contributions": (
        "The paper presents a GPU-accelerated document "
        "conversion approach."
    ),
    "limitations": (
        "No explicit limitations were identified in the source."
    ),
    "future_work": (
        "No explicit future work was identified in the source."
    ),
    "keywords": [
        "document conversion",
        "OCR",
        "GPU",
    ],
    "executive_summary": (
        "The paper evaluates a GPU-accelerated document conversion "
        "system and reports an 8x OCR speedup using an NVIDIA A40 GPU."
    ),
    "key_takeaways": [
        "The system uses GPU acceleration.",
        "The evaluation uses an NVIDIA A40 GPU.",
        "OCR processing achieved an 8x speedup.",
    ],
}


judge = SummaryQualityJudge()

result = judge.evaluate(
    source=source,
    summary=summary,
)

print(result)
from app.services.quality.judge_prompt import build_judge_prompt

prompt = build_judge_prompt(
    source=source,
    summary=summary,
)

print("PROMPT CHARACTERS =", len(prompt))
print("PROMPT WORDS      =", len(prompt.split()))
print("PROMPT LINES      =", len(prompt.splitlines()))