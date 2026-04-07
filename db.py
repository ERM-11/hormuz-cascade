"""
Hormuz Cascade Tracker - Database Layer
========================================
SQLite schema + CRUD helpers.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from config import DB_PATH


def get_connection():
    """Return a connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()

    # Daily price data for equities and commodity tickers (from yfinance)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (date, ticker)
        )
    """)

    # FRED macro series
    c.execute("""
        CREATE TABLE IF NOT EXISTS fred_series (
            date TEXT NOT NULL,
            series_id TEXT NOT NULL,
            value REAL,
            PRIMARY KEY (date, series_id)
        )
    """)

    # Scenario probability weights (user-updated)
    c.execute("""
        CREATE TABLE IF NOT EXISTS scenario_weights (
            date TEXT NOT NULL,
            scenario_id TEXT NOT NULL,
            probability REAL NOT NULL,
            PRIMARY KEY (date, scenario_id)
        )
    """)

    # Calculated wave signals (output of calculate_signals.py)
    c.execute("""
        CREATE TABLE IF NOT EXISTS wave_signals (
            date TEXT NOT NULL,
            wave_id TEXT NOT NULL,
            commodity_return_20d REAL,
            equity_return_20d REAL,
            correlation_20d REAL,
            correlation_zscore REAL,
            divergence_flag INTEGER DEFAULT 0,
            signal_strength REAL,
            PRIMARY KEY (date, wave_id)
        )
    """)

    # Paper portfolio trades
    c.execute("""
        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            direction TEXT NOT NULL,  -- 'long' or 'short'
            entry_price REAL NOT NULL,
            quantity REAL NOT NULL,
            wave_id TEXT,
            scenario_thesis TEXT,
            exit_date TEXT,
            exit_price REAL,
            pnl REAL,
            notes TEXT
        )
    """)

    # Futures curve data (Brent M1 vs M6 spread)
    c.execute("""
        CREATE TABLE IF NOT EXISTS futures_curve (
            date TEXT NOT NULL,
            m1_price REAL,
            m6_price REAL,
            spread REAL,  -- M1 - M6 (positive = backwardation)
            PRIMARY KEY (date)
        )
    """)

    # Manual commodity entries (helium, urea spot, etc.)
    c.execute("""
        CREATE TABLE IF NOT EXISTS manual_commodities (
            date TEXT NOT NULL,
            commodity TEXT NOT NULL,
            price REAL NOT NULL,
            unit TEXT,
            source TEXT,
            PRIMARY KEY (date, commodity)
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] All tables initialised.")


def upsert_prices(df, table="daily_prices"):
    """
    Insert or replace price data from a pandas DataFrame.
    df must have columns matching the table schema.
    """
    conn = get_connection()
    rows = df.to_dict("records")
    if table == "daily_prices":
        conn.executemany("""
            INSERT OR REPLACE INTO daily_prices 
            (date, ticker, open, high, low, close, volume)
            VALUES (:date, :ticker, :open, :high, :low, :close, :volume)
        """, rows)
    elif table == "fred_series":
        conn.executemany("""
            INSERT OR REPLACE INTO fred_series (date, series_id, value)
            VALUES (:date, :series_id, :value)
        """, rows)
    conn.commit()
    conn.close()


def upsert_wave_signals(records):
    """Insert or replace wave signal calculations."""
    conn = get_connection()
    conn.executemany("""
        INSERT OR REPLACE INTO wave_signals
        (date, wave_id, commodity_return_20d, equity_return_20d,
         correlation_20d, correlation_zscore, divergence_flag, signal_strength)
        VALUES (:date, :wave_id, :commodity_return_20d, :equity_return_20d,
                :correlation_20d, :correlation_zscore, :divergence_flag, :signal_strength)
    """, records)
    conn.commit()
    conn.close()


def upsert_scenario_weights(weights_dict):
    """
    Save scenario weights for today.
    weights_dict: {"A_FAST": 0.10, "B_SLOW_GRIND": 0.40, ...}
    """
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    for scenario_id, prob in weights_dict.items():
        conn.execute("""
            INSERT OR REPLACE INTO scenario_weights (date, scenario_id, probability)
            VALUES (?, ?, ?)
        """, (today, scenario_id, prob))
    conn.commit()
    conn.close()


def get_prices(tickers=None, start_date=None, end_date=None):
    """
    Load price data as a DataFrame.
    Returns pivot table: index=date, columns=ticker, values=close.
    """
    conn = get_connection()
    query = "SELECT date, ticker, close FROM daily_prices WHERE 1=1"
    params = []
    if tickers:
        placeholders = ",".join(["?"] * len(tickers))
        query += f" AND ticker IN ({placeholders})"
        params.extend(tickers)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
    
    # Pivot to wide format: date x ticker
    pivot = df.pivot_table(index="date", columns="ticker", values="close")
    pivot.index = pd.to_datetime(pivot.index)
    pivot = pivot.sort_index()
    return pivot


def get_latest_wave_signals():
    """Return the most recent wave signals as a list of dicts."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT * FROM wave_signals 
        WHERE date = (SELECT MAX(date) FROM wave_signals)
        ORDER BY ABS(signal_strength) DESC
    """, conn)
    conn.close()
    return df


def get_scenario_weights():
    """Return latest scenario weights as a dict."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT scenario_id, probability FROM scenario_weights
        WHERE date = (SELECT MAX(date) FROM scenario_weights)
    """).fetchall()
    conn.close()
    return {r["scenario_id"]: r["probability"] for r in rows}


if __name__ == "__main__":
    init_db()
