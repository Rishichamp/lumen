"""
PDF ingestion: extract per-page text and split into overlapping chunks
sized for embedding/retrieval.

Design choice: token-approximate chunking (word-count based) instead of
naive character slicing. This keeps chunks semantically coherent
(sentences rarely get cut mid-word) without pulling in a full tokenizer
dependency just for chunk boundaries — good enough for retrieval quality,
cheap to run on thousands of pages.
"""
from dataclasses import dataclass

import pypdf


@dataclass
class ExtractedChunk:
    content: str
    page_number: int
    chunk_index: int


def extract_pages(file_path: str) -> list[str]:
    """Return a list of raw text strings, one per PDF page."""
    reader = pypdf.PdfReader(file_path)
    return [page.extract_text() or "" for page in reader.pages]


def chunk_pages(
    pages: list[str],
    chunk_size_words: int = 300,
    overlap_words: int = 45,
) -> list[ExtractedChunk]:
    """
    Slide a word-count window over each page's text.

    A small overlap (≈15%) prevents losing context at chunk boundaries,
    e.g. a sentence defining a term right at the cut point.
    """
    chunks: list[ExtractedChunk] = []
    global_index = 0

    for page_number, page_text in enumerate(pages, start=1):
        words = page_text.split()
        if not words:
            continue

        start = 0
        while start < len(words):
            end = min(start + chunk_size_words, len(words))
            piece = " ".join(words[start:end]).strip()
            if piece:
                chunks.append(
                    ExtractedChunk(content=piece, page_number=page_number, chunk_index=global_index)
                )
                global_index += 1
            if end == len(words):
                break
            start = end - overlap_words  # step forward with overlap

    return chunks


def extract_title_and_abstract(pages: list[str]) -> tuple[str, str]:
    """
    Heuristic extraction from the first page: the first non-empty line is
    treated as the title, and the text following an "Abstract" marker (if
    present) up to the next blank-ish break is treated as the abstract.
    This is intentionally simple/fast; the LLM-based summary (see
    rag_service.summarize_paper) is the higher-quality source of truth
    shown in the UI, this is just a fallback for immediate display while
    that summary is generating.
    """
    if not pages:
        return "Untitled", ""

    first_page = pages[0]
    lines = [l.strip() for l in first_page.splitlines() if l.strip()]
    title = lines[0] if lines else "Untitled"

    lower = first_page.lower()
    abstract = ""
    if "abstract" in lower:
        idx = lower.index("abstract")
        after = first_page[idx + len("abstract"):].strip(" :\n")
        abstract = after[:1200]

    return title[:500], abstract
