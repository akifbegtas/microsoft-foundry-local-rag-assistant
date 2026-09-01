"""Yerel belgeleri oku ve RAG için kaynak bilgili parçalara ayır."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from pypdf import PdfReader


@dataclass(frozen=True)
class Chunk:
    source: str
    page: int | None
    chunk_index: int
    content: str


def _split_long_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    parts: list[str] = []
    current: list[str] = []
    current_length = 0

    for word in words:
        added_length = len(word) + (1 if current else 0)
        if current and current_length + added_length > max_chars:
            parts.append(" ".join(current))
            current = [word]
            current_length = len(word)
        else:
            current.append(word)
            current_length += added_length

    if current:
        parts.append(" ".join(current))
    return parts


def chunk_text(text: str, *, max_chars: int = 1200) -> list[str]:
    """Metni paragraf sınırlarını koruyarak yaklaşık boyutlu parçalara ayır."""
    if max_chars < 200:
        raise ValueError("max_chars en az 200 olmalı.")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", normalized)
        if paragraph.strip()
    ]

    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        pieces = (
            _split_long_text(paragraph, max_chars)
            if len(paragraph) > max_chars
            else [paragraph]
        )
        for piece in pieces:
            added_length = len(piece) + (2 if current else 0)
            if current and current_length + added_length > max_chars:
                chunks.append("\n\n".join(current))
                current = [piece]
                current_length = len(piece)
            else:
                current.append(piece)
                current_length += added_length

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def read_document(path: Path, *, max_chars: int = 1200) -> list[Chunk]:
    """PDF, TXT veya Markdown dosyasını kaynak bilgili parçalara dönüştür."""
    path = path.resolve()
    suffix = path.suffix.lower()
    chunks: list[Chunk] = []
    next_index = 0

    if suffix == ".pdf":
        reader = PdfReader(path)
        for page_number, page in enumerate(reader.pages, start=1):
            for content in chunk_text(page.extract_text() or "", max_chars=max_chars):
                chunks.append(Chunk(path.name, page_number, next_index, content))
                next_index += 1
        return chunks

    if suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8")
        return [
            Chunk(path.name, None, index, content)
            for index, content in enumerate(chunk_text(text, max_chars=max_chars))
        ]

    raise ValueError(f"Desteklenmeyen belge turu: {suffix}")
