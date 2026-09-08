"""Metadata extraction helpers for the preprocessing stage."""

import re
from datetime import datetime
from typing import Any, Dict, Optional

try:
    import fitz
except ImportError:  # pragma: no cover - optional dependency
    fitz = None

try:
    import spacy
except ImportError:  # pragma: no cover - optional dependency
    spacy = None


def normalize_value(value: Any) -> Any:
    """Normalize metadata values into JSON-friendly types."""
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip()
    invalid_values = {"", "none", "null", "unknown", "untitled", "non trouvé", "n/a"}
    if value.lower() in invalid_values:
        return None
    return value


def remove_markdown(text: str) -> str:
    """Remove markdown formatting from text."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"[*_`>|]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_authors(author_text: Any) -> list[str]:
    """Split author text into a list of author names."""
    author_text = normalize_value(author_text)
    if not author_text:
        return []
    authors = re.split(r"\s*;\s*|\s*,\s*(?=[A-ZÀ-ÖØ-Ý])|\s+\band\s+|\s+\bet\s+", author_text, flags=re.IGNORECASE)
    return [author.strip() for author in authors if 2 <= len(author.strip()) <= 100]


def get_pdf_information(pdf_path: Optional[str]) -> Dict[str, Any]:
    """Return internal PDF metadata and page count when available."""
    empty_information = {
        "title": None,
        "authors": None,
        "subject": None,
        "creation_date": None,
        "page_count": None,
    }
    if not pdf_path or fitz is None:
        return empty_information
    try:
        with fitz.open(pdf_path) as document:
            pdf_metadata = document.metadata or {}
            return {
                "title": normalize_value(pdf_metadata.get("title")),
                "authors": normalize_value(pdf_metadata.get("author")),
                "subject": normalize_value(pdf_metadata.get("subject")),
                "creation_date": normalize_value(pdf_metadata.get("creationDate")),
                "page_count": document.page_count,
            }
    except Exception:
        return empty_information


def detect_language(text: str) -> str:
    """Light language detection between French and English."""
    sample = text[:10000].lower()
    french_words = {"le", "la", "les", "des", "une", "dans", "pour", "avec", "nous", "résultats", "méthode"}
    english_words = {"the", "and", "of", "in", "for", "with", "we", "results", "method", "this"}
    words = set(re.findall(r"\b[a-zA-ZÀ-ÿ]+\b", sample))
    french_score = len(words.intersection(french_words))
    english_score = len(words.intersection(english_words))
    return "fr" if french_score > english_score else "en"


def extract_title(text: str, pdf_information: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """Extract the main title from text or PDF metadata."""
    pdf_title = pdf_information.get("title")
    invalid_title_fragments = {"microsoft word", "untitled", ".docx", ".pdf"}
    if pdf_title:
        title_lower = pdf_title.lower()
        if not any(fragment in title_lower for fragment in invalid_title_fragments):
            return pdf_title, "PDF metadata"
    first_lines = [normalize_value(line.lstrip("#").strip()) for line in text[:5000].splitlines()]
    excluded_words = {"abstract", "résumé", "introduction", "keywords", "mots-clés", "contents", "table of contents"}
    for line in first_lines[:30]:
        if not line:
            continue
        if not 15 <= len(line) <= 300:
            continue
        if line.lower() in excluded_words:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        return line, "First relevant text line"
    return None, None


def extract_authors(text: str, title: Optional[str], pdf_information: Dict[str, Any], language: str) -> tuple[list[str], Optional[str]]:
    """Extract author names from PDF metadata, the header, or NER when available."""
    pdf_authors = split_authors(pdf_information.get("authors"))
    if pdf_authors:
        return pdf_authors, "PDF metadata"
    header = text[:5000]
    abstract_match = re.search(r"\b(?:abstract|résumé)\b", header, flags=re.IGNORECASE)
    if abstract_match:
        header = header[:abstract_match.start()]
    # Scientific PDFs commonly put their explicit author list directly below the title.
    header_lines = [remove_markdown(line) for line in header.splitlines()]
    title_index = next((
        index for index, line in enumerate(header_lines)
        if title and line and line.casefold() == title.casefold()
    ), None)
    if title_index is not None:
        candidate_lines: list[str] = []
        for line in header_lines[title_index + 1:title_index + 5]:
            if not line or re.search(r"@|\b(?:abstract|university|institute|research|department|correspondence)\b", line, re.IGNORECASE):
                break
            candidate_lines.append(line)
        header_authors = split_authors(" ".join(candidate_lines).replace("*", " "))
        if header_authors and all(2 <= len(author.split()) <= 5 for author in header_authors):
            return header_authors, "Document header"

    header = remove_markdown(header)
    if title:
        header = header.replace(title, " ")
    if spacy is None:
        return [], None
    nlp = None
    try:
        if language == "fr":
            nlp = spacy.load("fr_core_news_sm")
        else:
            nlp = spacy.load("en_core_web_sm")
    except OSError:
        return [], None
    document = nlp(header[:3000])
    authors: list[str] = []
    for entity in document.ents:
        if entity.label_ not in {"PERSON", "PER"}:
            continue
        name = normalize_value(entity.text)
        if not name:
            continue
        number_of_words = len(name.split())
        if not 2 <= number_of_words <= 5:
            continue
        if any(character.isdigit() for character in name):
            continue
        if name.lower() not in [author.lower() for author in authors]:
            authors.append(name)
    return authors[:20], "spaCy"


def extract_doi(text: str) -> Optional[str]:
    """Extract a DOI from the text."""
    match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(0).rstrip(".,;:)")


def extract_year(text: str, pdf_information: Dict[str, Any]) -> Optional[int]:
    """Extract a publication year from text or PDF metadata."""
    current_year = datetime.now().year
    years = re.findall(r"\b(?:19\d{2}|20\d{2})\b", text[:8000])
    for year_text in years:
        year = int(year_text)
        if 1900 <= year <= current_year + 1:
            return year
    creation_date = pdf_information.get("creation_date")
    if creation_date:
        match = re.search(r"(?:19\d{2}|20\d{2})", creation_date)
        if match:
            year = int(match.group())
            if 1900 <= year <= current_year + 1:
                return year
    return None


def extract_source(text: str, pdf_information: Dict[str, Any]) -> Optional[str]:
    """Extract the publication source from text or PDF metadata."""
    header = text[:8000]
    copyright_match = re.search(
        r"copyright\b[^\d]{0,12}(?:19|20)\d{2}\s*,?\s*([^\n]{3,180})(?:\n([A-Z][^\n]{0,180}))?",
        header,
        flags=re.IGNORECASE,
    )
    if copyright_match:
        source = " ".join(part for part in copyright_match.groups() if part)
        source = re.sub(r"\s*\([^)]*\).*", "", source)
        source = re.sub(r"\s+all rights reserved\.?\s*$", "", source, flags=re.IGNORECASE)
        source = normalize_value(source.rstrip(".,;: "))
        if source:
            return source
    patterns = [
        r"(?:journal|published\s+in)\s*[:\-]\s*([^\n]{3,180})",
        r"(?:conference|proceedings)\s*[:\-]\s*([^\n]{3,180})",
        r"(?:revue|conférence)\s*[:\-]\s*([^\n]{3,180})",
    ]
    for pattern in patterns:
        match = re.search(pattern, header, flags=re.IGNORECASE)
        if match:
            return normalize_value(match.group(1))
    pdf_subject = pdf_information.get("subject")
    if pdf_subject and len(pdf_subject) <= 200:
        return pdf_subject
    return None


def extract_article_metadata(cleaned_text: str, pdf_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract the metadata structure used by the notebook pipeline."""
    pdf_information = get_pdf_information(pdf_path)
    language = detect_language(cleaned_text)
    title, title_source = extract_title(cleaned_text, pdf_information)
    authors, authors_source = extract_authors(cleaned_text, title, pdf_information, language)
    year = extract_year(cleaned_text, pdf_information)
    source = extract_source(cleaned_text, pdf_information)
    doi = extract_doi(cleaned_text)
    page_count = pdf_information.get("page_count")
    metadata = {
        "title": title,
        "authors": authors,
        "year": year,
        "source": source,
        "doi": doi,
        "page_count": page_count,
        "language": language,
        "extraction_sources": {
            "title": title_source,
            "authors": authors_source,
            "year": "Text or PDF metadata" if year else None,
            "source": "Text or PDF metadata" if source else None,
            "doi": "Regex" if doi else None,
            "page_count": "PDF" if page_count else None,
        },
    }
    required_fields = ["title", "authors", "year", "source"]
    optional_fields = ["doi", "page_count"]
    metadata["missing_required_fields"] = [field for field in required_fields if metadata.get(field) in (None, "", [])]
    metadata["missing_optional_fields"] = [field for field in optional_fields if metadata.get(field) in (None, "", [])]
    metadata["can_continue_summarization"] = True
    if metadata["missing_required_fields"]:
        metadata["status"] = "completed_with_missing_fields"
    elif metadata["missing_optional_fields"]:
        metadata["status"] = "completed_with_missing_optional_fields"
    else:
        metadata["status"] = "complete"
    return metadata
