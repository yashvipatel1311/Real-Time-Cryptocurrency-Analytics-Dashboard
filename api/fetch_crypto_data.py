"""
Fetch Live Cryptocurrency Data — CoinGecko API
================================================

This module fetches LIVE cryptocurrency market data from the CoinGecko API,
converts it into a pandas DataFrame, saves the raw JSON for archival, and
persists the data into the PostgreSQL database via SQLAlchemy.

Key Functions:
    - fetch_live_prices()      : Hit the CoinGecko /coins/markets endpoint
    - save_live_prices_to_db() : Write DataFrame rows to the live_crypto_prices table
    - fetch_and_store_live_prices() : Orchestrator that calls both above

Usage:
    python -m api.fetch_crypto_data
"""

# ──────────────────────────────────────────────────────────────────────
# Imports
# ──────────────────────────────────────────────────────────────────────
import requests                         # HTTP requests to CoinGecko
import pandas as pd                     # Data manipulation
from datetime import datetime, timezone # Timestamps
from typing import Optional, List       # Type hints

# Project-internal imports (shared interfaces)
from config.config import Config                      # Central configuration
from utils.logger import get_logger                   # Logging utility
from utils.helper_functions import (
    save_raw_json,                                    # Save raw API response
    safe_float,                                       # Safe numeric conversion
    retry_on_failure,                                 # Retry decorator
)
from database.db_connection import get_session        # SQLAlchemy session
from database.create_tables import LiveCryptoPrice    # ORM model

# ──────────────────────────────────────────────────────────────────────
# Logger setup
# ──────────────────────────────────────────────────────────────────────
logger = get_logger(__name__)


# ======================================================================
# 1. FETCH LIVE PRICES FROM COINGECKO
# ======================================================================

@retry_on_failure(max_retries=3, delay=5)
def fetch_live_prices(
    coins: Optional[List[str]] = None,
    currency: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch live cryptocurrency market data from the CoinGecko API.

    This function calls the ``/coins/markets`` endpoint, which returns
    current price, market cap, volume, and 24-hour change data for the
    requested coins.

    Parameters
    ----------
    coins : list of str, optional
        Coin IDs to fetch (e.g. ``['bitcoin', 'ethereum']``).
        Defaults to ``Config.DEFAULT_COINS``.
    currency : str, optional
        Fiat currency for prices (e.g. ``'usd'``).
        Defaults to ``Config.DEFAULT_CURRENCY``.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing live market data for each coin, or an
        empty DataFrame if the request fails.

    Example
    -------
    >>> df = fetch_live_prices(['bitcoin', 'ethereum'], 'usd')
    >>> print(df[['id', 'current_price']].head())
    """

    # --- Use defaults from Config if not provided -----------------------
    if coins is None:
        coins = Config.DEFAULT_COINS
    if currency is None:
        currency = Config.DEFAULT_CURRENCY

    # --- Build the request URL and query parameters ---------------------
    url = "https://api.coingecko.com/api/v3/coins/markets"

    params = {
        "vs_currency": currency,             # e.g. 'usd'
        "ids": ",".join(coins),              # Comma-separated coin IDs
        "order": "market_cap_desc",          # Sort by market cap
        "per_page": 50,                      # Max results per page
        "page": 1,                           # First page
        "sparkline": "false",                # No sparkline data needed
        "price_change_percentage": "24h",    # Include 24h change
    }

    # --- Build headers (include API key if available) -------------------
    headers = {
        "Accept": "application/json",
    }

    # Add the CoinGecko demo key header if a real key is configured
    api_key = Config.COINGECKO_API_KEY
    if api_key and api_key not in ("", "your_coingecko_api_key_here"):
        headers["x_cg_demo_key"] = api_key
        logger.info("Using CoinGecko API key for authenticated request.")
    else:
        logger.info("No CoinGecko API key set — using free tier.")

    # --- Make the API request -------------------------------------------
    logger.info(f"Fetching live prices for {len(coins)} coins in {currency}…")

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()  # Raise HTTPError for 4xx/5xx status codes

        # Parse the JSON response
        data = response.json()
        logger.info(f"Successfully fetched data for {len(data)} coins.")

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error while fetching live prices: {http_err}")
        logger.error(f"Response status: {response.status_code}")
        return pd.DataFrame()

    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error: {conn_err}")
        return pd.DataFrame()

    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Request timed out: {timeout_err}")
        return pd.DataFrame()

    except requests.exceptions.RequestException as req_err:
        logger.error(f"Unexpected request error: {req_err}")
        return pd.DataFrame()

    # --- Save the raw JSON for archival / debugging ---------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_filename = f"live_prices_{timestamp}.json"
    save_raw_json(data, raw_filename)
    logger.info(f"Raw JSON saved as {raw_filename}")

    # --- Convert to DataFrame -------------------------------------------
    try:
        df = pd.DataFrame(data)
        logger.info(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns.")
        return df

    except Exception as e:
        logger.error(f"Error creating DataFrame from API data: {e}")
        return pd.DataFrame()


# ======================================================================
# 2. SAVE LIVE PRICES TO DATABASE
# ======================================================================

def save_live_prices_to_db(df: pd.DataFrame) -> int:
    """
    Save live price data from a DataFrame into the ``live_crypto_prices``
    database table.

    Each row of the DataFrame is mapped to a ``LiveCryptoPrice`` ORM
    object and committed in a single batch transaction for efficiency.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame returned by ``fetch_live_prices()``, expected to have
        CoinGecko-style column names (e.g. ``id``, ``current_price``).

    Returns
    -------
    int
        The number of records successfully saved to the database.
    """

    # Guard: nothing to save
    if df.empty:
        logger.warning("Empty DataFrame received — nothing to save to DB.")
        return 0

    session = get_session()
    records_saved = 0

    try:
        # Iterate over each row and create an ORM object
        for _, row in df.iterrows():
            record = LiveCryptoPrice(
                coin_id=row.get("id", ""),
                coin_name=row.get("name", ""),
                symbol=row.get("symbol", ""),
                current_price=safe_float(row.get("current_price"), 0.0),
                market_cap=safe_float(row.get("market_cap"), 0.0),
                total_volume=safe_float(row.get("total_volume"), 0.0),
                price_change_24h=safe_float(row.get("price_change_24h"), 0.0),
                price_change_percentage_24h=safe_float(
                    row.get("price_change_percentage_24h"), 0.0
                ),
                market_cap_rank=int(row.get("market_cap_rank", 0) or 0),
                high_24h=safe_float(row.get("high_24h"), 0.0),
                low_24h=safe_float(row.get("low_24h"), 0.0),
                circulating_supply=safe_float(row.get("circulating_supply"), 0.0),
                total_supply=safe_float(row.get("total_supply"), 0.0),
                last_updated=row.get("last_updated", ""),
                fetched_at=datetime.now(timezone.utc),
            )
            session.add(record)
            records_saved += 1

        # Commit all records in one transaction
        session.commit()
        logger.info(f"✅ Successfully saved {records_saved} records to live_crypto_prices.")

    except Exception as e:
        # Roll back on any error to keep DB consistent
        session.rollback()
        logger.error(f"❌ Error saving live prices to database: {e}")
        records_saved = 0

    finally:
        # Always close the session to free resources
        session.close()

    return records_saved


# ======================================================================
# 3. ORCHESTRATOR — FETCH AND STORE
# ======================================================================

def fetch_and_store_live_prices() -> pd.DataFrame:
    """
    High-level orchestrator that fetches live prices from CoinGecko
    and persists them to the database.

    This is the main entry point for scheduled / cron-based data
    ingestion of live cryptocurrency prices.

    Returns
    -------
    pd.DataFrame
        The fetched DataFrame (also saved to DB), or an empty DataFrame
        on failure.
    """
    logger.info("=" * 60)
    logger.info("Starting live price fetch-and-store pipeline…")
    logger.info("=" * 60)

    # Step 1 — Fetch live prices from CoinGecko
    df = fetch_live_prices()

    if df.empty:
        logger.warning("No data fetched — pipeline aborted.")
        return df

    # Step 2 — Save to database
    saved_count = save_live_prices_to_db(df)
    logger.info(f"Pipeline complete. {saved_count} records stored.")

    return df


# ======================================================================
# 4. MAIN ENTRY POINT
# ======================================================================

if __name__ == "__main__":
    """
    Run this module directly to test the live price fetching pipeline.

    Usage:
        python -m api.fetch_crypto_data
    """
    logger.info("Running fetch_crypto_data as standalone script…")

    result_df = fetch_and_store_live_prices()

    if not result_df.empty:
        print("\n📊 Live Prices Summary:")
        print("-" * 50)
        # Display a compact table of the key columns
        display_cols = ["id", "current_price", "price_change_percentage_24h", "market_cap"]
        available_cols = [c for c in display_cols if c in result_df.columns]
        print(result_df[available_cols].to_string(index=False))
        print(f"\nTotal coins fetched: {len(result_df)}")
    else:
        print("⚠️  No data was fetched. Check logs for details.")
