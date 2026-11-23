from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db import models  # noqa: F401  (registers tables on Base.metadata)
from app.db.base import Base

config = context.config
# An explicitly set URL (e.g. by tests) wins over the environment.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """Only diff objects we own.

    PostGIS images ship extra schemas/tables (spatial_ref_sys, tiger geocoder, topology). A reflected
    table that is not in our metadata is never ours, so autogenerate must not propose dropping it —
    nor its indexes. Consequence: dropping one of *our* tables must be written by hand in a migration.
    """
    if reflected and compare_to is None:
        if type_ == "table":
            return False
        table = getattr(obj, "table", None)
        if table is not None and table.name not in target_metadata.tables:
            return False
    return alembic_helpers.include_object(obj, name, type_, reflected, compare_to)


def _configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        include_object=include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
        compare_type=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    _configure(url=config.get_main_option("sqlalchemy.url"), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        _configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
