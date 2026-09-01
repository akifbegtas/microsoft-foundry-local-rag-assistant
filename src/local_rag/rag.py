"""Retrieval ve Foundry Local cevap üretimini birleştiren RAG akışı."""

from __future__ import annotations

from pathlib import Path
import re

from .embeddings import generate_query_embedding
from .foundry_chat import (
    DEFAULT_MODEL,
    answer_question,
    translate_question_to_english,
)
from .store import connect, search_chunks


WEEK_ORDINALS = {
    "first": "1",
    "second": "2",
    "third": "3",
    "fourth": "4",
    "fifth": "5",
    "sixth": "6",
}


def normalize_search_query(query: str) -> str:
    normalized = query.lower()
    normalized = re.sub(
        r"\b(?:target|goal)\b",
        "end-of-week deliverable milestone",
        normalized,
    )
    for ordinal, number in WEEK_ORDINALS.items():
        normalized = re.sub(
            rf"\b(?:the\s+)?{ordinal}\s+week\b",
            f"week {number}",
            normalized,
        )
        normalized = re.sub(
            rf"\bweek\s+{ordinal}\b",
            f"week {number}",
            normalized,
        )
    normalized = re.sub(r"\b(\d+)(?:st|nd|rd|th)\s+week\b", r"week \1", normalized)
    return normalized


def _format_context(results: list[dict[str, object]]) -> str:
    sections: list[str] = []
    for result in results:
        page = result["page"]
        location = f"page {page}" if page is not None else "page unavailable"
        sections.append(
            f"[Source: {result['source']}, {location}]\n{result['content']}"
        )
    return "\n\n---\n\n".join(sections)


def answer_from_knowledge_base(
    question: str,
    db_path: Path,
    *,
    top_k: int = 2,
    chat_model: str = DEFAULT_MODEL,
) -> tuple[str, list[dict[str, object]]]:
    english_query = normalize_search_query(
        translate_question_to_english(question)
    )
    query_embedding = generate_query_embedding(english_query)
    with connect(db_path) as connection:
        results = search_chunks(
            connection,
            query_embedding,
            query_text=english_query,
            top_k=top_k,
        )
    if not results:
        raise RuntimeError("Embedding indeksi boş. Önce index_embeddings.py çalıştır.")

    answer = answer_question(
        english_query,
        context=_format_context(results),
        model_alias=chat_model,
    )
    return answer, results
