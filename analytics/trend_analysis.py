"""
trend_analysis.py — Trend Analysis and Moving Averages
======================================================

Provides SMA (Simple Moving Average), EMA (Exponential Moving Average),
Rate of Change (momentum) calculations, and trend detection classifiers
(Bullish/Bearish/Neutral) for historical price series.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Optional

from config.config import Config
from utils.logger import get_logger
from utils.helper_functions import export_to_csv, safe_float

logger = get_logger(__name__)


def calculate_sma(df: pd.DataFrame, price_column: str = "close_price", windows: Optional[List[int]] = None) -> pd.DataFrame:
    """
    Calculate Simple Moving Averages (SMA) for specified windows.
    """
    if df.empty or price_column not in df.columns:
        return df

    if windows is None:
        windows = [7, 14, 30]

    df_copy = df.copy()

    # Chronological sort check
    if "date" in df_copy.columns:
        df_copy = df_copy.sort_values(by="date")

    for w in windows:
        if "coin_id" in df_copy.columns:
            # Group by coin to prevent cross-contamination
            df_copy[f"sma_{w}"] = df_copy.groupby("coin_id")[price_column].transform(lambda x: x.rolling(window=w).mean())
        else:
            df_copy[f"sma_{w}"] = df_copy[price_column].rolling(window=w).mean()

    return df_copy


def calculate_ema(df: pd.DataFrame, price_column: str = "close_price", spans: Optional[List[int]] = None) -> pd.DataFrame:
    """
    Calculate Exponential Moving Averages (EMA) for specified spans.
    """
    if df.empty or price_column not in df.columns:
        return df

    if spans is None:
        spans = [7, 14, 30]

    df_copy = df.copy()

    # Chronological sort check
    if "date" in df_copy.columns:
        df_copy = df_copy.sort_values(by="date")

    for s in spans:
        if "coin_id" in df_copy.columns:
            # Group by coin to prevent cross-contamination
            df_copy[f"ema_{s}"] = df_copy.groupby("coin_id")[price_column].transform(lambda x: x.ewm(span=s, adjust=False).mean())
        else:
            df_copy[f"ema_{s}"] = df_copy[price_column].ewm(span=s, adjust=False).mean()

    return df_copy


def detect_trend_direction(df: pd.DataFrame, price_column: str = "close_price", window: int = 14) -> pd.DataFrame:
    """
    Detects trend direction (Bullish, Bearish, or Neutral) based on current price position
    relative to the Simple Moving Average.
    """
    sma_col = f"sma_{window}"
    
    # Ensure SMA is calculated first
    df_copy = calculate_sma(df, price_column=price_column, windows=[window])
    
    if df_copy.empty or sma_col not in df_copy.columns:
        return df_copy

    def classify_trend(row):
        price = safe_float(row[price_column])
        sma_val = safe_float(row[sma_col])
        
        if np.isnan(sma_val) or sma_val == 0.0:
            return "Neutral"
            
        threshold = 0.015  # 1.5% buffer for neutral channel
        ratio = price / sma_val
        
        if ratio > (1.0 + threshold):
            return "Bullish"
        elif ratio < (1.0 - threshold):
            return "Bearish"
        else:
            return "Neutral"

    df_copy["trend_direction"] = df_copy.apply(classify_trend, axis=1)
    return df_copy


def calculate_momentum(df: pd.DataFrame, price_column: str = "close_price", period: int = 14) -> pd.DataFrame:
    """
    Calculate momentum as the Rate of Change (ROC):
    ROC = ((Current Close - Close N periods ago) / Close N periods ago) * 100
    """
    if df.empty or price_column not in df.columns:
        return df

    df_copy = df.copy()

    # Chronological sort check
    if "date" in df_copy.columns:
        df_copy = df_copy.sort_values(by="date")

    def get_roc(series):
        # Shift values by N periods to calculate past price
        past_price = series.shift(period)
        return ((series - past_price) / past_price) * 100.0

    if "coin_id" in df_copy.columns:
        df_copy["momentum_roc"] = df_copy.groupby("coin_id")[price_column].transform(get_roc)
    else:
        df_copy["momentum_roc"] = get_roc(df_copy[price_column])

    # Fill NaN momentum values with 0.0
    df_copy["momentum_roc"] = df_copy["momentum_roc"].fillna(0.0)

    return df_copy


def generate_trend_report(df: pd.DataFrame, coin_id: Optional[str] = None) -> pd.DataFrame:
    """
    Generates a full trend analysis report containing SMA, EMA, trend classification,
    and momentum indicators for downstream reports.
    """
    if df.empty:
        logger.warning(f"Empty data received for trend analysis (coin_id: {coin_id})")
        return pd.DataFrame()

    logger.info(f"Generating trend report for {coin_id or 'all coins'}...")
    
    # 1. Calculate moving averages
    df_trends = calculate_sma(df, windows=[7, 14, 30])
    df_trends = calculate_ema(df_trends, spans=[7, 14, 30])
    
    # 2. Detect trend direction (using 14-day window as industry standard)
    df_trends = detect_trend_direction(df_trends, window=14)
    
    # 3. Calculate Rate of Change Momentum
    df_trends = calculate_momentum(df_trends, period=14)
    
    # If a specific coin ID was passed but doesn't exist inside the DataFrame, assign it
    if coin_id and "coin_id" not in df_trends.columns:
        df_trends["coin_id"] = coin_id

    # Format dates correctly as strings
    if "date" in df_trends.columns:
        df_trends["date"] = pd.to_datetime(df_trends["date"]).dt.strftime("%Y-%m-%d")

    return df_trends


def export_trend_report(trend_df: pd.DataFrame) -> Path:
    """
    Exports a trend analysis DataFrame to the Exports directory.
    Uses the coin_id present in the DataFrame to name the file dynamically.
    """
    coin_id = "general"
    if not trend_df.empty and "coin_id" in trend_df.columns:
        coin_id = str(trend_df["coin_id"].iloc[0]).lower()

    filename = f"trend_{coin_id}.csv"
    logger.info(f"Exporting trend analysis report for '{coin_id}'...")
    return export_to_csv(trend_df, filename)


if __name__ == "__main__":
    print("Testing Trend Analysis with mock historical series...")
    dates = pd.date_range(start="2026-04-01", periods=35, freq="D")
    
    # Simulate a nice trending upward series with some noise
    prices = [100.0 + i*1.5 + np.random.normal(0, 2) for i in range(35)]
    
    dummy_historical = pd.DataFrame({
        "date": dates,
        "coin_id": "bitcoin",
        "close_price": prices
    })

    print("\nSimulated Price Series (Last 5 days):")
    print(dummy_historical.tail())

    # Generate full report
    report = generate_trend_report(dummy_historical, "bitcoin")
    
    print("\nProcessed Trend Metrics (Last 5 records):")
    cols = ["date", "close_price", "sma_7", "ema_7", "trend_direction", "momentum_roc"]
    print(report[cols].tail())
