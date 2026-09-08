"""Deterministic extractive fallback summarization."""

import re
from typing import Any, Dict, List


INTRODUCTION_SECTIONS = {
    "introduction",
    "background",
    "contexte",
    "related work",
    "travaux connexes",
}

METHODOLOGY_SECTIONS = {
    # Standard scientific headings
    "method",
    "methods",
    "methodology",
    "méthode",
    "méthodes",
    "méthodologie",
    "materials and methods",

    # Technical methodology headings
    "approach",
    "approaches",
    "approche",
    "approches",
    "system",
    "system architecture",
    "architecture",
    "architecture and design",
    "pipeline",
    "document pipeline",
    "implementation",
    "implementation details",
    "technical approach",
    "experimental setup",
    "experimental setup and evaluation",

    # Model / processing descriptions
    "models",
    "model",
    "standardpdfpipeline",
}

METHODOLOGY_CONTENT_SECTIONS = {
    "pipeline",
    "architecture",
    "system",
    "approach",
    "implementation",
    "models",
    "experimental setup",
    "standardpdfpipeline",
}

RESULT_SECTIONS = {
    "results",
    "résultats",
}

CONTRIBUTION_SECTIONS = {
    "contributions",
    "scientific contributions",
    "contributions scientifiques",
    
}

LIMITATION_SECTIONS = {
    "limitations",
    "limites",
}

FUTURE_WORK_SECTIONS = {
    "future work",
    "perspectives",
}

def clean_extraction_artifacts(text: str) -> str:
    """Remove obvious figure, chart, and table extraction artifacts."""

    if not text:
        return ""

    # Normalize whitespace while preserving sentence boundaries.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove common figure/table caption blocks.
    # These are usually captions followed by extracted chart labels.
    text = re.sub(
        r"(?:^|\n)\s*(?:Figure|Fig\.|Table|Tab\.)\s*\d+\s*[:.\-].*?"
        r"(?=(?:\n\s*(?:Figure|Fig\.|Table|Tab\.)\s*\d+\s*[:.\-])|$)",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Remove standalone chart-axis / benchmark fragments.
    artifact_fragments = [
        r"\bsec\s*/\s*page\b",
        r"\bpages?\s*/\s*sec\b",
        r"\bx86\s+CPU\b",
        r"\bM3\s+Max\b",
        r"\bL4\s+GPU\b",
        r"\bA40\s+GPU\b",
        r"\bT4\s+GPU\b",
    ]

    for pattern in artifact_fragments:
        text = re.sub(
            pattern,
            " ",
            text,
            flags=re.IGNORECASE,
        )

    # Remove repeated chart-label sequences.
    text = re.sub(
        r"\b(?:PDF\s+Parse\s+OCR\s+Layout\s+Table\s+Structure)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Remove numeric chart-axis sequences such as:
    # 0.0 0.5 1.0 1.5 2.0 2.5 3.0
    text = re.sub(
        r"(?:\b\d+(?:\.\d+)?\b[\s,]*){4,}",
        " ",
        text,
    )

    # Remove repeated "Page Total" chart labels.
    text = re.sub(
        r"\bPage\s+Total\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Normalize whitespace again.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()

def split_sentences(text: str) -> List[str]:
    """Split text into simple sentences."""
    text = clean_extraction_artifacts(text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)

    return [
        sentence.strip()
        for sentence in sentences
        if len(sentence.strip()) >= 40
        and not is_low_quality_sentence(sentence)
    ]

def is_low_quality_sentence(sentence: str) -> bool:
    """Detect obvious extraction, figure, table, or OCR artifacts."""

    normalized = re.sub(r"\s+", " ", sentence).strip().lower()

    if not normalized:
        return True

    # Very short fragments are usually not useful narrative sentences.
    words = normalized.split()
    if len(words) < 6:
        return True

    # Common figure/table/caption markers.
    artifact_patterns = [
        r"^figure\s+\d+",
        r"^fig\.\s*\d+",
        r"^table\s+\d+",
        r"^tab\.\s*\d+",
        r"^figure\s+\d+\s*[:\-]",
        r"^table\s+\d+\s*[:\-]",
    ]

    for pattern in artifact_patterns:
        if re.search(pattern, normalized):
            return True

    # Typical chart-axis / benchmark fragments.
    technical_fragments = {
        "sec/page",
        "sec / page",
        "pages/sec",
        "page/sec",
        "x86 cpu",
        "m3 max",
        "l4 gpu",
        "a40 gpu",
        "t4 gpu",
    }

    if normalized in technical_fragments:
        return True

    # Extraction often produces strings that are mostly labels,
    # separated by spaces rather than forming a real sentence.
    alpha_words = re.findall(r"[a-zà-ÿ]+", normalized)

    if len(alpha_words) >= 6:
        unique_ratio = len(set(alpha_words)) / len(alpha_words)

        if unique_ratio < 0.45:
            return True

    # Sentences with very little alphabetic content are usually
    # chart/table/OCR artifacts.
    alpha_chars = sum(
        1 for char in normalized
        if char.isalpha()
    )

    if len(normalized) > 0:
        alpha_ratio = alpha_chars / len(normalized)

        if alpha_ratio < 0.55:
            return True

    return False


def _get_methodology_sentences(
    partial_summaries: List[Dict[str, Any]],
    keywords: List[str],
) -> List[str]:
    """Collect methodology-related sentences from technical sections."""

    methodology_sentences = _find_sentences_by_sections(
        partial_summaries,
        METHODOLOGY_SECTIONS,
    )

    # If explicit methodology sections are unavailable,
    # use technical/system sections as a fallback.
    if not methodology_sentences:
        methodology_sentences = _find_sentences_by_sections(
            partial_summaries,
            METHODOLOGY_CONTENT_SECTIONS,
        )

    return methodology_sentences

def score_sentence(
    sentence: str,
    keywords: List[str],
) -> float:
    """Score a sentence using keyword coverage and sentence length."""
    normalized = sentence.lower()

    keyword_score = sum(
        1
        for keyword in keywords
        if keyword.lower() in normalized
    )

    words = sentence.split()

    # Prefer informative but not excessively long sentences.
    length_score = min(len(words) / 30.0, 1.0)

    return keyword_score * 2.0 + length_score


def _extract_keyword_values(
    keywords: Dict[str, Any] | None,
) -> List[str]:
    """Extract normalized keyword strings from the keyword artifact."""
    if not keywords:
        return []

    keyword_values: List[str] = []

    for item in keywords.get("global_keywords", []):
        if isinstance(item, dict):
            keyword = item.get("keyword")
        else:
            keyword = item

        if keyword:
            keyword_values.append(str(keyword).strip())

    return keyword_values


def generate_extractive_partial_summary(
    chunk: Dict[str, Any],
    keywords: Dict[str, Any] | None = None,
    max_sentences: int = 3,
) -> str:
    """Generate a deterministic extractive summary from one chunk."""
    content = str(chunk.get("content", "")).strip()

    if not content:
        return "Not available"

    sentences = split_sentences(content)

    if not sentences:
        return content[:500]

    keyword_values = _extract_keyword_values(keywords)

    ranked = sorted(
        enumerate(sentences),
        key=lambda item: score_sentence(
            item[1],
            keyword_values,
        ),
        reverse=True,
    )

    selected_indexes = sorted(
        index
        for index, _ in ranked[:max_sentences]
    )

    selected_sentences = [
        sentences[index]
        for index in selected_indexes
    ]

    return " ".join(selected_sentences)


def _get_section_summaries(
    partial_summaries: List[Dict[str, Any]],
) -> Dict[str, str]:
    """Group partial summaries by their source section."""
    grouped: Dict[str, List[str]] = {}

    for item in partial_summaries:
        section_name = str(
            item.get("section_name", "")
        ).strip().lower()

        summary = str(
            item.get("summary", "")
        ).strip()

        if not section_name or not summary:
            continue

        grouped.setdefault(section_name, []).append(summary)

    return {
        section: " ".join(values)
        for section, values in grouped.items()
    }
def _find_sentences_by_sections(
    partial_summaries: List[Dict[str, Any]],
    target_sections: set[str],
) -> List[str]:
    """Collect sentences from partial summaries belonging to target sections."""

    sentences: List[str] = []

    for item in partial_summaries:
        section_name = str(
            item.get("section_name", "")
        ).strip().lower()

        if section_name not in target_sections:
            continue

        summary = str(
            item.get("summary", "")
        ).strip()

        if not summary:
            continue

        sentences.extend(split_sentences(summary))

    return sentences


def _select_best_sentence(
    sentences: List[str],
    keywords: List[str],
) -> str:
    """Select the most relevant sentence deterministically."""

    if not sentences:
        return ""

    ranked = sorted(
        enumerate(sentences),
        key=lambda item: score_sentence(
            item[1],
            keywords,
        ),
        reverse=True,
    )

    return ranked[0][1]
def _select_methodology_from_available_sections(
    section_summaries: Dict[str, str],
    keywords: List[str],
    max_sentences: int = 2,
) -> str:
    """Extract methodology-related sentences from available sections."""

    candidate_sections = [
        "method",
        "methods",
        "methodology",
        "approach",
        "architecture",
        "pipeline",
        "system",
        "implementation",
        "experimental setup",
        "introduction",
    ]

    methodology_sentences: List[str] = []

    for section_name in candidate_sections:
        section_text = section_summaries.get(
            section_name,
            "",
        )

        if not section_text:
            continue

        sentences = split_sentences(section_text)

        for sentence in sentences:
            normalized = sentence.lower()

            methodology_terms = [
                "pipeline",
                "architecture",
                "model",
                "models",
                "method",
                "approach",
                "system",
                "implementation",
                "algorithm",
                "processing",
                "detection",
                "recognition",
                "classification",
                "layout",
                "table",
                "document conversion",
            ]

            term_score = sum(
                1
                for term in methodology_terms
                if term in normalized
            )

            keyword_score = score_sentence(
                sentence,
                keywords,
            )

            if term_score > 0:
                methodology_sentences.append(
                    (
                        term_score * 5
                        + keyword_score,
                        sentence,
                    )
                )

    if not methodology_sentences:
        return ""

    methodology_sentences.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    selected: List[str] = []
    seen = set()

    for _, sentence in methodology_sentences:
        normalized = sentence.lower()

        if normalized in seen:
            continue

        selected.append(sentence)
        seen.add(normalized)

        if len(selected) >= max_sentences:
            break

    return " ".join(selected)

def is_likely_artifact(sentence: str) -> bool:
    """Detect table, figure, reference, or extraction artifacts."""

    normalized = re.sub(
        r"\s+",
        " ",
        sentence.strip().lower(),
    )

    if not normalized:
        return True

    # Obvious table / figure artifacts.
    artifact_prefixes = (
        "table ",
        "table i",
        "table ii",
        "table iii",
        "table iv",
        "table v",
        "figure ",
        "fig. ",
        "fig ",
        "references",
        "bibliography",
    )

    if normalized.startswith(artifact_prefixes):
        return True

    # Typical extracted table vocabulary.
    table_terms = [
        "document category",
        "pages with tables",
        "layout evaluations",
        "total",
        "single-column",
        "multi-column",
        "financial reports",
        "scientific articles",
        "laws & regulations",
        "government tenders",
    ]

    table_term_count = sum(
        1
        for term in table_terms
        if term in normalized
    )

    if table_term_count >= 2:
        return True

    # Very short fragments are usually not useful
    # as scientific summary sentences.
    words = normalized.split()

    if len(words) < 8:
        return True

    # A sentence containing many isolated numbers is
    # often a table extraction artifact.
    numeric_tokens = sum(
        1
        for word in words
        if re.search(r"\d", word)
    )

    if len(words) >= 8:
        numeric_ratio = numeric_tokens / len(words)

        if numeric_ratio >= 0.30:
            return True

    return False

def select_semantic_sentences(
    text: str,
    keywords: List[str],
    preferred_terms: List[str],
    excluded_terms: List[str] | None = None,
    max_sentences: int = 2,
    minimum_score: float = 0.0,
) -> List[str]:
    """Select sentences according to semantic evidence.

    The function is deterministic and does not use an LLM.
    Sentences must contain at least one preferred semantic term
    when preferred terms are provided.
    """

    if not text:
        return []

    sentences = split_sentences(text)

    if not sentences:
        return []

    excluded_terms = excluded_terms or []

    scored = []

    for index, sentence in enumerate(sentences):
        normalized = sentence.lower()
        if is_likely_artifact(sentence):
            continue

        # Base informativeness score.
        score = score_sentence(
            sentence,
            keywords,
        )

        # Count semantic evidence.
        matched_preferred = 0

        for term in preferred_terms:
            if term.lower() in normalized:
                score += 5.0
                matched_preferred += 1

        # Penalize sentences belonging to another semantic role.
        for term in excluded_terms:
            if term.lower() in normalized:
                score -= 5.0

        # If semantic terms were explicitly provided,
        # require at least one match.
        if preferred_terms and matched_preferred == 0:
            continue

        # Small position penalty to preserve document relevance.
        score -= index * 0.01

        if score < minimum_score:
            continue

        scored.append(
            (
                score,
                index,
                sentence,
            )
        )

    # Highest semantic evidence first.
    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    selected = []
    seen = set()

    for _, _, sentence in scored:
        normalized = sentence.lower().strip()

        if normalized in seen:
            continue

        selected.append(sentence)
        seen.add(normalized)

        if len(selected) >= max_sentences:
            break

    # Restore original document order.
    selected_with_indexes = []

    for sentence in selected:
        for index, original in enumerate(sentences):
            if original == sentence:
                selected_with_indexes.append(
                    (
                        index,
                        sentence,
                    )
                )
                break

    selected_with_indexes.sort(
        key=lambda item: item[0]
    )

    return [
        sentence
        for _, sentence in selected_with_indexes
    ]

def generate_extractive_final_summary(
    metadata: Dict[str, Any],
    keywords: Dict[str, Any],
    partial_summaries: List[Dict[str, Any]],
) -> str:
    """Build a deterministic, section-aware final Markdown summary."""

    language = str(
        metadata.get("language", "en")
    ).strip().lower()

    is_english = language == "en"

    unavailable = (
        "Not available"
        if is_english
        else "Non disponible"
    )

    if is_english:
        labels = {
            "title": "Title",
            "authors": "Authors",
            "year": "Year",
            "source": "Source",
            "doi": "DOI",
            "pages": "Total Number of Pages",
        }

        sections = {
            "metadata": "Metadata",
            "main_topic": "Main Topic",
            "problem": "Problem Statement",
            "objectives": "Objectives",
            "methodology": "Methodology",
            "results": "Main Results",
            "contributions": "Scientific Contributions",
            "limitations": "Limitations",
            "future_work": "Future Work",
            "keywords": "Keywords",
            "executive": "Executive Summary (maximum 5 lines)",
            "takeaways": "Key Takeaways",
        }

        title = "Scientific Summary"

    else:
        labels = {
            "title": "Titre",
            "authors": "Auteurs",
            "year": "Année",
            "source": "Source",
            "doi": "DOI",
            "pages": "Nombre de pages",
        }

        sections = {
            "metadata": "Métadonnées",
            "main_topic": "Sujet principal",
            "problem": "Problématique",
            "objectives": "Objectifs",
            "methodology": "Méthodologie",
            "results": "Résultats principaux",
            "contributions": "Contributions scientifiques",
            "limitations": "Limites",
            "future_work": "Perspectives",
            "keywords": "Mots-clés",
            "executive": "Résumé synthétique (5 lignes maximum)",
            "takeaways": "Points à retenir",
        }

        title = "Résumé scientifique"

    def metadata_value(value: Any) -> str:
        """Format metadata safely without inventing values."""

        if value is None or value == "" or value == []:
            return unavailable

        if isinstance(value, (list, tuple)):
            values = [
                str(item).strip()
                for item in value
                if str(item).strip()
            ]

            return (
                ", ".join(values)
                if values
                else unavailable
            )

        text = str(value).strip()

        return text if text else unavailable

    # --------------------------------------------------------------
    # Section summaries
    # --------------------------------------------------------------

    section_summaries = _get_section_summaries(
        partial_summaries
    )

    keyword_values = _extract_keyword_values(
        keywords
    )



    # --------------------------------------------------------------
    # Generic section retrieval
    # --------------------------------------------------------------

    def get_section_text(
        section_names: set[str],
    ) -> str:
        """Return combined text from matching sections."""

        matching_parts: List[str] = []

        for section_name, content in section_summaries.items():
            normalized_name = (
                str(section_name)
                .strip()
                .lower()
            )

            if normalized_name in section_names:
                matching_parts.append(content)

        return " ".join(matching_parts).strip()

    # --------------------------------------------------------------
    # Sentence selection
    # --------------------------------------------------------------

   

    # --------------------------------------------------------------
    # Generic semantic section groups
    # --------------------------------------------------------------

    abstract_text = get_section_text({
        "abstract",
        "résumé",
        "summary",
    })

    introduction_text = get_section_text(
        INTRODUCTION_SECTIONS
    )

    methodology_text = get_section_text(
        METHODOLOGY_SECTIONS
    )

    results_text = get_section_text(
        RESULT_SECTIONS
    )

    contribution_text = get_section_text(
        CONTRIBUTION_SECTIONS
        - {"future work"}
    )

    limitation_text = get_section_text(
        LIMITATION_SECTIONS
    )

    future_work_text = get_section_text(
        FUTURE_WORK_SECTIONS
    )

    # --------------------------------------------------------------
    # MAIN TOPIC
    # --------------------------------------------------------------

    topic_candidates = select_semantic_sentences(
        abstract_text,
        keyword_values,
        preferred_terms=[
            "we introduce",
            "we propose",
            "we present",
            "we develop",
            "this paper",
            "this work",
            "study",
            "toolkit",
            "framework",
            "system",
        ],
        max_sentences=1,
    )

    if not topic_candidates:
        topic_candidates = select_semantic_sentences(
            introduction_text,
            keyword_values,
            preferred_terms=[
            "we introduce",
            "we propose",
            "we present",
            "we develop",
            "this paper",
            "this work",
            ],
            max_sentences=1,
        )

    topic = (
        topic_candidates[0]
        if topic_candidates
        else unavailable
    )

    # --------------------------------------------------------------
    # PROBLEM STATEMENT
    # --------------------------------------------------------------

    problem_sentences = select_semantic_sentences(
        introduction_text,
        keyword_values,
        preferred_terms=[
            "problem",
            "challenge",
            "challenging",
            "difficulty",
            "issue",
            "limitation",
            "lack",
            "gap",
            "however",
            "despite",
            "remains",
            "need",
            "difficult"
        ],
        excluded_terms=[
            "we propose",
            "we present",
            "we introduce",
            "our contribution",
        ],
        max_sentences=2,
    )

    problem = (
        " ".join(problem_sentences[:1])
        if problem_sentences
        else unavailable
    )

    # --------------------------------------------------------------
    # OBJECTIVES
    # --------------------------------------------------------------

    objective_terms = [
        "objective",
        "objectives",
        "aim",
        "aims",
        "goal",
        "goals",
        "purpose",
        "designed to",
        "intended to",
        "we propose",
        "we present",
        "we introduce",
        "we develop",
        "we investigate",
        "we evaluate",
        "this paper aims",
        "this work aims",
    ]

    # --------------------------------------------------------------
# OBJECTIVES
# --------------------------------------------------------------

    objective_candidates = select_semantic_sentences(
        introduction_text,
        keyword_values,
        preferred_terms=[
            "objective",
            "objectives",
        "aim",
        "aims",
        "goal",
        "goals",
        "purpose",
        "purpose of this work",
        "purpose of this paper",
        "this paper aims",
        "this work aims",
        "we aim",
        "we seek",
        "we intend",
        "we investigate",
        "we evaluate",
        ],
        excluded_terms=[
            "we propose",
            "we introduce",
            "we present",
            "we develop",
            "future",
            "future work",
            "in the future",
            "references",
            "table",
            "figure",
        ],
        max_sentences=2,
        minimum_score=5.0,
    )

    objectives = (
        " ".join(objective_candidates)
        if objective_candidates
        else unavailable
    )
    # --------------------------------------------------------------
    # METHODOLOGY
    # --------------------------------------------------------------

    methodology_text = get_section_text(
        METHODOLOGY_SECTIONS
    )

    methodology_candidates = select_semantic_sentences(
        methodology_text,
        keyword_values,
        preferred_terms=[
            "method",
            "methodology",
            "approach",
            "architecture",
            "pipeline",
            "system",
            "implementation",
            "model",
            "models",
            "algorithm",
            "dataset",
            "experimental",
            "experiment",
            "processing",
            "framework",
            "evaluation",
            "design",
        ],
        excluded_terms=[
            "references",
            "future work",
            "future",
            "we plan",
            "in the future",
        ],
        max_sentences=2,
    )

    # --------------------------------------------------------------
    # If there is no explicit methodology section, search
    # generic technical sections.
    # --------------------------------------------------------------

    if not methodology_candidates:

        technical_sections = {
            "approach",
            "architecture",
            "design",
            "design and architecture",
            "pipeline",
            "pdf conversion pipeline",
            "conversion pipeline",
            "implementation",
            "implementation details",
            "experimental setup",
            "experimental setup and evaluation",
            "models",
            "model",
            "ai models",
            "system",
            "system architecture",
            "technical approach",
        }

        technical_text = get_section_text(
            technical_sections
        )

        # If technical sections exist, use them.
        if technical_text:

            methodology_candidates = select_semantic_sentences(
                technical_text,
                keyword_values,
                preferred_terms=[
                    "pipeline",
                    "architecture",
                    "approach",
                    "system",
                    "model",
                    "models",
                    "algorithm",
                    "processing",
                    "dataset",
                    "implementation",
                    "framework",
                    "evaluation",
                    "experimental",
                    "experiment",
                    "design",
                ],
                excluded_terms=[
                    "future",
                    "we plan",
                    "in the future",
                    "references",
                ],
                max_sentences=2,
            )

    # --------------------------------------------------------------
    # Final fallback: search Introduction for methodological
    # descriptions only if no technical section was detected.
    # --------------------------------------------------------------

    if not methodology_candidates:

        methodology_candidates = select_semantic_sentences(
            introduction_text,
            keyword_values,
            preferred_terms=[
                "approach",
                "architecture",
                "pipeline",
                "system",
                "method",
                "model",
                "framework",
                "algorithm",
                "processing",
                "implementation",
                "designed",
                "consists of",
                "based on",
                "uses",
                "leverages",
            ],
            excluded_terms=[
                "future",
                "we plan",
                "in the future",
                "references",
                "limitation",
            ],
            max_sentences=2,
        )

    methodology = (
        " ".join(methodology_candidates)
        if methodology_candidates
        else unavailable
    )

    # --------------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------------

    result_candidates = select_semantic_sentences(
        results_text,
        keyword_values,
        preferred_terms=[
                    "result",
        "results",
        "finding",
        "findings",
        "our results",
        "our findings",
        "we demonstrate",
        "we demonstrated",
        "we find",
        "we found",
        "results show",
        "results demonstrate",
        "results indicate",
        "results reveal",
        "demonstrate",
        "demonstrates",
        "demonstrated",
        "show",
        "shows",
        "reveals",
        "revealed",
        "indicate",
        "indicates",
        "performance",
        "improvement",
        "improved",
        "achieved",
        "higher",
        "lower",
        "better",
        "worse",
        "inverse",
        "significant",
        "statistically",
        "outperformed",
        "comparison",
        "fidelity",
        "accuracy",
        "score",
        "benchmark",
        "evaluation",
        ],
        excluded_terms=[
        "future work",
        "future",
        "we plan",
        "in the future",
        "references",
        "methodology",
        "architecture",
        "pipeline",
        "implementation",
        ],
        max_sentences=3,
        minimum_score=5.0,
    )

    results = (
        result_candidates
        if result_candidates
        else [unavailable]
    )
    # --------------------------------------------------------------
    # CONTRIBUTIONS
    # --------------------------------------------------------------

    contribution_text = get_section_text({
        "contributions",
        "scientific contributions",
        "contributions scientifiques",
        "future work and contributions",
    })

    contribution_candidates = select_semantic_sentences(
        contribution_text,
        keyword_values,
        preferred_terms=[
        "main contribution",
        "main contributions",
        "we contribute",
        "we propose",
        "we introduced",
        "we introduce",
        "we present",
        "we developed",
        "we develop",
        "we provide",
        "we propose a",
        "we introduce a",
        "novel",
        "new framework",
        "new system",
        "new toolkit",
        ],
        excluded_terms=[
            "future",
            "future work",
            "in the future",
            "we plan",
            "we will",
            "will extend",
            "further work",
            "limitation",
            "limitations",
        ],
        max_sentences=2,
        minimum_score=5.0,
    )

    # --------------------------------------------------------------
    # If there is no explicit contribution section, search
    # the Introduction for contribution statements.
    # --------------------------------------------------------------

    if not contribution_candidates:

        contribution_candidates = select_semantic_sentences(
            abstract_text,
            keyword_values,
            preferred_terms=[
            "we introduce",
            "we propose",
            "we present",
            "we develop",
            "our contribution",
            "our contributions",
            "novel",
            "new toolkit",
            "new framework",
            "new system",
            ],
            excluded_terms=[
                "future",
                "future work",
                "in the future",
                "we plan",
                "we will",
                "limitation",
            ],
            max_sentences=2,
            minimum_score=5.0,
        )
    if not contribution_candidates:
        contribution_candidates = select_semantic_sentences(
        introduction_text,
        keyword_values,
        preferred_terms=[
            "we introduce",
            "we propose",
            "we present",
            "we develop",
            "our contribution",
            "our contributions",
            "novel",
            "new framework",
            "new system",
            "new toolkit",
        ],
        excluded_terms=[
            "future",
            "future work",
            "in the future",
            "we plan",
            "we will",
            "limitation",
        ],
        max_sentences=2,
        minimum_score=5.0,
    )
    contributions = (
     " ".join(contribution_candidates)
    if contribution_candidates
    else unavailable
)

    # --------------------------------------------------------------
    # LIMITATIONS
    # --------------------------------------------------------------

    limitation_text = get_section_text(
        LIMITATION_SECTIONS
    )

    limitation_candidates = select_semantic_sentences(
        limitation_text,
        keyword_values,
        preferred_terms=[
            "limitation",
            "limitations",
            "limited",
            "challenge",
            "drawback",
            "constraint",
            "weakness",
            "shortcoming",
            "restrict",
            "restricted",
        ],
        excluded_terms=[
            "future work",
            "future",
        ],
        max_sentences=2,
    )

    limitations = (
        " ".join(limitation_candidates)
        if limitation_candidates
        else unavailable
    )

    # --------------------------------------------------------------
    # FUTURE WORK
    # --------------------------------------------------------------

    future_work_text = get_section_text(
        FUTURE_WORK_SECTIONS
    )

    future_candidates = select_semantic_sentences(
        future_work_text,
        keyword_values,
        preferred_terms=[
            "future",
            "future work",
            "in the future",
            "we plan",
            "we will",
            "will extend",
            "extend",
            "extension",
            "improve",
            "improvement",
            "further",
            "next",
            "ongoing",
            "planned",
            "plan",
            "focus on",
        ],
        excluded_terms=[
            "limitation",
            "limitations",
            "benchmark",
            "we introduce",
            "we propose",
            "our contribution",
        ],
        max_sentences=2,
    )

    future_work = (
        " ".join(future_candidates)
        if future_candidates
        else unavailable
    )

    # --------------------------------------------------------------
    # EXECUTIVE SUMMARY
    # --------------------------------------------------------------

    executive_candidates = select_semantic_sentences(
        abstract_text,
        keyword_values,
        preferred_terms=[
            "propose",
            "proposed",
            "present",
            "presented",
            "introduce",
            "introduced",
            "develop",
            "developed",
            "results",
            "performance",
            "evaluation",
            "study",
            "paper",
            "work",
        ],
        excluded_terms=[
            "future",
            "references",
        ],
        max_sentences=3,
    )

    if executive_candidates:
        executive_summary = " ".join(
            executive_candidates
        )
    else:
        executive_summary = topic

    # --------------------------------------------------------------
    # KEY TAKEAWAYS
    # --------------------------------------------------------------

    takeaways = result_candidates[:3]

    if not takeaways:
        takeaways = select_semantic_sentences(
            abstract_text,
            keyword_values,
            preferred_terms=[
                "result",
                "results",
                "performance",
                "evaluation",
                "finding",
                "findings",
                "propose",
                "present",
                "introduce",
            ],
            excluded_terms=[
                "future",
                "references",
            ],
            max_sentences=3,
        )

    if not takeaways:
        takeaways = [unavailable]

    # --------------------------------------------------------------
    # KEYWORDS
    # --------------------------------------------------------------

    keyword_lines = [
        f"- {keyword}"
        for keyword in keyword_values[:15]
    ]

    if not keyword_lines:
        keyword_lines = [
            f"- {unavailable}"
        ]

    # --------------------------------------------------------------
    # METADATA
    # --------------------------------------------------------------

    metadata_block = f"""## {sections["metadata"]}

**{labels["title"]}:**
{metadata_value(metadata.get("title"))}

**{labels["authors"]}:**
{metadata_value(metadata.get("authors"))}

**{labels["year"]}:**
{metadata_value(metadata.get("year"))}

**{labels["source"]}:**
{metadata_value(metadata.get("source"))}

**{labels["doi"]}:**
{metadata_value(metadata.get("doi"))}

**{labels["pages"]}:**
{metadata_value(metadata.get("page_count"))}
"""

    # --------------------------------------------------------------
    # RESULTS BULLETS
    # --------------------------------------------------------------

    result_lines = "\n".join(
        f"- {sentence}"
        for sentence in results[:3]
    )

    # --------------------------------------------------------------
    # TAKEAWAY BULLETS
    # --------------------------------------------------------------

    takeaway_lines = "\n".join(
        f"- {sentence}"
        for sentence in takeaways[:3]
    )

    # --------------------------------------------------------------
    # FINAL MARKDOWN
    # --------------------------------------------------------------

    return f"""# {title}

{metadata_block}

---

## {sections["main_topic"]}

{topic}

---

## {sections["problem"]}

{problem}

---

## {sections["objectives"]}

{objectives}

---

## {sections["methodology"]}

{methodology}

---

## {sections["results"]}

{result_lines}

---

## {sections["contributions"]}

{contributions}

---

## {sections["limitations"]}

{limitations}

---

## {sections["future_work"]}

{future_work}

---

## {sections["keywords"]}

{chr(10).join(keyword_lines)}

---

## {sections["executive"]}

{executive_summary}

---

## {sections["takeaways"]}

{takeaway_lines}
"""