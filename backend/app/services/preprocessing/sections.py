"""Section detection logic for the preprocessing stage."""

import re
from typing import Dict, List, Tuple

SECTION_KEYWORDS = {
    "Abstract": [r"abstract", r"r[ée]sum[ée]"],
    "Introduction": [r"introduction"],
    "Related Work": [r"related\s+works?", r"litt[ée]rature", r"travaux\s+connexes", r"[ée]tat\s+de\s+l'art"],
    "Methodology": [r"methodology", r"methods?", r"m[ée]thodologie", r"m[ée]thodes?", r"approach"],
    "Experiments": [r"experiments?", r"experimental\s+setup", r"exp[ée]rimentations?", r"exp[ée]riences?"],
    "Results": [r"results?", r"r[ée]sultats?"],
    "Discussion": [r"discussion"],
    "Conclusion": [r"conclusions?"],
    "Limitations": [r"limitations?", r"limites?"],
    "Future Work": [r"future\s+works?", r"perspectives?", r"travaux\s+futurs?"],
    "Appendix": [
        r"appendix",
        r"appendices",
        r"annexe",
        r"annexes",
    ],

    "Supplementary Material": [
        r"supplementary\s+materials?",
        r"supplement",
        r"supporting\s+(?:information|materials?)",
        r"additional\s+materials?",
    ],

    "Prompts": [
        r"prompts?",
        r"prompt\s+templates?",
        r"prompt\s+examples?",
    ],

    "Additional Results": [
        r"complete\s+results",
        r"additional\s+results",
        r"extended\s+results",
    ],

    "References": [r"references?", r"bibliography", r"r[ée]f[ée]rences?", r"bibliographie"],
}
SECTION_ORDER = list(SECTION_KEYWORDS.keys())
EXCLUDED_SECTIONS = {
    "Appendix",
    "Supplementary Material",
    "Prompts",
    "Additional Results",
    "References",
}
_NUMBERING_PREFIX = re.compile(r"^\s*(\d{1,2}[.)]|[IVXLC]{1,4}[.)])\s*")


def strip_markdown_emphasis(text: str) -> str:
    """Remove markdown formatting while preserving readable text."""
    text = re.sub(r"(^|\s)#{1,6}\s*", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"(?<!\w)\*(?!\s)(.*?)(?<!\s)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_(?!\s)(.*?)(?<!\s)_(?!\w)", r"\1", text)
    text = re.sub(r"[*_#]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_section_title(title: str) -> str:
    """Clean a section title into a canonical form."""
    title = title.strip()
    title = re.sub(r"^#{1,6}\s*", "", title)
    title = re.sub(r"^\s*\d+(?:\.\d+)*[\.\)\s\-:]*", "", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip().lower()

def is_valid_section_heading(
    candidate: str,
    canonical_name: str,
) -> bool:
    """Check whether a detected line is likely a real section heading."""

    candidate = candidate.strip()

    if not candidate:
        return False

    normalized = candidate.lower()

    # A heading should be reasonably short.
    if len(candidate) > 80:
        return False

    # Normal sentences are unlikely to be headings.
    if candidate.endswith((".", "?", "!")):
        return False

    # Reject very long sentence-like lines.
    if len(candidate.split()) > 12:
        return False

    # Reject lines containing common sentence connectors.
    sentence_markers = {
        "because",
        "although",
        "however",
        "therefore",
        "which",
        "where",
        "when",
        "while",
        "that",
        "this",
        "these",
        "those",
        "we",
        "our",
        "they",
        "their",
    }

    words = set(
        re.findall(
            r"[A-Za-zÀ-ÿ]+",
            normalized,
        )
    )

    # Don't reject the actual canonical heading if one of its
    # words happens to appear in the marker list.
    canonical_words = set(
        canonical_name.lower().split()
    )

    suspicious_words = words & sentence_markers

    if suspicious_words and not words.issubset(
        canonical_words | sentence_markers
    ):
        return False

    return True

def detect_sections(
    page_tagged_lines: List[Tuple[int, str]]
) -> Tuple[List[Dict[str, object]], List[str]]:
    """Detect logical document sections and return notebook-compatible output."""

    matches: List[Tuple[int, str, str]] = []

    for idx, (_, line) in enumerate(page_tagged_lines):
        stripped = line.strip()

        if not stripped or len(stripped) > 80:
            continue

        candidate = stripped.lstrip("#").strip()

        candidate = re.sub(
            r"^[*_]+|[*_]+$",
            "",
            candidate,
        ).strip()

        candidate = _NUMBERING_PREFIX.sub(
            "",
            candidate,
        )

        candidate = re.sub(
            r"^[*_]+|[*_]+$",
            "",
            candidate,
        ).strip()

        for canonical_name, patterns in SECTION_KEYWORDS.items():

            if any(
                re.fullmatch(
                    pattern,
                    candidate,
                    re.IGNORECASE,
                )
                or (
                    re.match(
                        pattern + r"\s*(?::|-)\s*",
                        candidate,
                        re.IGNORECASE,
                    )
                    and is_valid_section_heading(
                        candidate,
                        canonical_name,
                    )
                )
                for pattern in patterns
            ):
                matches.append(
                    (
                        idx,
                        canonical_name,
                        stripped,
                    )
                )
                break

    sections: List[Dict[str, object]] = []

    first_match_idx = (
        matches[0][0]
        if matches
        else len(page_tagged_lines)
    )

    leading_lines = [
        line
        for _, line in page_tagged_lines[:first_match_idx]
    ]

    if leading_lines:
        title_content = strip_markdown_emphasis(
            " ".join(leading_lines)
        )

        if title_content:
            sections.append({
                "section_name": "Title",
                "content": title_content,
                "metadata": {
                    "page_start": 1,
                    "page_end": 1,
                },
            })

    for i, (
        line_idx,
        section_name,
        heading_text,
    ) in enumerate(matches):

        if section_name in EXCLUDED_SECTIONS:
            continue

        start = line_idx + 1

        end = (
            matches[i + 1][0]
            if i + 1 < len(matches)
            else len(page_tagged_lines)
        )

        content_lines = [
            line
            for _, line in page_tagged_lines[start:end]
        ]

        content = strip_markdown_emphasis(
            " ".join(content_lines)
        )

        sections.append({
            "section_name": section_name,
            "content": content,
            "metadata": {
                "page_start": 1,
                "page_end": 1,
            },
        })

    detected_names = {
        section["section_name"]
        for section in sections
    }

    missing_sections = [
        section
        for section in SECTION_ORDER
        if section not in detected_names
    ]

    if not matches:
        sections = [{
            "section_name": "Full Text",
            "content": strip_markdown_emphasis(
                " ".join(
                    line
                    for _, line in page_tagged_lines
                )
            ),
            "metadata": {
                "page_start": 1,
                "page_end": 1,
            },
        }]

        missing_sections = SECTION_ORDER.copy()

    return sections, missing_sections