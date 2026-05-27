# ============================================================================
# Auto-Fetch Scheduler — Periodic Data Collection
# ============================================================================
# This module uses APScheduler (Advanced Python Scheduler) to automatically
# fetch cryptocurrency data at regular intervals. It runs three jobs:
#
#   1. Live Prices   — Every N minutes (configured in Config)
#   2. Historical    — Every 60 minutes (hourly snapshots)
#   3. Sentiment     — Every 30 minutes (if API key is available)
#
# Usage:
#   python scheduler/auto_fetch_scheduler.py
#   — OR —
#   python main.py --scheduler
#
# Dependencies:
#   pip install apscheduler
# ============================================================================

import time
import signal
import sys

# ---------------------------------------------------------------------------
# APScheduler imports
# ---------------------------------------------------------------------------
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ---------------------------------------------------------------------------
# Internal project imports
# ---------------------------------------------------------------------------
from config.config import Config
from utils.logger import get_logger
from api.fetch_crypto_data import fetch_and_store_live_prices
from api.fetch_historical_data import fetch_and_store_historical
from api.fetch_sentiment import fetch_and_store_sentiment

# ---------------------------------------------------------------------------
# Logger setup — all scheduler events are logged to console + file
# ---------------------------------------------------------------------------
logger = get_logger("scheduler")


# ============================================================================
# JOB 1: Scheduled Live Price Fetch
# ============================================================================
def scheduled_fetch_job():
    """
    Fetches the latest live cryptocurrency prices from CoinGecko and
    stores them in the PostgreSQL database.

    This job runs at the interval defined by Config.FETCH_INTERVAL_MINUTES.
    On success, it logs the number of coins fetched.
    On failure, it logs the error but does NOT crash the scheduler.
    """
    try:
        logger.info("=" * 60)
        logger.info("🔄 [Scheduler] Starting live price fetch job...")

        # Call the API module to fetch and store live prices
        result = fetch_and_store_live_prices()

        # Log success with details
        if result is not None:
            logger.info(
                f"✅ [Scheduler] Live price fetch completed successfully. "
                f"Fetched {len(result)} coins."
            )
        else:
            logger.warning(
                "⚠️ [Scheduler] Live price fetch returned no data."
            )

    except Exception as e:
        # IMPORTANT: We catch ALL exceptions here so the scheduler keeps running
        # even if one fetch fails (e.g., network timeout, API rate limit)
        logger.error(
            f"❌ [Scheduler] Live price fetch FAILED: {str(e)}",
            exc_info=True  # This logs the full traceback
        )


# ============================================================================
# JOB 2: Scheduled Historical Data Fetch
# ============================================================================
def scheduled_historical_job():
    """
    Fetches historical price data for all default coins configured in
    Config.DEFAULT_COINS. This runs less frequently (every 60 minutes)
    because historical data doesn't change as rapidly.

    Fetches 30 days of history for each coin by default.
    """
    try:
        logger.info("=" * 60)
        logger.info("📊 [Scheduler] Starting historical data fetch job...")

        # Get the list of coins from configuration
        coins = Config.DEFAULT_COINS
        days = 30  # Fetch 30 days of historical data

        logger.info(
            f"📋 [Scheduler] Fetching history for {len(coins)} coins: "
            f"{', '.join(coins)}"
        )

        # Fetch historical data for all configured coins
        fetch_and_store_historical(coins=coins, days=days)

        logger.info(
            f"✅ [Scheduler] Historical data fetch completed for "
            f"{len(coins)} coins ({days} days each)."
        )

    except Exception as e:
        logger.error(
            f"❌ [Scheduler] Historical data fetch FAILED: {str(e)}",
            exc_info=True
        )


# ============================================================================
# JOB 3: Scheduled Sentiment Fetch
# ============================================================================
def scheduled_sentiment_job():
    """
    Fetches cryptocurrency sentiment data from available APIs.
    This runs every 30 minutes. Only active if API keys are configured.
    """
    try:
        logger.info("=" * 60)
        logger.info("💬 [Scheduler] Starting sentiment data fetch job...")

        # Call the sentiment fetching module
        fetch_and_store_sentiment()

        logger.info(
            "✅ [Scheduler] Sentiment data fetch completed successfully."
        )

    except Exception as e:
        logger.error(
            f"❌ [Scheduler] Sentiment data fetch FAILED: {str(e)}",
            exc_info=True
        )


# ============================================================================
# START SCHEDULER — Creates and configures the BackgroundScheduler
# ============================================================================
def start_scheduler():
    """
    Creates a BackgroundScheduler instance and adds all periodic jobs.

    Jobs added:
        1. Live prices    — every Config.FETCH_INTERVAL_MINUTES minutes
        2. Historical     — every 60 minutes
        3. Sentiment      — every 30 minutes (only if API key exists)

    Returns:
        BackgroundScheduler: The running scheduler instance (so it can
        be stopped later with stop_scheduler).
    """
    logger.info("=" * 60)
    logger.info("🚀 [Scheduler] Initializing Auto-Fetch Scheduler...")
    logger.info("=" * 60)

    # -----------------------------------------------------------------------
    # Create the BackgroundScheduler
    # BackgroundScheduler runs jobs in a background thread, allowing the
    # main thread to continue (useful for CLI or web app integration)
    # -----------------------------------------------------------------------
    scheduler = BackgroundScheduler(
        job_defaults={
            'coalesce': True,         # If multiple runs are missed, only run once
            'max_instances': 1,       # Don't allow overlapping job runs
            'misfire_grace_time': 60  # Allow 60s grace period for misfired jobs
        }
    )

    # -----------------------------------------------------------------------
    # JOB 1: Live Price Fetch
    # Runs every FETCH_INTERVAL_MINUTES minutes (default: 5)
    # -----------------------------------------------------------------------
    live_interval = Config.FETCH_INTERVAL_MINUTES
    scheduler.add_job(
        func=scheduled_fetch_job,
        trigger=IntervalTrigger(minutes=live_interval),
        id='live_price_fetch',
        name='Live Crypto Price Fetch',
        replace_existing=True  # Replace if job with same ID exists
    )
    logger.info(
        f"📌 [Scheduler] Added job: Live Price Fetch "
        f"(every {live_interval} minutes)"
    )

    # -----------------------------------------------------------------------
    # JOB 2: Historical Data Fetch
    # Runs every 60 minutes (hourly)
    # -----------------------------------------------------------------------
    scheduler.add_job(
        func=scheduled_historical_job,
        trigger=IntervalTrigger(minutes=60),
        id='historical_data_fetch',
        name='Historical Data Fetch',
        replace_existing=True
    )
    logger.info(
        "📌 [Scheduler] Added job: Historical Data Fetch (every 60 minutes)"
    )

    # -----------------------------------------------------------------------
    # JOB 3: Sentiment Data Fetch (conditional)
    # Only added if CoinGecko API key is configured (sentiment may need it)
    # -----------------------------------------------------------------------
    api_key = Config.COINGECKO_API_KEY
    if api_key and api_key.strip():
        scheduler.add_job(
            func=scheduled_sentiment_job,
            trigger=IntervalTrigger(minutes=30),
            id='sentiment_data_fetch',
            name='Sentiment Data Fetch',
            replace_existing=True
        )
        logger.info(
            "📌 [Scheduler] Added job: Sentiment Data Fetch "
            "(every 30 minutes)"
        )
    else:
        logger.warning(
            "⚠️ [Scheduler] Skipping sentiment job — no API key configured. "
            "Set COINGECKO_API_KEY in your .env file to enable."
        )

    # -----------------------------------------------------------------------
    # Start the scheduler — jobs begin executing in background threads
    # -----------------------------------------------------------------------
    scheduler.start()

    # Log summary of all scheduled jobs
    logger.info("=" * 60)
    logger.info("✅ [Scheduler] Auto-Fetch Scheduler is now RUNNING!")
    logger.info(f"📋 [Scheduler] Active jobs: {len(scheduler.get_jobs())}")
    for job in scheduler.get_jobs():
        logger.info(f"   → {job.name} (next run: {job.next_run_time})")
    logger.info("=" * 60)
    logger.info("💡 Press Ctrl+C to stop the scheduler gracefully.")

    return scheduler


# ============================================================================
# STOP SCHEDULER — Graceful shutdown
# ============================================================================
def stop_scheduler(scheduler):
    """
    Gracefully shuts down the scheduler, waiting for any running jobs
    to complete before exiting.

    Args:
        scheduler (BackgroundScheduler): The scheduler instance to stop.
    """
    if scheduler and scheduler.running:
        logger.info("🛑 [Scheduler] Shutting down scheduler gracefully...")

        # wait=True ensures currently-running jobs finish before shutdown
        scheduler.shutdown(wait=True)

        logger.info("✅ [Scheduler] Scheduler has been stopped successfully.")
    else:
        logger.warning("⚠️ [Scheduler] Scheduler is not running.")


# ============================================================================
# MAIN — Run the scheduler as a standalone script
# ============================================================================
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  🚀 Crypto Analytics — Auto-Fetch Scheduler")
    print("  Starting background data collection...")
    print("=" * 60 + "\n")

    # Start the scheduler
    scheduler = start_scheduler()

    # -----------------------------------------------------------------------
    # Keep the main thread alive so the scheduler can run
    # The scheduler runs in a background thread, so without this loop,
    # the script would exit immediately.
    # -----------------------------------------------------------------------
    try:
        while True:
            # Sleep for 1 second at a time to remain responsive to Ctrl+C
            time.sleep(1)

    except KeyboardInterrupt:
        # User pressed Ctrl+C — stop gracefully
        print("\n\n⚠️ Keyboard interrupt received!")
        stop_scheduler(scheduler)
        print("👋 Goodbye!")
        sys.exit(0)

    except Exception as e:
        # Unexpected error — log and stop
        logger.error(f"💥 Unexpected error: {str(e)}", exc_info=True)
        stop_scheduler(scheduler)
        sys.exit(1)
