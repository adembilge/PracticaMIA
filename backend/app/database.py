"""SQLAlchemy database configuration and request-scoped sessions."""
from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def configure_database(database_url: str):
    if not database_url:
        raise ValueError("DATABASE_URL is required when the demo case API is enabled")
    args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=args)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, factory


def get_session(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        yield session
