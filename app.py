# ============================================================================
# Streamlit Dashboard — Crypto Analytics Platform
# ============================================================================
# A minimal but functional Streamlit web app that displays cryptocurrency
# analytics data. This serves as a placeholder for future dashboard
# development and provides a quick way to visualize data.
#
# Usage:
#   streamlit run app.py
#
# Prerequisites:
#   pip install streamlit plotly pandas
#
# Note: Run 'python main.py' first to populate data!
# ============================================================================

import os
import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------------------------
# Try to import plotly for charts (graceful fallback if not installed)
# ---------------------------------------------------------------------------
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ---------------------------------------------------------------------------
# Try to import project modules (graceful fallback if DB not configured)
# ---------------------------------------------------------------------------
try:
    from config.config import Config
    from database.db_connection import get_session, test_connection
    from database.create_tables import LiveCryptoPrice
    PROJECT_AVAILABLE = True
except ImportError:
    PROJECT_AVAILABLE = False


# ============================================================================
# PAGE CONFIGURATION — Must be the first Streamlit command
# ============================================================================
st.set_page_config(
    page_title="🪙 Crypto Analytics Dashboard",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# HELPER: Load live prices from database or CSV fallback
# ============================================================================
@st.cache_data(ttl=60)  # Cache for 60 seconds to avoid repeated DB queries
def load_live_prices():
    """
    Attempts to load live cryptocurrency prices from the database.
    Falls back to the CSV export file if the database is not available.

    Returns:
        pd.DataFrame or None: Live price data, or None if no data found
    """
    # -------------------------------------------------------------------
    # Try 1: Load from PostgreSQL database
    # -------------------------------------------------------------------
    if PROJECT_AVAILABLE:
        try:
            if test_connection():
                session = get_session()
                try:
                    # Query the latest price for each coin
                    records = session.query(LiveCryptoPrice).all()
                    if records:
                        data = []
                        for r in records:
                            data.append({
                                'coin_id': r.coin_id,
                                'symbol': r.symbol,
                                'name': r.name,
                                'current_price': r.current_price,
                                'market_cap': r.market_cap,
                                'total_volume': r.total_volume,
                                'price_change_percentage_24h': r.price_change_percentage_24h,
                                'last_updated': r.last_updated,
                            })
                        return pd.DataFrame(data)
                finally:
                    session.close()
        except Exception:
            pass  # Fall through to CSV fallback

    # -------------------------------------------------------------------
    # Try 2: Load from CSV export file
    # -------------------------------------------------------------------
    csv_paths = [
        os.path.join("data", "exports", "live_prices.csv"),
        os.path.join("data", "live_prices.csv"),
        "live_prices.csv",
    ]

    for csv_path in csv_paths:
        if os.path.exists(csv_path):
            try:
                return pd.read_csv(csv_path)
            except Exception:
                continue

    # No data found
    return None


@st.cache_data(ttl=60)
def load_kpi_report():
    """Loads the KPI report CSV if available."""
    csv_paths = [
        os.path.join("data", "exports", "kpi_report.csv"),
        "kpi_report.csv",
    ]
    for path in csv_paths:
        if os.path.exists(path):
            try:
                return pd.read_csv(path)
            except Exception:
                continue
    return None


# ============================================================================
# SIDEBAR — Navigation and Controls
# ============================================================================
with st.sidebar:
    st.title("🪙 Crypto Analytics")
    st.markdown("---")

    # Refresh button — clears the cache and reloads data
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    # Information section
    st.markdown("### ℹ️ Info")
    st.markdown(
        """
        This dashboard displays cryptocurrency
        analytics data from the platform.

        **Data Sources:**
        - CoinGecko API (live prices)
        - PostgreSQL (stored data)
        - CSV exports (fallback)

        **Quick Start:**
        ```bash
        python main.py
        ```
        """
    )

    st.markdown("---")

    # Display data freshness
    st.markdown("### 📡 Data Status")
    df = load_live_prices()
    if df is not None and 'last_updated' in df.columns:
        try:
            latest = pd.to_datetime(df['last_updated']).max()
            st.success(f"Last update: {latest}")
        except Exception:
            st.info("Data available")
    elif df is not None:
        st.info(f"Data loaded: {len(df)} coins")
    else:
        st.warning("No data available")

    st.markdown("---")
    st.caption(f"v1.0.0 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# ============================================================================
# MAIN CONTENT AREA
# ============================================================================

# Title and description
st.title("🪙 Real-Time Crypto Analytics Dashboard")
st.markdown(
    "Monitor cryptocurrency prices, market trends, and portfolio performance "
    "with real-time data from CoinGecko."
)

# Load data
prices_df = load_live_prices()
kpi_df = load_kpi_report()


# ============================================================================
# SECTION 1: KPI Metrics Row
# ============================================================================
if prices_df is not None and len(prices_df) > 0:
    st.markdown("---")
    st.subheader("📊 Market Overview")

    # Create KPI metric cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_coins = len(prices_df)
        st.metric("Total Coins Tracked", total_coins)

    with col2:
        if 'market_cap' in prices_df.columns:
            total_mcap = prices_df['market_cap'].sum()
            st.metric(
                "Total Market Cap",
                f"${total_mcap:,.0f}" if total_mcap > 0 else "N/A"
            )
        else:
            st.metric("Total Market Cap", "N/A")

    with col3:
        if 'total_volume' in prices_df.columns:
            total_vol = prices_df['total_volume'].sum()
            st.metric(
                "24h Volume",
                f"${total_vol:,.0f}" if total_vol > 0 else "N/A"
            )
        else:
            st.metric("24h Volume", "N/A")

    with col4:
        if 'price_change_percentage_24h' in prices_df.columns:
            avg_change = prices_df['price_change_percentage_24h'].mean()
            st.metric(
                "Avg 24h Change",
                f"{avg_change:+.2f}%",
                delta=f"{avg_change:+.2f}%"
            )
        else:
            st.metric("Avg 24h Change", "N/A")

    # ========================================================================
    # SECTION 2: Price Table
    # ========================================================================
    st.markdown("---")
    st.subheader("💰 Live Cryptocurrency Prices")

    # Format the DataFrame for display
    display_df = prices_df.copy()

    # Select and rename columns for cleaner display
    display_columns = {}
    column_mapping = {
        'name': 'Coin',
        'symbol': 'Symbol',
        'current_price': 'Price (USD)',
        'market_cap': 'Market Cap',
        'total_volume': '24h Volume',
        'price_change_percentage_24h': '24h Change (%)',
    }

    for col, label in column_mapping.items():
        if col in display_df.columns:
            display_columns[col] = label

    if display_columns:
        display_df = display_df[list(display_columns.keys())].rename(
            columns=display_columns
        )

    # Display the table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================================
    # SECTION 3: Price Chart
    # ========================================================================
    if PLOTLY_AVAILABLE and 'current_price' in prices_df.columns:
        st.markdown("---")
        st.subheader("📈 Price Comparison Chart")

        # Get the column for coin names
        name_col = 'name' if 'name' in prices_df.columns else 'coin_id'

        # Create a bar chart of current prices
        chart_df = prices_df.nlargest(10, 'current_price')

        fig = px.bar(
            chart_df,
            x=name_col,
            y='current_price',
            color='current_price',
            color_continuous_scale='Viridis',
            title='Top 10 Cryptocurrencies by Price',
            labels={
                name_col: 'Cryptocurrency',
                'current_price': 'Price (USD)',
            },
        )

        fig.update_layout(
            template='plotly_dark',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff'),
            xaxis_tickangle=-45,
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True)

        # ====================================================================
        # Market Cap Pie Chart
        # ====================================================================
        if 'market_cap' in prices_df.columns:
            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader("🥧 Market Cap Distribution")
                top_mcap = prices_df.nlargest(8, 'market_cap')

                fig_pie = px.pie(
                    top_mcap,
                    values='market_cap',
                    names=name_col,
                    title='Market Cap Share (Top 8)',
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )
                fig_pie.update_layout(
                    template='plotly_dark',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_right:
                st.subheader("📊 24h Price Changes")
                if 'price_change_percentage_24h' in prices_df.columns:
                    change_df = prices_df.dropna(
                        subset=['price_change_percentage_24h']
                    ).head(15)

                    colors = [
                        '#00d4aa' if x >= 0 else '#ff4757'
                        for x in change_df['price_change_percentage_24h']
                    ]

                    fig_change = go.Figure(data=[
                        go.Bar(
                            x=change_df[name_col],
                            y=change_df['price_change_percentage_24h'],
                            marker_color=colors,
                        )
                    ])

                    fig_change.update_layout(
                        title='24h Price Change (%)',
                        template='plotly_dark',
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        xaxis_tickangle=-45,
                        yaxis_title='Change (%)',
                    )
                    st.plotly_chart(fig_change, use_container_width=True)

    # ========================================================================
    # SECTION 4: KPI Report
    # ========================================================================
    if kpi_df is not None:
        st.markdown("---")
        st.subheader("🧮 KPI Analytics Report")
        st.dataframe(kpi_df, use_container_width=True, hide_index=True)

    # ========================================================================
    # Raw Data Download
    # ========================================================================
    st.markdown("---")
    st.subheader("📥 Download Data")

    col_dl1, col_dl2 = st.columns(2)

    with col_dl1:
        csv_data = prices_df.to_csv(index=False)
        st.download_button(
            label="📄 Download Live Prices CSV",
            data=csv_data,
            file_name="crypto_live_prices.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_dl2:
        if kpi_df is not None:
            kpi_csv = kpi_df.to_csv(index=False)
            st.download_button(
                label="📄 Download KPI Report CSV",
                data=kpi_csv,
                file_name="crypto_kpi_report.csv",
                mime="text/csv",
                use_container_width=True,
            )

else:
    # ========================================================================
    # NO DATA AVAILABLE — Show instructions
    # ========================================================================
    st.markdown("---")

    st.warning("⚠️ No cryptocurrency data available yet!")

    st.markdown(
        """
        ### 🚀 Getting Started

        To populate the dashboard with data, run the main pipeline first:

        ```bash
        # Run the full pipeline once
        python main.py

        # Or start the auto-fetch scheduler
        python main.py --scheduler
        ```

        ### What this will do:
        1. 📥 Fetch live prices from CoinGecko API
        2. 📊 Fetch historical data for trend analysis
        3. 🧮 Run analytics (KPI, trends, volatility)
        4. 📁 Export reports as CSV files

        Once data is available, this dashboard will automatically display:
        - **Live price table** with all tracked coins
        - **Interactive charts** with Plotly
        - **KPI metrics** and market overview
        - **Downloadable CSV** exports

        ### Prerequisites:
        ```bash
        pip install -r requirements.txt
        ```
        """
    )

    # Quick status check
    st.markdown("---")
    st.subheader("🔍 System Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        if PROJECT_AVAILABLE:
            st.success("✅ Project modules loaded")
        else:
            st.error("❌ Project modules not found")

    with col2:
        if PLOTLY_AVAILABLE:
            st.success("✅ Plotly available")
        else:
            st.warning("⚠️ Plotly not installed")

    with col3:
        if PROJECT_AVAILABLE:
            try:
                if test_connection():
                    st.success("✅ Database connected")
                else:
                    st.warning("⚠️ Database not connected")
            except Exception:
                st.warning("⚠️ Database check failed")
        else:
            st.info("ℹ️ Database not configured")


# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        🪙 Crypto Analytics Platform v1.0.0 | 
        Data from <a href='https://www.coingecko.com/'>CoinGecko</a> | 
        Built with Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
