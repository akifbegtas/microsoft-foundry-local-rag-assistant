"""SQLite'taki belge parçaları için yerel embedding üret."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from local_rag.embeddings import generate_embeddings
from local_rag.store import chunks_for_indexing, connect, save_embeddings


DB_PATH = Path(__file__).resolve().parent / "data" / "knowledge.db"


def main() -> None:
    with connect(DB_PATH) as connection:
        rows = chunks_for_indexing(connection)
        if not rows:
            raise SystemExit("Önce '.venv/bin/python ingest.py' komutunu çalıştır.")

        print(f"{len(rows)} parça için yerel embedding üretiliyor...")
        embeddings = generate_embeddings([row["content"] for row in rows])
        save_embeddings(connection, [row["id"] for row in rows], embeddings)
        print(f"{len(embeddings)} embedding SQLite'a kaydedildi.")


if __name__ == "__main__":
    main()
