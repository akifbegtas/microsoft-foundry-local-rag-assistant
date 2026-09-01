from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from local_rag.foundry_chat import build_messages


def test_build_messages_includes_context_and_question() -> None:
    messages = build_messages("Son teslim nedir?", "Teslim cuma gunudur.")

    assert messages[0]["role"] == "system"
    assert "Teslim cuma gunudur." in messages[1]["content"]
    assert "Son teslim nedir?" in messages[1]["content"]


def test_build_messages_rejects_empty_question() -> None:
    with pytest.raises(ValueError, match="Soru boş olamaz"):
        build_messages("   ")
