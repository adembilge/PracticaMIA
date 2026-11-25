import json
import math

import numpy as np

from fastembed import TextEmbedding

from app.rag.embed import as_passage, as_query, l2_normalize, register_e5_small


def test_e5_small_is_registered_without_loading_weights():
    register_e5_small()
    register_e5_small()
    names = {item["model"] for item in TextEmbedding.list_supported_models()}
    assert "intfloat/multilingual-e5-small" in names


def test_prefixes():
    assert as_passage("ciao").startswith("passage: ")
    assert as_query("ciao").startswith("query: ")


def test_normalize_unit():
    vector = l2_normalize([3.0, 4.0])
    assert vector is not None
    assert abs(sum(item * item for item in vector) - 1) < 1e-9


def test_normalize_zero():
    assert l2_normalize([0.0, 0.0]) is None


def test_l2_normalize_produces_json_serializable_floats():
    vector = np.array([3.0, 4.0], dtype=np.float32)
    normalized = l2_normalize(list(vector))
    assert normalized is not None
    json.dumps(normalized)
    assert all(type(item) is float for item in normalized)


class FakeEmbedder:
    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._unit_vector() for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._unit_vector()

    @staticmethod
    def _unit_vector() -> list[float]:
        component = 1 / math.sqrt(384)
        return [component] * 384


def test_fake_embedder_unit_vector():
    embedder = FakeEmbedder()
    vector = embedder.embed_query("ciao")
    assert len(vector) == 384
    assert abs(sum(item * item for item in vector) - 1) < 1e-9
    passages = embedder.embed_passages(["a", "b"])
    assert len(passages) == 2
    for item in passages:
        assert len(item) == 384
        assert abs(sum(x * x for x in item) - 1) < 1e-9