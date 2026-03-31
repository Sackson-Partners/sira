"""
Database Configuration and Session Management
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool, StaticPool
from contextlib import contextmanager
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def _normalize_db_url(url: str) -> str:
    """Normalise a DATABASE_URL so passwords containing special characters
    (e.g. '@' or '!') don't break URL parsing.

    Strategy: split on the *last* '@' to find the real host boundary, then
    percent-encode the username and password portions.  Safe to call on URLs
    that are already correctly encoded — urllib.parse.unquote+quote is
    idempotent when applied to a properly encoded string.
    """
    if not url or url.startswith("sqlite"):
        return url
    try:
        from urllib.parse import quote, unquote
        scheme_end = url.index("://") + 3
        scheme = url[:scheme_end]
        rest = url[scheme_end:]
        # Everything before the first '/' is the netloc
        slash = rest.find("/")
        netloc, path = (rest[:slash], rest[slash:]) if slash != -1 else (rest, "")
        last_at = netloc.rfind("@")
        if last_at == -1:
            return url  # no credentials in URL
        credentials, hostpart = netloc[:last_at], netloc[last_at + 1:]
        colon = credentials.find(":")
        if colon == -1:
            return url
        raw_user = unquote(credentials[:colon])
        raw_pass = unquote(credentials[colon + 1:])
        return f"{scheme}{quote(raw_user, safe='')}:{quote(raw_pass, safe='')}@{hostpart}{path}"
    except Exception:
        return url  # if anything goes wrong, return original and let SQLAlchemy report it


# Resolve the database URL: empty string (e.g. CI with DATABASE_URL="") falls
# back to SQLite so the module can be imported without a real database.
_DATABASE_URL = _normalize_db_url(settings.DATABASE_URL or "sqlite:///./sira.db")
# Fix asyncpg URLs — this engine is sync-only (psycopg2).
if _DATABASE_URL.startswith("postgresql+asyncpg://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Determine if using SQLite
is_sqlite = _DATABASE_URL.startswith("sqlite")

# Create engine with appropriate settings for database type
if is_sqlite:
    engine = create_engine(
        _DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG,
    )
else:
    engine = create_engine(
        _DATABASE_URL,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        poolclass=QueuePool,
        echo=settings.DEBUG,
        connect_args={"connect_timeout": 5},
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Session:
    """
    Database session dependency for FastAPI.
    Yields a database session and ensures proper cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions outside of FastAPI.
    Usage: with get_db_context() as db: ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def check_db_connection() -> bool:
    """Check if database is accessible"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
