"""İlk Foundry Local testi için komut satırı giriş noktası."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from local_rag.foundry_chat import DEFAULT_MODEL
from local_rag.rag import answer_from_knowledge_base


DB_PATH = Path(__file__).resolve().parent / "data" / "knowledge.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Yerel Foundry Local sohbet testi")
    parser.add_argument(
        "question",
        nargs="?",
        default="Projenin 4. hafta hedefi nedir?",
        help="Modele sorulacak soru",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Foundry model takma adi")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    answer, sources = answer_from_knowledge_base(
        args.question,
        DB_PATH,
        chat_model=args.model,
    )
    print(answer)
    print("\nKaynaklar:")
    for source in sources:
        print(
            f"- {source['source']}, sayfa {source['page']} "
            f"(benzerlik: {float(source['score']):.3f})"
        )


if __name__ == "__main__":
    main()
