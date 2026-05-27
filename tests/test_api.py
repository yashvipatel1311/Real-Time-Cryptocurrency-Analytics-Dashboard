# ============================================================================
# API Tests — Testing CoinGecko API Integration
# ============================================================================
# These tests verify that our API modules can successfully connect to
# CoinGecko, fetch cryptocurrency data, and return properly structured
# DataFrames.
#
# Some tests require network access and will be automatically skipped
# if the CoinGecko API is not reachable (e.g., in CI without internet).
#
# Run these tests with:
#   pytest tests/test_api.py -v
#
# Run only tests that don't need network:
#   pytest tests/test_api.py -v -m "not network"
# ============================================================================

import pytest
import requests
import pandas as pd

# ---------------------------------------------------------------------------
# Internal project imports
# ---------------------------------------------------------------------------
from api.fetch_crypto_data import fetch_live_prices, fetch_and_store_live_prices
from api.fetch_historical_data import fetch_and_store_historical
from config.config import Config


# ============================================================================
# HELPER: Check if CoinGecko API is reachable
# ============================================================================
def is_api_reachable():
    """
    Quick check to see if the CoinGecko API is reachable.
    Returns True if we get a successful response from /ping, False otherwise.

    This is used by @pytest.mark.skipif to skip network-dependent tests
    when running offline or in restricted environments.
    """
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/ping",
            timeout=10  # 10-second timeout to avoid hanging
        )
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False


# ---------------------------------------------------------------------------
# Flag: set once at module load time to avoid repeated network checks
# ---------------------------------------------------------------------------
API_AVAILABLE = is_api_reachable()

# Custom marker for tests that need network access
network_required = pytest.mark.skipif(
    not API_AVAILABLE,
    reason="CoinGecko API is not reachable — skipping network-dependent test"
)


# ============================================================================
# TEST 1: CoinGecko API Connectivity
# ============================================================================
@network_required
def test_coingecko_connection():
    """
    Test that the CoinGecko API is reachable and responds to a /ping request.

    The /ping endpoint is CoinGecko's health check endpoint. A successful
    response confirms that:
      - We have internet connectivity
      - CoinGecko's servers are up
      - We're not being rate-limited

    Expected response: {"gecko_says": "(V3) To the Moon!"}
    """
    # Send a GET request to the CoinGecko ping endpoint
    response = requests.get(
        "https://api.coingecko.com/api/v3/ping",
        timeout=10
    )

    # Assert we get a 200 OK status code
    assert response.status_code == 200, (
        f"Expected status 200, got {response.status_code}"
    )

    # Assert the response contains the expected JSON key
    data = response.json()
    assert "gecko_says" in data, (
        f"Expected 'gecko_says' key in response, got: {data}"
    )


# ============================================================================
# TEST 2: Fetch Live Prices Returns Valid DataFrame
# ============================================================================
@network_required
def test_fetch_live_prices():
    """
    Test that fetch_live_prices() returns a valid pandas DataFrame
    with at least one row of data.

    This verifies our data fetching and parsing logic works correctly
    end-to-end, from API call to DataFrame construction.
    """
    # Call our API function
    df = fetch_live_prices()

    # Verify the result is a DataFrame
    assert isinstance(df, pd.DataFrame), (
        f"Expected pandas DataFrame, got {type(df)}"
    )

    # Verify we got at least one row of data
    assert len(df) > 0, (
        "DataFrame is empty — expected at least one row of price data"
    )


# ============================================================================
# TEST 3: Validate Required Columns in Live Prices
# ============================================================================
@network_required
def test_live_prices_columns():
    """
    Test that the DataFrame returned by fetch_live_prices() contains
    all the required columns needed for downstream analytics.

    Required columns typically include: coin identifier, price, market cap,
    volume, and percentage changes. The exact column names depend on the
    CoinGecko API response structure.
    """
    # Fetch live price data
    df = fetch_live_prices()

    # Define the columns we expect to see in the DataFrame
    # These are common fields returned by CoinGecko's /coins/markets endpoint
    expected_columns = [
        'id',                           # Coin identifier (e.g., 'bitcoin')
        'current_price',                # Current price in target currency
        'market_cap',                   # Total market capitalization
        'total_volume',                 # 24h trading volume
        'price_change_percentage_24h',  # 24-hour price change (%)
    ]

    # Check each expected column exists in the DataFrame
    for col in expected_columns:
        assert col in df.columns, (
            f"Missing required column: '{col}'. "
            f"Available columns: {list(df.columns)}"
        )


# ============================================================================
# TEST 4: Fetch Historical Prices for Bitcoin
# ============================================================================
@network_required
def test_fetch_historical_prices():
    """
    Test that we can fetch historical price data for Bitcoin.

    This is a focused test on a single, well-known cryptocurrency to
    verify the historical data pipeline works. We fetch 7 days of data
    to keep the test quick while still verifying functionality.
    """
    # Fetch 7 days of historical data for bitcoin
    result = fetch_and_store_historical(coins=["bitcoin"], days=7)

    # The function should complete without errors
    # If it returns data, verify it's valid
    if result is not None:
        assert isinstance(result, (pd.DataFrame, dict, list)), (
            f"Expected DataFrame, dict, or list — got {type(result)}"
        )


# ============================================================================
# TEST 5: API Error Handling with Invalid Coin ID
# ============================================================================
@network_required
def test_api_error_handling():
    """
    Test that our API functions handle invalid coin IDs gracefully
    without crashing the application.

    This is a critical test for robustness — in production, we might
    encounter typos in coin names or coins that have been delisted.
    The function should handle these cases without raising exceptions.
    """
    # Use a deliberately invalid coin ID that doesn't exist on CoinGecko
    invalid_coin = "this_coin_definitely_does_not_exist_12345"

    # This should NOT raise an exception — it should handle the error
    # internally (log a warning, return empty data, etc.)
    try:
        result = fetch_and_store_historical(
            coins=[invalid_coin],
            days=7
        )
        # If we get here, the function handled the error gracefully
        # The result might be None, empty DataFrame, or similar
    except Exception as e:
        # If it does raise, it should be a handled exception type,
        # not a raw HTTP error or KeyError
        pytest.fail(
            f"API function crashed with invalid coin ID. "
            f"Error: {type(e).__name__}: {str(e)}"
        )


# ============================================================================
# TEST 6: Validate Data Types in API Response
# ============================================================================
@network_required
def test_response_data_types():
    """
    Test that the data returned by fetch_live_prices() has the correct
    data types for each column.

    This prevents subtle bugs where numeric data is stored as strings,
    which would break downstream calculations (averages, percentages, etc.).
    """
    # Fetch live price data
    df = fetch_live_prices()

    # Skip if no data returned
    if df is None or len(df) == 0:
        pytest.skip("No data returned from API — cannot validate types")

    # Verify numeric columns contain numeric data
    # These columns should be floats or ints, NOT strings
    numeric_columns = ['current_price', 'market_cap', 'total_volume']

    for col in numeric_columns:
        if col in df.columns:
            # Check that the column's dtype is numeric
            assert pd.api.types.is_numeric_dtype(df[col]), (
                f"Column '{col}' should be numeric but has dtype: "
                f"{df[col].dtype}. Sample values: {df[col].head().tolist()}"
            )

    # Verify the 'id' column contains strings (coin identifiers)
    if 'id' in df.columns:
        assert pd.api.types.is_string_dtype(df['id']) or \
               pd.api.types.is_object_dtype(df['id']), (
            f"Column 'id' should be string/object but has dtype: "
            f"{df['id'].dtype}"
        )


# ============================================================================
# TEST 7: Default Coins Configuration
# ============================================================================
def test_default_coins_configured():
    """
    Test that the Config.DEFAULT_COINS setting is properly configured
    with at least one coin. This test doesn't require network access.
    """
    # Verify DEFAULT_COINS is a list
    assert isinstance(Config.DEFAULT_COINS, list), (
        f"DEFAULT_COINS should be a list, got {type(Config.DEFAULT_COINS)}"
    )

    # Verify it contains at least one coin
    assert len(Config.DEFAULT_COINS) > 0, (
        "DEFAULT_COINS is empty — at least one coin should be configured"
    )

    # Verify all entries are strings
    for coin in Config.DEFAULT_COINS:
        assert isinstance(coin, str), (
            f"Each coin in DEFAULT_COINS should be a string, "
            f"got {type(coin)}: {coin}"
        )


# ============================================================================
# TEST 8: API Rate Limit Awareness
# ============================================================================
def test_fetch_interval_configured():
    """
    Test that the fetch interval is configured to a reasonable value
    to avoid hitting API rate limits.

    CoinGecko's free tier allows ~10-30 calls/minute. Our interval
    should be at least 1 minute to be safe.
    """
    interval = Config.FETCH_INTERVAL_MINUTES

    # Verify it's a positive number
    assert isinstance(interval, (int, float)), (
        f"FETCH_INTERVAL_MINUTES should be numeric, got {type(interval)}"
    )

    assert interval >= 1, (
        f"FETCH_INTERVAL_MINUTES is {interval} — should be at least 1 minute "
        f"to avoid API rate limiting"
    )
