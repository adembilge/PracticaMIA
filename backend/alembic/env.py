"""Apply the schema revision. The URL has no password."""
import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models import Base


def database_url():
    host = os.environ.get("PAPERPILOT_DB_HOST", "127.0.0.1")
    port = os.environ.get("PAPERPILOT_DB_PORT", "5432")
    name = os.environ.get("PAPERPILOT_DB_NAME", "paperpilot")
    user = os.environ.get("PAPERPILOT_DB_USER", "postgres")
    return "postgresql+psycopg://%s@%s:%s/%s" % (user, host, port, name)


def run_migrations_offline():
    context.configure(url=database_url(), target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(database_url())
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
