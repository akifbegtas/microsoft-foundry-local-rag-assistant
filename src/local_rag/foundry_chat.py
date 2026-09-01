"""Foundry Local ile tamamen cihaz uzerinde sohbet tamamlama yardimcilari."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from foundry_local_sdk import Configuration, FoundryLocalManager

DEFAULT_MODEL = "phi-3.5-mini"
DEFAULT_TRANSLATION_MODEL = "qwen2.5-1.5b"
SYSTEM_PROMPT = """You are a document question-answering assistant.
Rules:
1. Answer only from the information in the CONTEXT section.
2. Write at most two short English sentences.
3. Output only the final answer; never output reasoning or analysis.
4. If the context does not answer the question, write only: "This information was not found in the documents."
5. Never repeat a sentence or phrase.
6. For a goal or milestone question, explicitly state the end-of-week deliverable found in the context.
"""


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_messages(question: str, context: str = "") -> list[dict[str, str]]:
    """RAG katmanının daha sonra dolduracağı mesajı oluştur."""
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Soru boş olamaz.")

    clean_context = context.strip() or "No additional context was provided."
    user_prompt = f"CONTEXT:\n{clean_context}\n\nQUESTION:\n{clean_question}\n\nANSWER:"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def initialize_manager() -> Any:
    """SDK yoneticisini proje ici ayarlar ve ortak model onbellegiyle baslat."""
    if FoundryLocalManager.instance is None:
        app_data_dir = project_root() / ".local" / "foundry"
        app_data_dir.mkdir(parents=True, exist_ok=True)
        config = Configuration(
            app_name="local-rag-assistant",
            app_data_dir=str(app_data_dir),
            model_cache_dir=str(Path.home() / ".foundry" / "cache" / "models"),
        )
        FoundryLocalManager.initialize(config)
    return FoundryLocalManager.instance


def answer_question(
    question: str,
    *,
    context: str = "",
    model_alias: str = DEFAULT_MODEL,
) -> str:
    """Soruyu Foundry Local modeliyle cevapla ve modeli güvenle boşalt."""
    manager = initialize_manager()
    model = manager.catalog.get_model(model_alias)

    if not model.is_cached:
        model.download()
    if not model.is_loaded:
        model.load()

    try:
        client = model.get_chat_client()
        client.settings.temperature = 0.0
        client.settings.max_tokens = 160
        client.settings.frequency_penalty = 0.5
        client.settings.top_k = 20
        client.settings.top_p = 0.8
        response = client.complete_chat(build_messages(question, context))
        content = response.choices[0].message.content
        return (content or "").strip()
    finally:
        if model.is_loaded:
            model.unload()


def translate_question_to_english(
    question: str,
    *,
    model_alias: str = DEFAULT_TRANSLATION_MODEL,
) -> str:
    """Türkçe soruyu belge araması için kısa bir İngilizce sorguya çevir."""
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Soru boş olamaz.")

    manager = initialize_manager()
    model = manager.catalog.get_model(model_alias)
    if not model.is_cached:
        model.download()
    if not model.is_loaded:
        model.load()

    try:
        client = model.get_chat_client()
        client.settings.temperature = 0.0
        client.settings.max_tokens = 48
        response = client.complete_chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Translate the Turkish question into one concise English "
                        "document-search query. Preserve week numbers, names, and "
                        "technical terms. Output only the English query."
                    ),
                },
                {"role": "user", "content": clean_question},
            ]
        )
        content = (response.choices[0].message.content or "").strip()
        return content.strip('"')
    finally:
        if model.is_loaded:
            model.unload()
