"""
fetch_sentiment.py — Cryptocurrency News Sentiment Ingestion
=============================================================

Fetches cryptocurrency news and market sentiment data from public sentiment/news
APIs (CryptoPanic, NewsAPI) and parses/stores them inside the PostgreSQL database.

Note: Since this is designed to be runnable without actual API keys, it uses
placeholders and gracefully degrades to logging instructions when keys are missing.
"""

import requests
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, List

from config.config import Config
from utils.logger import get_logger
from utils.helper_functions import save_raw_json, retry_on_failure
from database.db_connection import get_session
from database.create_tables import SentimentData

logger = get_logger(__name__)


def is_placeholder(key: str) -> bool:
    """
    Helper function to check if an API key is a placeholder value.
    """
    if not key:
        return True
    placeholders = ["add_api_key_here", "your_api_key_here", "your_db_password_here"]
    return key.strip().lower() in placeholders


@retry_on_failure(max_retries=2, delay=5)
def fetch_cryptopanic_news(currencies: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Fetches real-time crypto news and user sentiment from the CryptoPanic API.
    Ref: https://cryptopanic.com/developers/api/

    Parameters
    ----------
    currencies : list of str, optional
        A list of ticker symbols to filter by (e.g. ['BTC', 'ETH']).
        Defaults to symbols parsed from Config.DEFAULT_COINS.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame of news sentiment data, or empty DataFrame.
    """
    api_key = Config.CRYPTOPANIC_API_KEY

    if is_placeholder(api_key):
        logger.info(
            "CryptoPanic API key is placeholder (ADD_API_KEY_HERE). "
            "Skipping CryptoPanic fetch. Please paste your key in the .env file to enable."
        )
        return pd.DataFrame()

    url = "https://cryptopanic.com/api/v1/posts/"
    params = {
        "auth_token": api_key,
        "public": "true",
        "filter": "hot",
    }

    if currencies:
        params["currencies"] = ",".join([c.upper() for c in currencies])

    logger.info("Fetching real-time news from CryptoPanic API...")

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        # Save raw JSON response for archiving
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_raw_json(data, f"cryptopanic_raw_{timestamp}.json")

        results = data.get("results", [])
        if not results:
            logger.info("No news posts returned from CryptoPanic.")
            return pd.DataFrame()

        news_items = []
        for post in results:
            published_str = post.get("published_at")
            published_at = datetime.now(timezone.utc)
            if published_str:
                try:
                    published_at = pd.to_datetime(published_str).to_pydatetime()
                except Exception:
                    pass

            # Sentiment calculation placeholder:
            # In a real system, we'd use NLTK/VADER/BERT on the title or use votes from the post
            # Let's extract a simple score based on 'votes' (liked - disliked) if available
            votes = post.get("votes", {})
            likes = int(votes.get("liked", 0))
            dislikes = int(votes.get("disliked", 0))
            score = 0.0
            if (likes + dislikes) > 0:
                score = (likes - dislikes) / (likes + dislikes)

            # Map currencies associated
            currencies_in_post = post.get("currencies", [])
            coin_id = currencies_in_post[0].get("code", "CRYPTO").lower() if currencies_in_post else "general"

            news_items.append({
                "coin_id": coin_id,
                "source": "CryptoPanic",
                "title": post.get("title", ""),
                "url": post.get("url", ""),
                "sentiment_score": score,
                "published_at": published_at
            })

        return pd.DataFrame(news_items)

    except Exception as e:
        logger.error(f"Error fetching from CryptoPanic: {e}")
        return pd.DataFrame()


@retry_on_failure(max_retries=2, delay=5)
def fetch_newsapi_crypto_news(query: str = "cryptocurrency") -> pd.DataFrame:
    """
    Fetches international crypto news and articles using NewsAPI.
    Ref: https://newsapi.org/

    Parameters
    ----------
    query : str, optional
        Search query keyword (defaults to 'cryptocurrency').

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame of articles with simulated sentiment scores, or empty.
    """
    api_key = Config.NEWS_API_KEY

    if is_placeholder(api_key):
        logger.info(
            "NewsAPI API key is placeholder (ADD_API_KEY_HERE). "
            "Skipping NewsAPI fetch. Please paste your key in the .env file to enable."
        )
        return pd.DataFrame()

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "apiKey": api_key,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20
    }

    logger.info(f"Fetching cryptocurrency articles from NewsAPI for query: '{query}'...")

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        # Save raw JSON response for archiving
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_raw_json(data, f"newsapi_raw_{timestamp}.json")

        articles = data.get("articles", [])
        if not articles:
            logger.info("No articles returned from NewsAPI.")
            return pd.DataFrame()

        news_items = []
        for article in articles:
            published_str = article.get("publishedAt")
            published_at = datetime.now(timezone.utc)
            if published_str:
                try:
                    published_at = pd.to_datetime(published_str).to_pydatetime()
                except Exception:
                    pass

            # Placeholder sentiment analysis using word occurrences
            title = article.get("title", "") or ""
            description = article.get("description", "") or ""
            text = (title + " " + description).lower()

            # Very simple dictionary-based sentiment scoring
            positive_words = ["bull", "surge", "gain", "profit", "adopt", "high", "growth", "rally", "success"]
            negative_words = ["bear", "crash", "fall", "loss", "ban", "low", "dip", "hack", "scam", "regulations"]

            pos_count = sum(1 for word in positive_words if word in text)
            neg_count = sum(1 for word in negative_words if word in text)

            score = 0.0
            total_words = pos_count + neg_count
            if total_words > 0:
                score = (pos_count - neg_count) / total_words

            # Identify coin in text
            coin_id = "general"
            for coin in Config.DEFAULT_COINS:
                if coin in text:
                    coin_id = coin
                    break

            news_items.append({
                "coin_id": coin_id,
                "source": article.get("source", {}).get("name", "NewsAPI"),
                "title": title,
                "url": article.get("url", ""),
                "sentiment_score": score,
                "published_at": published_at
            })

        return pd.DataFrame(news_items)

    except Exception as e:
        logger.error(f"Error fetching from NewsAPI: {e}")
        return pd.DataFrame()


def save_sentiment_to_db(df: pd.DataFrame) -> int:
    """
    Saves the processed sentiment/news records into the PostgreSQL database.
    """
    if df.empty:
        logger.warning("Empty DataFrame received for sentiment storage — skipping.")
        return 0

    session = get_session()
    records_saved = 0

    try:
        for _, row in df.iterrows():
            record = SentimentData(
                coin_id=row.get("coin_id", "general"),
                source=row.get("source", "Unknown"),
                title=row.get("title", ""),
                url=row.get("url", ""),
                sentiment_score=float(row.get("sentiment_score", 0.0)),
                published_at=row.get("published_at"),
                fetched_at=datetime.now(timezone.utc)
            )
            session.add(record)
            records_saved += 1

        session.commit()
        logger.info(f"✅ Successfully saved {records_saved} sentiment records to database.")

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to save sentiment data to database: {e}")
        records_saved = 0
    finally:
        session.close()

    return records_saved


def fetch_and_store_sentiment() -> pd.DataFrame:
    """
    Orchestration pipeline for fetching sentiment data from multiple sources
    and saving to the database. Handles graceful fallback when API keys are missing.
    """
    logger.info("=" * 60)
    logger.info("Starting Sentiment Data Collection Pipeline...")
    logger.info("=" * 60)

    # 1. Fetch from CryptoPanic
    cp_df = fetch_cryptopanic_news()

    # 2. Fetch from NewsAPI
    news_df = fetch_newsapi_crypto_news()

    # Combine dataframes
    all_dfs = []
    if not cp_df.empty:
        all_dfs.append(cp_df)
    if not news_df.empty:
        all_dfs.append(news_df)

    if not all_dfs:
        logger.info(
            "⚠️ No sentiment data fetched because API keys are configured as placeholders. "
            "Fill in CRYPTOPANIC_API_KEY or NEWS_API_KEY in your .env file to enable live feeds."
        )
        return pd.DataFrame()

    combined_df = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"Combined {len(combined_df)} sentiment items.")

    # Save to database
    save_sentiment_to_db(combined_df)

    return combined_df


if __name__ == "__main__":
    print("Running standalone sentiment fetcher test...")
    df = fetch_and_store_sentiment()
    if not df.empty:
        print(f"Fetched and stored {len(df)} sentiment rows:")
        print(df[["coin_id", "source", "sentiment_score", "title"]].head())
    else:
        print("\nPipeline finished: Gracefully degraded (no API keys configured or active).")
