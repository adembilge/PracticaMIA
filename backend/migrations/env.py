"""Alembic database migration configuration. DATABASE_URL is required."""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.database import Base
from app.cases import model  # noqa: F401 - register the table on Base.metadata
from app.knowledge import model as knowledge_model  # noqa: F401 - registry tables
from app.knowledge import snapshot_model  # noqa: F401 - snapshot and passage tables
from app.knowledge import review_model  # noqa: F401 - source review audit records
from app.knowledge import usage_model  # noqa: F401 - daily AI usage accounting

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

url = os.environ.get("DATABASE_URL")
if not url:
    raise RuntimeError("DATABASE_URL must be set to run database migrations")

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_engine(url, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
