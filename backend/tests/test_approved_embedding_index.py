"""No live model used: embedding call shape, dimensions and empty-plan safety."""
from dataclasses import replace

import pytest

from app.knowledge.approved_embedding_index import (
    EmbeddingTask, prepare_vectors, save_vectors,
)

TASK = EmbeddingTask(
    citation_id="123e4567-e89b-12d3-a456-426614174000:0000",
    source_id="milano-residence-change",
    version_id="123e4567-e89b-12d3-a456-426614174000",
    passage_sha256="a" * 64,
    content="Synthetic public-text-only test phrase.",
)


class FakeProvider:
    def __init__(self, vectors):
        self.vectors = vectors
        self.calls = []
    def embed_documents(self, texts):
        self.calls.append(texts)
        return self.vectors


def vector():
    return [1.0, 0.0] + [0.0] * 1534


def test_empty_batch_never_calls_external_provider():
    provider = FakeProvider([])
    assert prepare_vectors(provider, []) == []
    assert provider.calls == []


def test_provider_receives_only_explicit_selected_text():
    provider = FakeProvider([vector()])
    assert prepare_vectors(provider, [TASK]) == [vector()]
    assert provider.calls == [[TASK.content]]


@pytest.mark.parametrize("vectors", [
    [], [[1.0]], [[0.0] * 1536], [[float("nan")] * 1536],
    [[float("inf")] * 1536],
])
def test_invalid_provider_response_is_rejected(vectors):
    with pytest.raises(ValueError):
        prepare_vectors(FakeProvider(vectors), [TASK])


def test_mismatched_embedding_count_never_enters_database(client):
    with client.app.state.session_factory() as db:
        with pytest.raises(ValueError, match="count"):
            save_vectors(db, [TASK], [])
