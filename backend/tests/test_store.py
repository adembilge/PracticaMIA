from uuid import uuid4

from memory_store import MemoryChatStore


def test_conversations_isolated_by_user():
    store = MemoryChatStore()
    user_a = str(uuid4())
    user_b = str(uuid4())

    conv = store.insert_conversation(user_a, "A conversation")
    conv_id = conv["id"]

    ids_b = [c["id"] for c in store.list_conversations(user_b)]
    assert conv_id not in ids_b

    assert store.get_conversation(user_b, conv_id) is None