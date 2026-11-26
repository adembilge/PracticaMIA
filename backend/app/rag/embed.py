import math

from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType

E5_SMALL = "intfloat/multilingual-e5-small"


def register_e5_small() -> None:
    known = {item["model"] for item in TextEmbedding.list_supported_models()}
    if E5_SMALL in known:
        return
    TextEmbedding.add_custom_model(
        model=E5_SMALL,
        pooling=PoolingType.MEAN,
        normalization=True,
        sources=ModelSource(hf=E5_SMALL),
        dim=384,
        model_file="onnx/model.onnx",
    )


def as_passage(text: str) -> str:
    return "passage: " + text


def as_query(text: str) -> str:
    return "query: " + text


def l2_normalize(vector: list[float]) -> list[float] | None:
    norm = math.sqrt(sum(item * item for item in vector))
    if norm == 0.0:
        return None
    return [float(item) / norm for item in vector]


class Embedder:
    def __init__(self) -> None:
        register_e5_small()
        self._model = TextEmbedding(E5_SMALL)

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