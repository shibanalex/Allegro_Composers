"""Alembic environment: one schema for the whole modular monolith.

Runs on the application's engine, or on a connection handed in through `config.attributes["connection"]`
(migration tests do that).
"""
from logging.config import fileConfig

from alembic import context

from allegro import models  # noqa: F401  (every module's tables on Base.metadata)
from allegro.core.db import Base, engine

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=str(engine.url), target_metadata=target_metadata, literal_binds=True,
        render_as_batch=engine.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


def _migrate(connection) -> None:
    sqlite = connection.dialect.name == "sqlite"
    if sqlite:
        # SQLite can't drop or change a column in place: batch mode copies the table and drops the old one.
        # With foreign keys enforced (the application turns them on), dropping the old «users» would cascade
        # and delete every work and post. So they are off while migrating, and checked again afterwards.
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
    context.configure(
        connection=connection, target_metadata=target_metadata,
        render_as_batch=sqlite,  # SQLite needs batch mode for ALTER
    )
    with context.begin_transaction():
        context.run_migrations()
    if sqlite:
        broken = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()
        if broken:
            raise RuntimeError(f"Migration left broken references: {broken[:5]}")


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _migrate(connection)
        return
    with engine.connect() as connection:
        _migrate(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
