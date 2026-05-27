"""
portfolio_analysis.py — Portfolio Performance Evaluation
========================================================

Computes holding valuations, Return on Investment (ROI), portfolio diversification
weights, correlation matrices of assets, and exports reporting files suitable
for ingestion into Power BI.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any

from config.config import Config
from utils.logger import get_logger
from utils.helper_functions import export_to_csv, safe_float

logger = get_logger(__name__)


def create_sample_portfolio() -> pd.DataFrame:
    """
    Creates and returns a sample portfolio DataFrame with realistic initial
    investment parameters. Useful for testing pipelines and demonstrating
    dashboard functionality out of the box.

    Returns
    -------
    pd.DataFrame
        Columns: coin_id, symbol, coin_name, quantity, buy_price, buy_date, notes
    """
    sample_data = {
        "coin_id": ["bitcoin", "ethereum", "solana", "cardano"],
        "symbol": ["BTC", "ETH", "SOL", "ADA"],
        "coin_name": ["Bitcoin", "Ethereum", "Solana", "Cardano"],
        "quantity": [0.45, 3.2, 25.0, 1500.0],
        "buy_price": [45000.0, 2200.0, 85.0, 0.45],
        "buy_date": ["2025-06-15", "2025-08-20", "2025-11-10", "2025-12-05"],
        "notes": [
            "Accumulated at local support level",
            "Long-term staking allocation",
            "DCA entry during consolidation",
            "Staking node deposit"
        ]
    }
    df = pd.DataFrame(sample_data)
    df["buy_date"] = pd.to_datetime(df["buy_date"]).dt.date
    logger.info("Sample portfolio generated.")
    return df


def calculate_portfolio_value(portfolio_df: pd.DataFrame, current_prices_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merges portfolio holdings with current market price data and evaluates valuations.

    Parameters
    ----------
    portfolio_df : pd.DataFrame
        Holdings DataFrame.
    current_prices_df : pd.DataFrame
        Live price snapshot DataFrame.

    Returns
    -------
    pd.DataFrame
        Enriched DataFrame with calculated financial parameters per asset.
    """
    if portfolio_df.empty:
        return portfolio_df

    # Extract price column and coin_id for easy merging
    # CoinGecko live fetch puts coin_id in 'id' column or 'coin_id'
    price_df = current_prices_df.copy()
    if "id" in price_df.columns and "coin_id" not in price_df.columns:
        price_df["coin_id"] = price_df["id"]

    price_cols = ["coin_id", "current_price"]
    available_cols = [c for c in price_cols if c in price_df.columns]
    
    price_sub = price_df[available_cols]

    # Merge holdings with live prices
    merged = pd.merge(portfolio_df, price_sub, on="coin_id", how="left")

    # In case live price is not fetched, fallback to buy price to avoid NaNs
    merged["current_price"] = merged["current_price"].fillna(merged["buy_price"])

    # Calculate financial valuation fields
    merged["quantity"] = merged["quantity"].apply(safe_float)
    merged["buy_price"] = merged["buy_price"].apply(safe_float)
    merged["current_price"] = merged["current_price"].apply(safe_float)

    merged["total_cost"] = merged["quantity"] * merged["buy_price"]
    merged["current_value"] = merged["quantity"] * merged["current_price"]
    merged["net_profit"] = merged["current_value"] - merged["total_cost"]

    # ROI Calculation: ((Current - Buy) / Buy) * 100
    def calculate_roi(row):
        cost = safe_float(row["total_cost"])
        profit = safe_float(row["net_profit"])
        if cost == 0.0:
            return 0.0
        return (profit / cost) * 100.0

    merged["roi_pct"] = merged.apply(calculate_roi, axis=1)

    return merged


def calculate_portfolio_weights(portfolio_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the diversification weight of each asset relative to the total portfolio value.
    """
    if portfolio_df.empty or "current_value" not in portfolio_df.columns:
        return portfolio_df

    df_copy = portfolio_df.copy()
    total_val = df_copy["current_value"].sum()

    if total_val > 0:
        df_copy["weight_pct"] = (df_copy["current_value"] / total_val) * 100.0
    else:
        df_copy["weight_pct"] = 0.0

    return df_copy


def calculate_correlation_matrix(historical_df: pd.DataFrame, price_column: str = "close_price") -> pd.DataFrame:
    """
    Calculates the asset correlation matrix based on daily returns from historical series.

    Parameters
    ----------
    historical_df : pd.DataFrame
        Historical price records containing multiple assets.
    price_column : str
        Column representing historical pricing.

    Returns
    -------
    pd.DataFrame
        Correlation matrix DataFrame.
    """
    if historical_df.empty or len(historical_df) < 5:
        return pd.DataFrame()

    try:
        # Pivot the data to have date as index, coin_id as columns, and prices as values
        pivot_df = historical_df.pivot(index="date", columns="coin_id", values=price_column)
        
        # Calculate daily percentage returns per coin
        returns_df = pivot_df.pct_change().dropna(how="all")
        
        # Calculate standard Pearson correlation matrix
        correlation_matrix = returns_df.corr()
        logger.info("Asset correlation matrix calculated successfully.")
        return correlation_matrix

    except Exception as e:
        logger.error(f"Error calculating asset correlation matrix: {e}")
        return pd.DataFrame()


def generate_portfolio_report(
    portfolio_df: pd.DataFrame,
    current_prices_df: pd.DataFrame,
    historical_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Orchestrates the entire portfolio performance pipeline:
    Calculates values, ROIs, weights, adds total summary row, and prepares
    the final report sheet.

    Parameters
    ----------
    portfolio_df : pd.DataFrame
        User holdings DataFrame.
    current_prices_df : pd.DataFrame
        Live price DataFrame.
    historical_df : pd.DataFrame, optional
        Historical prices (optional, not currently aggregated in main file sheet).

    Returns
    -------
    pd.DataFrame
        Fully valued and formatted portfolio performance DataFrame.
    """
    if portfolio_df.empty:
        logger.warning("Empty portfolio received — returning empty report.")
        return pd.DataFrame()

    logger.info("Generating comprehensive portfolio valuation report...")

    # 1. Calculate values
    valued_df = calculate_portfolio_value(portfolio_df, current_prices_df)

    # 2. Calculate weights
    valued_df = calculate_portfolio_weights(valued_df)

    # 3. Add a summary 'TOTAL' row at the bottom for easy dashboard verification
    total_cost = valued_df["total_cost"].sum()
    total_value = valued_df["current_value"].sum()
    total_profit = valued_df["net_profit"].sum()
    total_roi = ((total_value - total_cost) / total_cost * 100.0) if total_cost > 0 else 0.0

    summary_row = {
        "coin_id": "TOTAL",
        "symbol": "ALL",
        "coin_name": "Total Portfolio",
        "quantity": 0.0,
        "buy_price": 0.0,
        "current_price": 0.0,
        "total_cost": total_cost,
        "current_value": total_value,
        "net_profit": total_profit,
        "roi_pct": total_roi,
        "weight_pct": 100.0,
        "notes": "Summarized portfolio parameters"
    }

    # Append summary row
    report_df = pd.concat([valued_df, pd.DataFrame([summary_row])], ignore_index=True)
    
    # Standardize columns ordering
    cols_order = [
        "coin_id", "symbol", "coin_name", "quantity", "buy_price", "current_price",
        "total_cost", "current_value", "net_profit", "roi_pct", "weight_pct", "notes"
    ]
    report_df = report_df[[c for c in cols_order if c in report_df.columns]]

    return report_df


def export_portfolio_report(portfolio_report_df: pd.DataFrame) -> Path:
    """
    Saves the calculated portfolio performance metrics to the exports directory.
    """
    filename = "portfolio_report.csv"
    logger.info("Exporting portfolio performance report...")
    return export_to_csv(portfolio_report_df, filename)


if __name__ == "__main__":
    print("Testing Portfolio Evaluation pipeline...")
    
    # 1. Create sample holdings
    holdings = create_sample_portfolio()
    
    # 2. Mock current prices
    prices = pd.DataFrame({
        "id": ["bitcoin", "ethereum", "solana", "cardano"],
        "current_price": [67200.00, 3480.00, 142.50, 0.48]
    })

    # 3. Generate report
    report = generate_portfolio_report(holdings, prices)
    print("\nCalculated Portfolio Report (Including Summary Row):")
    print(report.to_string(index=False))
