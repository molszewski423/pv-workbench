"""
Header-aware markdown chunker for Obsidian vault notes.

Splits on H1/H2/H3 boundaries to keep sections semantically coherent.
Falls back to paragraph-level splitting for oversized sections.
Strips Obsidian [[wikilinks]] to clean text for embedding.
"""

import re
from dataclasses import dataclass

HEADER_RE = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
WIKILINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')


@dataclass
class Chunk:
    text: str
    header: str
    chunk_index: int


def strip_wikilinks(text: str) -> str:
    """Replace [[Page|alias]] → alias, [[Page]] → Page."""
    return WIKILINK_RE.sub(lambda m: m.group(2) or m.group(1), text)


def chunk_note(text: str, max_size: int = 800) -> list[Chunk]:
    """
    Split a markdown note into chunks at header boundaries.
    Sections exceeding max_size are further split by paragraph.
    """
    splits = [(m.start(), m.group(2)) for m in HEADER_RE.finditer(text)]

    if not splits:
        return _paragraph_chunks(text, "document", max_size)

    sections = []
    for i, (start, header) in enumerate(splits):
        end = splits[i + 1][0] if i + 1 < len(splits) else len(text)
        sections.append((header, text[start:end].strip()))

    chunks: list[Chunk] = []
    for header, content in sections:
        if len(content) <= max_size:
            chunks.append(Chunk(
                text=strip_wikilinks(content),
                header=header,
                chunk_index=len(chunks),
            ))
        else:
            for sub in _paragraph_chunks(content, header, max_size):
                chunks.append(Chunk(
                    text=sub.text,
                    header=sub.header,
                    chunk_index=len(chunks),
                ))

    return chunks


def _paragraph_chunks(text: str, header: str, max_size: int) -> list[Chunk]:
    """Split text into paragraph-boundary chunks, each under max_size."""
    paragraphs = re.split(r'\n{2,}', text)
    chunks: list[Chunk] = []
    buf: list[str] = []
    size = 0

    for para in paragraphs:
        if size + len(para) > max_size and buf:
            chunks.append(Chunk(
                text=strip_wikilinks('\n\n'.join(buf)),
                header=header,
                chunk_index=len(chunks),
            ))
            buf, size = [], 0
        buf.append(para)
        size += len(para)

    if buf:
        chunks.append(Chunk(
            text=strip_wikilinks('\n\n'.join(buf)),
            header=header,
            chunk_index=len(chunks),
        ))

    return chunks
