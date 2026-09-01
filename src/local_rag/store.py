"""RAG belge parçaları ve embedding'leri için SQLite veri katmanı."""

from __future__ import annotations

from pathlib import Path
import json
import math
import re
import sqlite3
from typing import Iterable, Sequence

from .documents import Chunk


SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    page INTEGER,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding_json TEXT,
    UNIQUE(source, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def replace_chunks(
    connection: sqlite3.Connection,
    source: str,
    chunks: Iterable[Chunk],
) -> int:
    rows = list(chunks)
    with connection:
        connection.execute("DELETE FROM chunks WHERE source = ?", (source,))
        connection.executemany(
            """
            INSERT INTO chunks(source, page, chunk_index, content)
            VALUES (?, ?, ?, ?)
            """,
            [(c.source, c.page, c.chunk_index, c.content) for c in rows],
        )
    return len(rows)


def save_embedding(
    connection: sqlite3.Connection,
    chunk_id: int,
    embedding: Sequence[float],
) -> None:
    with connection:
        connection.execute(
            "UPDATE chunks SET embedding_json = ? WHERE id = ?",
            (json.dumps(list(embedding)), chunk_id),
        )


def chunks_for_indexing(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT id, source, page, chunk_index, content
            FROM chunks
            ORDER BY source, chunk_index
            """
        )
    )


def save_embeddings(
    connection: sqlite3.Connection,
    chunk_ids: Sequence[int],
    embeddings: Sequence[Sequence[float]],
) -> None:
    if len(chunk_ids) != len(embeddings):
        raise ValueError("Parça ve embedding sayıları eşit olmalı.")
    with connection:
        connection.executemany(
            "UPDATE chunks SET embedding_json = ? WHERE id = ?",
            [
                (json.dumps(list(embedding)), chunk_id)
                for chunk_id, embedding in zip(chunk_ids, embeddings)
            ],
        )


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Vektör boyutları eşit olmalı.")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def search_chunks(
    connection: sqlite3.Connection,
    query_embedding: Sequence[float],
    *,
    query_text: str = "",
    top_k: int = 3,
) -> list[dict[str, object]]:
    if top_k < 1:
        raise ValueError("top_k en az 1 olmalı.")

    query_tokens = set(re.findall(r"[a-z0-9]+", query_text.lower()))
    exact_phrases = re.findall(r"\b(?:week|phase)\s+\d+\b", query_text.lower())
    scored: list[dict[str, object]] = []
    rows = connection.execute(
        """
        SELECT id, source, page, chunk_index, content, embedding_json
        FROM chunks
        WHERE embedding_json IS NOT NULL
        """
    )
    for row in rows:
        embedding = json.loads(row["embedding_json"])
        embedding_score = cosine_similarity(query_embedding, embedding)
        content_lower = str(row["content"]).lower()
        content_tokens = set(re.findall(r"[a-z0-9]+", content_lower))
        lexical_score = (
            len(query_tokens & content_tokens) / len(query_tokens)
            if query_tokens
            else 0.0
        )
        phrase_bonus = 0.35 if any(
            phrase in content_lower for phrase in exact_phrases
        ) else 0.0
        combined_score = 0.7 * embedding_score + 0.3 * lexical_score + phrase_bonus
        scored.append(
            {
                "id": row["id"],
                "source": row["source"],
                "page": row["page"],
                "chunk_index": row["chunk_index"],
                "content": row["content"],
                "embedding_score": embedding_score,
                "lexical_score": lexical_score,
                "score": combined_score,
            }
        )
    return sorted(scored, key=lambda item: float(item["score"]), reverse=True)[:top_k]


def count_chunks(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COUNT(*) AS total FROM chunks").fetchone()
    return int(row["total"])
