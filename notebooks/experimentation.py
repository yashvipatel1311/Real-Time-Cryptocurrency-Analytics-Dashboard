# ============================================================================
# Experimentation Script — Crypto Analytics Platform
# ============================================================================
# This script is organized like a Jupyter notebook, with clearly marked
# "cells" that you can run individually or as a whole script.
#
# How to use:
#   Option 1: Run the entire script:  python notebooks/experimentation.py
#   Option 2: Copy-paste individual sections into a Jupyter notebook
#   Option 3: Run interactively in an IDE (VS Code, PyCharm)
#
# Each section is independent and can be run on its own after the
# "Setup and Imports" section.
# ============================================================================


# ============================================================================
# CELL 1: Setup and Imports
# ============================================================================
# This cell imports all necessary libraries and sets up the environment.
# Run this cell first before any other cells.
# ============================================================================

import os
import sys

# Add the project root directory to Python path so we can import our modules
# This is needed when running from the notebooks/ directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Standard library imports
from datetime import datetime, timedelta

# Data science imports
import pandas as pd
import numpy as np

# Visualization imports
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
    print("✅ Plotly loaded successfully")
except ImportError:
    PLOTLY_AVAILABLE = False
    print("⚠️ Plotly not installed. Run: pip install plotly")

# Project imports
try:
    from config.config import Config
    from api.fetch_crypto_data import fetch_live_prices
    from api.fetch_historical_data import fetch_and_store_historical
    from analytics.kpi_calculations import generate_kpi_summary
    from analytics.trend_analysis import generate_trend_report
    from analytics.volatility_analysis import calculate_risk_metrics
    from analytics.portfolio_analysis import (
        generate_portfolio_report,
        create_sample_portfolio,
    )
    PROJECT_AVAILABLE = True
    print("✅ Project modules loaded successfully")
except ImportError as e:
    PROJECT_AVAILABLE = False
    print(f"⚠️ Could not import project modules: {e}")
    print("   Make sure you're running from the project root directory")

print(f"\n📁 Project root: {project_root}")
print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)


# ============================================================================
# CELL 2: Fetch Sample Data
# ============================================================================
# This cell fetches live cryptocurrency prices from the CoinGecko API.
# It demonstrates how to use our API module and inspect the results.
# ============================================================================

print("\n" + "=" * 60)
print("📊 CELL 2: Fetching Sample Data")
print("=" * 60)

# Fetch live prices
live_df = None
if PROJECT_AVAILABLE:
    try:
        print("\n🔄 Fetching live prices from CoinGecko...")
        live_df = fetch_live_prices()

        if live_df is not None and len(live_df) > 0:
            print(f"✅ Fetched data for {len(live_df)} cryptocurrencies\n")

            # Display basic info about the DataFrame
            print("📋 DataFrame Info:")
            print(f"   Shape: {live_df.shape}")
            print(f"   Columns: {list(live_df.columns)}")
            print(f"   Memory: {live_df.memory_usage(deep=True).sum() / 1024:.1f} KB")

            # Show first 5 rows
            print("\n📄 First 5 rows:")
            print(live_df.head().to_string(index=False))

            # Show basic statistics
            if 'current_price' in live_df.columns:
                print("\n📊 Price Statistics:")
                print(live_df['current_price'].describe().to_string())
        else:
            print("⚠️ No data returned from API")
            print("   Creating sample data for experimentation...")

            # Create sample data for offline experimentation
            live_df = pd.DataFrame({
                'id': ['bitcoin', 'ethereum', 'solana', 'cardano', 'polkadot'],
                'symbol': ['btc', 'eth', 'sol', 'ada', 'dot'],
                'name': ['Bitcoin', 'Ethereum', 'Solana', 'Cardano', 'Polkadot'],
                'current_price': [67500.0, 3500.0, 150.0, 0.45, 7.5],
                'market_cap': [1.32e12, 4.2e11, 6.5e10, 1.6e10, 1.0e10],
                'total_volume': [2.85e10, 1.5e10, 3.2e9, 8.5e8, 4.2e8],
                'price_change_percentage_24h': [-2.35, 1.8, 5.2, -0.8, 3.1],
            })
            print("✅ Sample data created")

    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        print("   Creating sample data instead...")

        live_df = pd.DataFrame({
            'id': ['bitcoin', 'ethereum', 'solana', 'cardano', 'polkadot'],
            'symbol': ['btc', 'eth', 'sol', 'ada', 'dot'],
            'name': ['Bitcoin', 'Ethereum', 'Solana', 'Cardano', 'Polkadot'],
            'current_price': [67500.0, 3500.0, 150.0, 0.45, 7.5],
            'market_cap': [1.32e12, 4.2e11, 6.5e10, 1.6e10, 1.0e10],
            'total_volume': [2.85e10, 1.5e10, 3.2e9, 8.5e8, 4.2e8],
            'price_change_percentage_24h': [-2.35, 1.8, 5.2, -0.8, 3.1],
        })
else:
    # Create sample data when project modules are not available
    live_df = pd.DataFrame({
        'id': ['bitcoin', 'ethereum', 'solana', 'cardano', 'polkadot',
               'chainlink', 'avalanche', 'polygon', 'uniswap', 'litecoin'],
        'symbol': ['btc', 'eth', 'sol', 'ada', 'dot',
                    'link', 'avax', 'matic', 'uni', 'ltc'],
        'name': ['Bitcoin', 'Ethereum', 'Solana', 'Cardano', 'Polkadot',
                 'Chainlink', 'Avalanche', 'Polygon', 'Uniswap', 'Litecoin'],
        'current_price': [67500.0, 3500.0, 150.0, 0.45, 7.5,
                          15.0, 35.0, 0.85, 8.5, 80.0],
        'market_cap': [1.32e12, 4.2e11, 6.5e10, 1.6e10, 1.0e10,
                       8.5e9, 1.2e10, 7.5e9, 5.0e9, 6.0e9],
        'total_volume': [2.85e10, 1.5e10, 3.2e9, 8.5e8, 4.2e8,
                         6.5e8, 9.0e8, 5.5e8, 3.0e8, 4.0e8],
        'price_change_percentage_24h': [-2.35, 1.8, 5.2, -0.8, 3.1,
                                         -1.5, 4.0, 2.3, -3.0, 1.2],
    })
    print("📦 Using sample data (project modules not available)")


# ============================================================================
# CELL 3: Basic Analysis
# ============================================================================
# This cell performs basic exploratory data analysis (EDA) on the
# cryptocurrency data. Good for understanding the dataset structure.
# ============================================================================

print("\n" + "=" * 60)
print("🧮 CELL 3: Basic Analysis")
print("=" * 60)

if live_df is not None and len(live_df) > 0:
    # -------------------------------------------------------------------
    # 3.1 Top coins by price
    # -------------------------------------------------------------------
    print("\n🏆 Top 5 Coins by Price:")
    if 'current_price' in live_df.columns:
        top_by_price = live_df.nlargest(5, 'current_price')
        for i, (_, row) in enumerate(top_by_price.iterrows(), 1):
            name = row.get('name', row.get('id', 'N/A'))
            price = row['current_price']
            print(f"   {i}. {name:<15} ${price:>12,.2f}")

    # -------------------------------------------------------------------
    # 3.2 Top coins by market cap
    # -------------------------------------------------------------------
    print("\n📊 Top 5 Coins by Market Cap:")
    if 'market_cap' in live_df.columns:
        top_by_mcap = live_df.nlargest(5, 'market_cap')
        for i, (_, row) in enumerate(top_by_mcap.iterrows(), 1):
            name = row.get('name', row.get('id', 'N/A'))
            mcap = row['market_cap']
            print(f"   {i}. {name:<15} ${mcap:>15,.0f}")

    # -------------------------------------------------------------------
    # 3.3 Biggest gainers and losers
    # -------------------------------------------------------------------
    if 'price_change_percentage_24h' in live_df.columns:
        valid_changes = live_df.dropna(subset=['price_change_percentage_24h'])

        if len(valid_changes) > 0:
            print("\n📈 Biggest Gainers (24h):")
            gainers = valid_changes.nlargest(3, 'price_change_percentage_24h')
            for _, row in gainers.iterrows():
                name = row.get('name', row.get('id', 'N/A'))
                change = row['price_change_percentage_24h']
                print(f"   🟢 {name:<15} {change:+.2f}%")

            print("\n📉 Biggest Losers (24h):")
            losers = valid_changes.nsmallest(3, 'price_change_percentage_24h')
            for _, row in losers.iterrows():
                name = row.get('name', row.get('id', 'N/A'))
                change = row['price_change_percentage_24h']
                print(f"   🔴 {name:<15} {change:+.2f}%")

    # -------------------------------------------------------------------
    # 3.4 Summary statistics
    # -------------------------------------------------------------------
    print("\n📊 Summary Statistics:")
    numeric_cols = live_df.select_dtypes(include=[np.number])
    print(numeric_cols.describe().to_string())

    # -------------------------------------------------------------------
    # 3.5 Correlation analysis
    # -------------------------------------------------------------------
    if len(numeric_cols.columns) > 1:
        print("\n🔗 Correlation Matrix:")
        corr = numeric_cols.corr()
        print(corr.round(3).to_string())

    # -------------------------------------------------------------------
    # 3.6 Try running analytics modules
    # -------------------------------------------------------------------
    if PROJECT_AVAILABLE:
        print("\n🧮 Running Analytics Modules:")
        try:
            kpi = generate_kpi_summary(live_df)
            print("   ✅ KPI Summary generated")
            if isinstance(kpi, pd.DataFrame):
                print(kpi.to_string(index=False))
        except Exception as e:
            print(f"   ⚠️ KPI generation: {e}")

        try:
            risk = calculate_risk_metrics(live_df)
            print("   ✅ Risk metrics calculated")
        except Exception as e:
            print(f"   ⚠️ Risk metrics: {e}")

else:
    print("⚠️ No data available for analysis")


# ============================================================================
# CELL 4: Visualization with Plotly
# ============================================================================
# This cell creates interactive charts using Plotly.
# Charts are saved as HTML files that can be opened in any browser.
# ============================================================================

print("\n" + "=" * 60)
print("📊 CELL 4: Visualization")
print("=" * 60)

if PLOTLY_AVAILABLE and live_df is not None and len(live_df) > 0:
    # Create output directory for charts
    charts_dir = os.path.join(project_root, "data", "charts")
    os.makedirs(charts_dir, exist_ok=True)

    name_col = 'name' if 'name' in live_df.columns else 'id'

    # -------------------------------------------------------------------
    # 4.1 Price Bar Chart
    # -------------------------------------------------------------------
    if 'current_price' in live_df.columns:
        print("\n📊 Creating price bar chart...")

        fig_price = px.bar(
            live_df.nlargest(10, 'current_price'),
            x=name_col,
            y='current_price',
            color='current_price',
            color_continuous_scale='Viridis',
            title='Top 10 Cryptocurrencies by Price (USD)',
            labels={name_col: 'Coin', 'current_price': 'Price (USD)'},
        )
        fig_price.update_layout(template='plotly_dark', xaxis_tickangle=-45)

        chart_path = os.path.join(charts_dir, "price_chart.html")
        fig_price.write_html(chart_path)
        print(f"   ✅ Saved: {chart_path}")

    # -------------------------------------------------------------------
    # 4.2 Market Cap Treemap
    # -------------------------------------------------------------------
    if 'market_cap' in live_df.columns:
        print("📊 Creating market cap treemap...")

        fig_treemap = px.treemap(
            live_df[live_df['market_cap'] > 0],
            path=[name_col],
            values='market_cap',
            title='Market Capitalization Treemap',
            color='market_cap',
            color_continuous_scale='Blues',
        )
        fig_treemap.update_layout(template='plotly_dark')

        chart_path = os.path.join(charts_dir, "market_cap_treemap.html")
        fig_treemap.write_html(chart_path)
        print(f"   ✅ Saved: {chart_path}")

    # -------------------------------------------------------------------
    # 4.3 24h Change Waterfall Chart
    # -------------------------------------------------------------------
    if 'price_change_percentage_24h' in live_df.columns:
        print("📊 Creating 24h change chart...")

        change_df = live_df.dropna(subset=['price_change_percentage_24h']).head(15)
        colors = ['#00d4aa' if x >= 0 else '#ff4757'
                  for x in change_df['price_change_percentage_24h']]

        fig_change = go.Figure(data=[
            go.Bar(
                x=change_df[name_col],
                y=change_df['price_change_percentage_24h'],
                marker_color=colors,
                text=[f"{x:+.2f}%" for x in change_df['price_change_percentage_24h']],
                textposition='outside',
            )
        ])
        fig_change.update_layout(
            title='24-Hour Price Changes (%)',
            template='plotly_dark',
            xaxis_tickangle=-45,
            yaxis_title='Change (%)',
        )

        chart_path = os.path.join(charts_dir, "price_changes_24h.html")
        fig_change.write_html(chart_path)
        print(f"   ✅ Saved: {chart_path}")

    # -------------------------------------------------------------------
    # 4.4 Volume vs Market Cap Scatter
    # -------------------------------------------------------------------
    if 'total_volume' in live_df.columns and 'market_cap' in live_df.columns:
        print("📊 Creating volume vs market cap scatter...")

        fig_scatter = px.scatter(
            live_df,
            x='market_cap',
            y='total_volume',
            size='current_price' if 'current_price' in live_df.columns else None,
            color='price_change_percentage_24h' if 'price_change_percentage_24h' in live_df.columns else None,
            hover_name=name_col,
            title='Trading Volume vs Market Cap',
            labels={
                'market_cap': 'Market Cap (USD)',
                'total_volume': '24h Volume (USD)',
            },
            color_continuous_scale='RdYlGn',
        )
        fig_scatter.update_layout(template='plotly_dark')

        chart_path = os.path.join(charts_dir, "volume_vs_mcap.html")
        fig_scatter.write_html(chart_path)
        print(f"   ✅ Saved: {chart_path}")

    print(f"\n📁 All charts saved to: {charts_dir}")

else:
    if not PLOTLY_AVAILABLE:
        print("⚠️ Plotly is not installed. Install with: pip install plotly")
    else:
        print("⚠️ No data available for visualization")


# ============================================================================
# CELL 5: Export Results
# ============================================================================
# This cell exports analysis results to CSV and JSON files for further
# use in Power BI, Excel, or other tools.
# ============================================================================

print("\n" + "=" * 60)
print("📁 CELL 5: Export Results")
print("=" * 60)

if live_df is not None and len(live_df) > 0:
    # Create exports directory
    exports_dir = os.path.join(project_root, "data", "exports")
    os.makedirs(exports_dir, exist_ok=True)

    # -------------------------------------------------------------------
    # 5.1 Export live prices to CSV
    # -------------------------------------------------------------------
    csv_path = os.path.join(exports_dir, "experiment_live_prices.csv")
    live_df.to_csv(csv_path, index=False)
    print(f"   ✅ Live prices: {csv_path}")

    # -------------------------------------------------------------------
    # 5.2 Export summary statistics to CSV
    # -------------------------------------------------------------------
    numeric_df = live_df.select_dtypes(include=[np.number])
    if len(numeric_df.columns) > 0:
        stats_path = os.path.join(exports_dir, "experiment_statistics.csv")
        numeric_df.describe().to_csv(stats_path)
        print(f"   ✅ Statistics:   {stats_path}")

    # -------------------------------------------------------------------
    # 5.3 Export to JSON (for web applications)
    # -------------------------------------------------------------------
    json_path = os.path.join(exports_dir, "experiment_live_prices.json")
    live_df.to_json(json_path, orient='records', indent=2)
    print(f"   ✅ JSON export:  {json_path}")

    # -------------------------------------------------------------------
    # 5.4 Export gainers and losers
    # -------------------------------------------------------------------
    if 'price_change_percentage_24h' in live_df.columns:
        valid = live_df.dropna(subset=['price_change_percentage_24h'])
        if len(valid) > 0:
            gainers = valid.nlargest(5, 'price_change_percentage_24h')
            losers = valid.nsmallest(5, 'price_change_percentage_24h')

            gainers_path = os.path.join(exports_dir, "experiment_top_gainers.csv")
            gainers.to_csv(gainers_path, index=False)
            print(f"   ✅ Top gainers:  {gainers_path}")

            losers_path = os.path.join(exports_dir, "experiment_top_losers.csv")
            losers.to_csv(losers_path, index=False)
            print(f"   ✅ Top losers:   {losers_path}")

    print(f"\n📁 All exports saved to: {exports_dir}")

else:
    print("⚠️ No data to export")


# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 60)
print("✅ Experimentation Complete!")
print("=" * 60)
print(f"""
Next Steps:
  1. Run the full pipeline:     python main.py
  2. Start the scheduler:       python main.py --scheduler
  3. Launch the dashboard:      streamlit run app.py
  4. Run tests:                 pytest tests/ -v

Files created during this experiment:
  - data/exports/experiment_*.csv    (analysis exports)
  - data/charts/*.html               (interactive charts)
""")
