"""Unified database factory.

Selects backend adapter (sqlite, mariadb, postgresql) based on config and exposes
get_engine, get_sessionmaker, get_connection helpers.
"""
from typing import Optional

from . import sqlite as sqlite_adapter
from . import mariadb as mariadb_adapter
from . import postgresql as postgresql_adapter


def create_backend(config: dict):
    """Create engine and sessionmaker based on config.

    Expected config shape:
      {"backend": "sqlite"|"mariadb"|"postgresql", ...}
    """
    backend = config.get("backend", "sqlite").lower()
    if backend == "sqlite":
        engine = sqlite_adapter.get_engine(db_path=config.get("path"), memory=config.get("memory", False), echo=config.get("echo", False))
        SessionLocal = sqlite_adapter.get_sessionmaker(engine)
        get_connection = sqlite_adapter.get_connection
    elif backend == "mariadb":
        # validate required fields
        required = ("user", "password", "host", "dbname")
        for k in required:
            if not config.get(k):
                raise ValueError(f"mariadb config requires '{k}'")
        engine = mariadb_adapter.get_engine(
            user=config["user"], password=config["password"], host=config["host"], port=int(config.get("port", 3306)), db=config["dbname"], echo=config.get("echo", False)
        )
        SessionLocal = mariadb_adapter.get_sessionmaker(engine)
        get_connection = mariadb_adapter.get_connection
    elif backend == "postgresql":
        required = ("user", "password", "host", "dbname")
        for k in required:
            if not config.get(k):
                raise ValueError(f"postgresql config requires '{k}'")
        engine = postgresql_adapter.get_engine(
            user=config["user"], password=config["password"], host=config["host"], port=int(config.get("port", 5432)), db=config["dbname"], echo=config.get("echo", False)
        )
        SessionLocal = postgresql_adapter.get_sessionmaker(engine)
        get_connection = postgresql_adapter.get_connection
    else:
        raise ValueError(f"Unsupported backend: {backend}")

    return {
        "engine": engine,
        "SessionLocal": SessionLocal,
        "get_connection": get_connection,
    }
