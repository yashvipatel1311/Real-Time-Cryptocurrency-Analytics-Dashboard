"""
helper_functions.py — Common Helper and Utility Functions
==========================================================

Provides shared helper functions for saving/loading raw JSON files, formatting,
validating input, and a robust retry decorator for API operations.
"""

import json
import time
import functools
import pandas as pd
from typing import Any, Optional, Union, List
from pathlib import Path

from config.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to a float, returning the default if conversion fails.
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def save_raw_json(data: Union[dict, list], filename: str, directory: Optional[Path] = None) -> Path:
    """
    Save dict or list to a JSON file in the raw data directory.
    """
    if directory is None:
        directory = Config.DATA_RAW_DIR

    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / filename

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.debug(f"Saved raw JSON to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        raise


def load_raw_json(filename: str, directory: Optional[Path] = None) -> Union[dict, list]:
    """
    Load and return JSON data from a file in the raw data directory.
    """
    if directory is None:
        directory = Config.DATA_RAW_DIR

    file_path = directory / filename

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from {file_path}: {e}")
        raise


def format_timestamp(timestamp_ms: Union[int, float]) -> str:
    """
    Convert a millisecond Unix timestamp to a standardized string representation.
    """
    try:
        return pd.to_datetime(timestamp_ms, unit="ms", utc=True).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.error(f"Failed to format timestamp {timestamp_ms}: {e}")
        return ""


def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> bool:
    """
    Validate that a pandas DataFrame contains all required columns and is not empty.
    """
    if df is None or df.empty:
        logger.warning("DataFrame validation failed: DataFrame is empty or None")
        return False

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        logger.warning(f"DataFrame validation failed. Missing columns: {missing}")
        return False

    return True


def format_currency(value: Union[int, float]) -> str:
    """
    Format a numeric value as a USD currency string.
    """
    try:
        return f"${safe_float(value):,.2f}"
    except Exception:
        return "$0.00"


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate the percentage growth from an old value to a new value.
    """
    old_val = safe_float(old_value)
    new_val = safe_float(new_value)

    if old_val == 0.0:
        return 0.0

    return ((new_val - old_val) / old_val) * 100.0


def export_to_csv(df: pd.DataFrame, filename: str, directory: Optional[Path] = None) -> Path:
    """
    Save a DataFrame as a CSV file in the exports directory.
    """
    if directory is None:
        directory = Config.DATA_EXPORTS_DIR

    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / filename

    try:
        df.to_csv(file_path, index=False)
        logger.info(f"Successfully exported dataset to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to export DataFrame to CSV {file_path}: {e}")
        raise


def retry_on_failure(max_retries: int = 3, delay: int = 5):
    """
    A decorator that retries a function if it encounters an exception.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    logger.warning(
                        f"Exception in function '{func.__name__}': {e}. "
                        f"Attempt {retries}/{max_retries}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
            # Final attempt
            return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    print("Testing safe_float conversion:")
    print(f"  '123.45' -> {safe_float('123.45')}")
    print(f"  'invalid' -> {safe_float('invalid', -1.0)}")

    print("\nTesting currency formatting:")
    print(f"  1234567.89 -> {format_currency(1234567.89)}")
