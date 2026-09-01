"""Foundry Local embedding modeliyle cihaz ici vektor uretimi."""

from __future__ import annotations

from collections.abc import Sequence

from .foundry_chat import initialize_manager


DEFAULT_EMBEDDING_MODEL = "qwen3-embedding-0.6b"
QUERY_INSTRUCTION = (
    "Instruct: Retrieve English document passages that answer the search query.\n"
    "Query: "
)


def generate_embeddings(
    texts: Sequence[str],
    *,
    model_alias: str = DEFAULT_EMBEDDING_MODEL,
) -> list[list[float]]:
    if not texts:
        return []

    manager = initialize_manager()
    model = manager.catalog.get_model(model_alias)
    if not model.is_cached:
        model.download()
    if not model.is_loaded:
        model.load()

    try:
        client = model.get_embedding_client()
        response = client.generate_embeddings(list(texts))
        return [list(item.embedding) for item in response.data]
    finally:
        if model.is_loaded:
            model.unload()


def generate_query_embedding(
    question: str,
    *,
    model_alias: str = DEFAULT_EMBEDDING_MODEL,
) -> list[float]:
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Soru boş olamaz.")
    instructed_query = QUERY_INSTRUCTION + clean_question
    return generate_embeddings([instructed_query], model_alias=model_alias)[0]
