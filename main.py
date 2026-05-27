# ============================================================================
# Main CLI Entry Point — Crypto Analytics Platform v1.0
# ============================================================================
# This is the main entry point for the Crypto Analytics Platform.
# It orchestrates the entire pipeline:
#
#   1. Fetch live cryptocurrency prices from CoinGecko
#   2. Fetch historical data for trend analysis
#   3. Run analytics (KPI, trends, volatility, portfolio)
#   4. Export reports as CSV files for Power BI
#
# Usage:
#   python main.py             # Run the full pipeline once
#   python main.py --fetch     # Only fetch data
#   python main.py --analyze   # Only run analytics
#   python main.py --export    # Only export reports
#   python main.py --all       # Run everything
#   python main.py --scheduler # Start the auto-fetch scheduler
#   python main.py --test      # Run the test suite
#
# ============================================================================

import argparse
import sys
import os
import subprocess
from datetime import datetime

import pandas as pd

# ---------------------------------------------------------------------------
# Internal project imports — organized by layer
# ---------------------------------------------------------------------------
# Configuration
from config.config import Config

# Logging
from utils.logger import get_logger

# Database
from database.db_connection import get_engine, get_session, test_connection
from database.create_tables import create_all_tables

# API — Data Fetching
from api.fetch_crypto_data import fetch_live_prices, fetch_and_store_live_prices
from api.fetch_historical_data import fetch_and_store_historical
from api.fetch_sentiment import fetch_and_store_sentiment

# Analytics
from analytics.kpi_calculations import generate_kpi_summary, export_kpi_report
from analytics.trend_analysis import generate_trend_report, export_trend_report
from analytics.volatility_analysis import (
    calculate_risk_metrics,
    export_volatility_report,
)
from analytics.portfolio_analysis import (
    generate_portfolio_report,
    export_portfolio_report,
    create_sample_portfolio,
)

# Scheduler
from scheduler.auto_fetch_scheduler import start_scheduler, stop_scheduler

# ---------------------------------------------------------------------------
# Logger for the main module
# ---------------------------------------------------------------------------
logger = get_logger("main")

# ---------------------------------------------------------------------------
# Platform version
# ---------------------------------------------------------------------------
VERSION = "1.0.0"


# ============================================================================
# CONSOLE OUTPUT HELPERS — Rich ASCII art and formatted output
# ============================================================================
def print_banner():
    """
    Prints the application banner with version info and timestamp.
    Uses box-drawing characters for a professional look.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print()
    print("+----------------------------------------------------------+")
    print("|                                                          |")
    print("|   [Crypto Analytics Platform]                            |")
    print(f"|       Version {VERSION}                                      |")
    print("|                                                          |")
    print("|   Real-Time Cryptocurrency Analytics & Reporting         |")
    print("|   Powered by CoinGecko API + PostgreSQL                  |")
    print("|                                                          |")
    print("+----------------------------------------------------------+")
    print(f"|   Date: {timestamp}                                  |")
    print("+----------------------------------------------------------+")
    print()


def print_step(step_num, total_steps, message, status="running"):
    """
    Prints a formatted step indicator to the console.

    Args:
        step_num (int): Current step number (1-indexed)
        total_steps (int): Total number of steps
        message (str): Description of the step
        status (str): 'running', 'done', or 'error'
    """
    status_icons = {
        "running": "...",
        "done": "[OK]",
        "error": "[FAIL]",
        "skip": "[SKIP]",
    }
    icon = status_icons.get(status, "->")

    # Print the formatted step
    print(f"  {icon} [{step_num}/{total_steps}] {message}")


def print_separator():
    """Prints a horizontal separator line."""
    print("  " + "-" * 54)


def print_summary_box(title, items):
    """
    Prints a summary box with a title and list of key-value items.

    Args:
        title (str): Box title
        items (dict): Key-value pairs to display
    """
    print()
    print(f"  +- {title} " + "-" * max(0, 48 - len(title)))
    for key, value in items.items():
        print(f"  |  {key}: {value}")
    print("  +" + "-" * 54)
    print()


# ============================================================================
# PIPELINE STEP 1: Fetch Data
# ============================================================================
def run_data_pipeline():
    """
    Runs the complete data pipeline:
      Step 1: Fetch live cryptocurrency prices from CoinGecko
      Step 2: Fetch historical data for all configured coins
      Step 3: Run analytics on the fetched data
      Step 4: Export all reports as CSV files

    Returns:
        dict: A dictionary containing:
            - 'live_df': DataFrame of live prices
            - 'historical_dfs': dict of DataFrames keyed by coin ID
            - 'analytics_results': dict of analytics outputs
            - 'success': bool indicating overall success
    """
    total_steps = 4
    results = {
        'live_df': None,
        'historical_dfs': {},
        'analytics_results': {},
        'success': False,
    }

    print()
    print("  +------------------------------------------------------+")
    print("  |  Running Full Data Pipeline                          |")
    print("  +------------------------------------------------------+")

    # -------------------------------------------------------------------
    # STEP 1: Fetch Live Prices
    # -------------------------------------------------------------------
    print_step(1, total_steps, "Fetching live prices from CoinGecko...")
    try:
        live_df = fetch_live_prices()
        if live_df is not None and len(live_df) > 0:
            results['live_df'] = live_df
            print_step(1, total_steps, f"Fetched {len(live_df)} coins", "done")
            logger.info(f"Live prices fetched: {len(live_df)} coins")

            # Also store in database
            try:
                fetch_and_store_live_prices()
                logger.info("Live prices stored in database")
            except Exception as db_err:
                logger.warning(f"Could not store in DB: {db_err}")
        else:
            print_step(1, total_steps, "No live data returned", "error")
            logger.warning("No live price data returned from API")
    except Exception as e:
        print_step(1, total_steps, f"Failed: {str(e)[:50]}", "error")
        logger.error(f"Live price fetch failed: {e}", exc_info=True)

    print_separator()

    # -------------------------------------------------------------------
    # STEP 2: Fetch Historical Data
    # -------------------------------------------------------------------
    print_step(2, total_steps, "Fetching historical data...")
    try:
        coins = Config.DEFAULT_COINS
        days = 30  # 30 days of history

        # Use a single batch call which has built-in rate-limit delays
        hist_results = fetch_and_store_historical(coins=coins, days=days)
        if hist_results:
            results['historical_dfs'] = hist_results

        fetched_count = sum(1 for v in results.get('historical_dfs', {}).values() if v)
        print_step(
            2, total_steps,
            f"Fetched history for {fetched_count}/{len(coins)} coins",
            "done" if fetched_count > 0 else "error"
        )
    except Exception as e:
        print_step(2, total_steps, f"Failed: {str(e)[:50]}", "error")
        logger.error(f"Historical data fetch failed: {e}", exc_info=True)

    print_separator()

    # -------------------------------------------------------------------
    # STEP 3: Run Analytics
    # -------------------------------------------------------------------
    print_step(3, total_steps, "Running analytics...")
    try:
        analytics_results = run_analytics_pipeline(
            live_df=results['live_df'],
            historical_dfs=results['historical_dfs']
        )
        results['analytics_results'] = analytics_results
        print_step(3, total_steps, "Analytics completed", "done")
    except Exception as e:
        print_step(3, total_steps, f"Failed: {str(e)[:50]}", "error")
        logger.error(f"Analytics pipeline failed: {e}", exc_info=True)

    print_separator()

    # -------------------------------------------------------------------
    # STEP 4: Export Reports
    # -------------------------------------------------------------------
    print_step(4, total_steps, "Exporting reports to CSV...")
    try:
        export_all_reports(
            live_df=results['live_df'],
            historical_dfs=results['historical_dfs'],
            analytics_results=results['analytics_results']
        )
        print_step(4, total_steps, "Reports exported", "done")
    except Exception as e:
        print_step(4, total_steps, f"Failed: {str(e)[:50]}", "error")
        logger.error(f"Report export failed: {e}", exc_info=True)

    print("  |                                                      |")
    print("  +------------------------------------------------------+")

    results['success'] = True
    return results


# ============================================================================
# PIPELINE STEP 3: Run Analytics
# ============================================================================
def run_analytics_pipeline(live_df, historical_dfs):
    """
    Runs all analytics modules on the fetched data:
      - KPI Summary (top-level metrics)
      - Trend Analysis (per-coin trend reports)
      - Volatility Analysis (risk metrics)
      - Portfolio Analysis (portfolio performance)

    Args:
        live_df (pd.DataFrame or None): Live price data
        historical_dfs (dict): Historical DataFrames keyed by coin ID

    Returns:
        dict: Analytics results with keys:
            - 'kpi_summary': KPI metrics DataFrame
            - 'trend_reports': dict of trend reports by coin
            - 'risk_metrics': Volatility/risk DataFrame
            - 'portfolio_report': Portfolio performance DataFrame
    """
    analytics_results = {
        'kpi_summary': None,
        'trend_reports': {},
        'risk_metrics': None,
        'portfolio_report': None,
    }

    # -------------------------------------------------------------------
    # KPI Summary — High-level metrics from live data
    # -------------------------------------------------------------------
    if live_df is not None and len(live_df) > 0:
        try:
            kpi_summary = generate_kpi_summary(live_df)
            analytics_results['kpi_summary'] = kpi_summary
            logger.info("KPI summary generated successfully")
        except Exception as e:
            logger.warning(f"KPI generation failed: {e}")

    # -------------------------------------------------------------------
    # Trend Analysis — Per-coin trend reports from historical data
    # -------------------------------------------------------------------
    for coin_id, hist_df in historical_dfs.items():
        try:
            if hist_df is not None and isinstance(hist_df, pd.DataFrame) and len(hist_df) > 0:
                trend_report = generate_trend_report(hist_df, coin_id)
                analytics_results['trend_reports'][coin_id] = trend_report
                logger.info(f"Trend report generated for {coin_id}")
        except Exception as e:
            logger.warning(f"Trend analysis failed for {coin_id}: {e}")

    # -------------------------------------------------------------------
    # Volatility Analysis — Risk metrics from historical data
    # -------------------------------------------------------------------
    # Combine all historical data for overall risk analysis
    all_historical = []
    for coin_id, hist_df in historical_dfs.items():
        if hist_df is not None and isinstance(hist_df, pd.DataFrame):
            all_historical.append(hist_df)

    if all_historical:
        try:
            combined_df = pd.concat(all_historical, ignore_index=True)
            risk_metrics = calculate_risk_metrics(combined_df)
            analytics_results['risk_metrics'] = risk_metrics
            logger.info("Risk metrics calculated successfully")
        except Exception as e:
            logger.warning(f"Volatility analysis failed: {e}")

    # -------------------------------------------------------------------
    # Portfolio Analysis — Portfolio performance report
    # -------------------------------------------------------------------
    try:
        # Create a sample portfolio if no real portfolio exists
        portfolio_df = create_sample_portfolio()
        if live_df is not None and portfolio_df is not None:
            portfolio_report = generate_portfolio_report(portfolio_df, live_df)
            analytics_results['portfolio_report'] = portfolio_report
            logger.info("Portfolio report generated successfully")
    except Exception as e:
        logger.warning(f"Portfolio analysis failed: {e}")

    return analytics_results


# ============================================================================
# PIPELINE STEP 4: Export All Reports
# ============================================================================
def export_all_reports(live_df, historical_dfs, analytics_results):
    """
    Exports all analytics results to CSV files in the data/exports/ directory.
    These CSV files are designed to be imported into Power BI for visualization.

    Args:
        live_df (pd.DataFrame): Live price data
        historical_dfs (dict): Historical DataFrames by coin
        analytics_results (dict): Analytics outputs
    """
    # Ensure the exports directory exists
    exports_dir = Config.DATA_EXPORTS_DIR
    os.makedirs(exports_dir, exist_ok=True)

    exported_files = []

    # -------------------------------------------------------------------
    # Export live prices
    # -------------------------------------------------------------------
    if live_df is not None and len(live_df) > 0:
        try:
            export_path = os.path.join(exports_dir, "live_prices.csv")
            live_df.to_csv(export_path, index=False)
            exported_files.append("live_prices.csv")
            logger.info(f"Exported: {export_path}")
        except Exception as e:
            logger.warning(f"Failed to export live prices: {e}")

    # -------------------------------------------------------------------
    # Export KPI report
    # -------------------------------------------------------------------
    if analytics_results.get('kpi_summary') is not None:
        try:
            kpi_df = analytics_results['kpi_summary']
            if isinstance(kpi_df, pd.DataFrame):
                export_kpi_report(kpi_df)
                exported_files.append("kpi_report.csv")
                logger.info("Exported KPI report")
        except Exception as e:
            logger.warning(f"Failed to export KPI report: {e}")

    # -------------------------------------------------------------------
    # Export trend reports (one per coin)
    # -------------------------------------------------------------------
    for coin_id, trend_df in analytics_results.get('trend_reports', {}).items():
        try:
            if isinstance(trend_df, pd.DataFrame):
                export_trend_report(trend_df)
                exported_files.append(f"trend_{coin_id}.csv")
                logger.info(f"Exported trend report for {coin_id}")
        except Exception as e:
            logger.warning(f"Failed to export trend for {coin_id}: {e}")

    # -------------------------------------------------------------------
    # Export volatility / risk report
    # -------------------------------------------------------------------
    if analytics_results.get('risk_metrics') is not None:
        try:
            risk_df = analytics_results['risk_metrics']
            if isinstance(risk_df, pd.DataFrame):
                export_volatility_report(risk_df)
                exported_files.append("volatility_report.csv")
                logger.info("Exported volatility report")
        except Exception as e:
            logger.warning(f"Failed to export volatility report: {e}")

    # -------------------------------------------------------------------
    # Export portfolio report
    # -------------------------------------------------------------------
    if analytics_results.get('portfolio_report') is not None:
        try:
            portfolio_df = analytics_results['portfolio_report']
            if isinstance(portfolio_df, pd.DataFrame):
                export_portfolio_report(portfolio_df)
                exported_files.append("portfolio_report.csv")
                logger.info("Exported portfolio report")
        except Exception as e:
            logger.warning(f"Failed to export portfolio report: {e}")

    # Log summary
    logger.info(
        f"Export complete: {len(exported_files)} files saved to {exports_dir}"
    )

    return exported_files


# ============================================================================
# DISPLAY SUMMARY — Console output of results
# ============================================================================
def display_summary(results):
    """
    Prints a nicely formatted summary of the pipeline results to the console.

    Args:
        results (dict): The results dictionary from run_data_pipeline()
    """
    print()
    print("  +------------------------------------------------------+")
    print("  |              Pipeline Summary                        |")
    print("  +------------------------------------------------------+")

    # Live data summary
    live_df = results.get('live_df')
    if live_df is not None and len(live_df) > 0:
        print(f"  |  Live Prices:    {len(live_df)} coins fetched")
        # Show top 5 coins by market cap if available
        if 'current_price' in live_df.columns:
            print("  |")
            print("  |  Top coins by price:")
            top_coins = live_df.nlargest(5, 'current_price')
            for _, row in top_coins.iterrows():
                name = str(row.get('name') or row.get('coin_name') or 'N/A')[:15]
                price = row.get('current_price', 0)
                change = row.get('price_change_percentage_24h', 0)
                change_icon = "+" if change >= 0 else "-"
                print(
                    f"  |    {change_icon} {name:<15} "
                    f"${price:>12,.2f}  ({change:+.2f}%)"
                )
    else:
        print("  |  Live Prices:    No data available")

    print("  |")

    # Historical data summary
    hist_dfs = results.get('historical_dfs', {})
    print(f"  |  Historical Data: {len(hist_dfs)} coins")
    for coin_id in list(hist_dfs.keys())[:5]:
        df = hist_dfs[coin_id]
        rows = len(df) if isinstance(df, pd.DataFrame) else 0
        print(f"  |    -> {coin_id}: {rows} data points")

    print("  |")

    # Analytics summary
    analytics = results.get('analytics_results', {})
    kpi = analytics.get('kpi_summary')
    trends = analytics.get('trend_reports', {})
    risk = analytics.get('risk_metrics')
    portfolio = analytics.get('portfolio_report')

    print(f"  |  Analytics:")
    print(f"  |    KPI Summary:      {'Yes' if kpi is not None else 'No'}")
    print(f"  |    Trend Reports:    {'Yes' if trends else 'No'} ({len(trends)} coins)")
    print(f"  |    Risk Metrics:     {'Yes' if risk is not None else 'No'}")
    print(f"  |    Portfolio:        {'Yes' if portfolio is not None else 'No'}")

    print("  |")
    print(f"  |  Exports: {Config.DATA_EXPORTS_DIR}")
    print("  |")
    print("  +------------------------------------------------------+")
    print()


# ============================================================================
# SETUP — Initialize database and tables
# ============================================================================
def initialize_platform():
    """
    Performs initial setup:
      - Tests database connection
      - Creates all database tables (if they don't exist)
    """
    print("  [Setup] Initializing platform...")

    # Test database connection
    try:
        if test_connection():
            print("  [OK] Database connection: OK")
            logger.info("Database connection successful")
        else:
            print("  [WARNING] Database connection: FAILED")
            print("      Pipeline will still run but won't store data in DB.")
            logger.warning("Database connection failed — running without DB")
    except Exception as e:
        print(f"  [WARNING] Database check error: {str(e)[:50]}")
        logger.warning(f"Database check error: {e}")

    # Create tables
    try:
        create_all_tables()
        print("  [OK] Database tables: Ready")
        logger.info("Database tables created/verified")
    except Exception as e:
        print(f"  [WARNING] Table creation: {str(e)[:50]}")
        logger.warning(f"Table creation issue: {e}")

    print()


# ============================================================================
# CLI ARGUMENT PARSER
# ============================================================================
def parse_arguments():
    """
    Parses command-line arguments using argparse.

    Returns:
        argparse.Namespace: Parsed arguments with boolean flags
    """
    parser = argparse.ArgumentParser(
        description="🪙 Crypto Analytics Platform v{} — Real-Time Cryptocurrency Analytics".format(VERSION),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                Run the full pipeline once
  python main.py --fetch        Only fetch data (no analytics)
  python main.py --analyze      Only run analytics (on existing data)
  python main.py --export       Only export reports
  python main.py --all          Run everything (same as no args)
  python main.py --scheduler    Start the auto-fetch scheduler
  python main.py --test         Run the test suite
        """
    )

    # Define CLI arguments
    parser.add_argument(
        '--fetch',
        action='store_true',
        help='Fetch live and historical data from CoinGecko'
    )
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Run analytics on existing data'
    )
    parser.add_argument(
        '--export',
        action='store_true',
        help='Export analytics reports to CSV'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run the complete pipeline (fetch + analyze + export)'
    )
    parser.add_argument(
        '--scheduler',
        action='store_true',
        help='Start the auto-fetch scheduler (runs continuously)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run the test suite using pytest'
    )

    return parser.parse_args()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == '__main__':
    # Print the application banner
    print_banner()

    # Parse command-line arguments
    args = parse_arguments()

    # -------------------------------------------------------------------
    # MODE: Run Tests
    # -------------------------------------------------------------------
    if args.test:
        print("  [Tests] Running test suite...\n")
        logger.info("Running test suite via pytest")

        # Run pytest on the tests/ directory
        exit_code = subprocess.call(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        sys.exit(exit_code)

    # -------------------------------------------------------------------
    # MODE: Start Scheduler
    # -------------------------------------------------------------------
    if args.scheduler:
        print("  [Scheduler] Starting auto-fetch scheduler...\n")
        logger.info("Starting auto-fetch scheduler")

        # Initialize the platform first
        initialize_platform()

        # Start the scheduler (this runs until Ctrl+C)
        scheduler = start_scheduler()

        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n  [WARNING] Keyboard interrupt received!")
            stop_scheduler(scheduler)
            print("  Goodbye!")
            sys.exit(0)

    # -------------------------------------------------------------------
    # MODE: Selective Pipeline Steps
    # -------------------------------------------------------------------
    # If specific flags are set, only run those steps
    if args.fetch or args.analyze or args.export:
        initialize_platform()

        if args.fetch:
            print("  [Fetch] Fetching data...\n")
            try:
                live_df = fetch_live_prices()
                if live_df is not None:
                    print(f"  [OK] Fetched live prices for {len(live_df)} coins")
                fetch_and_store_live_prices()
                fetch_and_store_historical(
                    coins=Config.DEFAULT_COINS, days=30
                )
                print("  [OK] Data fetch complete\n")
            except Exception as e:
                print(f"  [FAIL] Fetch failed: {e}\n")
                logger.error(f"Fetch failed: {e}", exc_info=True)

        if args.analyze:
            print("  [Analyze] Running analytics...\n")
            try:
                # Try to get live data for analytics
                live_df = fetch_live_prices()
                analytics_results = run_analytics_pipeline(
                    live_df=live_df, historical_dfs={}
                )
                print("  [OK] Analytics complete\n")
            except Exception as e:
                print(f"  [FAIL] Analytics failed: {e}\n")
                logger.error(f"Analytics failed: {e}", exc_info=True)

        if args.export:
            print("  [Export] Exporting reports...\n")
            try:
                live_df = fetch_live_prices()
                analytics_results = run_analytics_pipeline(
                    live_df=live_df, historical_dfs={}
                )
                exported = export_all_reports(
                    live_df=live_df,
                    historical_dfs={},
                    analytics_results=analytics_results
                )
                print(f"  [OK] Exported {len(exported)} reports\n")
            except Exception as e:
                print(f"  [FAIL] Export failed: {e}\n")
                logger.error(f"Export failed: {e}", exc_info=True)

        sys.exit(0)

    # -------------------------------------------------------------------
    # DEFAULT MODE: Run Full Pipeline (--all or no arguments)
    # -------------------------------------------------------------------
    print("  [Pipeline] Running full pipeline...\n")
    logger.info("Starting full pipeline run")

    # Initialize database and tables
    initialize_platform()

    # Run the complete pipeline
    results = run_data_pipeline()

    # Display the summary
    display_summary(results)

    # Final message
    if results.get('success'):
        print("  [OK] Pipeline completed successfully!")
        print(f"  [Info] Reports saved to: {Config.DATA_EXPORTS_DIR}")
    else:
        print("  [WARNING] Pipeline completed with some issues.")
        print("      Check the logs for details.")

    print()
    print("  Tip: Run 'python main.py --scheduler' to start")
    print("     automatic data fetching in the background.")
    print()
    logger.info("Pipeline run completed")
