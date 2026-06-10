from __future__ import annotations

from langchain_openai import OpenAIEmbeddings

_embedder = OpenAIEmbeddings(model="text-embedding-3-small")


async def embed(text: str) -> list[float]:
    return await _embedder.aembed_query(text)


async def embed_batch(texts: list[str]) -> list[list[float]]:
    return await _embedder.aembed_documents(texts)
