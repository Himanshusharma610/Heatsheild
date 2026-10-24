"""Alembic environment configuration."""

import logging
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath("."))

from app.config import get_settings
from app.models import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Set SQLAlchemy target metadata for autogenerate support
target_metadata = Base.metadata

# Inject database URL from application settings (protecting secrets from alembic.ini)
settings = get_settings()
db_url = settings.DATABASE_URL or os.environ.get("DATABASE_URL")
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures context with just a URL and not an Engine, emitting SQL statements to script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise ValueError(
            "DATABASE_URL must be configured in environment or .env to run migrations."
        )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise ValueError(
            "DATABASE_URL must be configured in environment or .env to run migrations."
        )

    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
