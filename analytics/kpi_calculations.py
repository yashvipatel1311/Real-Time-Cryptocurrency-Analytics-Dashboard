"""
kpi_calculations.py — KPI Calculations and Reporting
======================================================

Implements calculations for daily returns, percentage growth over arbitrary
periods, market dominance, top gainers and losers, and overall high-level
KPI summaries suitable for executive reporting and dashboard visualization.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from config.config import Config
from utils.logger import get_logger
from utils.helper_functions import export_to_csv, safe_float

logger = get_logger(__name__)


def calculate_daily_returns(df: pd.DataFrame, price_column: str = "close_price") -> pd.DataFrame:
    """
    Calculate the daily returns (percentage change day-over-day) for a coin
    or multiple coins.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing price data. Must contain a date/timestamp and a price.
    price_column : str, optional
        The column representing price (default is 'close_price').

    Returns
    -------
    pd.DataFrame
        Original DataFrame with a new column 'daily_return' added.
    """
    if df.empty or price_column not in df.columns:
        logger.warning(f"Empty DataFrame or missing column '{price_column}'. Cannot calculate daily returns.")
        return df

    # Create a copy to prevent SettingWithCopyWarning
    df_copy = df.copy()

    # If the DataFrame contains multiple coins, group by coin_id to avoid cross-coin returns
    if "coin_id" in df_copy.columns:
        # Sort values chronologically before calculating percentage change
        if "date" in df_copy.columns:
            df_copy = df_copy.sort_values(by=["coin_id", "date"])
        df_copy["daily_return"] = df_copy.groupby("coin_id")[price_column].pct_change()
    else:
        if "date" in df_copy.columns:
            df_copy = df_copy.sort_values(by="date")
        df_copy["daily_return"] = df_copy[price_column].pct_change()

    # Fill NaN values (first day return) with 0.0
    df_copy["daily_return"] = df_copy["daily_return"].fillna(0.0)

    logger.debug("Successfully calculated daily returns.")
    return df_copy


def calculate_percentage_growth(
    df: pd.DataFrame,
    price_column: str = "close_price",
    periods: Optional[Dict[str, int]] = None
) -> Dict[str, float]:
    """
    Calculate price growth percentages over various periods (e.g. 7-day, 30-day).

    Parameters
    ----------
    df : pd.DataFrame
        Chronological price DataFrame for a single coin.
    price_column : str, optional
        The column representing price (default is 'close_price').
    periods : dict, optional
        A dictionary mapping period name to number of days (e.g. {'7d': 7}).

    Returns
    -------
    dict
        A dictionary containing period names and their respective percentage growths.
    """
    if df.empty or len(df) < 2 or price_column not in df.columns:
        return {"growth_pct": 0.0}

    if periods is None:
        periods = {"7d": 7, "30d": 30, "90d": 90}

    # Ensure chronological order
    df_sorted = df.copy()
    if "date" in df_sorted.columns:
        df_sorted = df_sorted.sort_values(by="date")

    latest_price = safe_float(df_sorted.iloc[-1][price_column])
    growth_metrics = {}

    for label, days in periods.items():
        if len(df_sorted) > days:
            past_price = safe_float(df_sorted.iloc[-(days + 1)][price_column])
            if past_price > 0:
                growth_metrics[label] = ((latest_price - past_price) / past_price) * 100.0
            else:
                growth_metrics[label] = 0.0
        else:
            # Fallback to the first available price if historical series is too short
            first_price = safe_float(df_sorted.iloc[0][price_column])
            if first_price > 0:
                growth_metrics[label] = ((latest_price - first_price) / first_price) * 100.0
            else:
                growth_metrics[label] = 0.0

    return growth_metrics


def get_top_gainers_losers(
    df: pd.DataFrame,
    price_change_col: str = "price_change_percentage_24h",
    n: int = 3
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identifies top N gainers and top N losers in a set of market ticks.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of live cryptocurrency snapshot data.
    price_change_col : str, optional
        The column containing percentage change (default is 'price_change_percentage_24h').
    n : int, optional
        Number of items to return (default is 3).

    Returns
    -------
    (pd.DataFrame, pd.DataFrame)
        Top gainers and top losers.
    """
    if df.empty or price_change_col not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    # Filter out records where coin_id or price change is null
    df_clean = df.dropna(subset=[price_change_col])

    # Get largest and smallest price changes
    top_gainers = df_clean.nlargest(n, price_change_col)
    top_losers = df_clean.nsmallest(n, price_change_col)

    return top_gainers, top_losers


def calculate_market_dominance(df: pd.DataFrame, market_cap_col: str = "market_cap") -> pd.DataFrame:
    """
    Calculates the market cap dominance of each coin relative to the total cap in the dataset.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing live prices/caps.
    market_cap_col : str, optional
        The column representing market capitalization.

    Returns
    -------
    pd.DataFrame
        Original DataFrame with a new column 'market_dominance_pct' added.
    """
    if df.empty or market_cap_col not in df.columns:
        return df

    df_copy = df.copy()
    total_market_cap = df_copy[market_cap_col].sum()

    if total_market_cap > 0:
        df_copy["market_dominance_pct"] = (df_copy[market_cap_col] / total_market_cap) * 100.0
    else:
        df_copy["market_dominance_pct"] = 0.0

    return df_copy


def generate_kpi_summary(live_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates high-level portfolio/market KPIs from a live snapshot DataFrame into a
    tidy DataFrame, perfect for importing into power BI.

    Parameters
    ----------
    live_df : pd.DataFrame
        DataFrame returned by the live data fetch pipeline.

    Returns
    -------
    pd.DataFrame
        Single-row or aggregated KPI summary DataFrame.
    """
    if live_df.empty:
        logger.warning("Empty live data received — creating mock empty KPI summary.")
        return pd.DataFrame()

    try:
        # 1. Total Market Cap
        total_market_cap = live_df["market_cap"].sum() if "market_cap" in live_df.columns else 0.0

        # 2. Total Volume
        total_volume = live_df["total_volume"].sum() if "total_volume" in live_df.columns else 0.0

        # 3. Average Price Change (24h)
        avg_change_24h = (
            live_df["price_change_percentage_24h"].mean()
            if "price_change_percentage_24h" in live_df.columns
            else 0.0
        )

        # 4. Top Gainer / Loser
        top_gainer = "N/A"
        top_gainer_pct = 0.0
        top_loser = "N/A"
        top_loser_pct = 0.0

        if "price_change_percentage_24h" in live_df.columns and "coin_id" in live_df.columns:
            g, l = get_top_gainers_losers(live_df, n=1)
            if not g.empty:
                top_gainer = g.iloc[0]["coin_id"]
                top_gainer_pct = safe_float(g.iloc[0]["price_change_percentage_24h"])
            if not l.empty:
                top_loser = l.iloc[0]["coin_id"]
                top_loser_pct = safe_float(l.iloc[0]["price_change_percentage_24h"])

        # 5. Build KPI DataFrame
        kpi_data = {
            "metric_date": [pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")],
            "total_market_cap": [total_market_cap],
            "total_volume": [total_volume],
            "average_price_change_24h": [avg_change_24h],
            "top_gainer_coin": [top_gainer],
            "top_gainer_pct": [top_gainer_pct],
            "top_loser_coin": [top_loser],
            "top_loser_pct": [top_loser_pct],
            "active_coins_count": [len(live_df)]
        }

        kpi_df = pd.DataFrame(kpi_data)
        logger.info("Generated high-level market KPI summary.")
        return kpi_df

    except Exception as e:
        logger.error(f"Error generating KPI summary: {e}")
        return pd.DataFrame()


def export_kpi_report(kpi_df: pd.DataFrame) -> Path:
    """
    Exports the calculated KPI metrics to a designated CSV file.
    """
    filename = "kpi_report.csv"
    logger.info("Exporting KPI report to CSV...")
    return export_to_csv(kpi_df, filename)


if __name__ == "__main__":
    print("Testing KPI calculations with dummy data...")
    dummy_market = pd.DataFrame({
        "id": ["bitcoin", "ethereum", "solana"],
        "coin_id": ["bitcoin", "ethereum", "solana"],
        "name": ["Bitcoin", "Ethereum", "Solana"],
        "current_price": [68000.0, 3500.0, 150.0],
        "market_cap": [1300000000000.0, 420000000000.0, 65000000000.0],
        "total_volume": [30000000000.0, 15000000000.0, 4000000000.0],
        "price_change_percentage_24h": [1.5, -2.3, 8.4]
    })

    print("\nLive Snapshot:")
    print(dummy_market)

    print("\nDominance calculation:")
    print(calculate_market_dominance(dummy_market)[["coin_id", "market_dominance_pct"]])

    print("\nGainers & Losers (n=1):")
    g, l = get_top_gainers_losers(dummy_market, n=1)
    print("Gainers:", g["coin_id"].tolist())
    print("Losers:", l["coin_id"].tolist())

    print("\nKPI Summary:")
    kpi = generate_kpi_summary(dummy_market)
    print(kpi.to_string(index=False))
