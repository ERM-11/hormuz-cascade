"""
Hormuz Cascade Tracker - Configuration
=======================================
All tickers, wave definitions, commodity mappings, and scenario parameters.
Updated: 2026-04-07 (post-Kharg Island strikes)
"""

# ============================================================
# WAVE DEFINITIONS
# Each wave has: upstream commodities that drive it,
# downstream equities that respond with a lag,
# and an estimated lag in trading days.
# ============================================================

WAVES = {
    "W0_MACRO": {
        "name": "Macro Regime Shift",
        "description": "Stagflation: inflation up, growth down, rate cuts delayed",
        "lag_days": 0,  # already happening
        "commodities": ["CL=F", "BZ=F", "GC=F"],  # WTI, Brent, Gold
        "equities": ["SPY", "TLT", "TIP", "UUP"],  # S&P, long bonds, TIPS, USD
        "direction": {
            # expected direction if crisis persists
            "SPY": "short", "TLT": "short", "TIP": "long", 
            "UUP": "long", "GC=F": "long"
        },
    },
    "W1_ENERGY": {
        "name": "Energy Direct",
        "description": "Oil/LNG price spike, refiner margin expansion, shipping reroute",
        "lag_days": 0,  # already priced (partially)
        "commodities": ["CL=F", "BZ=F", "NG=F"],  # WTI, Brent, Nat Gas
        "equities": [
            "DVN",   # Devon Energy - low breakeven US E&P
            "FANG",  # Diamondback Energy - Permian pure play
            "VLO",   # Valero - refiner, crack spread beneficiary
            "PBF",   # PBF Energy - refiner
            "STNG",  # Scorpio Tankers - tanker rates
            "INSW",  # International Seaways - tanker rates
            "FLNG",  # FLEX LNG - LNG shipping reroute
            "CEIX",  # CONSOL Energy - thermal coal substitution
        ],
        "direction": {
            "DVN": "long", "FANG": "long", "VLO": "long", "PBF": "long",
            "STNG": "long", "INSW": "long", "FLNG": "long", "CEIX": "long"
        },
    },
    "W2_FERTILISER": {
        "name": "Fertiliser & Ag Inputs",
        "description": "Urea/ammonia/sulfur shortage, domestic producers benefit",
        "lag_days": 10,  # 2-6 weeks from oil shock
        "commodities": ["NG=F"],  # nat gas as proxy (urea feedstock)
        "equities": [
            "CF",    # CF Industries - US nitrogen producer, domestic gas
            "NTR",   # Nutrien - Canadian, largest fertiliser co
            "MOS",   # Mosaic - phosphate/potash, sulfur-dependent (RISK)
            "IPI",   # Intrepid Potash - potash producer
            "LXU",   # LSB Industries - nitrogen fertiliser
        ],
        "direction": {
            "CF": "long", "NTR": "long", "MOS": "mixed",  # sulfur dependency
            "IPI": "long", "LXU": "long"
        },
    },
    "W3_AGRICULTURE": {
        "name": "Food & Agriculture",
        "description": "Crop yield reduction from fertiliser shortage, food inflation",
        "lag_days": 60,  # 3-6 months (planting to harvest)
        "commodities": ["ZC=F", "ZW=F", "ZS=F"],  # Corn, Wheat, Soybean futures
        "equities": [
            "DBA",   # Invesco DB Agriculture Fund (broad ag ETF)
            "CORN",  # Teucrium Corn Fund
            "WEAT",  # Teucrium Wheat Fund
            "ADM",   # Archer Daniels Midland - ag processor (pass-through)
            "BG",    # Bunge - ag processor (pass-through)
            "TSN",   # Tyson Foods - SHORT thesis (feed cost squeeze)
            "PPC",   # Pilgrim's Pride - SHORT thesis (feed cost squeeze)
        ],
        "direction": {
            "DBA": "long", "CORN": "long", "WEAT": "long",
            "ADM": "long", "BG": "long",
            "TSN": "short", "PPC": "short"  # margin squeeze from feed costs
        },
    },
    "W4_PETROCHEMICALS": {
        "name": "Petrochemicals & Plastics",
        "description": "250-275 day unwind, domestic feedstock advantage",
        "lag_days": 40,  # 2-4 months
        "commodities": ["CL=F"],  # oil as proxy
        "equities": [
            "WLK",   # Westlake Chemical - US ethylene, domestic feedstock
            "LYB",   # LyondellBasell - diversified chemicals
            "MEOH",  # Methanex - methanol producer (non-Gulf)
            "DOW",   # Dow Inc - MIXED (CEO flagged 250-day unwind)
            "SW",    # Smurfit WestRock - packaging (cost pressure)
            "PKG",   # Packaging Corp - packaging (cost pressure)
        ],
        "direction": {
            "WLK": "long", "LYB": "long", "MEOH": "long",
            "DOW": "mixed", "SW": "short", "PKG": "short"
        },
    },
    "W5_HELIUM_SEMIS": {
        "name": "Helium → Semiconductors & Healthcare",
        "description": "Qatar helium loss constrains chip fabs and MRI ops",
        "lag_days": 30,  # 1-3 months (inventory drawdown)
        "commodities": [],  # no liquid helium futures; manual tracking
        "equities": [
            "SOXX",  # iShares Semiconductor ETF (broad exposure)
            "LRCX",  # Lam Research - fab equipment
            "AMAT",  # Applied Materials - fab equipment
        ],
        "direction": {
            "SOXX": "short", "LRCX": "short", "AMAT": "short"
        },
    },
    "W6_EV_BATTERY": {
        "name": "EV Battery Supply Chain",
        "description": "Pet coke → graphite, sulfur → HPAL for Ni/Co/Cu",
        "lag_days": 60,  # multi-quarter
        "commodities": ["CL=F"],
        "equities": [
            "TSLA",  # Tesla - battery cost pressure
            "ALB",   # Albemarle - lithium (mixed: demand up, costs up)
            "LIT",   # Global X Lithium & Battery Tech ETF
        ],
        "direction": {
            "TSLA": "short", "ALB": "mixed", "LIT": "mixed"
        },
    },
    "W7_TRANSPORT": {
        "name": "Airlines & Shipping",
        "description": "Jet fuel +95%, route lengthening benefits shippers",
        "lag_days": 5,  # near-immediate
        "commodities": [],  # jet fuel not easily tracked via free APIs
        "equities": [
            "JETS",  # US Global Jets ETF - SHORT thesis
            "DAL",   # Delta - fuel cost pressure
            "AAL",   # American Airlines - fuel cost pressure
            "DHT",   # DHT Holdings - crude tanker
            "FRO",   # Frontline - crude tanker
        ],
        "direction": {
            "JETS": "short", "DAL": "short", "AAL": "short",
            "DHT": "long", "FRO": "long"
        },
    },
    "W8_SAFE_HAVEN": {
        "name": "Safe Haven & Currency",
        "description": "Gold up, EM currencies down, USD strength",
        "lag_days": 0,
        "commodities": ["GC=F", "SI=F"],  # Gold, Silver
        "equities": [
            "GLD",   # SPDR Gold Shares
            "GDX",   # VanEck Gold Miners ETF
            "EEM",   # iShares MSCI Emerging Markets ETF (SHORT)
            "UUP",   # Invesco DB US Dollar Index Bullish Fund
        ],
        "direction": {
            "GLD": "long", "GDX": "long", "EEM": "short", "UUP": "long"
        },
    },
}

# ============================================================
# SCENARIO DEFINITIONS
# Post-Kharg Island strikes, 2026-04-07
# ============================================================

SCENARIOS = {
    "A_FAST": {
        "name": "Fast Resolution",
        "description": "Strait opens April-May via deal",
        "default_probability": 0.10,
        "oil_target": 75,   # Brent $/bbl
        "duration_days": 30,
        "wave_multipliers": {
            # how much each wave's thesis pays off (1.0 = full, 0.0 = nothing)
            "W0_MACRO": 0.1, "W1_ENERGY": 0.2, "W2_FERTILISER": 0.3,
            "W3_AGRICULTURE": 0.2, "W4_PETROCHEMICALS": 0.2,
            "W5_HELIUM_SEMIS": 0.1, "W6_EV_BATTERY": 0.1,
            "W7_TRANSPORT": 0.2, "W8_SAFE_HAVEN": 0.1,
        },
    },
    "B_SLOW_GRIND": {
        "name": "Slow Grind",
        "description": "Strait opens Q3-Q4 2026, 250-day unwind",
        "default_probability": 0.40,
        "oil_target": 100,
        "duration_days": 150,
        "wave_multipliers": {
            "W0_MACRO": 0.7, "W1_ENERGY": 0.7, "W2_FERTILISER": 0.9,
            "W3_AGRICULTURE": 1.0, "W4_PETROCHEMICALS": 0.8,
            "W5_HELIUM_SEMIS": 0.6, "W6_EV_BATTERY": 0.5,
            "W7_TRANSPORT": 0.7, "W8_SAFE_HAVEN": 0.7,
        },
    },
    "C_PROLONGED": {
        "name": "Prolonged / Structural",
        "description": "Closed through 2026, toll-booth system, supply chain realignment",
        "default_probability": 0.40,
        "oil_target": 130,
        "duration_days": 300,
        "wave_multipliers": {
            "W0_MACRO": 1.0, "W1_ENERGY": 0.9, "W2_FERTILISER": 1.0,
            "W3_AGRICULTURE": 1.0, "W4_PETROCHEMICALS": 1.0,
            "W5_HELIUM_SEMIS": 0.8, "W6_EV_BATTERY": 0.7,
            "W7_TRANSPORT": 0.9, "W8_SAFE_HAVEN": 0.9,
        },
    },
    "D_CATASTROPHIC": {
        "name": "Catastrophic Escalation",
        "description": "Energy infrastructure destroyed, multi-year rebuild",
        "default_probability": 0.10,
        "oil_target": 180,
        "duration_days": 700,
        "wave_multipliers": {
            "W0_MACRO": 1.0, "W1_ENERGY": 1.0, "W2_FERTILISER": 1.0,
            "W3_AGRICULTURE": 1.0, "W4_PETROCHEMICALS": 1.0,
            "W5_HELIUM_SEMIS": 1.0, "W6_EV_BATTERY": 0.9,
            "W7_TRANSPORT": 1.0, "W8_SAFE_HAVEN": 1.0,
        },
    },
}

# ============================================================
# FRED SERIES (macro indicators)
# ============================================================

FRED_SERIES = {
    "T10YIE":   "10Y Breakeven Inflation Rate",
    "T5YIE":    "5Y Breakeven Inflation Rate",
    "DGS10":    "10Y Treasury Yield",
    "DGS2":     "2Y Treasury Yield",
    "DTWEXBGS": "Trade Weighted USD Index",
    "GASREGW":  "US Regular Gasoline Price (weekly)",
    "DCOILBRENTEU": "Brent Crude (daily, FRED)",
}

# ============================================================
# MASTER TICKER LIST (deduplicated for fetching)
# ============================================================

def get_all_tickers():
    """Return deduplicated list of all equity + commodity tickers."""
    tickers = set()
    for wave in WAVES.values():
        tickers.update(wave.get("commodities", []))
        tickers.update(wave.get("equities", []))
    return sorted(tickers)

# ============================================================
# PIPELINE SETTINGS
# ============================================================

DB_PATH = "hormuz_cascade.db"
LOOKBACK_DAYS = 180      # how far back to fetch on first run
CORRELATION_WINDOW = 20  # rolling correlation window (trading days)
ZSCORE_LOOKBACK = 40     # z-score baseline window (trading days)
DIVERGENCE_THRESHOLD = 2.0  # z-score threshold to flag divergence
