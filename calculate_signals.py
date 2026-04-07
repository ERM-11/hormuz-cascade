"""
Hormuz Cascade Tracker - Signal Calculator
============================================
Core analytical engine:
  1. Rolling correlations between commodity drivers and downstream equities
  2. Z-score divergence detection (where correlations break from historical norms)
  3. Relative performance by wave (is the wave ahead of or behind implied impact?)
  4. Composite signal strength per wave
"""

import pandas as pd
import numpy as np
from datetime import datetime

from config import WAVES, CORRELATION_WINDOW, ZSCORE_LOOKBACK, DIVERGENCE_THRESHOLD
from db import get_prices, upsert_wave_signals


def calculate_returns(prices_df, window=20):
    """Calculate rolling N-day returns for all columns."""
    return prices_df.pct_change(window)


def rolling_correlation(series_a, series_b, window=20):
    """Calculate rolling Pearson correlation between two return series."""
    return series_a.rolling(window).corr(series_b)


def zscore(series, lookback=60):
    """
    Z-score of the latest value relative to a trailing lookback window.
    Positive z-score = current value is above the lookback mean.
    """
    rolling_mean = series.rolling(lookback).mean()
    rolling_std = series.rolling(lookback).std()
    # Avoid division by zero
    rolling_std = rolling_std.replace(0, np.nan)
    return (series - rolling_mean) / rolling_std


def compute_wave_signals(prices_df):
    """
    For each wave, compute:
      - Average commodity driver return (20d)
      - Average equity basket return (20d)
      - Rolling correlation between the two
      - Z-score of the correlation (divergence detector)
      - Divergence flag (z-score exceeds threshold)
      - Composite signal strength
    
    Returns a list of dicts ready for DB insertion.
    """
    if prices_df.empty or len(prices_df) < ZSCORE_LOOKBACK + CORRELATION_WINDOW:
        print(f"[SIGNALS] Not enough data ({len(prices_df)} rows). Need at least {ZSCORE_LOOKBACK + CORRELATION_WINDOW}.")
        return []

    returns_20d = calculate_returns(prices_df, window=CORRELATION_WINDOW)
    returns_1d = prices_df.pct_change(1)  # for correlation calculation

    signals = []
    latest_date = prices_df.index[-1].strftime("%Y-%m-%d")

    for wave_id, wave in WAVES.items():
        commodity_tickers = [t for t in wave.get("commodities", []) if t in prices_df.columns]
        equity_tickers = [t for t in wave.get("equities", []) if t in prices_df.columns]

        if not commodity_tickers or not equity_tickers:
            # Some waves (W5, W7) may lack commodity tickers
            # Use W1 oil as a proxy driver if no commodities defined
            proxy_commodities = ["CL=F", "BZ=F"]
            commodity_tickers = [t for t in proxy_commodities if t in prices_df.columns]
            if not commodity_tickers:
                print(f"[SIGNALS] Skipping {wave_id}: no commodity or equity data")
                continue

        # Average daily return across commodity drivers
        commodity_returns = returns_1d[commodity_tickers].mean(axis=1)
        
        # Average daily return across equity basket
        equity_returns = returns_1d[equity_tickers].mean(axis=1)

        # 20-day average returns for reporting
        commodity_return_20d = returns_20d[commodity_tickers].iloc[-1].mean() if len(returns_20d) > 0 else 0
        equity_return_20d = returns_20d[equity_tickers].iloc[-1].mean() if len(returns_20d) > 0 else 0

        # Rolling correlation between commodity and equity baskets
        corr_series = rolling_correlation(
            commodity_returns, equity_returns, 
            window=CORRELATION_WINDOW
        )

        # Z-score of correlation (how unusual is current correlation?)
        corr_zscore = zscore(corr_series, lookback=ZSCORE_LOOKBACK)

        # Get latest values
        latest_corr = corr_series.iloc[-1] if not corr_series.empty else 0
        latest_zscore = corr_zscore.iloc[-1] if not corr_zscore.empty else 0

        # Handle NaN
        if pd.isna(latest_corr):
            latest_corr = 0
        if pd.isna(latest_zscore):
            latest_zscore = 0
        if pd.isna(commodity_return_20d):
            commodity_return_20d = 0
        if pd.isna(equity_return_20d):
            equity_return_20d = 0

        # Divergence flag: z-score beyond threshold
        divergence_flag = 1 if abs(latest_zscore) > DIVERGENCE_THRESHOLD else 0

        # Composite signal strength
        # Positive = equities lagging commodities (potential long opportunity)
        # Negative = equities leading commodities (already priced in or overshoot)
        # Formula: commodity return - equity return, scaled by z-score magnitude
        return_gap = float(commodity_return_20d) - float(equity_return_20d)
        signal_strength = return_gap * (1 + abs(float(latest_zscore)))

        signals.append({
            "date": latest_date,
            "wave_id": wave_id,
            "commodity_return_20d": round(float(commodity_return_20d), 6),
            "equity_return_20d": round(float(equity_return_20d), 6),
            "correlation_20d": round(float(latest_corr), 4),
            "correlation_zscore": round(float(latest_zscore), 4),
            "divergence_flag": divergence_flag,
            "signal_strength": round(float(signal_strength), 6),
        })

    return signals


def print_signal_report(signals):
    """Print a formatted report of current wave signals."""
    if not signals:
        print("[SIGNALS] No signals computed.")
        return

    print("\n" + "=" * 80)
    print(f"  HORMUZ CASCADE TRACKER - WAVE SIGNALS ({signals[0]['date']})")
    print("=" * 80)

    # Sort by absolute signal strength (strongest first)
    sorted_signals = sorted(signals, key=lambda x: abs(x["signal_strength"]), reverse=True)

    for s in sorted_signals:
        wave = WAVES.get(s["wave_id"], {})
        name = wave.get("name", s["wave_id"])
        
        # Divergence indicator
        div = " ** DIVERGENCE **" if s["divergence_flag"] else ""
        
        # Signal direction
        if s["signal_strength"] > 0.01:
            direction = "EQUITIES LAGGING (potential opportunity)"
        elif s["signal_strength"] < -0.01:
            direction = "EQUITIES LEADING (already priced)"
        else:
            direction = "NEUTRAL"

        print(f"\n  [{s['wave_id']}] {name}{div}")
        print(f"    Commodity 20d return: {s['commodity_return_20d']:+.2%}")
        print(f"    Equity 20d return:    {s['equity_return_20d']:+.2%}")
        print(f"    Correlation (20d):    {s['correlation_20d']:.3f}")
        print(f"    Correlation z-score:  {s['correlation_zscore']:+.2f}")
        print(f"    Signal strength:      {s['signal_strength']:+.4f}")
        print(f"    Assessment:           {direction}")

    print("\n" + "=" * 80)
    
    # Summary: top divergences
    divergences = [s for s in sorted_signals if s["divergence_flag"]]
    if divergences:
        print(f"\n  ACTIVE DIVERGENCES: {len(divergences)}")
        for d in divergences:
            name = WAVES.get(d["wave_id"], {}).get("name", d["wave_id"])
            print(f"    - {name}: z-score = {d['correlation_zscore']:+.2f}, signal = {d['signal_strength']:+.4f}")
    else:
        print("\n  No active divergences (z-score threshold: {:.1f})".format(DIVERGENCE_THRESHOLD))
    
    print()


def run_signals():
    """Main signal calculation orchestrator."""
    print("[SIGNALS] Loading price data...")
    prices = get_prices()
    
    if prices.empty:
        print("[SIGNALS] No price data in DB. Run fetch_prices.py --full first.")
        return []

    print(f"[SIGNALS] Loaded {len(prices)} days x {len(prices.columns)} tickers")
    print(f"[SIGNALS] Date range: {prices.index[0].date()} to {prices.index[-1].date()}")

    # Compute signals
    signals = compute_wave_signals(prices)

    if signals:
        # Store in DB
        upsert_wave_signals(signals)
        print(f"[SIGNALS] Stored {len(signals)} wave signals.")
        
        # Print report
        print_signal_report(signals)
    
    return signals


if __name__ == "__main__":
    run_signals()
