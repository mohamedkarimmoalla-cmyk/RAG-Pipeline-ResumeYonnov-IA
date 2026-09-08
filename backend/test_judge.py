from app.services.quality.judge import SummaryQualityJudge

source = {
    "metadata": {
        "title": "Test Scientific Paper",
        "authors": ["Author One"],
        "year": 2025,
        "source": "Example Journal",
        "doi": None,
        "page_count": 5
    },
    "keywords": [
        "document conversion",
        "OCR",
        "GPU"
    ],
    "sections": {
        "main_results": """
        The system was evaluated using an NVIDIA A40 GPU.
        OCR processing achieved an 8x speedup.
        """
    }
}

summary = {
    "metadata": {
        "title": "Test Scientific Paper",
        "authors": ["Author One"],
        "year": 2025,
        "source": "Example Journal",
        "doi": None,
        "page_count": 5
    },
    "main_topic": "A document conversion system.",
    "problem_statement": "Document processing is challenging.",
    "objectives": "Evaluate document conversion performance.",
    "methodology": "The system was evaluated using GPU acceleration.",
    "main_results": """
        The system was evaluated using an NVIDIA A50 GPU.
        OCR processing achieved a 6x speedup.
    """,
    "scientific_contributions": "The paper presents a document conversion system.",
    "limitations": "No explicit limitations were identified in the source.",
    "future_work": "No explicit future work was identified in the source.",
    "keywords": [
        "document conversion",
        "OCR",
        "GPU"
    ],
    "executive_summary": "The paper evaluates document conversion performance.",
    "key_takeaways": [
        "The system uses GPU acceleration.",
        "OCR performance was evaluated.",
        "Document conversion was studied."
    ]
}

judge = SummaryQualityJudge()

result = judge.evaluate(
    source=source,
    summary=summary,
)

print(result)
