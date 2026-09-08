"""Chunking utilities for the preprocessing stage."""

from typing import Dict, List

CHUNK_CONFIG = {"max_tokens": 2000, "overlap_tokens": 200}
WORDS_PER_TOKEN = 0.75
MAX_WORDS = int(CHUNK_CONFIG["max_tokens"] * WORDS_PER_TOKEN)
OVERLAP_WORDS = int(CHUNK_CONFIG["overlap_tokens"] * WORDS_PER_TOKEN)


def chunk_section(section: Dict[str, object]) -> List[Dict[str, object]]:
    """Split one section into overlapping word-based chunks."""
    words = str(section.get("content", "")).split()
    chunks: List[Dict[str, object]] = []
    start = 0
    chunk_id = 1
    while start < len(words):
        end = min(start + MAX_WORDS, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append({
            "chunk_id": chunk_id,
            "section_name": section.get("section_name"),
            "priority": section.get("priority"),
            "content": chunk_text,
        })
        if end == len(words):
            break
        start = end - OVERLAP_WORDS
        chunk_id += 1
    return chunks


def chunk_document(filtered_sections: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Chunk an entire article section list."""
    all_chunks: List[Dict[str, object]] = []
    global_chunk_id = 1
    for section in filtered_sections:
        section_chunks = chunk_section(section)
        for chunk in section_chunks:
            chunk["chunk_id"] = global_chunk_id
            all_chunks.append(chunk)
            global_chunk_id += 1
    return all_chunks
