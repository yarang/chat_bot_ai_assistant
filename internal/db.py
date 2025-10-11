"""Centralized database session utilities.

Provides a DBSession class that exposes a connection context manager for SQLite.
This allows other modules to reuse the same connection creation logic.
"""
import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional


class DBSession:
    """Represents a SQLite DB session provider.

    Usage:
        session = DBSession("/path/to/db")
        with session.get_connection() as conn:
            conn.execute(...)
    """

    def __init__(self, db_path: str = "bot_messages.db", timeout: float = 30.0):
        self.db_path = db_path
        self.timeout = timeout
        # Lock is available for callers that need to serialize multi-statement operations.
        self.lock = threading.Lock()

    @contextmanager
    def get_connection(self):
        """Context manager that yields an sqlite3.Connection with a Row factory.

        Returns a fresh connection each time. Caller is responsible for committing.
        """
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                # Best-effort close
                pass


def get_default_session(db_path: Optional[str] = None, timeout: float = 30.0) -> DBSession:
    """Return a DBSession configured with the provided path or default."""
    return DBSession(db_path or "bot_messages.db", timeout=timeout)


@contextmanager
def get_connection(db_path: Optional[str] = None, timeout: float = 30.0):
    """Convenience context manager that yields a DB connection.

    Example:
        with get_connection() as conn:
            ...
    """
    session = get_default_session(db_path, timeout=timeout)
    with session.get_connection() as conn:
        yield conn

__all__ = ["DBSession", "get_default_session", "get_connection"]
