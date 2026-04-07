"""
Hormuz Cascade Tracker - Price Fetcher
=======================================
Pulls daily prices from yfinance (equities + commodity futures)
and FRED (macro indicators). Stores everything in SQLite.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys
import time

from config import get_all_tickers, FRED_SERIES, LOOKBACK_DAYS
from db import init_db, upsert_prices, get_connection


def fetch_yfinance_prices(tickers, start_date, end_date):
    """
    Fetch daily OHLCV from yfinance for a list of tickers.
    Returns a long-format DataFrame ready for DB insertion.
    """
    print(f"[FETCH] Downloading {len(tickers)} tickers from yfinance...")
    print(f"[FETCH] Date range: {start_date} to {end_date}")

    all_rows = []
    # Batch download for speed, then reshape
    # yfinance can be flaky with large batches, so chunk into groups of 10
    chunk_size = 10
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        chunk_str = " ".join(chunk)
        print(f"[FETCH] Batch {i // chunk_size + 1}: {chunk}")

        try:
            data = yf.download(
                chunk_str,
                start=start_date,
                end=end_date,
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
        except Exception as e:
            print(f"[WARN] yfinance download failed for batch: {e}")
            continue

        if data.empty:
            print(f"[WARN] No data returned for batch: {chunk}")
            continue

        # Handle single vs multi-ticker response
        if len(chunk) == 1:
            ticker = chunk[0]
            for date_val, row in data.iterrows():
                date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, 'strftime') else str(date_val)[:10]
                all_rows.append({
                    "date": date_str,
                    "ticker": ticker,
                    "open": float(row.get("Open", 0) or 0),
                    "high": float(row.get("High", 0) or 0),
                    "low": float(row.get("Low", 0) or 0),
                    "close": float(row.get("Close", 0) or 0),
                    "volume": float(row.get("Volume", 0) or 0),
                })
        else:
            # Multi-ticker: data has MultiIndex columns (ticker, field)
            for ticker in chunk:
                try:
                    # Try to extract this ticker's data
                    if isinstance(data.columns, pd.MultiIndex):
                        ticker_data = data[ticker] if ticker in data.columns.get_level_values(0) else None
                    else:
                        ticker_data = data  # single ticker fallback
                    
                    if ticker_data is None or ticker_data.empty:
                        print(f"[WARN] No data for {ticker}")
                        continue

                    for date_val, row in ticker_data.iterrows():
                        date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, 'strftime') else str(date_val)[:10]
                        close_val = row.get("Close", 0)
                        # Skip rows with NaN close
                        if pd.isna(close_val):
                            continue
                        all_rows.append({
                            "date": date_str,
                            "ticker": ticker,
                            "open": float(row.get("Open", 0) or 0),
                            "high": float(row.get("High", 0) or 0),
                            "low": float(row.get("Low", 0) or 0),
                            "close": float(close_val),
                            "volume": float(row.get("Volume", 0) or 0),
                        })
                except Exception as e:
                    print(f"[WARN] Error processing {ticker}: {e}")
                    continue

        # Brief pause to avoid rate limits
        time.sleep(0.5)

    df = pd.DataFrame(all_rows)
    print(f"[FETCH] Got {len(df)} price rows for {df['ticker'].nunique() if not df.empty else 0} tickers.")
    return df


def fetch_fred_data(start_date, end_date):
    """
    Fetch FRED series. Uses yfinance's FRED proxy (^IRX etc.) or
    falls back to direct download where possible.
    For simplicity, we fetch key rates from yfinance as ticker proxies.
    """
    # FRED API requires a key. For now, use yfinance proxies where possible
    # and store Brent from yfinance as our primary oil benchmark.
    # Users can add FRED_API_KEY later for full FRED access.
    
    fred_proxies = {
        "^TNX": "DGS10",   # 10Y Treasury Yield
        "^IRX": "DGS3M",   # 3-Month T-Bill
        "^TYX": "DGS30",   # 30Y Treasury Yield
    }
    
    all_rows = []
    for yf_ticker, series_id in fred_proxies.items():
        try:
            data = yf.download(yf_ticker, start=start_date, end=end_date, 
                             progress=False, auto_adjust=True)
            if data.empty:
                continue
            for date_val, row in data.iterrows():
                close_val = row.get("Close")
                # Handle both scalar and single-element Series
                if hasattr(close_val, 'item'):
                    close_val = close_val.item()
                if close_val is None or pd.isna(close_val):
                    continue
                date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, 'strftime') else str(date_val)[:10]
                all_rows.append({
                    "date": date_str,
                    "series_id": series_id,
                    "value": float(close_val),
                })
        except Exception as e:
            print(f"[WARN] FRED proxy fetch failed for {yf_ticker}: {e}")

    df = pd.DataFrame(all_rows)
    print(f"[FETCH] Got {len(df)} FRED proxy rows.")
    return df


def fetch_futures_curve():
    """
    Fetch Brent M1 and M6 contracts to calculate the futures curve spread.
    Backwardation (M1 > M6) = market expects prices to fall (short disruption).
    Contango at high levels = market expects prolonged high prices.
    """
    # Brent futures: BZ=F is front month
    # For M6 approximation, we use the 6-month forward contract
    # yfinance has limited futures chain support, so we approximate
    # using BZ=F (front) and a manually calculated spread
    
    # For now, store front-month Brent from daily_prices
    # TODO: Add proper futures chain when moving to a paid data source
    print("[FETCH] Futures curve: using BZ=F front-month from daily_prices (M6 requires futures chain API)")
    return None


def run_fetch(full_refresh=False):
    """Main fetch orchestrator."""
    init_db()

    # Determine date range
    end_date = datetime.now().strftime("%Y-%m-%d")
    if full_refresh:
        start_date = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        print(f"[FETCH] Full refresh: {start_date} to {end_date}")
    else:
        # Incremental: fetch last 7 days to catch any gaps
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        print(f"[FETCH] Incremental: {start_date} to {end_date}")

    # 1. Fetch all equity and commodity tickers
    tickers = get_all_tickers()
    print(f"[FETCH] Master ticker list: {len(tickers)} tickers")
    price_df = fetch_yfinance_prices(tickers, start_date, end_date)
    if not price_df.empty:
        upsert_prices(price_df, table="daily_prices")
        print(f"[FETCH] Stored {len(price_df)} price rows.")

    # 2. Fetch FRED proxy data
    fred_df = fetch_fred_data(start_date, end_date)
    if not fred_df.empty:
        upsert_prices(fred_df, table="fred_series")
        print(f"[FETCH] Stored {len(fred_df)} FRED rows.")

    # 3. Futures curve (placeholder)
    fetch_futures_curve()

    print("[FETCH] Done.")
    return price_df


if __name__ == "__main__":
    # Pass --full for full historical refresh
    full = "--full" in sys.argv
    run_fetch(full_refresh=full)
