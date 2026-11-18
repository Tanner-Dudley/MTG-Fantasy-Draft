"""
Database engine, session factory, and table initialization.

SQLAlchemy acts as an ORM (Object-Relational Mapper): you define Python
classes that map to database tables, and SQLAlchemy translates attribute
access and method calls into SQL queries behind the scenes.

Key concepts:
  - Engine:       the connection to the actual database file/server.
  - SessionLocal: a factory that creates new database sessions (one per request).
  - Base:         every ORM model class inherits from this so SQLAlchemy
                  knows about it and can create the corresponding table.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

db_url = settings.effective_database_url

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(db_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Create all tables that don't exist yet (safe to call repeatedly)."""
    from . import models  # noqa: F401  -- import so Base knows about them
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    FastAPI dependency that yields a database session for the duration of
    a single request, then closes it automatically.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
