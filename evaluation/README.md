Deterministic retrieval checks. No threshold and no scored result. [COMPONENTS.md](../docs/architecture/COMPONENTS.md)

The fixture is [passages.json](fixtures/passages.json). The check is [ragcheck.py](ragcheck.py). From the repository root, `py -3 scripts/check_rag.py` runs [check_rag.py](../scripts/check_rag.py).

The document walk is `py -3 scripts/check_documents.py`, and it has no threshold.

The groundedness walk is `py -3 scripts/check_grounded.py`, and it has no threshold.

The adversarial walk is `py -3 scripts/check_adversarial.py`, and it has no threshold.

The privacy walk is `py -3 scripts/check_privacy.py`, and it has no threshold.
