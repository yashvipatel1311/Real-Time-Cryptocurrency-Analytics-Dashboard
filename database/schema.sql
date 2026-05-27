-- ==========================================================================
-- schema.sql — PostgreSQL DDL for Real-Time Cryptocurrency Analytics
-- ==========================================================================
-- This file is a *reference* copy of the database schema.  The application
-- normally creates tables via SQLAlchemy ORM models (create_tables.py),
-- but you can also run this script manually with:
--
--     psql -U <user> -d <database> -f database/schema.sql
--
-- All tables use IF NOT EXISTS so re-running is safe.
-- ==========================================================================


-- ==========================================================================
-- TABLE 1: live_crypto_prices
-- --------------------------------------------------------------------------
-- Stores the latest price snapshot for each cryptocurrency, fetched from
-- a live API (e.g., CoinGecko).  Each row represents a single "tick" for
-- one coin at a specific point in time.
-- ==========================================================================
CREATE TABLE IF NOT EXISTS live_crypto_prices (
    id                          SERIAL PRIMARY KEY,             -- Auto-increment primary key
    coin_id                     VARCHAR(50)  NOT NULL,          -- API identifier (e.g. 'bitcoin')
    coin_name                   VARCHAR(100),                   -- Human-readable name
    symbol                      VARCHAR(20),                    -- Ticker symbol (e.g. 'BTC')
    current_price               DECIMAL(20, 8),                 -- Current price in USD
    market_cap                  DECIMAL(25, 2),                 -- Total market capitalisation
    total_volume                DECIMAL(25, 2),                 -- 24-hour trading volume
    price_change_24h            DECIMAL(20, 8),                 -- Absolute price change (24 h)
    price_change_percentage_24h DECIMAL(10, 4),                 -- Percentage price change (24 h)
    market_cap_rank             INTEGER,                        -- Rank by market cap
    high_24h                    DECIMAL(20, 8),                 -- 24-hour high
    low_24h                     DECIMAL(20, 8),                 -- 24-hour low
    circulating_supply          DECIMAL(25, 2),                 -- Coins currently in circulation
    total_supply                DECIMAL(25, 2),                 -- Maximum / total supply
    last_updated                TIMESTAMP,                      -- Timestamp from the API
    fetched_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- When we fetched the data
);

-- Indexes: speed up filtering by coin and time-range queries
CREATE INDEX IF NOT EXISTS idx_live_coin_id    ON live_crypto_prices (coin_id);
CREATE INDEX IF NOT EXISTS idx_live_fetched_at ON live_crypto_prices (fetched_at);


-- ==========================================================================
-- TABLE 2: historical_prices
-- --------------------------------------------------------------------------
-- Stores daily OHLCV (Open, High, Low, Close, Volume) data for each coin.
-- Used for trend analysis, moving averages, and volatility calculations.
-- ==========================================================================
CREATE TABLE IF NOT EXISTS historical_prices (
    id          SERIAL PRIMARY KEY,             -- Auto-increment primary key
    coin_id     VARCHAR(50) NOT NULL,           -- API identifier (e.g. 'bitcoin')
    date        DATE        NOT NULL,           -- Trading date
    open_price  DECIMAL(20, 8),                 -- Opening price (USD)
    high_price  DECIMAL(20, 8),                 -- Highest price of the day
    low_price   DECIMAL(20, 8),                 -- Lowest price of the day
    close_price DECIMAL(20, 8),                 -- Closing price (USD)
    volume      DECIMAL(25, 2),                 -- Trading volume for the day
    fetched_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- When we stored this record
);

-- Indexes: queries usually filter by coin + date range
CREATE INDEX IF NOT EXISTS idx_hist_coin_id ON historical_prices (coin_id);
CREATE INDEX IF NOT EXISTS idx_hist_date    ON historical_prices (date);

-- Composite unique constraint — one row per coin per day
ALTER TABLE historical_prices
    ADD CONSTRAINT uq_hist_coin_date UNIQUE (coin_id, date);


-- ==========================================================================
-- TABLE 3: portfolio
-- --------------------------------------------------------------------------
-- Tracks the user's cryptocurrency holdings.  Each row is a single "lot"
-- (one purchase of a specific coin).  current_value and roi are updated
-- periodically by the analytics engine.
-- ==========================================================================
CREATE TABLE IF NOT EXISTS portfolio (
    id             SERIAL PRIMARY KEY,                  -- Auto-increment primary key
    coin_id        VARCHAR(50)  NOT NULL,               -- API identifier (e.g. 'bitcoin')
    coin_name      VARCHAR(100),                        -- Human-readable name
    symbol         VARCHAR(20),                         -- Ticker symbol
    quantity       DECIMAL(20, 8)  NOT NULL,            -- Number of coins held
    buy_price      DECIMAL(20, 8)  NOT NULL,            -- Price per coin at purchase
    buy_date       DATE            NOT NULL,            -- Date of purchase
    current_value  DECIMAL(20, 8),                      -- quantity × latest price (computed)
    roi            DECIMAL(10, 4),                       -- Return on Investment in % (computed)
    notes          TEXT,                                 -- Optional user notes
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Record creation timestamp
);

-- Index: look up holdings by coin quickly
CREATE INDEX IF NOT EXISTS idx_portfolio_coin_id ON portfolio (coin_id);


-- ==========================================================================
-- TABLE 4: sentiment_data
-- --------------------------------------------------------------------------
-- Stores sentiment analysis results scraped / fetched from news APIs or
-- social-media sources.  Each row is one article or post, scored between
-- –1.0 (very negative) and +1.0 (very positive).
-- ==========================================================================
CREATE TABLE IF NOT EXISTS sentiment_data (
    id               SERIAL PRIMARY KEY,                  -- Auto-increment primary key
    coin_id          VARCHAR(50) NOT NULL,                -- Related cryptocurrency
    source           VARCHAR(100),                        -- Source name (e.g. 'CryptoPanic')
    title            TEXT,                                -- Article / post headline
    url              TEXT,                                -- Link to the original content
    sentiment_score  DECIMAL(5, 4),                       -- Score: –1.0 … +1.0
    published_at     TIMESTAMP,                           -- When the content was published
    fetched_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- When we stored this record
);

-- Indexes: filter by coin and by publication date
CREATE INDEX IF NOT EXISTS idx_sent_coin_id      ON sentiment_data (coin_id);
CREATE INDEX IF NOT EXISTS idx_sent_published_at ON sentiment_data (published_at);


-- ==========================================================================
-- Done!  All four tables and their indexes are ready.
-- ==========================================================================
