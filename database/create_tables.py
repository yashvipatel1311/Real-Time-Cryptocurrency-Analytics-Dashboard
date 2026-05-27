"""
create_tables.py — SQLAlchemy ORM Models & Table Creation Utilities
====================================================================

Defines the four core ORM models that mirror the PostgreSQL schema:

    1. LiveCryptoPrice   → live_crypto_prices
    2. HistoricalPrice   → historical_prices
    3. Portfolio         → portfolio
    4. SentimentData     → sentiment_data

Also provides two convenience functions:
    - create_all_tables()  — creates every table that doesn't already exist
    - drop_all_tables()    — drops *all* tables (asks for confirmation first)

Dependencies:
    - sqlalchemy
    - database.db_connection.get_engine
    - utils.logger.get_logger

Typical usage:
    from database.create_tables import create_all_tables
    create_all_tables()
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Text,
    Date,
    DateTime,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, synonym

from database.db_connection import get_engine
from utils.logger import get_logger

# ---------------------------------------------------------------------------
# Logger & Base
# ---------------------------------------------------------------------------
logger = get_logger(__name__)

# Base class that all ORM models inherit from
Base = declarative_base()


# ===========================================================================
# MODEL 1: LiveCryptoPrice
# ===========================================================================
class LiveCryptoPrice(Base):
    """
    Stores the latest price snapshot for each cryptocurrency.

    Each row is one "tick" fetched from a live API (e.g., CoinGecko).
    The table grows over time so you can chart intra-day price movements.
    """

    __tablename__ = "live_crypto_prices"

    # --- Columns -----------------------------------------------------------
    id                          = Column(Integer, primary_key=True, autoincrement=True)
    coin_id                     = Column(String(50),   nullable=False, index=True)
    coin_name                   = Column(String(100))
    name                        = synonym("coin_name")
    symbol                      = Column(String(20))
    current_price               = Column(Numeric(20, 8))
    market_cap                  = Column(Numeric(25, 2))
    total_volume                = Column(Numeric(25, 2))
    price_change_24h            = Column(Numeric(20, 8))
    price_change_percentage_24h = Column(Numeric(10, 4))
    market_cap_rank             = Column(Integer)
    high_24h                    = Column(Numeric(20, 8))
    low_24h                     = Column(Numeric(20, 8))
    circulating_supply          = Column(Numeric(25, 2))
    total_supply                = Column(Numeric(25, 2))
    last_updated                = Column(DateTime)
    fetched_at                  = Column(DateTime, default=datetime.utcnow)

    # --- Index on fetched_at for time-range queries -------------------------
    __table_args__ = (
        Index("idx_live_fetched_at", "fetched_at"),
    )

    def __repr__(self):
        return (
            f"<LiveCryptoPrice(coin_id='{self.coin_id}', "
            f"price={self.current_price}, fetched_at={self.fetched_at})>"
        )


# ===========================================================================
# MODEL 2: HistoricalPrice
# ===========================================================================
class HistoricalPrice(Base):
    """
    Stores daily OHLCV data (Open, High, Low, Close, Volume) per coin.

    Used for trend analysis, moving-average calculations, and volatility
    metrics.  A unique constraint ensures only one row per coin per day.
    """

    __tablename__ = "historical_prices"

    # --- Columns -----------------------------------------------------------
    id          = Column(Integer, primary_key=True, autoincrement=True)
    coin_id     = Column(String(50), nullable=False, index=True)
    date        = Column(Date,       nullable=False, index=True)
    open_price  = Column(Numeric(20, 8))
    high_price  = Column(Numeric(20, 8))
    low_price   = Column(Numeric(20, 8))
    close_price = Column(Numeric(20, 8))
    volume      = Column(Numeric(25, 2))
    fetched_at  = Column(DateTime, default=datetime.utcnow)

    # --- One row per coin per day -------------------------------------------
    __table_args__ = (
        UniqueConstraint("coin_id", "date", name="uq_hist_coin_date"),
    )

    def __repr__(self):
        return (
            f"<HistoricalPrice(coin_id='{self.coin_id}', "
            f"date={self.date}, close={self.close_price})>"
        )


# ===========================================================================
# MODEL 3: Portfolio
# ===========================================================================
class Portfolio(Base):
    """
    Tracks the user's cryptocurrency holdings.

    Each row represents a single "lot" — one purchase event of a specific
    coin.  The `current_value` and `roi` columns are refreshed periodically
    by the analytics engine.
    """

    __tablename__ = "portfolio"

    # --- Columns -----------------------------------------------------------
    id            = Column(Integer, primary_key=True, autoincrement=True)
    coin_id       = Column(String(50),  nullable=False, index=True)
    coin_name     = Column(String(100))
    name          = synonym("coin_name")
    symbol        = Column(String(20))
    quantity      = Column(Numeric(20, 8), nullable=False)
    buy_price     = Column(Numeric(20, 8), nullable=False)
    buy_date      = Column(Date,           nullable=False)
    current_value = Column(Numeric(20, 8))
    roi           = Column(Numeric(10, 4))
    notes         = Column(Text)
    created_at    = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<Portfolio(coin_id='{self.coin_id}', qty={self.quantity}, "
            f"buy_price={self.buy_price}, roi={self.roi})>"
        )


# ===========================================================================
# MODEL 4: SentimentData
# ===========================================================================
class SentimentData(Base):
    """
    Stores sentiment analysis results from news / social-media sources.

    Each row is one article or post, scored on a scale from –1.0 (very
    negative) to +1.0 (very positive).
    """

    __tablename__ = "sentiment_data"

    # --- Columns -----------------------------------------------------------
    id              = Column(Integer, primary_key=True, autoincrement=True)
    coin_id         = Column(String(50),  nullable=False, index=True)
    source          = Column(String(100))
    title           = Column(Text)
    url             = Column(Text)
    sentiment_score = Column(Numeric(5, 4))
    published_at    = Column(DateTime, index=True)
    fetched_at      = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<SentimentData(coin_id='{self.coin_id}', "
            f"score={self.sentiment_score}, source='{self.source}')>"
        )


# ===========================================================================
# Table creation / deletion helpers
# ===========================================================================

def create_all_tables():
    """
    Create all tables defined above in the database.

    Uses SQLAlchemy's `Base.metadata.create_all()`, which is safe to call
    repeatedly — it only creates tables that do not already exist.
    """
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("All database tables created successfully ✓")
        print("All tables created successfully.")
    except Exception as exc:
        logger.error("Failed to create tables: %s", exc)
        print(f"Error creating tables: {exc}")


def drop_all_tables():
    """
    Drop ALL tables defined in this module.

    ⚠️  This is destructive!  A confirmation prompt is shown before
    proceeding so that tables are not accidentally deleted.
    """
    # Safety confirmation — prevents accidental data loss
    confirm = input(
        "⚠️  WARNING: This will DROP all tables and delete all data.\n"
        "Type 'yes' to confirm: "
    )

    if confirm.strip().lower() != "yes":
        print("Aborted — no tables were dropped.")
        logger.info("drop_all_tables() aborted by user.")
        return

    try:
        engine = get_engine()
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables DROPPED.")
        print("All tables dropped successfully.")
    except Exception as exc:
        logger.error("Failed to drop tables: %s", exc)
        print(f"Error dropping tables: {exc}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    """
    Run directly to create all tables:
        python -m database.create_tables
    """
    print("Creating database tables …")
    create_all_tables()
