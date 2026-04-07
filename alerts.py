"""
Hormuz Cascade Tracker - Alert System
=======================================
Checks tripwires against latest DB data and fires ntfy.sh push notifications.

Tripwires:
  1. Brent crude (BZ=F) level crossings: $75, $100, $130, $180
  2. Any wave signal z-score divergence flag triggered
  3. Corn (ZC=F) or wheat (ZW=F) moved >5% in trailing 5 trading days
  4. SPY dropped >3% in trailing 5 trading days
"""

import requests
import sqlite3
import pandas as pd
from datetime import datetime

from config import DB_PATH
from db import get_connection

NTFY_TOPIC = "https://ntfy.sh/hormuz-cascade-ethan"
BRENT_LEVELS = [75, 100, 130, 180]


def _post(title, body, priority="default"):
    """Send a push notification to ntfy.sh."""
    try:
        resp = requests.post(
            NTFY_TOPIC,
            data=body.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": "chart_with_upwards_trend",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            print(f"[ALERT] Sent: {title}")
        else:
            print(f"[ALERT] ntfy.sh returned {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[ALERT] Failed to send notification: {e}")


def check_brent_crossings():
    """
    Check if Brent crude (BZ=F) crossed any of the defined price levels today.
    A crossing is when today's close is on the opposite side of a level vs yesterday.
    """
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT date, close FROM daily_prices
        WHERE ticker = 'BZ=F'
        ORDER BY date DESC
        LIMIT 2
        """,
        conn,
    )
    conn.close()

    if len(df) < 2:
        print("[ALERT] Not enough Brent data for crossing check.")
        return

    today_close = df.iloc[0]["close"]
    yesterday_close = df.iloc[1]["close"]
    today_date = df.iloc[0]["date"]

    print(f"[ALERT] Brent check: yesterday={yesterday_close:.2f}, today={today_close:.2f}")

    for level in BRENT_LEVELS:
        crossed_up = yesterday_close < level <= today_close
        crossed_down = yesterday_close > level >= today_close
        if crossed_up or crossed_down:
            direction = "crossed above" if crossed_up else "crossed below"
            _post(
                title=f"Cascade Alert: Brent ${level} Level",
                body=f"BZ=F {direction} ${level} — now ${today_close:.2f}/bbl ({today_date})",
                priority="default",
            )


def check_divergence_flags():
    """
    Check if any wave signal has divergence_flag=1 in today's data.
    """
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT wave_id, correlation_zscore, signal_strength, date
        FROM wave_signals
        WHERE date = (SELECT MAX(date) FROM wave_signals)
          AND divergence_flag = 1
        """,
        conn,
    )
    conn.close()

    if df.empty:
        print("[ALERT] No divergence flags active.")
        return

    for _, row in df.iterrows():
        _post(
            title=f"Cascade Alert: {row['wave_id']} Divergence",
            body=(
                f"{row['wave_id']} z-score={row['correlation_zscore']:+.2f} "
                f"signal={row['signal_strength']:+.4f} ({row['date']})"
            ),
            priority="high",
        )


def check_ag_moves():
    """
    Check if corn (ZC=F) or wheat (ZW=F) moved more than 5% in trailing 5 trading days.
    """
    conn = get_connection()
    for ticker in ["ZC=F", "ZW=F"]:
        df = pd.read_sql_query(
            f"""
            SELECT date, close FROM daily_prices
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 6
            """,
            conn,
            params=(ticker,),
        )
        if len(df) < 2:
            print(f"[ALERT] Not enough data for {ticker}")
            continue

        latest = df.iloc[0]["close"]
        oldest = df.iloc[-1]["close"]
        if oldest == 0:
            continue
        pct_change = (latest - oldest) / oldest

        print(f"[ALERT] {ticker} 5-day move: {pct_change:+.2%} (from {oldest:.2f} to {latest:.2f})")

        if abs(pct_change) > 0.05:
            direction = "surged" if pct_change > 0 else "dropped"
            name = "Corn" if ticker == "ZC=F" else "Wheat"
            _post(
                title=f"Cascade Alert: {name} 5-Day Move",
                body=f"{ticker} {direction} {pct_change:+.1%} over 5 trading days — now {latest:.2f} ({df.iloc[0]['date']})",
                priority="default",
            )
    conn.close()


def check_spy_drop():
    """
    Check if SPY dropped more than 3% over the trailing 5 trading days.
    """
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT date, close FROM daily_prices
        WHERE ticker = 'SPY'
        ORDER BY date DESC
        LIMIT 6
        """,
        conn,
    )
    conn.close()

    if len(df) < 2:
        print("[ALERT] Not enough SPY data.")
        return

    latest = df.iloc[0]["close"]
    oldest = df.iloc[-1]["close"]
    if oldest == 0:
        return
    pct_change = (latest - oldest) / oldest

    print(f"[ALERT] SPY 5-day move: {pct_change:+.2%} (from {oldest:.2f} to {latest:.2f})")

    if pct_change < -0.03:
        _post(
            title="Cascade Alert: SPY 5-Day Drop",
            body=f"SPY dropped {pct_change:+.1%} over 5 trading days — now ${latest:.2f} ({df.iloc[0]['date']})",
            priority="default",
        )


def run_alerts():
    """Run all tripwire checks."""
    print("\n[ALERTS] Running tripwire checks...")
    check_brent_crossings()
    check_divergence_flags()
    check_ag_moves()
    check_spy_drop()
    print("[ALERTS] Done.\n")


if __name__ == "__main__":
    run_alerts()
