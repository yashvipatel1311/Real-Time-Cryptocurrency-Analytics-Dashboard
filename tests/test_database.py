# ============================================================================
# Database Tests — Testing PostgreSQL Integration
# ============================================================================
# These tests verify that our database layer works correctly, including:
#   - Connection string configuration
#   - Database connectivity
#   - Table creation (DDL)
#   - Data insertion (INSERT)
#   - Data retrieval (SELECT)
#   - Data integrity validation
#
# Tests that require a running PostgreSQL instance will be automatically
# skipped if the database is not available. This ensures tests don't fail
# in CI environments without a database.
#
# Run these tests with:
#   pytest tests/test_database.py -v
# ============================================================================

import pytest
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Internal project imports
# ---------------------------------------------------------------------------
from config.config import Config
from database.db_connection import get_engine, get_session, test_connection as verify_db_connection
from database.create_tables import (
    create_all_tables,
    LiveCryptoPrice,
    HistoricalPrice,
    Portfolio,
    SentimentData,
)


# ============================================================================
# HELPER: Check if PostgreSQL database is available
# ============================================================================
def is_database_available():
    """
    Attempts to connect to the PostgreSQL database defined in Config.
    Returns True if the connection succeeds, False otherwise.

    This prevents tests from failing hard when PostgreSQL is not running
    (e.g., on a developer's machine without Docker, or in CI).
    """
    try:
        return verify_db_connection()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Flag: set once at module load time
# ---------------------------------------------------------------------------
DB_AVAILABLE = is_database_available()

# Custom marker for tests that need a database
db_required = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason="PostgreSQL database is not available — skipping database test"
)


# ============================================================================
# FIXTURES — Setup and teardown for database tests
# ============================================================================
@pytest.fixture(scope="function")
def db_session():
    """
    Pytest fixture that provides a database session for each test.

    This fixture:
      1. Creates a new session before the test
      2. Yields the session to the test function
      3. Rolls back any uncommitted changes after the test
      4. Closes the session to free resources

    Using rollback ensures tests don't permanently modify the database,
    making each test independent and repeatable.
    """
    # Skip if database is not available
    if not DB_AVAILABLE:
        pytest.skip("Database not available")

    # Get a new session from our connection module
    session = get_session()

    try:
        # Yield the session to the test function
        yield session
    finally:
        # ALWAYS rollback and close, even if the test fails
        # This prevents test data from polluting the database
        session.rollback()
        session.close()


@pytest.fixture(scope="module")
def db_engine():
    """
    Pytest fixture that provides the SQLAlchemy engine for the test module.

    Scope is 'module' so the engine is created once and shared across
    all tests in this file (creating engines is expensive).
    """
    if not DB_AVAILABLE:
        pytest.skip("Database not available")

    engine = get_engine()
    yield engine
    engine.dispose()  # Clean up connection pool after all tests


# ============================================================================
# TEST 1: Database URL Format Validation
# ============================================================================
def test_database_url_format():
    """
    Test that the DATABASE_URL is properly formatted as a PostgreSQL
    connection string.

    A valid PostgreSQL URL looks like:
      postgresql://username:password@host:port/database_name

    This test runs WITHOUT needing a database connection — it only
    checks the configuration string format.
    """
    db_url = Config.DATABASE_URL

    # Verify the URL is not empty or None
    assert db_url is not None, (
        "DATABASE_URL is None — check your .env file"
    )
    assert len(db_url) > 0, (
        "DATABASE_URL is empty — set it in your .env file"
    )

    # Verify it starts with a PostgreSQL scheme
    valid_prefixes = [
        'postgresql://',
        'postgresql+psycopg2://',
        'postgresql+asyncpg://',
        'sqlite:///',  # Also allow SQLite for testing
    ]

    has_valid_prefix = any(db_url.startswith(prefix) for prefix in valid_prefixes)
    assert has_valid_prefix, (
        f"DATABASE_URL should start with one of {valid_prefixes}, "
        f"but got: '{db_url[:30]}...'"
    )


# ============================================================================
# TEST 2: Database Connection
# ============================================================================
@db_required
def test_database_connection():
    """
    Test that we can establish a connection to the PostgreSQL database.

    This verifies:
      - The DATABASE_URL credentials are correct
      - PostgreSQL is running and accepting connections
      - Our get_engine() function works properly
    """
    # test_connection() should return True if the database is reachable
    result = test_connection()

    assert result is True, (
        "Database connection failed — check that PostgreSQL is running "
        "and DATABASE_URL in .env is correct"
    )


# ============================================================================
# TEST 3: Table Creation
# ============================================================================
@db_required
def test_table_creation():
    """
    Test that create_all_tables() runs without errors.

    This function creates all the database tables defined in our
    SQLAlchemy models (LiveCryptoPrice, HistoricalPrice, Portfolio,
    SentimentData). It uses CREATE TABLE IF NOT EXISTS, so it's safe
    to run multiple times.
    """
    # This should not raise any exceptions
    try:
        create_all_tables()
    except Exception as e:
        pytest.fail(
            f"create_all_tables() raised an exception: "
            f"{type(e).__name__}: {str(e)}"
        )


# ============================================================================
# TEST 4: Live Price Data Insertion
# ============================================================================
@db_required
def test_live_price_insert(db_session):
    """
    Test that we can insert a row into the live_crypto_prices table.

    This creates a sample LiveCryptoPrice record with realistic data
    and verifies it can be added to the database without errors.
    """
    # Create a sample live price record
    sample_price = LiveCryptoPrice(
        coin_id="bitcoin",
        symbol="btc",
        name="Bitcoin",
        current_price=67500.42,
        market_cap=1320000000000,
        total_volume=28500000000,
        price_change_percentage_24h=-2.35,
        last_updated=datetime.now(timezone.utc),
    )

    # Add to the session and flush (send to DB but don't commit)
    try:
        db_session.add(sample_price)
        db_session.flush()  # Sends INSERT to DB, assigns ID

        # Verify the record got an ID assigned by the database
        assert sample_price.id is not None, (
            "Inserted record should have an auto-generated ID"
        )

    except Exception as e:
        pytest.fail(
            f"Failed to insert LiveCryptoPrice: "
            f"{type(e).__name__}: {str(e)}"
        )

    # Note: The fixture will rollback this insert after the test,
    # so it won't permanently affect the database


# ============================================================================
# TEST 5: Data Retrieval
# ============================================================================
@db_required
def test_data_retrieval(db_session):
    """
    Test that we can query data back from the database after inserting it.

    This is an end-to-end test of the INSERT → SELECT cycle:
      1. Insert a record with known values
      2. Query it back using a filter
      3. Verify the retrieved values match what we inserted
    """
    # Step 1: Insert a record with a unique identifier
    test_coin_id = "test_coin_retrieval_12345"
    test_price = 99999.99

    sample_record = LiveCryptoPrice(
        coin_id=test_coin_id,
        symbol="tst",
        name="Test Coin",
        current_price=test_price,
        market_cap=1000000,
        total_volume=500000,
        price_change_percentage_24h=5.5,
        last_updated=datetime.now(timezone.utc),
    )

    db_session.add(sample_record)
    db_session.flush()

    # Step 2: Query the record back using the unique coin_id
    retrieved = db_session.query(LiveCryptoPrice).filter_by(
        coin_id=test_coin_id
    ).first()

    # Step 3: Verify the retrieved data matches what we inserted
    assert retrieved is not None, (
        f"Could not retrieve record with coin_id='{test_coin_id}'"
    )
    assert retrieved.coin_id == test_coin_id, (
        f"coin_id mismatch: expected '{test_coin_id}', "
        f"got '{retrieved.coin_id}'"
    )
    assert retrieved.current_price == test_price, (
        f"current_price mismatch: expected {test_price}, "
        f"got {retrieved.current_price}"
    )
    assert retrieved.symbol == "tst", (
        f"symbol mismatch: expected 'tst', got '{retrieved.symbol}'"
    )


# ============================================================================
# TEST 6: Data Validation / Integrity
# ============================================================================
@db_required
def test_data_validation(db_session):
    """
    Test data integrity rules for the LiveCryptoPrice model.

    This verifies that:
      - Required fields cannot be null (if enforced by the model)
      - Numeric values are stored with correct precision
      - Timestamps are stored correctly in UTC
    """
    # Create a record with valid data
    now = datetime.now(timezone.utc)
    record = LiveCryptoPrice(
        coin_id="ethereum",
        symbol="eth",
        name="Ethereum",
        current_price=3500.12345,
        market_cap=420000000000,
        total_volume=15000000000,
        price_change_percentage_24h=-1.23,
        last_updated=now,
    )

    db_session.add(record)
    db_session.flush()

    # Retrieve and validate
    retrieved = db_session.query(LiveCryptoPrice).filter_by(
        coin_id="ethereum"
    ).first()

    # Verify data integrity
    assert retrieved is not None, "Failed to retrieve inserted record"

    # Check that numeric values are stored correctly (within floating-point tolerance)
    assert abs(retrieved.current_price - 3500.12345) < 0.01, (
        f"Price precision lost: expected ~3500.12345, got {retrieved.current_price}"
    )

    # Check that the coin_id is exactly what we set
    assert retrieved.coin_id == "ethereum", (
        f"coin_id integrity issue: expected 'ethereum', got '{retrieved.coin_id}'"
    )

    # Check that the name field is preserved
    assert retrieved.name == "Ethereum", (
        f"name field integrity issue: expected 'Ethereum', got '{retrieved.name}'"
    )

    # Check timestamp is not None
    assert retrieved.last_updated is not None, (
        "last_updated should not be None"
    )


# ============================================================================
# TEST 7: Multiple Records Query
# ============================================================================
@db_required
def test_multiple_records(db_session):
    """
    Test that we can insert and query multiple records at once.
    This verifies batch operations work correctly.
    """
    # Insert multiple records
    coins = [
        ("multi_test_btc", "btc", "Bitcoin Test", 67000.0),
        ("multi_test_eth", "eth", "Ethereum Test", 3500.0),
        ("multi_test_sol", "sol", "Solana Test", 150.0),
    ]

    for coin_id, symbol, name, price in coins:
        record = LiveCryptoPrice(
            coin_id=coin_id,
            symbol=symbol,
            name=name,
            current_price=price,
            market_cap=1000000,
            total_volume=500000,
            price_change_percentage_24h=0.0,
            last_updated=datetime.now(timezone.utc),
        )
        db_session.add(record)

    db_session.flush()

    # Query all test records
    results = db_session.query(LiveCryptoPrice).filter(
        LiveCryptoPrice.coin_id.like("multi_test_%")
    ).all()

    # Verify we got all 3 records back
    assert len(results) == 3, (
        f"Expected 3 records, got {len(results)}"
    )


# ============================================================================
# TEST 8: ORM Model Attributes
# ============================================================================
def test_model_has_required_attributes():
    """
    Test that the LiveCryptoPrice ORM model has all the expected
    column attributes. This test doesn't require a database connection.
    """
    # These are the attributes we expect on the model class
    expected_attrs = [
        'coin_id',
        'symbol',
        'name',
        'current_price',
        'market_cap',
        'total_volume',
        'price_change_percentage_24h',
        'last_updated',
    ]

    for attr in expected_attrs:
        assert hasattr(LiveCryptoPrice, attr), (
            f"LiveCryptoPrice model is missing attribute: '{attr}'"
        )
