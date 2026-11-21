"""Migrations must build the same schema the models declare, in the app's database.

The defect this guards against: ``alembic/env.py`` only configured a URL when
``DRIFTGUARD_DATABASE_URL`` happened to be exported, so migrations silently wrote
to whatever ``alembic.ini`` held (a ``driver://`` placeholder, or a path resolved
against the current working directory) while the application opened a different,
empty database.
"""
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from alembic import command
from sqlalchemy import create_engine, inspect

from driftguard import migrations
from driftguard.database import DATABASE_URL, Base


class AlembicUrlTests(unittest.TestCase):
    def test_defaults_to_the_application_database(self):
        # No override: migrations and the application must open the same database.
        saved = os.environ.pop("DRIFTGUARD_DATABASE_URL", None)
        try:
            self.assertEqual(migrations.resolve_database_url(), DATABASE_URL)
        finally:
            if saved is not None:
                os.environ["DRIFTGUARD_DATABASE_URL"] = saved

    def test_environment_override_wins(self):
        saved = os.environ.get("DRIFTGUARD_DATABASE_URL")
        os.environ["DRIFTGUARD_DATABASE_URL"] = "sqlite:///elsewhere.db"
        try:
            self.assertEqual(migrations.resolve_database_url(), "sqlite:///elsewhere.db")
        finally:
            if saved is None:
                os.environ.pop("DRIFTGUARD_DATABASE_URL", None)
            else:
                os.environ["DRIFTGUARD_DATABASE_URL"] = saved

    def test_config_carries_the_resolved_url(self):
        saved = os.environ.pop("DRIFTGUARD_DATABASE_URL", None)
        try:
            cfg = migrations.alembic_config()
            self.assertEqual(cfg.get_main_option("sqlalchemy.url"), DATABASE_URL)
        finally:
            if saved is not None:
                os.environ["DRIFTGUARD_DATABASE_URL"] = saved

    def test_upgrade_without_an_override_targets_the_application_database(self):
        # Exactly what ``alembic upgrade head`` loads: the .ini alone, no programmatic
        # URL, no environment override. The schema must land in the application's
        # database rather than wherever the placeholder in alembic.ini points.
        from alembic.config import Config

        saved_env = os.environ.pop("DRIFTGUARD_DATABASE_URL", None)
        saved_url = migrations.DATABASE_URL
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "cli.db"
            migrations.DATABASE_URL = f"sqlite:///{db_path}"
            try:
                command.upgrade(Config(str(migrations.ALEMBIC_INI)), "head")
            finally:
                migrations.DATABASE_URL = saved_url
                if saved_env is not None:
                    os.environ["DRIFTGUARD_DATABASE_URL"] = saved_env

            engine = create_engine(f"sqlite:///{db_path}")
            try:
                self.assertIn("targets", inspect(engine).get_table_names())
            finally:
                engine.dispose()


class MigrationSchemaTests(unittest.TestCase):
    def test_migrations_build_exactly_the_model_schema(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "migrated.db"
            cfg = migrations.alembic_config(f"sqlite:///{db_path}")
            command.upgrade(cfg, "head")

            engine = create_engine(f"sqlite:///{db_path}")
            try:
                inspector = inspect(engine)
                tables = set(inspector.get_table_names()) - {"alembic_version"}
                self.assertEqual(tables, set(Base.metadata.tables))
                for name, table in Base.metadata.tables.items():
                    columns = {c["name"] for c in inspector.get_columns(name)}
                    self.assertEqual(columns, set(table.columns.keys()), name)
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
