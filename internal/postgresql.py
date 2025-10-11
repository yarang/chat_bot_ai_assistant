"""PostgreSQL backend adapter for SQLAlchemy."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Optional


def get_engine(user: str, password: str, host: str, port: int, db: str, echo: bool = False):
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    engine = create_engine(url, pool_size=10, max_overflow=20, pool_timeout=30, echo=echo)
    return engine


def get_sessionmaker(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_connection(engine):
    conn = engine.connect()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass
