"""
config.py — Centralized Configuration Loader
============================================

Loads environment variables from `.env` using python-dotenv and defines
a unified `Config` class containing API keys, database credentials, default
settings, and directory paths.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
# This finds the .env file in the project root and loads it into os.environ
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")


class Config:
    # --- CoinGecko API ---
    COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")

    # --- Binance API (Optional) ---
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")

    # --- CryptoPanic API (Optional) ---
    CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "")

    # --- NewsAPI (Optional) ---
    NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

    # --- PostgreSQL Database ---
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "crypto_analytics")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # Construct SQLAlchemy connection URL
    # SQLite is allowed as a fallback for offline development
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # --- Default Settings ---
    DEFAULT_COINS = [
        "bitcoin",
        "ethereum",
        "cardano",
        "solana",
        "dogecoin",
        "polkadot",
        "ripple",
        "litecoin"
    ]
    DEFAULT_CURRENCY = "usd"
    FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "5"))

    # --- Directory Paths ---
    DATA_DIR = BASE_DIR / "data"
    DATA_RAW_DIR = DATA_DIR / "raw"
    DATA_PROCESSED_DIR = DATA_DIR / "processed"
    DATA_EXPORTS_DIR = DATA_DIR / "exports"
    LOGS_DIR = BASE_DIR / "logs"


# Ensure all critical directories exist on application startup
for path in [Config.DATA_RAW_DIR, Config.DATA_PROCESSED_DIR, Config.DATA_EXPORTS_DIR, Config.LOGS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Allow standalone execution to verify environment loading
if __name__ == "__main__":
    print("Loaded configuration successfully:")
    print(f"  BASE_DIR:         {Config.BASE_DIR}")
    print(f"  DATABASE_URL:     {Config.DATABASE_URL.split('@')[-1] if '@' in Config.DATABASE_URL else Config.DATABASE_URL}")
    print(f"  DEFAULT_COINS:    {Config.DEFAULT_COINS}")
    print(f"  FETCH_INTERVAL:   {Config.FETCH_INTERVAL_MINUTES} minutes")
