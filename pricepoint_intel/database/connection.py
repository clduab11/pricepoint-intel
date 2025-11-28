"""Database connection and session management.

Supports both SQLite (MVP) and PostgreSQL (production) via configuration.
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator, Optional
import logging

from sqlalchemy import create_engine, event, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from pricepoint_intel.database.models import Base

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration with PostgreSQL-ready flags.

    Attributes:
        use_postgres: If True, use PostgreSQL; otherwise use SQLite (default for MVP)
        postgres_host: PostgreSQL host
        postgres_port: PostgreSQL port
        postgres_db: PostgreSQL database name
        postgres_user: PostgreSQL username
        postgres_password: PostgreSQL password
        sqlite_path: Path to SQLite database file
        echo: If True, log all SQL statements
        pool_size: Connection pool size (PostgreSQL only)
        max_overflow: Max connections above pool_size (PostgreSQL only)
    """

    use_postgres: bool = False
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "pricepoint_intel"
    postgres_user: str = "pricepoint"
    postgres_password: str = ""
    sqlite_path: str = "pricepoint_intel.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    connect_timeout: int = 10

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create configuration from environment variables."""
        database_url = os.getenv("DATABASE_URL", "")

        # Check if PostgreSQL URL is provided
        use_postgres = database_url.startswith("postgresql")

        if use_postgres:
            # Parse PostgreSQL URL
            # Format: postgresql://user:password@host:port/dbname
            import urllib.parse

            parsed = urllib.parse.urlparse(database_url)
            return cls(
                use_postgres=True,
                postgres_host=parsed.hostname or "localhost",
                postgres_port=parsed.port or 5432,
                postgres_db=parsed.path.lstrip("/") or "pricepoint_intel",
                postgres_user=parsed.username or "pricepoint",
                postgres_password=parsed.password or "",
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
                pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
                max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            )

        return cls(
            use_postgres=False,
            sqlite_path=os.getenv("SQLITE_PATH", "pricepoint_intel.db"),
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )

    def get_connection_string(self) -> str:
        """Get the appropriate connection string based on configuration."""
        if self.use_postgres:
            return (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return f"sqlite:///{self.sqlite_path}"

    def get_sync_connection_string(self) -> str:
        """Get synchronous connection string (for non-async operations)."""
        if self.use_postgres:
            return (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return f"sqlite:///{self.sqlite_path}"


# Global engine and session factory
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine(config: Optional[DatabaseConfig] = None) -> Engine:
    """Get or create the database engine.

    Args:
        config: Database configuration. If None, loads from environment.

    Returns:
        SQLAlchemy Engine instance
    """
    global _engine

    if _engine is not None:
        return _engine

    if config is None:
        config = DatabaseConfig.from_env()

    connection_string = config.get_sync_connection_string()
    logger.info(
        f"Creating database engine: {'PostgreSQL' if config.use_postgres else 'SQLite'}"
    )

    if config.use_postgres:
        # PostgreSQL configuration
        _engine = create_engine(
            connection_string,
            echo=config.echo,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_pre_ping=True,  # Enable connection health checks
            connect_args={"connect_timeout": config.connect_timeout},
        )
    else:
        # SQLite configuration
        _engine = create_engine(
            connection_string,
            echo=config.echo,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,  # Use static pool for SQLite
        )
        # Enable foreign keys for SQLite
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


def get_session_factory(config: Optional[DatabaseConfig] = None) -> sessionmaker:
    """Get or create the session factory.

    Args:
        config: Database configuration. If None, loads from environment.

    Returns:
        SQLAlchemy sessionmaker instance
    """
    global _SessionLocal

    if _SessionLocal is not None:
        return _SessionLocal

    engine = get_engine(config)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return _SessionLocal


def get_session(config: Optional[DatabaseConfig] = None) -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup.

    Args:
        config: Database configuration. If None, loads from environment.

    Yields:
        SQLAlchemy Session instance
    """
    SessionLocal = get_session_factory(config)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope(config: Optional[DatabaseConfig] = None) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations.

    Args:
        config: Database configuration. If None, loads from environment.

    Yields:
        SQLAlchemy Session instance
    """
    SessionLocal = get_session_factory(config)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()


def init_database(config: Optional[DatabaseConfig] = None, drop_existing: bool = False) -> None:
    """Initialize the database schema.

    Args:
        config: Database configuration. If None, loads from environment.
        drop_existing: If True, drop all existing tables before creating.
    """
    engine = get_engine(config)

    if drop_existing:
        logger.warning("Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)

    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialization complete.")


def reset_engine() -> None:
    """Reset the global engine and session factory.

    Useful for testing or when changing database configuration.
    """
    global _engine, _SessionLocal

    if _engine is not None:
        _engine.dispose()
        _engine = None

    _SessionLocal = None
    logger.info("Database engine reset.")


def check_connection(config: Optional[DatabaseConfig] = None) -> bool:
    """Check if the database connection is working.

    Args:
        config: Database configuration. If None, loads from environment.

    Returns:
        True if connection is successful, False otherwise.
    """
    try:
        engine = get_engine(config)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_database_info(config: Optional[DatabaseConfig] = None) -> dict:
    """Get information about the current database configuration.

    Args:
        config: Database configuration. If None, loads from environment.

    Returns:
        Dictionary with database information.
    """
    if config is None:
        config = DatabaseConfig.from_env()

    return {
        "type": "PostgreSQL" if config.use_postgres else "SQLite",
        "host": config.postgres_host if config.use_postgres else "local",
        "database": config.postgres_db if config.use_postgres else config.sqlite_path,
        "pool_size": config.pool_size if config.use_postgres else 1,
        "connection_string": config.get_sync_connection_string().split("@")[-1]
        if config.use_postgres
        else config.sqlite_path,
    }
