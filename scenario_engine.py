"""
Hormuz Cascade Tracker - Scenario Engine
==========================================
Takes scenario probability weights and wave signals,
produces portfolio tilt recommendations.

Each scenario implies different payoffs for each wave.
The expected value across scenarios determines optimal positioning.
"""

import json
from datetime import datetime

from config import WAVES, SCENARIOS
from db import get_scenario_weights, upsert_scenario_weights, get_latest_wave_signals


def get_active_weights():
    """Load scenario weights from DB, or use defaults."""
    weights = get_scenario_weights()
    if not weights:
        # Use default weights from config
        weights = {sid: s["default_probability"] for sid, s in SCENARIOS.items()}
        upsert_scenario_weights(weights)
        print("[SCENARIO] Using default weights (post-Kharg, 2026-04-07)")
    return weights


def calculate_wave_expected_payoff(weights):
    """
    For each wave, calculate expected payoff across all scenarios.
    
    Expected payoff = sum(P(scenario) * wave_multiplier(scenario))
    
    Higher values = the wave thesis pays off in more/likelier scenarios.
    This tells you which waves are robust bets vs. which are scenario-dependent.
    """
    wave_payoffs = {}

    for wave_id in WAVES:
        expected = 0.0
        for scenario_id, prob in weights.items():
            scenario = SCENARIOS.get(scenario_id, {})
            multiplier = scenario.get("wave_multipliers", {}).get(wave_id, 0.5)
            expected += prob * multiplier
        wave_payoffs[wave_id] = round(expected, 3)

    return wave_payoffs


def calculate_portfolio_tilts(weights, wave_signals_df=None):
    """
    Combine scenario-weighted wave payoffs with live divergence signals
    to produce a ranked list of actionable tilts.
    
    Score = expected_payoff * (1 + abs(signal_strength)) * divergence_boost
    
    Returns sorted list of (wave_id, score, direction, rationale).
    """
    wave_payoffs = calculate_wave_expected_payoff(weights)
    
    # Load latest wave signals if not provided
    signals_dict = {}
    if wave_signals_df is not None and not wave_signals_df.empty:
        for _, row in wave_signals_df.iterrows():
            signals_dict[row["wave_id"]] = {
                "signal_strength": row.get("signal_strength", 0),
                "divergence_flag": row.get("divergence_flag", 0),
                "correlation_zscore": row.get("correlation_zscore", 0),
            }

    tilts = []
    for wave_id, wave in WAVES.items():
        payoff = wave_payoffs.get(wave_id, 0.5)
        signal = signals_dict.get(wave_id, {})
        signal_strength = abs(signal.get("signal_strength", 0))
        divergence = signal.get("divergence_flag", 0)
        
        # Composite score
        divergence_boost = 1.5 if divergence else 1.0
        score = payoff * (1 + signal_strength * 10) * divergence_boost
        
        # Determine primary direction from wave config
        directions = wave.get("direction", {})
        long_count = sum(1 for d in directions.values() if d == "long")
        short_count = sum(1 for d in directions.values() if d == "short")
        primary_direction = "long" if long_count >= short_count else "short"

        # Build rationale
        rationale_parts = []
        rationale_parts.append(f"Scenario-weighted payoff: {payoff:.0%}")
        if divergence:
            rationale_parts.append(f"DIVERGENCE DETECTED (z={signal.get('correlation_zscore', 0):+.1f})")
        if signal_strength > 0.01:
            rationale_parts.append("Equities lagging commodity signal")
        elif signal_strength > 0:
            rationale_parts.append("Equities tracking commodity signal")

        tilts.append({
            "wave_id": wave_id,
            "wave_name": wave["name"],
            "score": round(score, 4),
            "expected_payoff": payoff,
            "primary_direction": primary_direction,
            "divergence": bool(divergence),
            "rationale": "; ".join(rationale_parts),
            "top_tickers": _get_top_tickers(wave, primary_direction),
        })

    # Sort by score descending
    tilts.sort(key=lambda x: x["score"], reverse=True)
    return tilts


def _get_top_tickers(wave, primary_direction):
    """Get the top 3 tickers aligned with the primary direction."""
    directions = wave.get("direction", {})
    aligned = [t for t, d in directions.items() if d == primary_direction]
    return aligned[:3]


def print_scenario_report(weights, tilts):
    """Print formatted scenario and portfolio tilt report."""
    print("\n" + "=" * 80)
    print("  HORMUZ CASCADE TRACKER - SCENARIO ENGINE")
    print("=" * 80)
    
    # Scenario probabilities
    print("\n  SCENARIO PROBABILITIES:")
    for sid, prob in weights.items():
        scenario = SCENARIOS.get(sid, {})
        name = scenario.get("name", sid)
        oil = scenario.get("oil_target", "?")
        duration = scenario.get("duration_days", "?")
        bar = "█" * int(prob * 40) + "░" * (40 - int(prob * 40))
        print(f"    {name:25s} [{bar}] {prob:.0%}  (Oil: ${oil}, {duration}d)")

    # Expected oil price
    expected_oil = sum(
        weights.get(sid, 0) * SCENARIOS[sid]["oil_target"]
        for sid in SCENARIOS
    )
    print(f"\n  Probability-weighted oil price: ${expected_oil:.0f}/bbl")

    # Portfolio tilts
    print("\n  PORTFOLIO TILTS (ranked by composite score):")
    print("  " + "-" * 76)
    
    for i, tilt in enumerate(tilts, 1):
        div_marker = " *** " if tilt["divergence"] else "     "
        direction_marker = "▲ LONG " if tilt["primary_direction"] == "long" else "▼ SHORT"
        tickers_str = ", ".join(tilt["top_tickers"])
        
        print(f"\n  {i}. [{tilt['wave_id']}] {tilt['wave_name']}{div_marker}")
        print(f"     Score: {tilt['score']:.3f} | Payoff: {tilt['expected_payoff']:.0%} | {direction_marker}")
        print(f"     Top tickers: {tickers_str}")
        print(f"     {tilt['rationale']}")

    # Actionable summary
    print("\n  " + "=" * 76)
    print("  ACTIONABLE SUMMARY:")
    top3 = tilts[:3]
    for t in top3:
        print(f"    → {t['wave_name']}: {t['primary_direction'].upper()} {', '.join(t['top_tickers'])}")
    
    divergent = [t for t in tilts if t["divergence"]]
    if divergent:
        print(f"\n  DIVERGENCE ALERTS ({len(divergent)} waves):")
        for d in divergent:
            print(f"    ⚠ {d['wave_name']}: equities may be mispriced vs. commodity signal")

    print()


def update_scenario_weights(new_weights):
    """
    Update scenario weights. Validates they sum to ~1.0.
    new_weights: dict like {"A_FAST": 0.10, "B_SLOW_GRIND": 0.40, ...}
    """
    total = sum(new_weights.values())
    if abs(total - 1.0) > 0.05:
        print(f"[WARN] Weights sum to {total:.2f}, not 1.0. Normalising.")
        factor = 1.0 / total
        new_weights = {k: v * factor for k, v in new_weights.items()}
    
    upsert_scenario_weights(new_weights)
    print(f"[SCENARIO] Updated weights: {new_weights}")
    return new_weights


def run_scenario_engine():
    """Main scenario engine orchestrator."""
    weights = get_active_weights()
    signals_df = get_latest_wave_signals()
    tilts = calculate_portfolio_tilts(weights, signals_df)
    print_scenario_report(weights, tilts)
    return tilts


if __name__ == "__main__":
    run_scenario_engine()
