<!-- ====================================================================== -->
<!-- README.md — Real-Time Cryptocurrency Analytics Platform                -->
<!-- ====================================================================== -->

<div align="center">

# 🪙 Real-Time Cryptocurrency Analytics Platform

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=for-the-badge&logo=pandas&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)

**A production-grade, modular, and scalable cryptocurrency analytics platform**

*Automated data ingestion • Statistical analytics • Power BI-ready exports*

[Getting Started](#-installation-steps) •
[Features](#-features) •
[Architecture](#-architecture) •
[Documentation](#-how-to-run-the-project)

</div>

---

## 📋 1. Project Overview

The **Real-Time Cryptocurrency Analytics Platform** is a Python-based data pipeline that:

- 📥 **Fetches** live and historical cryptocurrency data from CoinGecko API
- 💾 **Stores** data in a PostgreSQL relational database
- 🧮 **Analyzes** market trends, volatility, KPIs, and portfolio performance
- 📊 **Exports** cleaned datasets as CSV files ready for Power BI visualization
- ⏰ **Automates** data collection with a configurable scheduler

### Who is this for?

| Audience | Use Case |
|----------|----------|
| 📚 **Students** | Learn data engineering, ETL pipelines, and analytics |
| 📊 **Data Analysts** | Build Power BI dashboards from real crypto data |
| 💼 **Portfolio Managers** | Track and analyze cryptocurrency portfolios |
| 🐍 **Python Developers** | Reference implementation for API + DB + Analytics pipeline |

---

## 🏗️ 2. Architecture

The platform follows a modular ETL (Extract, Transform, Load) architecture:

```mermaid
graph LR
    A["🌐 CoinGecko API"] --> B["📥 Data Fetchers"]
    B --> C["🐘 PostgreSQL Database"]
    C --> D["🧮 Analytics Engine"]
    D --> E["📁 CSV Exports"]
    E --> F["📊 Power BI Dashboards"]

    subgraph "Data Fetchers"
        B1["fetch_crypto_data.py"]
        B2["fetch_historical_data.py"]
        B3["fetch_sentiment.py"]
    end

    subgraph "Analytics Engine"
        D1["KPI Calculations"]
        D2["Trend Analysis"]
        D3["Volatility Analysis"]
        D4["Portfolio Analysis"]
    end

    subgraph "Automation"
        G["⏰ APScheduler"] --> B
    end

    B --> B1
    B --> B2
    B --> B3
    D --> D1
    D --> D2
    D --> D3
    D --> D4

    style A fill:#f9a825,stroke:#f57f17,color:#000
    style C fill:#1565c0,stroke:#0d47a1,color:#fff
    style F fill:#43a047,stroke:#2e7d32,color:#fff
```

### Data Flow

```
CoinGecko API  →  Python Fetchers  →  PostgreSQL  →  Analytics  →  CSV/Power BI
     ↑                                                                    ↓
     └──────────────── APScheduler (auto-fetch every N minutes) ──────────┘
```

---

## ✅ 3. Features

| # | Feature | Status |
|---|---------|--------|
| 1 | ✅ Live cryptocurrency price fetching | Implemented |
| 2 | ✅ Historical price data collection | Implemented |
| 3 | ✅ Market sentiment analysis | Implemented |
| 4 | ✅ PostgreSQL database storage | Implemented |
| 5 | ✅ SQLAlchemy ORM models | Implemented |
| 6 | ✅ Automated data fetching (APScheduler) | Implemented |
| 7 | ✅ KPI summary calculations | Implemented |
| 8 | ✅ Trend analysis with moving averages | Implemented |
| 9 | ✅ Volatility & risk metrics | Implemented |
| 10 | ✅ Portfolio performance tracking | Implemented |
| 11 | ✅ CSV export for Power BI | Implemented |
| 12 | ✅ Environment-based configuration | Implemented |
| 13 | ✅ Structured logging | Implemented |
| 14 | ✅ CLI entry point with argparse | Implemented |
| 15 | ✅ Streamlit dashboard (basic) | Implemented |
| 16 | ✅ Comprehensive test suite | Implemented |
| 17 | ✅ Error handling & graceful degradation | Implemented |
| 18 | ✅ Secure credential management (.env) | Implemented |
| 19 | ✅ Beginner-friendly documentation | Implemented |

---

## 🛠️ 4. Tech Stack

| Technology | Purpose | Version |
|-----------|---------|---------|
| 🐍 **Python** | Core programming language | 3.9+ |
| 🐼 **Pandas** | Data manipulation & analysis | 2.0+ |
| 🗄️ **SQLAlchemy** | ORM & database toolkit | 2.0+ |
| 🐘 **PostgreSQL** | Relational database | 15+ |
| 🌐 **Requests** | HTTP API calls | 2.28+ |
| ⏰ **APScheduler** | Background job scheduling | 3.10+ |
| 📊 **Plotly** | Interactive visualizations | 5.0+ |
| 🖥️ **Streamlit** | Web dashboard framework | 1.28+ |
| 🧪 **Pytest** | Testing framework | 7.0+ |
| 🔐 **python-dotenv** | Environment variable management | 1.0+ |

---

## 📂 5. Folder Structure

```
Crypto Analytics Dashboard/
│
├── 📁 config/                  # Configuration & environment settings
│   ├── __init__.py
│   └── config.py               # Config class (reads .env variables)
│
├── 📁 utils/                   # Utility functions
│   ├── __init__.py
│   └── logger.py               # Centralized logging setup
│
├── 📁 database/                # Database layer
│   ├── __init__.py
│   ├── db_connection.py        # Engine, session, connection testing
│   └── create_tables.py        # ORM models & table creation
│
├── 📁 api/                     # External API integration
│   ├── __init__.py
│   ├── fetch_crypto_data.py    # Live price fetching (CoinGecko)
│   ├── fetch_historical_data.py # Historical price data
│   └── fetch_sentiment.py      # Market sentiment data
│
├── 📁 analytics/               # Data analysis modules
│   ├── __init__.py
│   ├── kpi_calculations.py     # KPI summary metrics
│   ├── trend_analysis.py       # Trend detection & moving averages
│   ├── volatility_analysis.py  # Risk & volatility metrics
│   └── portfolio_analysis.py   # Portfolio performance tracking
│
├── 📁 scheduler/               # Automated data collection
│   ├── __init__.py
│   └── auto_fetch_scheduler.py # APScheduler background jobs
│
├── 📁 tests/                   # Test suite
│   ├── __init__.py
│   ├── test_api.py             # API connectivity & data tests
│   └── test_database.py        # Database CRUD tests
│
├── 📁 notebooks/               # Experimentation scripts
│   └── experimentation.py      # Notebook-style analysis script
│
├── 📁 data/                    # Data storage (auto-created)
│   ├── exports/                # CSV exports for Power BI
│   └── charts/                 # Plotly HTML charts
│
├── 📄 main.py                  # CLI entry point (run this!)
├── 📄 app.py                   # Streamlit web dashboard
├── 📄 requirements.txt         # Python dependencies
├── 📄 .env                     # Environment variables (DO NOT COMMIT)
├── 📄 .gitignore               # Git ignore rules
└── 📄 README.md                # This file
```

---

## 🚀 6. Installation Steps

### Prerequisites

- **Python 3.9+** — [Download Python](https://www.python.org/downloads/)
- **PostgreSQL 15+** — [Download PostgreSQL](https://www.postgresql.org/download/)
- **Git** — [Download Git](https://git-scm.com/downloads)

### Step-by-Step Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/crypto-analytics-platform.git
cd crypto-analytics-platform

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Copy the environment template and configure
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux

# 6. Edit .env with your database credentials (see Section 8)

# 7. Create the PostgreSQL database (see Section 7)

# 8. Run the platform!
python main.py
```

---

## 🐘 7. How to Create PostgreSQL Database

### Option A: Using pgAdmin (GUI)

1. Open **pgAdmin**
2. Right-click on **Databases** → **Create** → **Database**
3. Enter name: `crypto_analytics`
4. Click **Save**

### Option B: Using psql (Command Line)

```sql
-- Connect to PostgreSQL as the default user
psql -U postgres

-- Create a new database
CREATE DATABASE crypto_analytics;

-- Create a dedicated user (recommended)
CREATE USER crypto_user WITH PASSWORD 'your_secure_password';

-- Grant all privileges on the database to the user
GRANT ALL PRIVILEGES ON DATABASE crypto_analytics TO crypto_user;

-- Connect to the new database
\c crypto_analytics

-- Verify the connection
\conninfo

-- Exit psql
\q
```

### Option C: One-liner

```bash
createdb -U postgres crypto_analytics
```

### Option D: SQLite Fallback (Zero Setup)

If you don't have PostgreSQL installed or want a quick setup without a database server, you can use SQLite.
Simply configure `DATABASE_URL` in your `.env` file as:
```env
DATABASE_URL=sqlite:///crypto_analytics.db
```
This will automatically create a local `crypto_analytics.db` file in your project root on the first run.

> **📝 Note:** Tables are created automatically when you run the platform for the first time. You don't need to create tables manually!

---

## 🔑 8. Where to Add API Keys

All sensitive configuration is stored in the `.env` file in the project root.

```
📂 Project Root/
└── 📄 .env          ← Your API keys go HERE (line 3-4)
```

**Important:** The `.env` file is listed in `.gitignore` and will **never** be committed to version control.

### Getting a CoinGecko API Key

1. Visit [CoinGecko API](https://www.coingecko.com/en/api)
2. Sign up for a **free** account
3. Navigate to **API Keys** in your dashboard
4. Generate a new API key
5. Copy it to your `.env` file

> **💡 Free Tier:** CoinGecko's free API works without an API key (with rate limits). An API key is optional but recommended for higher rate limits.

---

## ⚙️ 9. How to Configure .env

Create a `.env` file in the project root with the following variables:

```env
# ============================================
# DATABASE CONFIGURATION
# ============================================
# Format (PostgreSQL): postgresql://username:password@host:port/database_name
# Format (SQLite):     sqlite:///crypto_analytics.db
DATABASE_URL=sqlite:///crypto_analytics.db

# ============================================
# API CONFIGURATION
# ============================================
# CoinGecko API key (optional for free tier, recommended for higher limits)
# Get yours at: https://www.coingecko.com/en/api
COINGECKO_API_KEY=your_api_key_here

# ============================================
# DATA FETCHING SETTINGS
# ============================================
# How often to fetch live prices (in minutes)
# Recommended: 5 for free tier, 1 for paid tier
FETCH_INTERVAL_MINUTES=5

# Coins to track (comma-separated CoinGecko IDs)
# Find IDs at: https://api.coingecko.com/api/v3/coins/list
DEFAULT_COINS=bitcoin,ethereum,solana,cardano,polkadot,chainlink,avalanche-2,polygon-ecosystem-token,uniswap,litecoin

# Currency for price conversion
DEFAULT_CURRENCY=usd

# ============================================
# EXPORT SETTINGS
# ============================================
# Directory for CSV exports (relative to project root)
DATA_EXPORTS_DIR=data/exports
```

### Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ Yes | — | PostgreSQL connection string |
| `COINGECKO_API_KEY` | ❌ No | — | API key for higher rate limits |
| `FETCH_INTERVAL_MINUTES` | ❌ No | `5` | Live price fetch frequency |
| `DEFAULT_COINS` | ❌ No | 10 coins | Comma-separated coin IDs |
| `DEFAULT_CURRENCY` | ❌ No | `usd` | Price conversion currency |
| `DATA_EXPORTS_DIR` | ❌ No | `data/exports` | CSV output directory |

---

## ▶️ 10. How to Run the Project

### Quick Start

```bash
# Run the full pipeline once (fetch → analyze → export)
python main.py
```

> **💡 Windows Console Unicode Tip:** If you encounter encoding errors (e.g., `UnicodeEncodeError: 'charmap' codec can't encode character...`) when running scripts on Windows, set the terminal output encoding to UTF-8 before running:
>
> **In PowerShell:**
> ```powershell
> $env:PYTHONIOENCODING="utf-8"
> python main.py
> ```
>
> **In Command Prompt:**
> ```cmd
> set PYTHONIOENCODING=utf-8
> python main.py
> ```

### All Run Modes

| Command | Description |
|---------|-------------|
| `python main.py` | Run the complete pipeline once |
| `python main.py --fetch` | Only fetch data from APIs |
| `python main.py --analyze` | Only run analytics on existing data |
| `python main.py --export` | Only export reports to CSV |
| `python main.py --all` | Same as running without arguments |
| `python main.py --scheduler` | Start continuous auto-fetch |
| `python main.py --test` | Run the test suite |

### Running the Streamlit Dashboard

```bash
streamlit run app.py
```

This opens a web browser with the interactive dashboard at `http://localhost:8501`.

### Running the Experimentation Script

```bash
python notebooks/experimentation.py
```

---

## ⏰ 11. How to Run the Scheduler

The auto-fetch scheduler uses **APScheduler** to periodically collect data:

```bash
# Start the scheduler (runs until you press Ctrl+C)
python main.py --scheduler

# Or run the scheduler module directly
python scheduler/auto_fetch_scheduler.py
```

### What the Scheduler Does

| Job | Frequency | Description |
|-----|-----------|-------------|
| 📈 Live Prices | Every 5 min* | Fetches current prices for all coins |
| 📊 Historical Data | Every 60 min | Fetches 30-day price history |
| 💬 Sentiment | Every 30 min | Fetches market sentiment data |

*\* Configurable via `FETCH_INTERVAL_MINUTES` in `.env`*

### Scheduler Console Output

```
══════════════════════════════════════════════════════════
  🚀 Crypto Analytics — Auto-Fetch Scheduler
  Starting background data collection...
══════════════════════════════════════════════════════════

📌 Added job: Live Price Fetch (every 5 minutes)
📌 Added job: Historical Data Fetch (every 60 minutes)
📌 Added job: Sentiment Data Fetch (every 30 minutes)

✅ Auto-Fetch Scheduler is now RUNNING!
📋 Active jobs: 3
💡 Press Ctrl+C to stop the scheduler gracefully.
```

---

## 📊 12. How to Export Power BI Data

### CSV Export Location

All CSV files are exported to the `data/exports/` directory:

```
data/exports/
├── live_prices.csv          # Current prices for all tracked coins
├── kpi_report.csv           # KPI summary metrics
├── trend_report.csv         # Trend analysis with moving averages
├── volatility_report.csv    # Risk & volatility metrics
└── portfolio_report.csv     # Portfolio performance data
```

### Importing into Power BI

1. Open **Power BI Desktop**
2. Click **Get Data** → **Text/CSV**
3. Navigate to the `data/exports/` folder
4. Select the CSV file(s) to import
5. Click **Load** to import the data
6. Build your visualizations!

### Recommended Power BI Visualizations

| CSV File | Suggested Chart |
|----------|----------------|
| `live_prices.csv` | Card visuals, bar charts, tables |
| `kpi_report.csv` | KPI cards, gauge charts |
| `trend_report.csv` | Line charts, area charts |
| `volatility_report.csv` | Scatter plots, heat maps |
| `portfolio_report.csv` | Donut charts, waterfall charts |

> **💡 Pro Tip:** Set Power BI to refresh data from the CSV files periodically to keep your dashboards up-to-date!

---

## 📄 13. Example Output

### Pipeline Console Output

```
╔══════════════════════════════════════════════════════════╗
║                                                        ║
║   🪙  Crypto Analytics Platform                        ║
║       Version 1.0.0                                    ║
║                                                        ║
║   Real-Time Cryptocurrency Analytics & Reporting       ║
║   Powered by CoinGecko API + PostgreSQL                ║
║                                                        ║
╠══════════════════════════════════════════════════════════╣
║   📅 2026-05-25 16:45:00                               ║
╚══════════════════════════════════════════════════════════╝

  🚀 Running full pipeline...

  🔧 Initializing platform...
  ✅ Database connection: OK
  ✅ Database tables: Ready

  ╔══════════════════════════════════════════════════════╗
  ║  📊 Running Full Data Pipeline                      ║
  ╠══════════════════════════════════════════════════════╣
  ✅ [1/4] Fetched 10 coins
  ──────────────────────────────────────────────────────
  ✅ [2/4] Fetched history for 10/10 coins
  ──────────────────────────────────────────────────────
  ✅ [3/4] Analytics completed
  ──────────────────────────────────────────────────────
  ✅ [4/4] Reports exported
  ╚══════════════════════════════════════════════════════╝

  ┌──────────────────────────────────────────────────────┐
  │              📊 Pipeline Summary                     │
  ├──────────────────────────────────────────────────────┤
  │  🟢 Live Prices:    10 coins fetched
  │
  │  Top coins by price:
  │    📈 Bitcoin          $  67,500.42  (-2.35%)
  │    📈 Ethereum         $   3,500.18  (+1.80%)
  │    📉 Solana           $     150.25  (+5.20%)
  │    📉 Litecoin         $      80.10  (+1.20%)
  │    📈 Avalanche        $      35.50  (+4.00%)
  │
  │  📈 Historical Data: 10 coins
  │  🧮 Analytics:
  │    KPI Summary:      ✅
  │    Trend Reports:    ✅ (10 coins)
  │    Risk Metrics:     ✅
  │    Portfolio:        ✅
  │
  │  📁 Exports: data/exports
  └──────────────────────────────────────────────────────┘

  ✅ Pipeline completed successfully!
  📁 Reports saved to: data/exports
```

---

## 🧪 14. Testing

### Running All Tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run with short traceback
pytest tests/ -v --tb=short

# Run only API tests
pytest tests/test_api.py -v

# Run only database tests
pytest tests/test_database.py -v

# Run using main.py
python main.py --test
```

### Test Categories

| Test File | Tests | Requires |
|-----------|-------|----------|
| `test_api.py` | API connectivity, data structure, error handling | Internet (some tests skipped offline) |
| `test_database.py` | CRUD operations, data integrity, table creation | PostgreSQL (skipped if unavailable) |

### Expected Test Output

```
tests/test_api.py::test_coingecko_connection PASSED
tests/test_api.py::test_fetch_live_prices PASSED
tests/test_api.py::test_live_prices_columns PASSED
tests/test_api.py::test_fetch_historical_prices PASSED
tests/test_api.py::test_api_error_handling PASSED
tests/test_api.py::test_response_data_types PASSED
tests/test_api.py::test_default_coins_configured PASSED
tests/test_api.py::test_fetch_interval_configured PASSED
tests/test_database.py::test_database_url_format PASSED
tests/test_database.py::test_database_connection PASSED
tests/test_database.py::test_table_creation PASSED
tests/test_database.py::test_live_price_insert PASSED
tests/test_database.py::test_data_retrieval PASSED
tests/test_database.py::test_data_validation PASSED
tests/test_database.py::test_multiple_records PASSED
tests/test_database.py::test_model_has_required_attributes PASSED

=================== 16 passed in 12.34s ===================
```

---

## 🔮 15. Future Improvements

| Priority | Feature | Description |
|----------|---------|-------------|
| 🔴 High | 📊 Power BI Templates | Pre-built .pbix dashboards |
| 🔴 High | 🤖 ML Price Predictions | LSTM/Prophet forecasting models |
| 🟡 Medium | 🔔 Price Alerts | Email/Telegram notifications |
| 🟡 Medium | 📱 Mobile Dashboard | Responsive Streamlit mobile UI |
| 🟡 Medium | 🔄 WebSocket Live Feed | Real-time price streaming |
| 🟢 Low | 🌍 Multi-Exchange Support | Binance, Coinbase APIs |
| 🟢 Low | 📈 Technical Indicators | RSI, MACD, Bollinger Bands |
| 🟢 Low | 🐳 Docker Deployment | Containerized deployment |
| 🟢 Low | ☁️ Cloud Hosting | AWS/GCP deployment guides |

---

## 📜 16. License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 Crypto Analytics Platform

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🤝 17. Contributing

Contributions are welcome! Here's how to get started:

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Write** your code with comments and docstrings
4. **Add tests** for new functionality
5. **Run** the test suite to ensure nothing is broken:
   ```bash
   pytest tests/ -v
   ```
6. **Commit** with a descriptive message:
   ```bash
   git commit -m "feat: add your feature description"
   ```
7. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Open** a Pull Request with a clear description

### Coding Standards

- ✅ Follow PEP 8 style guidelines
- ✅ Add docstrings to all functions and classes
- ✅ Include inline comments for complex logic
- ✅ Write tests for new features
- ✅ Keep functions small and focused
- ✅ Use meaningful variable and function names

### Commit Message Convention

```
feat: add new feature
fix: fix a bug
docs: update documentation
test: add or update tests
refactor: code restructuring
style: formatting changes
```

---

<div align="center">

**Built with ❤️ for the crypto community**

⭐ Star this repo if you find it helpful!

</div>
