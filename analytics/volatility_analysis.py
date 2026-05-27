"""
volatility_analysis.py — Volatility and Risk Metrics
====================================================

Calculates historical price volatility, Bollinger Bands, ATR (Average True Range),
and overall portfolio risk metrics (max drawdown, annualised risk, standard
deviation of daily returns) for reporting and downstream visualization.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional

from config.config import Config
from utils.logger import get_logger
from utils.helper_functions import export_to_csv, safe_float

logger = get_logger(__name__)


def calculate_rolling_volatility(
    df: pd.DataFrame,
    price_column: str = "close_price",
    window: int = 14
) -> pd.DataFrame:
    """
    Calculate the rolling standard deviation of daily returns as a volatility proxy.
    """
    if df.empty or price_column not in df.columns:
        return df

    df_copy = df.copy()

    # Chronological sort check
    if "date" in df_copy.columns:
        df_copy = df_copy.sort_values(by="date")

    # Ensure daily return is calculated
    def compute_vol(series):
        returns = series.pct_change().fillna(0.0)
        return returns.rolling(window=window).std()

    if "coin_id" in df_copy.columns:
        df_copy["rolling_volatility"] = df_copy.groupby("coin_id")[price_column].transform(compute_vol)
    else:
        df_copy["rolling_volatility"] = compute_vol(df_copy[price_column])

    # Fill NaN values with 0.0
    df_copy["rolling_volatility"] = df_copy["rolling_volatility"].fillna(0.0)

    return df_copy


def calculate_bollinger_bands(
    df: pd.DataFrame,
    price_column: str = "close_price",
    window: int = 20,
    num_std: int = 2
) -> pd.DataFrame:
    """
    Calculate standard Bollinger Bands (Middle Band, Upper Band, Lower Band).
    """
    if df.empty or price_column not in df.columns:
        return df

    df_copy = df.copy()

    # Chronological sort check
    if "date" in df_copy.columns:
        df_copy = df_copy.sort_values(by="date")

    def get_bb_middle(s):
        return s.rolling(window=window).mean()

    def get_bb_std(s):
        return s.rolling(window=window).std()

    if "coin_id" in df_copy.columns:
        df_copy["bb_middle"] = df_copy.groupby("coin_id")[price_column].transform(get_bb_middle)
        df_copy["bb_std"] = df_copy.groupby("coin_id")[price_column].transform(get_bb_std)
    else:
        df_copy["bb_middle"] = get_bb_middle(df_copy[price_column])
        df_copy["bb_std"] = get_bb_std(df_copy[price_column])

    # Calculate Bands
    df_copy["bb_upper"] = df_copy["bb_middle"] + (num_std * df_copy["bb_std"])
    df_copy["bb_lower"] = df_copy["bb_middle"] - (num_std * df_copy["bb_std"])

    # Drop temporary std column
    df_copy = df_copy.drop(columns=["bb_std"])

    # Fill NaNs
    df_copy["bb_middle"] = df_copy["bb_middle"].fillna(df_copy[price_column])
    df_copy["bb_upper"] = df_copy["bb_upper"].fillna(df_copy[price_column])
    df_copy["bb_lower"] = df_copy["bb_lower"].fillna(df_copy[price_column])

    return df_copy


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Average True Range (ATR).
    If high_price and low_price columns are missing, we approximate using close price.
    """
    if df.empty:
        return df

    df_copy = df.copy()
    
    # Check if high and low prices are available, if not, use close price as proxy
    high_col = "high_price" if "high_price" in df_copy.columns else "close_price"
    low_col = "low_price" if "low_price" in df_copy.columns else "close_price"
    close_col = "close_price" if "close_price" in df_copy.columns else df_copy.columns[0]

    # Calculate True Range (TR)
    def compute_tr(group):
        high = group[high_col]
        low = group[low_col]
        close = group[close_col]
        
        # Prevent division/empty array errors
        if len(group) < 2:
            return pd.Series(0.0, index=group.index)

        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        # Maximum of the three ranges
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr

    if "coin_id" in df_copy.columns:
        df_copy["true_range"] = df_copy.groupby("coin_id", group_keys=False).apply(compute_tr)
        df_copy["atr"] = df_copy.groupby("coin_id")["true_range"].transform(lambda x: x.rolling(window=period).mean())
        df_copy = df_copy.drop(columns=["true_range"])
    else:
        tr = compute_tr(df_copy)
        df_copy["atr"] = tr.rolling(window=period).mean()

    df_copy["atr"] = df_copy["atr"].fillna(0.0)
    return df_copy


def classify_volatility(df: pd.DataFrame, volatility_col: str = "rolling_volatility") -> pd.DataFrame:
    """
    Classify volatility levels as Low, Medium, or High using standard quantile thresholds.
    """
    if df.empty or volatility_col not in df.columns:
        return df

    df_copy = df.copy()
    vol_series = df_copy[volatility_col]

    # Handle case where all values are identical or zero
    if vol_series.nunique() <= 1:
        df_copy["volatility_class"] = "Medium"
        return df_copy

    low_threshold = vol_series.quantile(0.33)
    high_threshold = vol_series.quantile(0.66)

    def label_vol(val):
        if np.isnan(val) or val == 0.0:
            return "Low"
        elif val <= low_threshold:
            return "Low"
        elif val <= high_threshold:
            return "Medium"
        else:
            return "High"

    df_copy["volatility_class"] = df_copy[volatility_col].apply(label_vol)
    return df_copy


def calculate_risk_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combines volatility analysis and aggregates standard risk metrics per coin:
    - Annualised Volatility (std of returns * sqrt(365))
    - Maximum Drawdown
    - Standard Deviation of daily returns

    Perfect to export for Power BI reporting.
    """
    if df.empty:
        logger.warning("Empty data passed to calculate_risk_metrics — returning empty DF.")
        return pd.DataFrame()

    logger.info("Aggregating portfolio risk metrics...")
    
    # 1. Ensure sorted order
    df_sorted = df.copy()
    if "date" in df_sorted.columns:
        df_sorted = df_sorted.sort_values(by="date")

    price_col = "close_price" if "close_price" in df_sorted.columns else "price"

    # Aggregating per coin
    risk_records = []
    
    # Group by coin or process globally
    groups = df_sorted.groupby("coin_id") if "coin_id" in df_sorted.columns else [("general", df_sorted)]
    
    for coin_id, group in groups:
        if len(group) < 2:
            continue
            
        prices = group[price_col].values
        returns = group[price_col].pct_change().dropna().values

        # Annualised Volatility (Standard Deviation of daily return * sqrt(365) since crypto trades 24/7)
        daily_std = np.std(returns) if len(returns) > 0 else 0.0
        annual_vol = daily_std * np.sqrt(365) * 100.0  # Percentage

        # Maximum Drawdown calculation
        # Peak values
        peaks = np.maximum.accumulate(prices)
        drawdowns = (prices - peaks) / peaks
        max_drawdown = np.min(drawdowns) * 100.0 if len(drawdowns) > 0 else 0.0 # Percentage

        risk_records.append({
            "coin_id": coin_id,
            "daily_return_std": daily_std,
            "annualized_volatility_pct": annual_vol,
            "max_drawdown_pct": max_drawdown,
            "current_price": safe_float(prices[-1]),
            "risk_date": pd.Timestamp.now().strftime("%Y-%m-%d")
        })

    risk_df = pd.DataFrame(risk_records)
    return risk_df


def generate_volatility_report(df: pd.DataFrame, coin_id: Optional[str] = None) -> pd.DataFrame:
    """
    Generates a continuous volatility report (rolling statistics, Bollinger Bands,
    and ATR) for specific charts or details.
    """
    if df.empty:
        return pd.DataFrame()

    df_vol = calculate_rolling_volatility(df)
    df_vol = calculate_bollinger_bands(df_vol)
    df_vol = calculate_atr(df_vol)
    df_vol = classify_volatility(df_vol)

    if coin_id and "coin_id" not in df_vol.columns:
        df_vol["coin_id"] = coin_id

    return df_vol


def export_volatility_report(risk_df: pd.DataFrame) -> Path:
    """
    Exports a calculated risk/volatility summary DataFrame to the Exports directory.
    """
    filename = "volatility_report.csv"
    logger.info("Saving aggregated volatility report...")
    return export_to_csv(risk_df, filename)


if __name__ == "__main__":
    print("Testing Volatility Analysis with dummy series...")
    dates = pd.date_range(start="2026-04-01", periods=40, freq="D")
    
    # Simulate a highly volatile asset
    prices = [100.0]
    for _ in range(39):
        change = np.random.normal(0, 0.05) # 5% daily standard dev
        prices.append(prices[-1] * (1.0 + change))

    dummy_historical = pd.DataFrame({
        "date": dates,
        "coin_id": "ethereum",
        "close_price": prices,
        "high_price": [p * 1.02 for p in prices],
        "low_price": [p * 0.98 for p in prices]
    })

    # Continuous variables
    continuous_report = generate_volatility_report(dummy_historical, "ethereum")
    print("\nProcessed indicators (Last 3 days):")
    print(continuous_report[["date", "rolling_volatility", "bb_upper", "bb_lower", "atr", "volatility_class"]].tail(3))

    # Aggregated Summary
    aggregated_metrics = calculate_risk_metrics(dummy_historical)
    print("\nAggregated Risk Metrics:")
    print(aggregated_metrics)
