"""Alembic wiring.

Migrations must target the *same* database the application opens. Resolving the
URL in one place (rather than letting ``alembic.ini`` hold a placeholder) is what
keeps a migrated deployment and the running service on one database instead of
two.
"""
from __future__ import annotations

import os
from pathlib import Path

from alembic.config import Config

from .database import DATABASE_URL

#: The repository's Alembic configuration file (``backend/alembic.ini``).
ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def resolve_database_url() -> str:
    """The database migrations should operate on.

    An explicit ``DRIFTGUARD_DATABASE_URL`` wins; otherwise migrations follow the
    application's own database so the two cannot drift apart.
    """
    return os.getenv("DRIFTGUARD_DATABASE_URL") or DATABASE_URL


def alembic_config(url: str | None = None) -> Config:
    """An Alembic configuration pointed at *url* (default: the application database)."""
    cfg = Config(str(ALEMBIC_INI))
    # ConfigParser interpolates ``%`` in values, so escape it for literal paths.
    target = (url if url is not None else resolve_database_url()).replace("%", "%%")
    cfg.set_main_option("sqlalchemy.url", target)
    return cfg
