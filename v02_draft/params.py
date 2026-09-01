"""params.py -- all engine parameters in one place.

Section A reproduces the v0.1 LOCKED parameters verbatim (owner sign-off
23 Aug 2026). Changing any of them changes the shipped engine, not a draft.

Section B holds NEW parameters introduced by the v0.2 draft. None of them are
signed off; each one is marked and defaulted so that, where possible, OFF is
the default behaviour (the draft must be able to reproduce v0.1 behaviour).
"""

# ---------------------------------------------------------------------------
# SECTION A -- v0.1 LOCKED PARAMETERS (do not touch without owner sign-off)
# ---------------------------------------------------------------------------
BASE_RATE = 0.10          # discount rate: 10% base
CYCLICAL_BUMP = 0.02      # +2pts if cyclical
WIDE_MOAT_DISC = 0.01     # -1pt if wide moat
RATE_FLOOR = 0.09
TERMINAL_G = 0.02
BARS = {'strong': 0.50, 'buy': 0.30, 'cautious': 0.15}   # MoS bars
CYCLICAL_MOS_BUMP = 0.10  # cyclical names must clear +10pts on every bar
ASYMMETRY = 3.0           # cautious buy needs bull upside >= 3x bear downside
DISAGREE_CAP = 2.5        # max/min method ratio beyond which verdict caps
FULL_POS, HALF_POS = 0.08, 0.04   # position caps (owner signed off)
FLAT_MULTIPLE = 15        # v0.1 Method 4 fallback multiple
COVERAGE_KILL = 2.0       # interest coverage below this = fatal flag
NEG_FCF_YEARS_KILL = 2    # FCF negative in >= this many of >=3 years = fatal

# Fatal flags specced in ENGINE_DESIGN v0.1 but NOT implemented in engine_v01:
# completing the spec here is a fix, not a parameter change (see metrics.py).
ALTMAN_Z_KILL = 1.8       # Altman Z below this = fatal flag (spec'd, now coded)
FSCORE_KILL = 3           # Piotroski F-Score at/below this = fatal flag (spec'd)

# ---------------------------------------------------------------------------
# SECTION B -- v0.2 DRAFT PARAMETERS (owner sign-off required for each)
# ---------------------------------------------------------------------------
# Risk panel: subscore -> weight for the composite used ONLY for ordering
# (position sizing, watchlist ranking). The panel itself carries no weights.
RISK_WEIGHTS = {           # DRAFT
    'method_agreement': 0.20,
    'fcf_stability':     0.20,
    'coverage':          0.20,
    'leverage':          0.15,
    'accruals':          0.15,
    'measurement':       0.10,
}

# Risk-scaled margin-of-safety bars (VERSION_PLAN issue #5 extension).
# OFF by default: with this False the verdict ladder is bit-identical to v0.1.
# When True: required bar scales between x0.83 (composite 100, "earned
# reduction through measured predictability") and x1.33 (composite 0).
RISK_SCALED_BARS = False   # DRAFT
BAR_SCALE_BEST, BAR_SCALE_WORST = 0.83, 1.33   # DRAFT

# Position sizing engine (spec Part B). Caps are v0.1-locked; the deployment
# fraction is draft.
MAX_DEPLOYED = 0.80        # DRAFT: at most 80% deployed by the sizing rule;
                           # remainder is cash (cash is a position)
MIN_POSITION = 0.02        # spec Part B: below 2% "not worth holding"

# IFRS 16 lease adjustment (issue #8): deduct lease principal repayments from
# headline FCF when the data exposes them. Applied automatically when present;
# the deduction size is always printed, never silent.
LEASE_ADJUST = True        # DRAFT (default on: the bias it fixes is documented)

# Owner earnings (issue #1): FCF input = OCF - min(capex, D&A) per year,
# 4-yr median, falling back to headline FCF when OCF/capex rows are missing.
OWNER_EARNINGS = True      # DRAFT

# Sensitivity grid ranges for the bear DCF (deterministic; no distributions).
SENS_RATES = [0.09, 0.10, 0.11, 0.12]        # DRAFT
SENS_TERMINAL = [0.01, 0.02, 0.03]           # DRAFT

# Exit-multiple terminal cross-check (peer-proven; Sturzo). Default multiple
# is deliberately ungenerous.
EXIT_EBITDA_MULT = 7.0     # DRAFT

# Wrong-model detection (issue #4).
WRONG_MODEL_SECTORS = {    # industries the engine refuses to value
    'bank', 'banks', 'savings banks', 'credit services', 'insurance',
    'insurance-life', 'insurance-property & casualty', 'insurance-reinsurance',
    'insurance-brokers', 'capital markets', 'financial exchanges',
    'asset management',
}

# Reverse-DCF solver bounds.
IMPLIED_G_BOUNDS = (-0.30, 0.60)
IMPLIED_R_BOUNDS = (0.03, 0.30)
