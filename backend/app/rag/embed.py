import math

from fastembed import TextEmbedding


def as_passage(text: str) -> str:
    return "passage: " + text


def as_query(text: str) -> str:
    return "query: " + text


def l2_normalize(vector: list[float]) -> list[float] | None:
    norm = math.sqrt(sum(item * item for item in vector))
    if norm == 0.0:
        return None
    return [item / norm for item in vector]


class Embedder:
    def __init__(self) -> None:
        self._model = TextEmbedding("intfloat/multilingual-e5-small")

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        prefixed = [as_passage(text) for text in texts]
        vectors: list[list[float]] = []
        for embedding in self._model.embed(prefixed):
            normalized = l2_normalize(list(embedding))
            if normalized is not None:
                vectors.append(normalized)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        prefixed = as_query(text)
        embedding = next(iter(self._model.embed([prefixed])))
        normalized = l2_normalize(list(embedding))
        if normalized is None:
            raise ValueError("zero-norm embedding")
        return normalized