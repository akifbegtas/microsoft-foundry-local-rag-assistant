from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from local_rag.documents import Chunk, chunk_text
from local_rag.rag import normalize_search_query
from local_rag.store import (
    connect,
    cosine_similarity,
    count_chunks,
    replace_chunks,
    save_embeddings,
    search_chunks,
)


def test_chunk_text_preserves_content_and_limit() -> None:
    text = "Birinci paragraf.\n\n" + ("uzun kelime " * 80)
    chunks = chunk_text(text, max_chars=240)

    assert len(chunks) > 1
    assert all(len(chunk) <= 240 for chunk in chunks)
    assert chunks[0].startswith("Birinci paragraf")


def test_replace_chunks_is_repeatable(tmp_path: Path) -> None:
    db_path = tmp_path / "knowledge.db"
    chunks = [
        Chunk("notlar.txt", None, 0, "Birinci"),
        Chunk("notlar.txt", None, 1, "Ikinci"),
    ]

    with connect(db_path) as connection:
        assert replace_chunks(connection, "notlar.txt", chunks) == 2
        assert replace_chunks(connection, "notlar.txt", chunks) == 2
        assert count_chunks(connection) == 2


def test_cosine_similarity_and_search(tmp_path: Path) -> None:
    db_path = tmp_path / "knowledge.db"
    chunks = [
        Chunk("notlar.txt", None, 0, "Elma kirmizidir."),
        Chunk("notlar.txt", None, 1, "Deniz mavidir."),
    ]
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0

    with connect(db_path) as connection:
        replace_chunks(connection, "notlar.txt", chunks)
        rows = list(connection.execute("SELECT id FROM chunks ORDER BY chunk_index"))
        save_embeddings(connection, [rows[0]["id"], rows[1]["id"]], [[1, 0], [0, 1]])
        results = search_chunks(
            connection,
            [0.9, 0.1],
            query_text="red apple",
            top_k=1,
        )

    assert results[0]["content"] == "Elma kirmizidir."


def test_normalize_search_query_preserves_week_number() -> None:
    assert normalize_search_query("target for the fourth week") == (
        "end-of-week deliverable milestone for week 4"
    )
    assert normalize_search_query("goal of the 4th week") == (
        "end-of-week deliverable milestone of the week 4"
    )
