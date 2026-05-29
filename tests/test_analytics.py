# ============================================================================
# Analytics Tests — Testing KPI, Trend, Volatility, Portfolio & Data Cleaning
# ============================================================================
# These tests verify that all analytics modules produce correct outputs
# from known input data. They run entirely offline using dummy DataFrames
# — no API calls or database connections required.
#
# Run these tests with:
#   pytest tests/test_analytics.py -v
# ============================================================================

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Internal project imports
# ---------------------------------------------------------------------------
from analytics.kpi_calculations import (
    calculate_daily_returns,
    calculate_percentage_growth,
    get_top_gainers_losers,
    calculate_market_dominance,
    generate_kpi_summary,
)
from analytics.trend_analysis import (
    calculate_sma,
    calculate_ema,
    detect_trend_direction,
    calculate_momentum,
    generate_trend_report,
)
from analytics.volatility_analysis import (
    calculate_rolling_volatility,
    calculate_bollinger_bands,
    calculate_atr,
    classify_volatility,
    calculate_risk_metrics,
)
from analytics.portfolio_analysis import (
    create_sample_portfolio,
    calculate_portfolio_value,
    calculate_portfolio_weights,
    calculate_correlation_matrix,
    generate_portfolio_report,
)
from analytics.data_cleaning import (
    standardize_column_names,
    handle_missing_values,
    remove_duplicates,
    normalize_numeric_cols,
    detect_outliers,
    clean_live_prices,
    clean_historical_data,
)


# ============================================================================
# FIXTURES — Reusable test data
# ============================================================================

@pytest.fixture
def live_market_df():
    """Simulated live market snapshot with 4 coins."""
    return pd.DataFrame({
        "id": ["bitcoin", "ethereum", "solana", "cardano"],
        "coin_id": ["bitcoin", "ethereum", "solana", "cardano"],
        "name": ["Bitcoin", "Ethereum", "Solana", "Cardano"],
        "symbol": ["btc", "eth", "sol", "ada"],
        "current_price": [68000.0, 3500.0, 150.0, 0.45],
        "market_cap": [1.3e12, 4.2e11, 6.5e10, 1.5e10],
        "total_volume": [3e10, 1.5e10, 4e9, 1e9],
        "price_change_percentage_24h": [1.5, -2.3, 8.4, -0.5],
        "price_change_24h": [1020.0, -80.5, 12.6, -0.002],
    })


@pytest.fixture
def historical_df():
    """35-day simulated historical price series for a single coin."""
    dates = pd.date_range(start="2026-04-01", periods=35, freq="D")
    np.random.seed(42)
    prices = [100.0]
    for _ in range(34):
        prices.append(prices[-1] * (1 + np.random.normal(0.005, 0.02)))
    return pd.DataFrame({
        "date": dates,
        "coin_id": "bitcoin",
        "close_price": prices,
        "high_price": [p * 1.01 for p in prices],
        "low_price": [p * 0.99 for p in prices],
        "volume": [3e10] * 35,
    })


@pytest.fixture
def multi_coin_historical_df():
    """Historical data for two coins (for correlation tests)."""
    dates = pd.date_range(start="2026-04-01", periods=20, freq="D")
    np.random.seed(42)

    btc_prices = [68000 + np.random.normal(0, 500) for _ in range(20)]
    eth_prices = [3500 + np.random.normal(0, 100) for _ in range(20)]

    df_btc = pd.DataFrame({
        "date": dates, "coin_id": "bitcoin", "close_price": btc_prices
    })
    df_eth = pd.DataFrame({
        "date": dates, "coin_id": "ethereum", "close_price": eth_prices
    })
    return pd.concat([df_btc, df_eth], ignore_index=True)


# ============================================================================
# KPI CALCULATIONS TESTS
# ============================================================================

class TestKPICalculations:
    """Tests for analytics/kpi_calculations.py"""

    def test_calculate_daily_returns_adds_column(self, historical_df):
        result = calculate_daily_returns(historical_df)
        assert "daily_return" in result.columns
        assert len(result) == len(historical_df)

    def test_calculate_daily_returns_first_row_is_zero(self, historical_df):
        result = calculate_daily_returns(historical_df)
        assert result.iloc[0]["daily_return"] == 0.0

    def test_calculate_daily_returns_empty_df(self):
        result = calculate_daily_returns(pd.DataFrame())
        assert result.empty

    def test_calculate_percentage_growth(self, historical_df):
        growth = calculate_percentage_growth(historical_df)
        assert isinstance(growth, dict)
        assert "7d" in growth or "30d" in growth

    def test_calculate_percentage_growth_empty_df(self):
        growth = calculate_percentage_growth(pd.DataFrame())
        assert growth == {"growth_pct": 0.0}

    def test_get_top_gainers_losers(self, live_market_df):
        gainers, losers = get_top_gainers_losers(live_market_df, n=2)
        assert len(gainers) == 2
        assert len(losers) == 2
        # Solana (+8.4%) should be top gainer
        assert gainers.iloc[0]["coin_id"] == "solana"
        # Ethereum (-2.3%) should be top loser
        assert losers.iloc[0]["coin_id"] == "ethereum"

    def test_get_top_gainers_losers_empty_df(self):
        gainers, losers = get_top_gainers_losers(pd.DataFrame())
        assert gainers.empty
        assert losers.empty

    def test_calculate_market_dominance(self, live_market_df):
        result = calculate_market_dominance(live_market_df)
        assert "market_dominance_pct" in result.columns
        # Dominance percentages should sum to ~100%
        assert abs(result["market_dominance_pct"].sum() - 100.0) < 0.01

    def test_generate_kpi_summary(self, live_market_df):
        kpi = generate_kpi_summary(live_market_df)
        assert not kpi.empty
        assert "total_market_cap" in kpi.columns
        assert "total_volume" in kpi.columns
        assert "top_gainer_coin" in kpi.columns

    def test_generate_kpi_summary_empty(self):
        kpi = generate_kpi_summary(pd.DataFrame())
        assert kpi.empty


# ============================================================================
# TREND ANALYSIS TESTS
# ============================================================================

class TestTrendAnalysis:
    """Tests for analytics/trend_analysis.py"""

    def test_calculate_sma_adds_columns(self, historical_df):
        result = calculate_sma(historical_df, windows=[7, 14])
        assert "sma_7" in result.columns
        assert "sma_14" in result.columns

    def test_calculate_sma_values_are_valid(self, historical_df):
        result = calculate_sma(historical_df, windows=[7])
        # First 6 rows should be NaN for a 7-window SMA
        assert pd.isna(result.iloc[0]["sma_7"])
        # Row 7+ should have a valid value
        assert not pd.isna(result.iloc[6]["sma_7"])

    def test_calculate_ema_adds_columns(self, historical_df):
        result = calculate_ema(historical_df, spans=[7, 14])
        assert "ema_7" in result.columns
        assert "ema_14" in result.columns

    def test_detect_trend_direction(self, historical_df):
        result = detect_trend_direction(historical_df, window=7)
        assert "trend_direction" in result.columns
        valid_trends = {"Bullish", "Bearish", "Neutral"}
        actual_trends = set(result["trend_direction"].unique())
        assert actual_trends.issubset(valid_trends)

    def test_calculate_momentum(self, historical_df):
        result = calculate_momentum(historical_df, period=7)
        assert "momentum_roc" in result.columns
        assert len(result) == len(historical_df)

    def test_generate_trend_report(self, historical_df):
        report = generate_trend_report(historical_df, "bitcoin")
        assert not report.empty
        expected_cols = ["sma_7", "ema_7", "trend_direction", "momentum_roc"]
        for col in expected_cols:
            assert col in report.columns

    def test_generate_trend_report_empty(self):
        report = generate_trend_report(pd.DataFrame(), "bitcoin")
        assert report.empty


# ============================================================================
# VOLATILITY ANALYSIS TESTS
# ============================================================================

class TestVolatilityAnalysis:
    """Tests for analytics/volatility_analysis.py"""

    def test_calculate_rolling_volatility(self, historical_df):
        result = calculate_rolling_volatility(historical_df, window=7)
        assert "rolling_volatility" in result.columns
        # All values should be non-negative
        assert (result["rolling_volatility"] >= 0).all()

    def test_calculate_bollinger_bands(self, historical_df):
        result = calculate_bollinger_bands(historical_df, window=10)
        assert "bb_middle" in result.columns
        assert "bb_upper" in result.columns
        assert "bb_lower" in result.columns
        # Upper band should always be >= middle >= lower
        valid_rows = result.dropna(subset=["bb_upper", "bb_lower"])
        if not valid_rows.empty:
            assert (valid_rows["bb_upper"] >= valid_rows["bb_lower"]).all()

    def test_calculate_atr(self, historical_df):
        result = calculate_atr(historical_df, period=7)
        assert "atr" in result.columns
        assert (result["atr"] >= 0).all()

    def test_classify_volatility(self, historical_df):
        vol_df = calculate_rolling_volatility(historical_df, window=7)
        result = classify_volatility(vol_df)
        assert "volatility_class" in result.columns
        valid_classes = {"Low", "Medium", "High"}
        actual_classes = set(result["volatility_class"].unique())
        assert actual_classes.issubset(valid_classes)

    def test_calculate_risk_metrics(self, historical_df):
        result = calculate_risk_metrics(historical_df)
        assert not result.empty
        assert "annualized_volatility_pct" in result.columns
        assert "max_drawdown_pct" in result.columns
        assert "coin_id" in result.columns

    def test_calculate_risk_metrics_empty(self):
        result = calculate_risk_metrics(pd.DataFrame())
        assert result.empty


# ============================================================================
# PORTFOLIO ANALYSIS TESTS
# ============================================================================

class TestPortfolioAnalysis:
    """Tests for analytics/portfolio_analysis.py"""

    def test_create_sample_portfolio(self):
        portfolio = create_sample_portfolio()
        assert not portfolio.empty
        assert "coin_id" in portfolio.columns
        assert "quantity" in portfolio.columns
        assert "buy_price" in portfolio.columns
        assert len(portfolio) == 4  # 4 sample coins

    def test_calculate_portfolio_value(self, live_market_df):
        portfolio = create_sample_portfolio()
        result = calculate_portfolio_value(portfolio, live_market_df)
        assert "current_value" in result.columns
        assert "net_profit" in result.columns
        assert "roi_pct" in result.columns
        # Current value should be positive for all holdings
        assert (result["current_value"] > 0).all()

    def test_calculate_portfolio_weights(self, live_market_df):
        portfolio = create_sample_portfolio()
        valued = calculate_portfolio_value(portfolio, live_market_df)
        result = calculate_portfolio_weights(valued)
        assert "weight_pct" in result.columns
        # Weights should sum to ~100%
        assert abs(result["weight_pct"].sum() - 100.0) < 0.01

    def test_calculate_correlation_matrix(self, multi_coin_historical_df):
        corr = calculate_correlation_matrix(multi_coin_historical_df)
        assert not corr.empty
        # Diagonal should be 1.0 (self-correlation)
        for coin in corr.columns:
            assert abs(corr.loc[coin, coin] - 1.0) < 0.001

    def test_generate_portfolio_report(self, live_market_df):
        portfolio = create_sample_portfolio()
        report = generate_portfolio_report(portfolio, live_market_df)
        assert not report.empty
        # Should contain a TOTAL summary row
        total_rows = report[report["coin_id"] == "TOTAL"]
        assert len(total_rows) == 1

    def test_generate_portfolio_report_empty(self, live_market_df):
        report = generate_portfolio_report(pd.DataFrame(), live_market_df)
        assert report.empty


# ============================================================================
# DATA CLEANING TESTS
# ============================================================================

class TestDataCleaning:
    """Tests for analytics/data_cleaning.py"""

    def test_standardize_column_names(self):
        df = pd.DataFrame({"First Name": [1], "Last-Name": [2], "  Age  ": [3]})
        result = standardize_column_names(df)
        assert list(result.columns) == ["first_name", "last_name", "age"]

    def test_handle_missing_values_zero(self):
        df = pd.DataFrame({"a": [1.0, None, 3.0], "b": ["x", None, "z"]})
        result = handle_missing_values(df, numeric_strategy="zero")
        assert result["a"].iloc[1] == 0.0
        assert result["b"].iloc[1] == "unknown"

    def test_handle_missing_values_mean(self):
        df = pd.DataFrame({"a": [10.0, None, 30.0]})
        result = handle_missing_values(df, numeric_strategy="mean")
        assert result["a"].iloc[1] == 20.0  # mean of 10 and 30

    def test_remove_duplicates(self):
        df = pd.DataFrame({"id": [1, 2, 2, 3], "val": ["a", "b", "b", "c"]})
        result = remove_duplicates(df)
        assert len(result) == 3

    def test_remove_duplicates_subset(self):
        df = pd.DataFrame({
            "coin_id": ["btc", "eth", "btc"],
            "date": ["2026-01-01", "2026-01-01", "2026-01-01"],
            "price": [100, 200, 105],
        })
        result = remove_duplicates(df, subset=["coin_id", "date"], keep="last")
        assert len(result) == 2
        # Should keep the last BTC row (price=105)
        btc_row = result[result["coin_id"] == "btc"]
        assert btc_row.iloc[0]["price"] == 105

    def test_normalize_numeric_cols(self):
        df = pd.DataFrame({"price": ["100.5", "invalid", "300.0"]})
        result = normalize_numeric_cols(df, columns=["price"])
        assert result["price"].iloc[0] == 100.5
        assert result["price"].iloc[1] == 0.0  # invalid → 0.0
        assert result["price"].iloc[2] == 300.0

    def test_detect_outliers(self):
        df = pd.DataFrame({"price": [100, 102, 98, 101, 99, 500]})
        result = detect_outliers(df, "price")
        assert "is_outlier" in result.columns
        # 500 should be flagged as outlier
        assert bool(result.iloc[-1]["is_outlier"]) is True
        # Normal values should not be flagged
        assert bool(result.iloc[0]["is_outlier"]) is False

    def test_clean_live_prices(self):
        raw = pd.DataFrame({
            "Id": ["bitcoin", "ethereum", "bitcoin"],
            "Name": ["Bitcoin", "Ethereum", "Bitcoin"],
            "Current Price": [68000.0, 3500.0, 68000.0],
            "Market Cap": [1.3e12, 4.2e11, 1.3e12],
        })
        result = clean_live_prices(raw)
        # Should remove the duplicate Bitcoin row
        assert len(result) == 2
        # Column names should be standardised
        assert "current_price" in result.columns

    def test_clean_historical_data(self):
        raw = pd.DataFrame({
            "coin_id": ["bitcoin"] * 3,
            "date": ["2026-05-01", "2026-05-02", "2026-05-01"],
            "close_price": [67000, 67500, 67100],
        })
        result = clean_historical_data(raw)
        # Should remove the duplicate (bitcoin, 2026-05-01) row
        assert len(result) == 2
        # Should be sorted by date
        assert result.iloc[0]["date"] <= result.iloc[1]["date"]

    def test_clean_empty_dataframes(self):
        assert clean_live_prices(pd.DataFrame()).empty
        assert clean_historical_data(pd.DataFrame()).empty


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases across all analytics modules."""

    def test_single_row_dataframe(self):
        """Analytics should handle single-row DataFrames gracefully."""
        single = pd.DataFrame({
            "date": [datetime(2026, 5, 1)],
            "coin_id": ["bitcoin"],
            "close_price": [68000.0],
        })
        # These should not raise exceptions
        sma = calculate_sma(single, windows=[7])
        assert len(sma) == 1

        ema = calculate_ema(single, spans=[7])
        assert len(ema) == 1

    def test_all_nan_column(self):
        """Missing-value handling should work when entire column is NaN."""
        # Use np.nan instead of None so the column is inferred as float dtype
        df = pd.DataFrame({"a": [np.nan, np.nan, np.nan], "b": [1.0, 2.0, 3.0]})
        result = handle_missing_values(df, numeric_strategy="zero")
        assert (result["a"] == 0.0).all()

    def test_negative_prices(self):
        """Analytics should handle negative prices without crashing."""
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=5),
            "coin_id": "test",
            "close_price": [-10, -5, 0, 5, 10],
        })
        result = calculate_sma(df, windows=[3])
        assert not result.empty
