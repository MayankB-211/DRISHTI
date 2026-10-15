"""Engine and session factory.

API code must call `get_engine(pooled=True)`.
Alembic and the pipeline must call `get_engine(pooled=False)`.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from core.config import get_settings, sqlalchemy_url

_engines: dict[str, Engine] = {}


def get_engine(*, pooled: bool) -> Engine:
    """Build (and cache) an engine. Neon pooler connections use NullPool."""
    settings = get_settings()
    raw = settings.database_url if pooled else settings.database_url_direct
    key = "pooled" if pooled else "direct"
    if key not in _engines:
        # NullPool for the pooler: Neon already pools; stacking SQLAlchemy's pool
        # on top causes stale checkouts behind the pooler.
        kwargs: dict = {"pool_pre_ping": True}
        if pooled:
            kwargs["poolclass"] = NullPool
        _engines[key] = create_engine(sqlalchemy_url(raw), **kwargs)
    return _engines[key]


def get_session_factory(*, pooled: bool) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(pooled=pooled), expire_on_commit=False, autoflush=False)


def session_scope(*, pooled: bool) -> Generator[Session, None, None]:
    factory = get_session_factory(pooled=pooled)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
