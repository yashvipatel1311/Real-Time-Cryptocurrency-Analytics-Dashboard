"""
data_cleaning.py — Data Cleaning & Preprocessing Module
=========================================================

Consolidates all data-cleaning and preprocessing routines in a single,
reusable module.  Every analytics pipeline should run raw data through
these functions **before** performing calculations.

Key Functions:
    - clean_live_prices()      : Standardise a live-price DataFrame
    - clean_historical_data()  : Standardise a historical-price DataFrame
    - handle_missing_values()  : Generic NaN / None handling
    - remove_duplicates()      : De-duplicate rows
    - detect_outliers()        : IQR-based outlier flagging
    - normalize_numeric_cols() : Safe type casting for numeric columns
    - standardize_column_names(): Lowercase + underscore column renaming

Usage:
    from analytics.data_cleaning import clean_live_prices, clean_historical_data
"""

import pandas as pd
import numpy as np
from typing import List, Optional

from utils.logger import get_logger
from utils.helper_functions import safe_float

logger = get_logger(__name__)


# ======================================================================
# 1. COLUMN NAME STANDARDISATION
# ======================================================================

def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise DataFrame column names to lowercase with underscores.

    Strips leading/trailing whitespace, converts to lowercase, and
    replaces spaces and hyphens with underscores.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.

    Returns
    -------
    pd.DataFrame
        DataFrame with cleaned column names.
    """
    if df.empty:
        return df

    df_copy = df.copy()
    df_copy.columns = (
        df_copy.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    logger.debug(f"Standardised {len(df_copy.columns)} column names.")
    return df_copy


# ======================================================================
# 2. MISSING VALUE HANDLING
# ======================================================================

def handle_missing_values(
    df: pd.DataFrame,
    numeric_strategy: str = "zero",
    string_strategy: str = "unknown",
) -> pd.DataFrame:
    """
    Handle missing (NaN / None) values in a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    numeric_strategy : str
        How to fill missing numeric values.
        Options: ``'zero'`` (default), ``'mean'``, ``'median'``, ``'ffill'``.
    string_strategy : str
        Replacement value for missing string columns (default ``'unknown'``).

    Returns
    -------
    pd.DataFrame
        DataFrame with missing values handled.
    """
    if df.empty:
        return df

    df_copy = df.copy()
    initial_nulls = int(df_copy.isnull().sum().sum())

    # --- Numeric columns ---------------------------------------------------
    numeric_cols = df_copy.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        if numeric_strategy == "zero":
            df_copy[numeric_cols] = df_copy[numeric_cols].fillna(0.0)
        elif numeric_strategy == "mean":
            df_copy[numeric_cols] = df_copy[numeric_cols].fillna(
                df_copy[numeric_cols].mean()
            )
        elif numeric_strategy == "median":
            df_copy[numeric_cols] = df_copy[numeric_cols].fillna(
                df_copy[numeric_cols].median()
            )
        elif numeric_strategy == "ffill":
            df_copy[numeric_cols] = df_copy[numeric_cols].ffill()

    # --- String / object columns -------------------------------------------
    string_cols = df_copy.select_dtypes(include=["object"]).columns
    if len(string_cols) > 0:
        df_copy[string_cols] = df_copy[string_cols].fillna(string_strategy)

    final_nulls = int(df_copy.isnull().sum().sum())
    logger.info(
        f"Missing-value handling: {initial_nulls} → {final_nulls} nulls "
        f"(strategy: numeric={numeric_strategy}, string={string_strategy})"
    )
    return df_copy


# ======================================================================
# 3. DUPLICATE REMOVAL
# ======================================================================

def remove_duplicates(
    df: pd.DataFrame,
    subset: Optional[List[str]] = None,
    keep: str = "last",
) -> pd.DataFrame:
    """
    Remove duplicate rows from a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    subset : list of str, optional
        Column names to consider when identifying duplicates.
        Defaults to all columns.
    keep : str
        Which duplicate to keep: ``'first'``, ``'last'``, or ``False``
        (drop all duplicates).  Default is ``'last'``.

    Returns
    -------
    pd.DataFrame
        De-duplicated DataFrame.
    """
    if df.empty:
        return df

    before = len(df)
    df_clean = df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)
    removed = before - len(df_clean)

    if removed > 0:
        logger.info(f"Removed {removed} duplicate rows (subset={subset}, keep={keep}).")
    else:
        logger.debug("No duplicate rows found.")

    return df_clean


# ======================================================================
# 4. NUMERIC TYPE NORMALISATION
# ======================================================================

def normalize_numeric_cols(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Safely convert columns to float using ``safe_float()``.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    columns : list of str, optional
        Columns to convert.  If ``None``, all columns that *look* numeric
        (contain at least 50 % non-null numeric values) are converted.

    Returns
    -------
    pd.DataFrame
        DataFrame with normalised numeric columns.
    """
    if df.empty:
        return df

    df_copy = df.copy()

    if columns is None:
        # Auto-detect columns that should be numeric
        columns = []
        for col in df_copy.columns:
            try:
                numeric_pct = pd.to_numeric(df_copy[col], errors="coerce").notna().mean()
                if numeric_pct >= 0.5 and df_copy[col].dtype == "object":
                    columns.append(col)
            except Exception:
                continue

    for col in columns:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(lambda v: safe_float(v, default=0.0))

    if columns:
        logger.debug(f"Normalised numeric columns: {columns}")

    return df_copy


# ======================================================================
# 5. OUTLIER DETECTION (IQR)
# ======================================================================

def detect_outliers(
    df: pd.DataFrame,
    column: str,
    factor: float = 1.5,
) -> pd.DataFrame:
    """
    Flag outlier rows using the Interquartile Range (IQR) method.

    A new boolean column ``is_outlier`` is added to the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    column : str
        Numeric column to check for outliers.
    factor : float
        IQR multiplier (default 1.5 — standard Tukey fence).

    Returns
    -------
    pd.DataFrame
        DataFrame with an ``is_outlier`` column appended.
    """
    if df.empty or column not in df.columns:
        return df

    df_copy = df.copy()
    series = pd.to_numeric(df_copy[column], errors="coerce")

    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - factor * iqr
    upper_bound = q3 + factor * iqr

    df_copy["is_outlier"] = (series < lower_bound) | (series > upper_bound)

    outlier_count = int(df_copy["is_outlier"].sum())
    logger.info(
        f"Outlier detection on '{column}': {outlier_count}/{len(df_copy)} flagged "
        f"(IQR bounds: [{lower_bound:.4f}, {upper_bound:.4f}])"
    )
    return df_copy


# ======================================================================
# 6. HIGH-LEVEL CLEANERS — Live Prices
# ======================================================================

def clean_live_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full cleaning pipeline for a live-price snapshot DataFrame.

    Steps:
        1. Standardise column names
        2. Remove exact-duplicate rows
        3. Normalise key numeric columns
        4. Handle missing values (zeros for numbers, 'unknown' for strings)
        5. Sort by market cap descending

    Parameters
    ----------
    df : pd.DataFrame
        Raw live-price DataFrame (e.g., from ``fetch_live_prices()``).

    Returns
    -------
    pd.DataFrame
        Cleaned and standardised DataFrame.
    """
    if df.empty:
        logger.warning("Empty DataFrame passed to clean_live_prices — returning as-is.")
        return df

    logger.info(f"Cleaning live prices DataFrame ({len(df)} rows)…")

    # 1. Standardise column names
    df_clean = standardize_column_names(df)

    # 2. Remove exact duplicates
    id_col = "id" if "id" in df_clean.columns else "coin_id"
    df_clean = remove_duplicates(df_clean, subset=[id_col] if id_col in df_clean.columns else None)

    # 3. Normalise numeric columns
    numeric_cols = [
        "current_price", "market_cap", "total_volume",
        "price_change_24h", "price_change_percentage_24h",
        "high_24h", "low_24h", "circulating_supply", "total_supply",
    ]
    existing_numeric = [c for c in numeric_cols if c in df_clean.columns]
    df_clean = normalize_numeric_cols(df_clean, columns=existing_numeric)

    # 4. Handle remaining NaN values
    df_clean = handle_missing_values(df_clean, numeric_strategy="zero")

    # 5. Sort by market cap descending
    if "market_cap" in df_clean.columns:
        df_clean = df_clean.sort_values("market_cap", ascending=False).reset_index(drop=True)

    logger.info(f"Live prices cleaned: {len(df_clean)} rows ready.")
    return df_clean


# ======================================================================
# 7. HIGH-LEVEL CLEANERS — Historical Data
# ======================================================================

def clean_historical_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full cleaning pipeline for a historical-price DataFrame.

    Steps:
        1. Standardise column names
        2. Parse and validate date column
        3. Remove duplicate (coin_id, date) rows
        4. Normalise price/volume columns
        5. Handle missing values (forward-fill for time-series)
        6. Sort chronologically

    Parameters
    ----------
    df : pd.DataFrame
        Raw historical-price DataFrame.

    Returns
    -------
    pd.DataFrame
        Cleaned and chronologically sorted DataFrame.
    """
    if df.empty:
        logger.warning("Empty DataFrame passed to clean_historical_data — returning as-is.")
        return df

    logger.info(f"Cleaning historical data DataFrame ({len(df)} rows)…")

    # 1. Standardise column names
    df_clean = standardize_column_names(df)

    # 2. Parse date column
    if "date" in df_clean.columns:
        df_clean["date"] = pd.to_datetime(df_clean["date"], errors="coerce")
        # Drop rows where date parsing failed entirely
        before = len(df_clean)
        df_clean = df_clean.dropna(subset=["date"])
        dropped = before - len(df_clean)
        if dropped > 0:
            logger.warning(f"Dropped {dropped} rows with unparseable dates.")

    # 3. Remove duplicate (coin_id, date) pairs
    dedup_cols = []
    if "coin_id" in df_clean.columns:
        dedup_cols.append("coin_id")
    if "date" in df_clean.columns:
        dedup_cols.append("date")
    if dedup_cols:
        df_clean = remove_duplicates(df_clean, subset=dedup_cols, keep="last")

    # 4. Normalise price/volume columns
    price_cols = ["open_price", "high_price", "low_price", "close_price", "volume"]
    existing_price = [c for c in price_cols if c in df_clean.columns]
    df_clean = normalize_numeric_cols(df_clean, columns=existing_price)

    # 5. Handle missing values — forward-fill is best for time-series
    df_clean = handle_missing_values(df_clean, numeric_strategy="ffill")

    # 6. Sort chronologically
    sort_cols = []
    if "coin_id" in df_clean.columns:
        sort_cols.append("coin_id")
    if "date" in df_clean.columns:
        sort_cols.append("date")
    if sort_cols:
        df_clean = df_clean.sort_values(sort_cols).reset_index(drop=True)

    logger.info(f"Historical data cleaned: {len(df_clean)} rows ready.")
    return df_clean


# ======================================================================
# STANDALONE TEST
# ======================================================================

if __name__ == "__main__":
    print("Testing Data Cleaning Module…\n")

    # --- Test with dummy live data -----------------------------------------
    raw_live = pd.DataFrame({
        "Id": ["bitcoin", "ethereum", "bitcoin", "solana"],
        "Name": ["Bitcoin", "Ethereum", "Bitcoin", "Solana"],
        "Current Price": [68000.0, 3500.0, 68000.0, None],
        "Market Cap": [1.3e12, 4.2e11, 1.3e12, 6.5e10],
        "Total Volume": [3e10, 1.5e10, 3e10, 4e9],
        "Price Change Percentage 24h": [1.5, -2.3, 1.5, None],
    })

    print("Raw live data:")
    print(raw_live)
    print()

    cleaned = clean_live_prices(raw_live)
    print("Cleaned live data:")
    print(cleaned)
    print()

    # --- Test with dummy historical data -----------------------------------
    raw_hist = pd.DataFrame({
        "coin_id": ["bitcoin"] * 5,
        "date": pd.date_range("2026-05-01", periods=5),
        "close_price": [67000, 67500, None, 68200, 68500],
        "volume": [3e10, 3.1e10, 2.9e10, None, 3.2e10],
    })

    print("Raw historical data:")
    print(raw_hist)
    print()

    cleaned_hist = clean_historical_data(raw_hist)
    print("Cleaned historical data:")
    print(cleaned_hist)
    print()

    # --- Test outlier detection --------------------------------------------
    prices = pd.DataFrame({
        "coin_id": ["a"] * 10,
        "price": [100, 102, 98, 101, 99, 103, 97, 500, 100, 101],
    })
    flagged = detect_outliers(prices, "price")
    print("Outlier detection:")
    print(flagged[["price", "is_outlier"]])
