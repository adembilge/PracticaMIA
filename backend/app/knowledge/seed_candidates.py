"""Explicit, idempotent CLI to register official URL candidates, without approvals.

Examples:
    python -m app.knowledge.seed_candidates             # validate and display counts
    python -m app.knowledge.seed_candidates --apply      # insert metadata only
"""
import argparse
from os import environ

from app.database import configure_database
from app.knowledge.catalog import candidate_sources, register_candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Insert missing pending-review records into DATABASE_URL")
    args = parser.parse_args()
    sources = candidate_sources()
    if not args.apply:
        print(f"Validated {len(sources)} candidate URLs; nothing written.")
        return
    url = environ.get("DATABASE_URL")
    if not url:
        parser.error("DATABASE_URL is required when using --apply")
    engine, factory = configure_database(url)
    try:
        with factory.begin() as session:
            count = register_candidates(session)
        print(f"Inserted {count} candidate source(s), all pending human review.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
