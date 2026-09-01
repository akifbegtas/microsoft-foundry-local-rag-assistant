"""documents klasöründeki belgeleri SQLite bilgi bankasına aktar."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from local_rag.documents import read_document
from local_rag.store import connect, replace_chunks


ROOT = Path(__file__).resolve().parent
DOCUMENTS_DIR = ROOT / "documents"
DB_PATH = ROOT / "data" / "knowledge.db"


def main() -> None:
    document_paths = sorted(
        path
        for path in DOCUMENTS_DIR.iterdir()
        if path.suffix.lower() in {".pdf", ".txt", ".md"}
        and path.name.lower() != "readme.md"
    )
    if not document_paths:
        raise SystemExit("documents klasöründe desteklenen belge bulunamadı.")

    with connect(DB_PATH) as connection:
        for path in document_paths:
            chunks = read_document(path)
            total = replace_chunks(connection, path.name, chunks)
            print(f"{path.name}: {total} parça kaydedildi")

    print(f"Bilgi bankası hazır: {DB_PATH}")


if __name__ == "__main__":
    main()
