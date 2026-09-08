"""Prompt building helpers for the prompting stage."""

from typing import Any, Dict

from app.services.prompting.templates import SYSTEM_PROMPT


def build_document_context(metadata: Dict[str, Any], keywords: Dict[str, Any]) -> str:
    """Build the shared document context used by all prompts."""
    title = metadata.get("title", "Unknown Title")
    language = metadata.get("language", "Unknown")

    global_keywords = keywords.get("global_keywords", [])
    keyword_list = [item["keyword"] for item in global_keywords if "keyword" in item]

    return f"""
Article Information

Title:
{title}

Language:
{language}

Keywords:
{", ".join(keyword_list)}
""".strip()


def build_shared_prefix(metadata: Dict[str, Any], keywords: Dict[str, Any]) -> str:
    """Create the shared prompt prefix for the document."""
    return "\n\n".join([SYSTEM_PROMPT, build_document_context(metadata, keywords)])


def build_chunk_context(chunk: Dict[str, Any]) -> str:
    """Build the chunk-specific context section."""
    return f"""
Section Information

Section Name:
{chunk['section_name']}

Priority:
{chunk['priority']}

Section Content:
{chunk['content']}
""".strip()


def build_prompt(chunk: Dict[str, Any], shared_prefix: str) -> str:
    """Build the final inference prompt for a chunk."""
    chunk_context = build_chunk_context(chunk)
    return "\n\n".join([shared_prefix, chunk_context])
