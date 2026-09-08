"""Preprocessing orchestration helpers."""

from typing import Any, Dict, List

from app.services.preprocessing.cleaning import clean_extracted_text
from app.services.preprocessing.chunking import chunk_document
from app.services.preprocessing.keywords import extract_article_keywords
from app.services.preprocessing.metadata import extract_article_metadata
from app.services.preprocessing.sections import detect_sections

CORE_SECTIONS = {
    "title",
    "abstract",
    "introduction",
    "results",
    "discussion",
    "conclusion",
}
OPTIONAL_SECTIONS = {
    "methodology",
    "methods",
    "materials and methods",
    "related work",
    "background",
}
EXCLUDED_SECTIONS = {
    "references",
    "bibliography",
    "acknowledgements",
    "acknowledgments",
    "appendix",
    "supplementary material",
}


def select_relevant_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Assign the notebook's priority to each detected section."""
    selected_sections = []
    for section in sections:
        section_name = str(section.get("section_name", "")).strip().lower()
        selected_section = section.copy()

        if section_name in CORE_SECTIONS:
            selected_section["priority"] = "core"
        elif section_name in OPTIONAL_SECTIONS:
            selected_section["priority"] = "optional"
        elif section_name in EXCLUDED_SECTIONS:
            selected_section["priority"] = "excluded"
        else:
            selected_section["priority"] = "unknown"

        selected_sections.append(selected_section)

    return selected_sections


def remove_excluded_sections(
    selected_sections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Remove sections marked as excluded before chunking."""
    return [
        section
        for section in selected_sections
        if section.get("priority") != "excluded"
    ]


def preprocess_document(cleaned_text: str, pdf_path: str | None = None) -> Dict[str, Any]:
    """Run the preprocessing services and return notebook-compatible artifacts."""
    cleaned_content, page_tagged_lines, cleaning_report = clean_extracted_text(cleaned_text)
    sections, missing_sections = detect_sections(page_tagged_lines)
    article_metadata = extract_article_metadata(cleaned_content, pdf_path=pdf_path)
    article_keywords = extract_article_keywords(
        cleaned_content,
        language=article_metadata.get("language", "en"),
        top_n=15,
        keywords_per_section=5,
    )
    selected_sections = select_relevant_sections(sections)
    filtered_sections = remove_excluded_sections(selected_sections)
    chunked_sections = chunk_document(filtered_sections)
    return {
        "cleaned_text": cleaned_content,
        "page_tagged_lines": page_tagged_lines,
        "cleaning_report": cleaning_report,
        "sections": sections,
        "missing_sections": missing_sections,
        "selected_sections": selected_sections,
        "filtered_sections": filtered_sections,
        "chunked_sections": chunked_sections,
        "article_metadata": article_metadata,
        "article_keywords": article_keywords,
    }
