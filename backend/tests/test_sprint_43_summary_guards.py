import json
from io import StringIO
from unittest.mock import MagicMock

from app.services.export.pdf_generator import _load_persisted_summary
from app.services.preprocessing.metadata import extract_article_metadata
from app.services.summarization.merge_summary import build_merge_prompt, finalize_summary, parse_summary_to_json
import ollama

METADATA = {"title": "Benchmark paper", "authors": [], "year": 2025, "source": None, "doi": None, "page_count": 3, "language": "en"}
KEYWORDS = {"global_keywords": [{"keyword": "docling", "score": 0.9, "method": "tfidf"}, {"keyword": "table recognition", "score": 0.8, "method": "tfidf"}]}


def _summary_with_required_sections():
    sections = {
        "Main Topic": "Topic.", "Problem Statement": "Problem.", "Objectives": "Objective.",
        "Methodology": "Method.", "Main Results": "- Docling: 0.49 sec/page on Nvidia L4 GPU with OCR enabled.",
        "Scientific Contributions": "- The paper presents a modular pipeline.",
        "Limitations": "No explicit limitations were identified in the source.",
        "Future Work": "The authors plan an evaluation framework.", "Keywords": "- invented keyword",
        "Executive Summary (maximum 5 lines)": "Topic, method, finding, and conclusion.",
        "Key Takeaways": "- First concrete finding.\n- Second concrete finding.\n- Third concrete finding.",
    }
    return "# Scientific Summary\n\n## Metadata\n\nignored\n\n---\n\n" + "\n\n---\n\n".join(f"## {heading}\n\n{content}" for heading, content in sections.items())


def test_required_sections_keywords_and_grounded_sections():
    markdown = finalize_summary(_summary_with_required_sections(), METADATA, KEYWORDS)
    structured = parse_summary_to_json(markdown, METADATA, KEYWORDS)
    for heading in ("Metadata", "Main Topic", "Problem Statement", "Objectives", "Methodology", "Main Results", "Scientific Contributions", "Limitations", "Future Work", "Keywords", "Executive Summary (maximum 5 lines)", "Key Takeaways"):
        assert f"## {heading}" in markdown
    assert "- docling\n- table recognition" in markdown
    assert "invented keyword" not in markdown
    assert structured["keywords"] == KEYWORDS
    assert structured["limitations"] == "No explicit limitations were identified in the source."
    assert "plan" not in structured["scientific_contributions"].lower()
    assert structured["future_work"] == "The authors plan an evaluation framework."


def test_keyword_artifact_is_the_shared_json_markdown_pdf_source():
    markdown = finalize_summary(_summary_with_required_sections(), METADATA, KEYWORDS)
    json_path, markdown_path = MagicMock(), MagicMock()
    json_path.is_file.return_value = True
    json_path.open.return_value.__enter__.return_value = StringIO(
        json.dumps({"summary_markdown": markdown})
    )
    assert _load_persisted_summary(json_path, markdown_path) == markdown
    assert "- docling\n- table recognition" in markdown
    assert parse_summary_to_json(markdown, METADATA, KEYWORDS)["keywords"] == KEYWORDS


def test_merge_prompt_requires_numerical_attribution_and_grounded_sections():
    prompt = build_merge_prompt(METADATA, KEYWORDS, [{"summary": "source"}])
    assert "ENTITY -> VALUE -> METRIC -> UNIT -> CONFIGURATION" in prompt
    assert "Never move a value between tools" in prompt
    assert "No explicit limitations were identified in the source." in prompt
    assert "Do not include planned, proposed, or future work" in prompt
    assert "Copy its global_keywords exactly" in prompt


def test_metadata_recovers_header_and_preserves_missing_values():
    text = ("A Scientific Toolkit for Conversion\nAda Lovelace*, Grace Hopper, Alan Turing\n"
            "Institute of Computing\nAbstract\nThis paper presents a toolkit.\n"
            "Copyright © 2025, Example Scientific Society. All rights reserved.\n")
    metadata = extract_article_metadata(text)
    assert metadata["authors"] == ["Ada Lovelace", "Grace Hopper", "Alan Turing"]
    assert metadata["extraction_sources"]["authors"] == "Document header"
    assert metadata["source"] == "Example Scientific Society"
    markdown = finalize_summary(_summary_with_required_sections(), METADATA, KEYWORDS)
    assert "**Authors:**\nNot available" in markdown
    assert "**Source:**\nNot available" in markdown
