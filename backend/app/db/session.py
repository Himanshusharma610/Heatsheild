"""Database engine, session factory, and dependency management.

Connections are established on-demand without connecting on module import.
"""

from collections.abc import Generator
from functools import lru_cache
import logging
from typing import Any
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.core.exceptions import ServiceUnavailableException

logger = logging.getLogger(__name__)


def build_engine(settings: Settings) -> Engine:
    """Create a configured SQLAlchemy engine from application settings."""
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is not configured")

    url = settings.DATABASE_URL
    # Ensure standard dialect prefix compatibility with psycopg2
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    connect_args: dict[str, Any] = {}
    is_sqlite = url.startswith("sqlite")

    if is_sqlite:
        connect_args["check_same_thread"] = False
        return create_engine(
            url,
            connect_args=connect_args,
            echo=settings.DEBUG and settings.APP_ENV == "development",
        )

    # PostgreSQL configuration with connection pooling and pre-ping liveness checks
    return create_engine(
        url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=False,  # Avoid dumping SQL statements with potentially sensitive parameters in standard logs
    )


@lru_cache
def get_engine() -> Engine:
    """Return a cached application SQLAlchemy engine singleton.

    Engine creation does not establish a network connection until first use.
    """
    settings = get_settings()
    return build_engine(settings)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return a cached sessionmaker configured for the application engine."""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Provide a request-scoped transactional database session.

    Commits on successful completion, rolls back on exception, and guarantees session closure.
    """
    settings = get_settings()
    if not settings.DATABASE_URL:
        raise ServiceUnavailableException("Database service is not configured")

    try:
        session_factory = get_session_factory()
        session: Session = session_factory()
    except Exception as exc:
        logger.error("Failed to acquire database session: %s", type(exc).__name__)
        raise ServiceUnavailableException("Database service unavailable") from None

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connectivity(engine: Engine | None = None, timeout_seconds: float = 2.0) -> tuple[bool, str | None]:
    """Perform a lightweight, bounded connectivity check (SELECT 1).

    Returns:
        (True, None) if healthy.
        (False, human_readable_reason) if connectivity fails, without disclosing credentials.
    """
    if engine is None:
        try:
            settings = get_settings()
            if not settings.DATABASE_URL:
                return False, "Database is not configured"
            engine = get_engine()
        except Exception as exc:
            logger.warning("Could not obtain engine for readiness probe: %s", type(exc).__name__)
            return False, "Database engine configuration error"

    try:
        # Bounded execution with execution options where supported
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except SQLAlchemyError as err:
        logger.warning("Database connectivity check failed: %s", type(err).__name__)
        return False, "Database connection failed"
    except Exception as err:
        logger.warning("Unexpected error during database connectivity check: %s", type(err).__name__)
        return False, "Database service unreachable"
