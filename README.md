# Hormuz Cascade Tracker

Financial model tracking the cascading economic effects of the Strait of Hormuz closure (2026 Iran war).

## What It Does

Monitors 9 supply chain "waves" from the Hormuz blockade, detects where equity prices are lagging or leading the commodity signal, and produces scenario-weighted portfolio tilts.

## Waves Tracked

| Wave | Name | Key Tickers | Status |
|------|------|-------------|--------|
| W0 | Macro Regime Shift | SPY, TLT, TIP, UUP | Active |
| W1 | Energy Direct | DVN, FANG, VLO, PBF, STNG, FLNG | Mostly priced |
| W2 | Fertiliser & Ag Inputs | CF, NTR, MOS, IPI, LXU | Equities leading |
| W3 | Food & Agriculture | DBA, CORN, WEAT, ADM, BG | **Lag opportunity** |
| W4 | Petrochemicals & Plastics | WLK, LYB, MEOH, DOW | Equities lagging |
| W5 | Helium → Semiconductors | SOXX, LRCX, AMAT | Watch list |
| W6 | EV Battery Supply Chain | TSLA, ALB, LIT | Watch list |
| W7 | Airlines & Shipping | JETS, DAL, AAL, DHT, FRO | Mixed |
| W8 | Safe Haven & Currency | GLD, GDX, EEM, UUP | Active |

## Setup

```bash
pip install yfinance pandas numpy --break-system-packages
```

## Usage

```bash
# Full historical refresh (180 days)
python run_pipeline.py --full

# Daily incremental update (last 7 days)
python run_pipeline.py

# Update scenario weights (edit in config.py or use scenario_engine.py)
```

## Files

- `config.py` - All tickers, wave definitions, scenario parameters
- `db.py` - SQLite schema and helpers
- `fetch_prices.py` - yfinance + FRED proxy data fetcher
- `calculate_signals.py` - Divergence detection, z-scores, wave analysis
- `scenario_engine.py` - Scenario-weighted portfolio tilt calculator
- `run_pipeline.py` - Main orchestrator
- `hormuz_cascade.db` - SQLite database (auto-created)
- `cascade_summary.json` - JSON export for React dashboard

## Signal Interpretation

- **Positive signal strength**: equities lagging commodities (potential entry)
- **Negative signal strength**: equities leading commodities (already priced)
- **Divergence flag**: z-score > 2.0 (unusual correlation breakdown)
- **Scenario-weighted payoff**: how robust the wave thesis is across all scenarios

## Next Steps

- Phase 2: React dashboard widget (cascade heatmap, scenario sliders)
- Phase 3: Paper portfolio tracking, backtest against 2022 Ukraine shock
- Add proper futures curve data (Brent M1-M6 spread)
- Add USDA crop progress reports as signal input
