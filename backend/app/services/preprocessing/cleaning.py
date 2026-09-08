"""Cleaning utilities for the preprocessing stage."""

import re
import unicodedata
from collections import Counter
from typing import Dict, List, Tuple


page_number_pattern = re.compile(
    r"^\(?-?\s*(page\s*)?\d{1,4}\s*((/|of|sur)\s*\d{1,4})?\s*\)?-?\s*$",
    re.IGNORECASE,
)


def detect_repeated_lines(page_lines: List[List[str]], min_repeat_ratio: float) -> set[str]:
    """Detect repeated headers and footers appearing across pages."""
    line_counter = Counter()
    for lines in page_lines:
        line_counter.update(set(lines[:3] + lines[-3:]))

    n_pages = max(len(page_lines), 1)
    repeated_lines = {
        line
        for line, count in line_counter.items()
        if count / n_pages >= min_repeat_ratio and len(line) < 120
    }
    return repeated_lines


def is_ocr_noise(line: str) -> bool:
    """Detect OCR artifacts."""
    if len(line) < 4:
        return False
    alnum_ratio = sum(c.isalnum() for c in line) / len(line)
    return alnum_ratio < 0.35


def normalize_line(line: str) -> str:
    """Normalize Unicode text and whitespace."""
    line = unicodedata.normalize("NFKC", line)
    line = re.sub(r"[ \t]+", " ", line)
    return line.strip()


def merge_hyphenation(lines: List[str], report: Dict[str, object]) -> List[str]:
    """Merge words split across lines by hyphenation."""
    merged: List[str] = []
    index = 0
    while index < len(lines):
        current = lines[index]
        has_next = index + 1 < len(lines)
        if has_next and re.search(r"\w-$", current) and re.match(r"^\w", lines[index + 1]):
            report["hyphenation_fixes"] += 1
            merged.append(current[:-1] + lines[index + 1])
            index += 2
        else:
            merged.append(current)
            index += 1
    return merged


def clean_extracted_text(pages_text: str | List[str], min_repeat_ratio: float = 0.6) -> Tuple[str, List[Tuple[int, str]], Dict[str, object]]:
    """Clean extracted markdown/text while preserving notebook-compatible structure."""
    if isinstance(pages_text, str):
        pages = [pages_text]
    else:
        pages = pages_text

    report: Dict[str, object] = {
        "chars_before": 0,
        "chars_after": 0,
        "reduction_ratio": 0.0,
        "headers_footers_removed": [],
        "page_numbers_removed": 0,
        "ocr_noise_removed": 0,
        "hyphenation_fixes": 0,
    }

    cleaned_pages: List[str] = []
    page_tagged_lines: List[Tuple[int, str]] = []

    for page_idx, page_text in enumerate(pages, start=1):
        lines = page_text.splitlines()
        normalized_lines: List[str] = []
        for line in lines:
            line = normalize_line(line)
            if not line:
                continue
            if page_number_pattern.match(line):
                report["page_numbers_removed"] = int(report.get("page_numbers_removed", 0)) + 1
                continue
            if is_ocr_noise(line):
                report["ocr_noise_removed"] = int(report.get("ocr_noise_removed", 0)) + 1
                continue
            normalized_lines.append(line)
        normalized_lines = merge_hyphenation(normalized_lines, report)
        cleaned_pages.append("\n".join(normalized_lines))
        page_tagged_lines.extend((page_idx, line) for line in normalized_lines)

    cleaned_text = "\n\n".join(cleaned_pages)
    report["chars_before"] = len("\n\n".join(pages))
    report["chars_after"] = len(cleaned_text)
    report["reduction_ratio"] = 1 - (report["chars_after"] / report["chars_before"] if report["chars_before"] else 0)
    return cleaned_text, page_tagged_lines, report
