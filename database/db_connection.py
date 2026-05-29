"""
db_connection.py — SQLAlchemy Database Connection Module
========================================================

Provides helper functions to create a SQLAlchemy engine, obtain database
sessions, and verify that the PostgreSQL server is reachable.

Dependencies:
    - sqlalchemy
    - config.config.Config   (for DATABASE_URL and other DB settings)
    - utils.logger.get_logger (for structured logging)

Typical usage:
    from database.db_connection import get_engine, get_session, test_connection

    engine  = get_engine()          # Create / reuse the engine
    session = get_session()         # Open a new ORM session
    ok      = test_connection()     # True if DB is reachable
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config.config import Config
from utils.logger import get_logger

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Singleton engine — created once and reused across the application
# ---------------------------------------------------------------------------
_engine = None


def get_engine():
    """
    Create (or return the cached) SQLAlchemy engine.

    Engine parameters:
        pool_size    – number of persistent connections in the pool  (5)
        max_overflow – extra connections allowed above pool_size     (10)
        pool_timeout – seconds to wait for a free connection         (30)
        pool_recycle – seconds before a connection is recycled        (1800 = 30 min)

    Returns:
        sqlalchemy.engine.Engine
    """
    global _engine

    if _engine is None:
        try:
            db_url = Config.DATABASE_URL

            # SQLite does not support connection pooling — use StaticPool
            # to avoid warnings about pool_size, max_overflow, etc.
            if db_url.startswith("sqlite"):
                from sqlalchemy.pool import StaticPool

                _engine = create_engine(
                    db_url,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                    echo=False,
                )
                logger.info("SQLAlchemy engine created (SQLite mode).")
            else:
                # PostgreSQL / other production databases — use full pooling
                _engine = create_engine(
                    db_url,
                    pool_size=5,          # Keep 5 connections ready in the pool
                    max_overflow=10,      # Allow up to 10 extra connections when busy
                    pool_timeout=30,      # Wait 30 s for a connection before raising
                    pool_recycle=1800,    # Recycle connections every 30 minutes
                    echo=False,           # Set True to log every SQL statement (debug)
                )
                logger.info("SQLAlchemy engine created (PostgreSQL mode).")
        except Exception as exc:
            logger.warning("Failed to create SQLAlchemy engine: %s", exc)
            raise

    return _engine


def get_session():
    """
    Create and return a new SQLAlchemy ORM Session bound to the engine.

    The caller is responsible for closing the session when done:
        session = get_session()
        try:
            ...
        finally:
            session.close()

    Returns:
        sqlalchemy.orm.Session
    """
    engine = get_engine()

    # sessionmaker returns a Session *class*; we call it to get an instance
    Session = sessionmaker(bind=engine)
    session = Session()

    logger.debug("New database session opened.")
    return session


def test_connection():
    """
    Attempt a lightweight query (SELECT 1) to verify the database is reachable.

    Returns:
        bool – True if the connection succeeds, False otherwise.
    """
    try:
        engine = get_engine()

        # 'with engine.connect()' automatically closes the connection afterward
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        logger.info("Database connection test PASSED ✓")
        return True

    except Exception as exc:
        # Log a warning instead of crashing — the caller can decide what to do
        logger.warning("Database connection test FAILED ✗ — %s", exc)
        return False


# ---------------------------------------------------------------------------
# Quick CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    """
    Run this file directly to verify that the database is reachable:
        python -m database.db_connection
    """
    print("Testing database connection …")
    if test_connection():
        print("SUCCESS — connected to the database.")
    else:
        print("FAILURE — could not reach the database. Check your .env settings.")
