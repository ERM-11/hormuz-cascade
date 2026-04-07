"""
Hormuz Cascade Tracker - Pipeline Orchestrator
================================================
Runs the full pipeline:
  1. Fetch prices (yfinance + FRED proxies)
  2. Calculate wave signals (divergence detection)
  3. Run scenario engine (portfolio tilts)
  4. Run alerts (ntfy.sh tripwire checks)

Usage:
  python run_pipeline.py          # incremental update (last 7 days)
  python run_pipeline.py --full   # full 90-day historical refresh
"""

import sys
import os
from datetime import datetime

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from db import init_db
from fetch_prices import run_fetch
from calculate_signals import run_signals
from scenario_engine import run_scenario_engine


def run_pipeline(full_refresh=False):
    """Execute the full pipeline."""
    start_time = datetime.now()

    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + "  HORMUZ CASCADE TRACKER".center(78) + "║")
    print("║" + f"  Pipeline run: {start_time.strftime('%Y-%m-%d %H:%M:%S')}".center(78) + "║")
    print("╚" + "═" * 78 + "╝")

    # Step 0: Initialise database
    print("\n[PIPELINE] Step 0: Initialise database")
    init_db()

    # Step 1: Fetch prices
    print("\n[PIPELINE] Step 1: Fetch prices")
    price_df = run_fetch(full_refresh=full_refresh)

    # Step 2: Calculate wave signals
    print("\n[PIPELINE] Step 2: Calculate wave signals")
    signals = run_signals()

    # Step 3: Run scenario engine
    print("\n[PIPELINE] Step 3: Scenario engine & portfolio tilts")
    tilts = run_scenario_engine()

    # Step 4: Run alerts
    print("\n[PIPELINE] Step 4: Tripwire alerts")
    from alerts import run_alerts
    run_alerts()

    # Done
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n[PIPELINE] Complete in {elapsed:.1f}s")

    # Export summary to JSON for dashboard consumption
    export_summary(signals, tilts)

    return signals, tilts


def export_summary(signals, tilts):
    """Export latest results as JSON for the React dashboard."""
    import json
    from config import SCENARIOS
    from db import get_scenario_weights

    weights = get_scenario_weights()

    summary = {
        "generated_at": datetime.now().isoformat(),
        "scenario_weights": weights,
        "scenarios": {
            sid: {
                "name": s["name"],
                "oil_target": s["oil_target"],
                "duration_days": s["duration_days"],
                "probability": weights.get(sid, s["default_probability"]),
            }
            for sid, s in SCENARIOS.items()
        },
        "wave_signals": signals if isinstance(signals, list) else [],
        "portfolio_tilts": tilts if isinstance(tilts, list) else [],
        "expected_oil_price": sum(
            weights.get(sid, s["default_probability"]) * s["oil_target"]
            for sid, s in SCENARIOS.items()
        ),
    }

    output_path = "cascade_summary.json"
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"[PIPELINE] Summary exported to {output_path}")


if __name__ == "__main__":
    full = "--full" in sys.argv
    run_pipeline(full_refresh=full)
