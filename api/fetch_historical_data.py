"""
Fetch Historical Cryptocurrency Data — CoinGecko API
======================================================

This module fetches HISTORICAL price data from the CoinGecko
``/coins/{id}/market_chart`` endpoint.  The raw OHLC-like data is
transformed into a clean pandas DataFrame, saved as raw JSON, and
persisted to the ``historical_prices`` database table.

Key Functions:
    - fetch_historical_prices()       : Fetch data for a single coin
    - save_historical_to_db()         : Write DataFrame to the DB
    - fetch_and_store_historical()    : Orchestrate fetch + store for many coins

Usage:
    python -m api.fetch_historical_data
"""

# ──────────────────────────────────────────────────────────────────────
# Imports
# ──────────────────────────────────────────────────────────────────────
import requests                         # HTTP requests
import pandas as pd                     # Data manipulation
import numpy as np                      # Numeric helpers
from datetime import datetime, timezone # Timestamps
from typing import Optional, List       # Type hints

# Project-internal imports
from config.config import Config
from utils.logger import get_logger
from utils.helper_functions import (
    save_raw_json,
    safe_float,
    retry_on_failure,
)
from database.db_connection import get_session
from database.create_tables import HistoricalPrice

# ──────────────────────────────────────────────────────────────────────
# Logger
# ──────────────────────────────────────────────────────────────────────
logger = get_logger(__name__)


# ======================================================================
# 1. FETCH HISTORICAL PRICES FOR A SINGLE COIN
# ======================================================================

@retry_on_failure(max_retries=3, delay=5)
def fetch_historical_prices(
    coin_id: str,
    days: int = 30,
    currency: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch historical market-chart data for a single coin from CoinGecko.

    The ``/coins/{id}/market_chart`` endpoint returns arrays of
    ``[timestamp_ms, value]`` pairs for prices, market caps, and volumes.
    This function converts those arrays into a tidy DataFrame.

    Parameters
    ----------
    coin_id : str
        CoinGecko coin identifier, e.g. ``'bitcoin'``.
    days : int, optional
        Number of past days of data to request (default ``30``).
    currency : str, optional
        Fiat currency (default from ``Config.DEFAULT_CURRENCY``).

    Returns
    -------
    pd.DataFrame
        Columns: ``date``, ``open_price``, ``high_price``, ``low_price``,
        ``close_price``, ``volume``, ``market_cap``.
        Empty DataFrame on failure.

    Notes
    -----
    CoinGecko returns *prices* (not true OHLC) in the ``market_chart``
    endpoint.  We approximate OHLC by resampling daily:
        - open  → first price of the day
        - close → last price of the day
        - high  → max price of the day
        - low   → min price of the day
    """

    # --- Defaults -------------------------------------------------------
    if currency is None:
        currency = Config.DEFAULT_CURRENCY

    # --- Build request --------------------------------------------------
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"

    params = {
        "vs_currency": currency,
        "days": days,
    }

    headers = {"Accept": "application/json"}

    # Add API key header if configured
    api_key = Config.COINGECKO_API_KEY
    if api_key and api_key not in ("", "your_coingecko_api_key_here"):
        headers["x_cg_demo_key"] = api_key

    logger.info(f"Fetching {days}-day historical data for '{coin_id}' in {currency}…")

    # --- API call -------------------------------------------------------
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Received historical data for '{coin_id}'.")

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error fetching history for {coin_id}: {http_err}")
        return pd.DataFrame()

    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error: {conn_err}")
        return pd.DataFrame()

    except requests.exceptions.Timeout:
        logger.error(f"Request timed out for {coin_id}.")
        return pd.DataFrame()

    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request error for {coin_id}: {req_err}")
        return pd.DataFrame()

    # --- Save raw JSON ---------------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_filename = f"historical_{coin_id}_{timestamp}.json"
    save_raw_json(data, raw_filename)
    logger.info(f"Raw JSON saved as {raw_filename}")

    # --- Transform into DataFrame ----------------------------------------
    try:
        # Extract the three arrays from the API response
        prices = data.get("prices", [])
        market_caps = data.get("market_caps", [])
        volumes = data.get("total_volumes", [])

        if not prices:
            logger.warning(f"No price data returned for '{coin_id}'.")
            return pd.DataFrame()

        # Build a raw DataFrame with millisecond timestamps
        price_df = pd.DataFrame(prices, columns=["timestamp_ms", "price"])
        price_df["date"] = pd.to_datetime(price_df["timestamp_ms"], unit="ms", utc=True)

        # Resample to daily OHLC-like values
        price_df = price_df.set_index("date")
        daily = price_df["price"].resample("D").agg(
            open_price="first",
            high_price="max",
            low_price="min",
            close_price="last",
        ).dropna()

        # Add volume (daily sum)
        if volumes:
            vol_df = pd.DataFrame(volumes, columns=["timestamp_ms", "volume"])
            vol_df["date"] = pd.to_datetime(vol_df["timestamp_ms"], unit="ms", utc=True)
            vol_df = vol_df.set_index("date")
            daily_vol = vol_df["volume"].resample("D").sum()
            daily = daily.join(daily_vol, how="left")
        else:
            daily["volume"] = 0.0

        # Add market cap (daily last)
        if market_caps:
            mc_df = pd.DataFrame(market_caps, columns=["timestamp_ms", "market_cap"])
            mc_df["date"] = pd.to_datetime(mc_df["timestamp_ms"], unit="ms", utc=True)
            mc_df = mc_df.set_index("date")
            daily_mc = mc_df["market_cap"].resample("D").last()
            daily = daily.join(daily_mc, how="left")
        else:
            daily["market_cap"] = 0.0

        # Reset index so 'date' is a regular column
        daily = daily.reset_index()
        daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")

        logger.info(
            f"Transformed historical data for '{coin_id}': "
            f"{len(daily)} daily records."
        )
        return daily

    except Exception as e:
        logger.error(f"Error transforming historical data for {coin_id}: {e}")
        return pd.DataFrame()


# ======================================================================
# 2. SAVE HISTORICAL DATA TO DATABASE
# ======================================================================

def save_historical_to_db(df: pd.DataFrame, coin_id: str) -> int:
    """
    Save historical price data to the ``historical_prices`` table.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns ``date``, ``open_price``, ``high_price``,
        ``low_price``, ``close_price``, ``volume``, ``market_cap``.
    coin_id : str
        CoinGecko coin identifier (stored alongside each row).

    Returns
    -------
    int
        Number of records saved.
    """

    if df.empty:
        logger.warning(f"Empty DataFrame for '{coin_id}' — skipping DB save.")
        return 0

    session = get_session()
    records_saved = 0

    try:
        for _, row in df.iterrows():
            record = HistoricalPrice(
                coin_id=coin_id,
                date=row.get("date", ""),
                open_price=safe_float(row.get("open_price"), 0.0),
                high_price=safe_float(row.get("high_price"), 0.0),
                low_price=safe_float(row.get("low_price"), 0.0),
                close_price=safe_float(row.get("close_price"), 0.0),
                volume=safe_float(row.get("volume"), 0.0),
                fetched_at=datetime.now(timezone.utc),
            )
            session.add(record)
            records_saved += 1

        session.commit()
        logger.info(
            f"✅ Saved {records_saved} historical records for '{coin_id}'."
        )

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error saving historical data for '{coin_id}': {e}")
        records_saved = 0

    finally:
        session.close()

    return records_saved


# ======================================================================
# 3. ORCHESTRATOR — FETCH AND STORE FOR ALL COINS
# ======================================================================

def fetch_and_store_historical(
    coins: Optional[List[str]] = None,
    days: int = 30,
) -> dict:
    """
    Fetch and store historical data for a list of coins.

    Parameters
    ----------
    coins : list of str, optional
        Coin IDs to fetch.  Defaults to ``Config.DEFAULT_COINS``.
    days : int, optional
        Number of days of history to request (default ``30``).

    Returns
    -------
    dict
        Mapping of ``{coin_id: records_saved}`` for each coin.
    """

    if coins is None:
        coins = Config.DEFAULT_COINS

    logger.info("=" * 60)
    logger.info(
        f"Starting historical data pipeline for {len(coins)} coins "
        f"({days} days)…"
    )
    logger.info("=" * 60)

    results: dict = {}

    for idx, coin_id in enumerate(coins):
        logger.info(f"--- Processing: {coin_id} ---")

        # Fetch
        df = fetch_historical_prices(coin_id, days=days)

        if df.empty:
            logger.warning(f"No data for '{coin_id}' — skipping.")
            results[coin_id] = 0
        else:
            # Store
            saved = save_historical_to_db(df, coin_id)
            results[coin_id] = saved

        # Respect CoinGecko free-tier rate limit (~10 calls/min).
        # Sleep between requests to avoid HTTP 429 errors.
        if idx < len(coins) - 1:
            import time
            time.sleep(6)

    # Summary
    total = sum(results.values())
    logger.info(f"Historical pipeline complete. Total records saved: {total}")
    return results


# ======================================================================
# 4. MAIN ENTRY POINT
# ======================================================================

if __name__ == "__main__":
    """
    Run this module directly to test historical data fetching.

    Usage:
        python -m api.fetch_historical_data
    """
    logger.info("Running fetch_historical_data as standalone script…")

    results = fetch_and_store_historical()

    print("\n📈 Historical Data Fetch Results:")
    print("-" * 40)
    for coin, count in results.items():
        status = "✅" if count > 0 else "⚠️"
        print(f"  {status} {coin}: {count} records")
    print(f"\n  Total: {sum(results.values())} records")
