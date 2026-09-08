"""Final scientific-summary generation from existing pipeline artifacts."""

import json
import re
from typing import Any, Dict, List
import time

from app.services.inference.base_engine import BaseInferenceEngine


FRENCH_SUMMARY_STRUCTURE = """# Résumé scientifique

## Métadonnées

**Titre :**
...

**Auteurs :**
...

**Année :**
...

**Source :**
...

**DOI :**
...

**Nombre total de pages :**
...

---

## Sujet principal

...

---

## Problématique

...

---

## Objectifs

...

---

## Méthodologie

...

---

## Résultats principaux

- ...
- ...

---

## Contributions scientifiques

- ...
- ...

---

## Limites

...

---

## Perspectives

...

---

## Mots-clés

- ...
- ...
- ...

---

## Résumé synthétique (5 lignes maximum)

...

---

## Points à retenir

- ...
- ...
- ..."""


ENGLISH_SUMMARY_STRUCTURE = """# Scientific Summary

## Metadata

**Title:**
...

**Authors:**
...

**Year:**
...

**Source:**
...

**DOI:**
...

**Total Number of Pages:**
...

---

## Main Topic

...

---

## Problem Statement

...

---

## Objectives

...

---

## Methodology

...

---

## Main Results

- ...
- ...

---

## Scientific Contributions

- ...
- ...

---

## Limitations

...

---

## Future Work

...

---

## Keywords

- ...
- ...
- ...

---

## Executive Summary (maximum 5 lines)

...

---

## Key Takeaways

- ...
- ...
- ..."""


# Preserve the original public constant as the French default.
SUMMARY_STRUCTURE = FRENCH_SUMMARY_STRUCTURE


def get_summary_structure(language: str) -> str:
    """Return the summary structure matching the detected document language."""
    if language == "en":
        return ENGLISH_SUMMARY_STRUCTURE
    return FRENCH_SUMMARY_STRUCTURE


_PLACEHOLDER_PATTERN = re.compile(
    r"\[\s*(?:your\b|insert\b|author\s*\d*\b)",
    flags=re.IGNORECASE,
)


def _metadata_value(value: Any, unavailable: str) -> str:
    """Format one extracted value without allowing template placeholders through."""
    if value is None or value == "" or value == []:
        return unavailable
    if isinstance(value, (list, tuple)):
        values = [
            str(item).strip()
            for item in value
            if str(item).strip() and not _PLACEHOLDER_PATTERN.search(str(item))
        ]
        return ", ".join(values) if values else unavailable
    text = str(value).strip()
    if not text or _PLACEHOLDER_PATTERN.search(text):
        return unavailable
    return text


def _ground_metadata(summary: str, metadata: Dict[str, Any]) -> str:
    """Replace model-written metadata with authoritative extracted metadata."""
    language = str(metadata.get("language", "fr")).strip().lower()
    is_english = language == "en"
    unavailable = "Not available" if is_english else "Non disponible"
    heading = "Metadata" if is_english else "Métadonnées"
    labels = (
        ("Title" if is_english else "Titre", "title"),
        ("Authors" if is_english else "Auteurs", "authors"),
        ("Year" if is_english else "Année", "year"),
        ("Source", "source"),
        ("DOI", "doi"),
        (
            "Total Number of Pages" if is_english else "Nombre total de pages",
            "page_count",
        ),
    )
    fields = "\n\n".join(
        f"**{label}:**\n{_metadata_value(metadata.get(key), unavailable)}"
        for label, key in labels
    )
    authoritative_block = f"## {heading}\n\n{fields}\n\n---\n\n"

    metadata_heading = re.search(
        r"(?im)^##\s+(?:Metadata|Métadonnées)\s*$",
        summary,
    )
    if metadata_heading:
        next_section = re.search(
            r"(?im)^##\s+.+$",
            summary[metadata_heading.end():],
        )
        block_end = (
            metadata_heading.end() + next_section.start()
            if next_section
            else len(summary)
        )
        return (
            summary[:metadata_heading.start()].rstrip()
            + "\n\n"
            + authoritative_block
            + summary[block_end:].lstrip()
        ).strip()

    title_match = re.search(r"(?m)^#\s+.+$", summary)
    if title_match:
        insertion_point = title_match.end()
        return (
            summary[:insertion_point]
            + "\n\n"
            + authoritative_block
            + summary[insertion_point:].lstrip()
        ).strip()
    return (authoritative_block + summary.lstrip()).strip()


def _remove_malformed_trailing_fragment(summary: str) -> str:
    """Remove only unmistakably incomplete fragments at the end of model output."""
    lines = summary.rstrip().splitlines()
    while lines:
        trailing = lines[-1].strip()
        heading = re.fullmatch(r"#{1,6}\s*([A-Za-zÀ-ÖØ-öø-ÿ]{1,2})", trailing)
        isolated_character = re.fullmatch(r"[A-ZÀ-ÖØ-Þ]", trailing)
        dangling_marker = trailing in {"#", "##", "###", "-", "*", "**", "---"}
        if not (heading or isolated_character or dangling_marker):
            break
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
    return "\n".join(lines).strip()


def _authoritative_keyword_lines(keywords: Dict[str, Any]) -> str:
    """Render the preprocessing keyword artifact without recreating it with the LLM."""
    values: List[str] = []
    for item in keywords.get("global_keywords", []):
        value = item.get("keyword") if isinstance(item, dict) else item
        if value is not None and str(value).strip():
            values.append(str(value).strip())
    return "\n".join(f"- {value}" for value in values) or "- Not available"


def _ground_keywords(summary: str, metadata: Dict[str, Any], keywords: Dict[str, Any]) -> str:
    """Replace model-written keywords with the authoritative preprocessing output."""
    language = str(metadata.get("language", "fr")).strip().lower()
    heading = "Keywords" if language == "en" else "Mots-clés"
    authoritative_block = f"## {heading}\n\n{_authoritative_keyword_lines(keywords)}\n\n---\n\n"
    keyword_heading = re.search(rf"(?im)^##\s+{re.escape(heading)}\s*$", summary)
    if not keyword_heading:
        return summary
    next_section = re.search(r"(?im)^##\s+.+$", summary[keyword_heading.end():])
    block_end = keyword_heading.end() + next_section.start() if next_section else len(summary)
    return (
        summary[:keyword_heading.start()].rstrip()
        + "\n\n" + authoritative_block + summary[block_end:].lstrip()
    ).strip()


def finalize_summary(
    summary: str,
    metadata: Dict[str, Any],
    keywords: Dict[str, Any] | None = None,
) -> str:
    """Ground metadata and keywords, then conservatively clean model output."""
    grounded_summary = _ground_metadata(summary.strip(), metadata)
    if keywords is not None:
        grounded_summary = _ground_keywords(grounded_summary, metadata, keywords)
    return _remove_malformed_trailing_fragment(grounded_summary)
def parse_summary_to_json(
    summary: str,
    metadata: Dict[str, Any],
    keywords: Dict[str, Any],
) -> Dict[str, Any]:
    """Convert the finalized Markdown summary into structured JSON."""

    heading_map = {
        # English
        "Main Topic": "main_topic",
        "Problem Statement": "problem_statement",
        "Objectives": "objectives",
        "Methodology": "methodology",
        "Main Results": "main_results",
        "Scientific Contributions": "scientific_contributions",
        "Limitations": "limitations",
        "Future Work": "future_work",
        "Executive Summary (maximum 5 lines)": "executive_summary",
        "Key Takeaways": "key_takeaways",

        # French
        "Sujet principal": "main_topic",
        "Problématique": "problem_statement",
        "Objectifs": "objectives",
        "Méthodologie": "methodology",
        "Résultats principaux": "main_results",
        "Contributions scientifiques": "scientific_contributions",
        "Limites": "limitations",
        "Perspectives": "future_work",
        "Résumé synthétique (5 lignes maximum)": "executive_summary",
        "Points à retenir": "key_takeaways",
    }

    structured_summary: Dict[str, Any] = {
        "metadata": metadata.copy(),
        "main_topic": "",
        "problem_statement": "",
        "objectives": "",
        "methodology": "",
        "main_results": "",
        "scientific_contributions": "",
        "limitations": "",
        "future_work": "",
        "keywords": keywords,
        "executive_summary": "",
        "key_takeaways": "",
    }

    heading_pattern = re.compile(
        r"^##\s+(.+?)\s*$",
        re.MULTILINE,
    )

    matches = list(heading_pattern.finditer(summary))

    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        field = heading_map.get(heading)

        if not field:
            continue

        content_start = match.end()
        content_end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(summary)
        )

        content = summary[content_start:content_end].strip()

        # Remove separator lines.
        content = re.sub(
            r"^\s*---\s*$",
            "",
            content,
            flags=re.MULTILINE,
        ).strip()

        structured_summary[field] = content

    return structured_summary

def build_merge_prompt(
    metadata: Dict[str, Any],
    keywords: Dict[str, Any],
    partial_summaries: List[Dict[str, Any]],
) -> str:
    """Build the dedicated prompt from already-generated pipeline artifacts."""
    language = str(metadata.get("language", "fr")).strip().lower()
    summary_structure = get_summary_structure(language)
    metadata_payload = json.dumps(metadata, indent=2, ensure_ascii=False)
    keywords_payload = json.dumps(keywords, indent=2, ensure_ascii=False)
    summaries_payload = json.dumps(
        partial_summaries,
        indent=2,
        ensure_ascii=False,
    )

    if language == "en":
        return f"""You must produce the final scientific summary of a document.

Mandatory rules:
- Merge all supplied partial summaries.
- Remove duplicated information.
- Keep the complete summary concise and under 600 words.
- Summarize Main Results in at most three concise bullet points.
- Preserve every unique benchmark result needed to support the paper's finding; do not omit one merely to shorten the summary.
- For every numerical result, preserve the complete attribution as one inseparable fact: ENTITY -> VALUE -> METRIC -> UNIT -> CONFIGURATION.
- Never move a value between tools, models, hardware, configurations, percentiles, or settings. Never merge values from different tools or configurations into one comparison.
- Use at most two concise sentences per narrative section.
- Summarize Methodology concisely; do not reproduce detailed subsections from the source.
- Summarize Scientific Contributions in at most three concise bullet points.
- Scientific Contributions must describe only what the paper presents or demonstrates now. Do not include planned, proposed, or future work there.
- Summarize Limitations in at most two concise sentences.
- Report a limitation only when it is explicitly stated as a limitation, constraint, or unresolved shortcoming in the supplied partial summaries. Do not relabel supported capabilities, benchmark controls, or methodology choices as limitations. If none is explicit, write exactly: No explicit limitations were identified in the source.
- Summarize Future Work in at most two concise sentences.
- Future Work must contain only author plans or intended later work, not current contributions.
- The Executive Summary is mandatory and MUST be included.
- The Executive Summary must contain one concise paragraph covering the topic, methodology, main findings, and overall conclusion.
- The Executive Summary must not exceed five lines and must never be empty.
- The Key Takeaways section is mandatory and MUST be included.
- Key Takeaways MUST be the final section of the document.
- Provide exactly three concise bullet points under Key Takeaways.
- Each Key Takeaway must contain a concrete finding, result, contribution, or conclusion supported by the supplied partial summaries.
- The final response MUST include every section from the required structure, in exactly the specified order.
- Before returning the answer, verify that both Executive Summary and Key Takeaways exist and contain non-empty content.
- Metadata values must exactly match METADATA below; never infer or replace them.
- The Keywords section is supplied by preprocessing and is authoritative. Copy its global_keywords exactly; never create, normalize, translate, rank, omit, or add keywords.
- Never output template placeholders such as "[Your ...]" or "[Insert ...]".
- Produce one coherent and factually accurate scientific summary.
- Do not invent information.
- Use only the metadata, keywords, and partial summaries supplied below.
- Write the summary in English because the detected document language is English.
- Do not translate the document or any supplied factual content.
- When requested metadata or information is missing, write exactly: Not available.
- For every required section, use information from the supplied partial summaries.
- If the methodology is not available in the source material, write exactly: Not available.
- Follow the required Markdown structure exactly and in the same order.
- Replace every "..." marker with available content or "Not available".
- Return only the final Markdown, without a preamble or code block.

METADATA:
{metadata_payload}

KEYWORDS:
{keywords_payload}

PARTIAL SUMMARIES:
{summaries_payload}

REQUIRED MARKDOWN STRUCTURE:
{summary_structure}
"""

    return f"""Tu dois produire le résumé scientifique final d'un document.

Règles obligatoires :
- Fusionne toutes les synthèses partielles fournies.
- Supprime les informations dupliquées.
- Limite le résumé complet à 600 mots.
- Résume les Résultats principaux avec au maximum trois puces concises.
- Ne reproduis pas les sous-sections détaillées, les figures, les détails de profilage ou les longues comparaisons numériques dans les Résultats principaux.
- Utilise au maximum deux phrases concises par section narrative.
- Résume la Méthodologie de manière concise ; ne reproduis pas les sous-sections détaillées du document source.
- Résume les Contributions scientifiques avec au maximum trois puces concises.
- Résume les Limites en deux phrases concises au maximum.
- Résume les Perspectives en deux phrases concises au maximum.
- Le Résumé synthétique est obligatoire et DOIT être inclus.
- Le Résumé synthétique doit contenir un paragraphe concis couvrant le sujet, la méthodologie, les principaux résultats et la conclusion générale.
- Le Résumé synthétique ne doit pas dépasser cinq lignes et ne doit jamais être vide.
- La section « Points à retenir » est obligatoire et DOIT être incluse.
- « Points à retenir » DOIT être la dernière section du document.
- Fournis exactement trois puces concises sous « Points à retenir ».
- Chaque point à retenir doit contenir un résultat, une contribution ou une conclusion concrète soutenue par les synthèses partielles fournies.
- La réponse finale DOIT contenir toutes les sections de la structure obligatoire, dans l'ordre exact spécifié.
- Avant de retourner la réponse, vérifie que le Résumé synthétique et les Points à retenir existent et contiennent du contenu non vide.
- Les métadonnées doivent correspondre exactement aux MÉTADONNÉES ci-dessous ; ne les déduis pas et ne les remplace pas.
- Ne retourne jamais de marqueurs de modèle tels que « [Your ...] » ou « [Insert ...] ».
- Produis un résumé scientifique unique, cohérent et factuellement exact.
- N'invente aucune information.
- Utilise uniquement les métadonnées, les mots-clés et les synthèses partielles fournis ci-dessous.
- Rédige le résumé en français car la langue détectée du document est le français.
- Ne traduis pas le document ni les contenus factuels fournis.
- Lorsqu'une métadonnée ou une information demandée est absente, écris exactement : Non disponible.
- Pour chaque section obligatoire, utilise uniquement les informations présentes dans les synthèses partielles fournies.
- Si la méthodologie n'est pas disponible dans le contenu source, écris exactement : Non disponible.
- Respecte exactement la structure Markdown imposée, dans le même ordre.
- Remplace tous les marqueurs « ... » par le contenu disponible ou par « Non disponible ».
- Retourne uniquement le Markdown final, sans préambule et sans bloc de code.
    
MÉTADONNÉES :
{metadata_payload}

MOTS-CLÉS :
{keywords_payload}

SYNTHÈSES PARTIELLES :
{summaries_payload}

STRUCTURE MARKDOWN OBLIGATOIRE :
{summary_structure}
"""


def merge_summary(
    metadata: Dict[str, Any],
    keywords: Dict[str, Any],
    partial_summaries: List[Dict[str, Any]],
    engine: BaseInferenceEngine,
) -> str:
    """Generate one final Markdown summary with the existing inference engine."""
    request = {
        "chunk_id": "final_summary",
        "section_name": "Final Summary",
        "priority": "core",
        "prompt": build_merge_prompt(metadata, keywords, partial_summaries),
    }
    start_time = time.perf_counter()
    response = engine.generate(request)
    final_summary_time = time.perf_counter() - start_time
    print(
        f"Timing | Final Summary LLM | "
        f"{final_summary_time:.3f} seconds"
    )



    raw_summary = str(response["summary"])

    print("\n" + "=" * 80)
    print("RAW LLM FINAL SUMMARY")
    print("=" * 80)
    print(raw_summary)
    print("=" * 80)

    return finalize_summary(raw_summary, metadata, keywords)
