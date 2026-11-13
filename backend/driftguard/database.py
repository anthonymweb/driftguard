"""Database setup. SQLite is the default to keep local research reproducible."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv("DRIFTGUARD_DATABASE_URL", "sqlite:///./driftguard.db")
engine_options = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory():
    """The session factory the background assessment uses.

    A background task runs after the request's session is closed, so it opens
    its own. Exposing the factory as a dependency means a test can point the
    assessment at its own database exactly as it points the request at one.
    """
    return SessionLocal
