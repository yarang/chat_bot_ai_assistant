"""SQLite backend adapter for SQLAlchemy.

Provides a unified API: get_engine, get_sessionmaker, get_connection.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
from contextlib import contextmanager
from typing import Optional


def get_engine(db_path: Optional[str] = None, memory: bool = False, echo: bool = False):
    if memory:
        url = "sqlite:///:memory:"
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=echo,
        )
    else:
        path = db_path or "bot_messages.db"
        url = f"sqlite:///{path}"
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            echo=echo,
        )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()
        except Exception:
            # best-effort
            pass

    return engine


def get_sessionmaker(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_connection(engine):
    """Yield a connection (SQLAlchemy Connection) from engine."""
    conn = engine.connect()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass
